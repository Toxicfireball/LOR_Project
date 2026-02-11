# characters/audit_signals.py
from __future__ import annotations

from functools import lru_cache

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete, m2m_changed
from django.dispatch import receiver

from .audit_context import get_current_user, get_current_path, set_before_snapshot, pop_before_snapshot
from .models import AuditTrackedModel, ModelChangeLog


AUDIT_EXCLUDE_MODEL_NAMES = {
    "audittrackedmodel",
    "changecategory",
    "modelchangelog",
}


def _is_audit_model(sender: type[models.Model]) -> bool:
    return sender._meta.model_name in AUDIT_EXCLUDE_MODEL_NAMES


def _snapshot_key(sender: type[models.Model], pk: int) -> tuple[str, str, int]:
    return (sender._meta.app_label, sender._meta.model_name, int(pk))


@lru_cache(maxsize=512)
def _tracked_cfg_for_ct_id(ct_id: int):
    try:
        tm = AuditTrackedModel.objects.get(content_type_id=ct_id, enabled=True)
    except AuditTrackedModel.DoesNotExist:
        return None

    include = tm.include_fields or None
    exclude = set(tm.exclude_fields or [])
    return {
        "track_creates": tm.track_creates,
        "track_updates": tm.track_updates,
        "track_deletes": tm.track_deletes,
        "track_m2m": tm.track_m2m,
        "include_fields": include,
        "exclude_fields": exclude,
    }


@receiver(post_save, sender=AuditTrackedModel)
@receiver(post_delete, sender=AuditTrackedModel)
def _clear_tracking_cache(*args, **kwargs):
    _tracked_cfg_for_ct_id.cache_clear()


def _iter_concrete_fields(sender: type[models.Model], cfg) -> list[models.Field]:
    fields = []
    for f in sender._meta.get_fields():
        if not isinstance(f, models.Field):
            continue
        if not f.concrete or f.auto_created:
            continue
        if f.many_to_many:
            continue
        if f.primary_key:
            continue
        fields.append(f)

    include = cfg["include_fields"]
    exclude = cfg["exclude_fields"]

    if include:
        fields = [f for f in fields if f.name in include]
    fields = [f for f in fields if f.name not in exclude]
    return fields


def _serialize_instance(instance: models.Model, fields: list[models.Field]) -> dict:
    data = {}
    for f in fields:
        # FK values should use attname (field_id)
        if f.is_relation and f.many_to_one:
            data[f.name] = getattr(instance, f.attname, None)
        else:
            val = getattr(instance, f.name, None)
            # keep JSON-serializable primitives; fallback to str for unknowns
            if isinstance(val, (str, int, float, bool)) or val is None or isinstance(val, (list, dict)):
                data[f.name] = val
            else:
                data[f.name] = str(val)
    return data


def _diff(before: dict | None, after: dict | None) -> dict:
    before = before or {}
    after = after or {}
    out = {}
    keys = set(before.keys()) | set(after.keys())
    for k in sorted(keys):
        if before.get(k) != after.get(k):
            out[k] = {"before": before.get(k), "after": after.get(k)}
    return out


@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    if sender._meta.app_label != "characters":
        return
    if _is_audit_model(sender):
        return
    if instance.pk is None:
        return

    ct_id = ContentType.objects.get_for_model(sender).id
    cfg = _tracked_cfg_for_ct_id(ct_id)
    if not cfg or not cfg["track_updates"]:
        return

    fields = _iter_concrete_fields(sender, cfg)
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    before = _serialize_instance(old, fields)
    set_before_snapshot(_snapshot_key(sender, instance.pk), before)


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    if sender._meta.app_label != "characters":
        return
    if _is_audit_model(sender):
        return

    ct = ContentType.objects.get_for_model(sender)
    cfg = _tracked_cfg_for_ct_id(ct.id)
    if not cfg:
        return

    user = get_current_user()
    path = get_current_path()
    obj_repr = str(instance)[:200]

    if created:
        if not cfg["track_creates"]:
            return
        fields = _iter_concrete_fields(sender, cfg)
        after = _serialize_instance(instance, fields)
        changes = {k: {"before": None, "after": v} for k, v in after.items()}
        ModelChangeLog.objects.create(
            content_type=ct,
            object_id=int(instance.pk),
            object_repr=obj_repr,
            action=ModelChangeLog.ACTION_CREATE,
            changed_by=user if getattr(user, "is_authenticated", False) else None,
            request_path=path,
            changes=changes,
        )
        return

    if not cfg["track_updates"]:
        return

    fields = _iter_concrete_fields(sender, cfg)
    after = _serialize_instance(instance, fields)
    before = pop_before_snapshot(_snapshot_key(sender, instance.pk))
    changes = _diff(before, after)
    if not changes:
        return

    ModelChangeLog.objects.create(
        content_type=ct,
        object_id=int(instance.pk),
        object_repr=obj_repr,
        action=ModelChangeLog.ACTION_UPDATE,
        changed_by=user if getattr(user, "is_authenticated", False) else None,
        request_path=path,
        changes=changes,
    )


@receiver(pre_delete)
def audit_pre_delete(sender, instance, **kwargs):
    if sender._meta.app_label != "characters":
        return
    if _is_audit_model(sender):
        return
    if instance.pk is None:
        return

    ct_id = ContentType.objects.get_for_model(sender).id
    cfg = _tracked_cfg_for_ct_id(ct_id)
    if not cfg or not cfg["track_deletes"]:
        return

    fields = _iter_concrete_fields(sender, cfg)
    before = _serialize_instance(instance, fields)
    set_before_snapshot(_snapshot_key(sender, instance.pk), before)


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    if sender._meta.app_label != "characters":
        return
    if _is_audit_model(sender):
        return
    if instance.pk is None:
        return

    ct = ContentType.objects.get_for_model(sender)
    cfg = _tracked_cfg_for_ct_id(ct.id)
    if not cfg or not cfg["track_deletes"]:
        return

    user = get_current_user()
    path = get_current_path()
    obj_repr = str(instance)[:200]

    before = pop_before_snapshot(_snapshot_key(sender, instance.pk))
    changes = {k: {"before": v, "after": None} for k, v in (before or {}).items()}

    ModelChangeLog.objects.create(
        content_type=ct,
        object_id=int(instance.pk),
        object_repr=obj_repr,
        action=ModelChangeLog.ACTION_DELETE,
        changed_by=user if getattr(user, "is_authenticated", False) else None,
        request_path=path,
        changes=changes,
    )


@receiver(m2m_changed)
def audit_m2m(sender, instance, action, reverse, model, pk_set, **kwargs):
    # This fires for every M2M everywhere; keep it extremely cheap.
    if instance._meta.app_label != "characters":
        return
    if action not in {"post_add", "post_remove", "post_clear"}:
        return

    ct = ContentType.objects.get_for_model(instance.__class__)
    cfg = _tracked_cfg_for_ct_id(ct.id)
    if not cfg or not cfg["track_m2m"]:
        return

    # Best-effort: identify which M2M field this through model belongs to.
    field_name = None
    for f in instance._meta.many_to_many:
        if f.remote_field.through == sender:
            field_name = f.name
            break
    if not field_name:
        return

    user = get_current_user()
    path = get_current_path()

    ModelChangeLog.objects.create(
        content_type=ct,
        object_id=int(instance.pk),
        object_repr=str(instance)[:200],
        action=ModelChangeLog.ACTION_M2M,
        changed_by=user if getattr(user, "is_authenticated", False) else None,
        request_path=path,
        changes={
            field_name: {
                "before": None,
                "after": {"action": action, "pks": sorted(list(pk_set)) if pk_set else []},
            }
        },
    )
