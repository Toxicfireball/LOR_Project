(function () {
  window.addEventListener("DOMContentLoaded", function () {
    // ── Inputs ─────────────────────────────────────────────────────────────────────
    const scopeEl    = document.getElementById("id_scope");
    const kindEl     = document.getElementById("id_kind");
    const grpSelect  = document.getElementById("id_subclass_group");
    const optsEl     = document.getElementById("id_has_options");
    const activityEl = document.getElementById("id_activity_type");

    // ── Helpers ────────────────────────────────────────────────────────────────────
 function row(name) {
   return document.querySelector(".form-row.field-" + name)
       || document.querySelector("div.fieldBox.field-" + name);
 }    function show(el, on) { if (el) el.style.display = on ? "" : "none"; }
    function currentGmpMode() {
      const r = document.querySelector('input[name="gmp_mode"]:checked');
      return r ? r.value : "";
    }
    function getInherentSpellInline() {
      const el = document.querySelector(".spell-inline");
      return el && (el.classList.contains("inline-group") ? el : (el.closest(".inline-group") || el));
    }
    function getSpellTableInline() {
      return document.querySelector(
        ".spell-slot-inline, " +                 // custom class on Inline group
        "[id$='-spellslotrow_set-group'], " +    // common id pattern for tabular inline
        "#spellslotrow_set-group"                // fallback id
      );
    }

    // Rows we toggle
    const rows = {
      levelRequired:  row("level_required"),  
      subgroup:       row("subclass_group"),
      subclasses:     row("subclasses"),
      tier:           row("tier"),
      masteryRank:    row("mastery_rank"),
      activity:       row("activity_type"),
      formulaTarget:  row("formula_target"),
      formula:        row("formula"),
      uses:           row("uses"),
      action:         row("action_type"),
      damage:         row("damage_type"),
      savingReq:      row("saving_throw_required"),
      savingType:     row("saving_throw_type"),
      savingGran:     row("saving_throw_granularity"),
      basicSuccess:   row("saving_throw_basic_success"),
      basicFailure:   row("saving_throw_basic_failure"),
      normalCritSuccess: row("saving_throw_critical_success"),
      normalSuccess:     row("saving_throw_success"),
      normalFailure:     row("saving_throw_failure"),
      normalCritFailure: row("saving_throw_critical_failure"),
      mmPoints:       row("martial_points_formula"),
      mmAvailable:    row("available_masteries_formula"),
      gmpMode:        row("gmp_mode"),
      profTarget:     row("modify_proficiency_target"),
      profAmount:     row("modify_proficiency_amount"),
      spellList:      row("spell_list"),
      cantrips:       row("cantrips_formula"),
      known:          row("spells_known_formula"),
      prepared:       row("spells_prepared_formula"),
      gainSubskills:  row("gain_subskills"),
      gainResMode:    row("gain_resistance_mode"),
      gainResTypes:   row("gain_resistance_types"),
      gainResAmt:     row("gain_resistance_amount"),
    };

    function toggleAll() {
      const scopeVal = scopeEl ? scopeEl.value : "";
      const scopeNorm = (scopeVal || "").toLowerCase().replace("feature", "feat");

      const kindVal  = kindEl  ? kindEl.value  : "";
      const actVal   = activityEl ? activityEl.value : "";

      // Always re-resolve inline containers (they may or may not be present)
      const inherentInline = getInherentSpellInline();
      const slotsInline    = getSpellTableInline();
  Object.values(rows).forEach(el => el && (el.style.display = "none"));
  if (inherentInline) inherentInline.style.display = "none";
  if (slotsInline)    slotsInline.style.display    = "none";

  // 0.5) Options inline FIRST so it also works in early-return branches
  (function toggleOptionsInlineNow() {
    const optsEl = document.getElementById("id_has_options");
    const optionsInline = getOptionsInline();
    if (optionsInline) {
      optionsInline.style.display = (optsEl && optsEl.checked) ? "" : "none";
    }
  })();


      // Gain Subclass Feature ⇒ only Tier, also hide the Kind row itself
if (scopeNorm  === "gain_subclass_feat") {
  // ← make the umbrella visible so the system type can be chosen
  show(rows.subgroup, true);
  // optional: this chooser doesn’t attach to specific subclasses
  show(rows.subclasses, false);

  const st = grpSelect ? (grpSelect.getAttribute("data-system-type") || "") : "";
  show(rows.levelRequired, false);
  show(rows.tier,        st === "modular_linear");
  show(rows.masteryRank, st === "modular_mastery");

  const kindRow = document.querySelector(".form-row.field-kind");
  if (kindRow) kindRow.style.display = "none";
  return;
}


      // Subclass scaffolding
if (scopeNorm  === "subclass_feat" || scopeNorm  === "subclass_choice") {
  show(rows.subgroup,   true);
  show(rows.subclasses, true);
  // never show level_required for subclass flows
  show(rows.levelRequired, false);
}

      // Tier vs Mastery (only for subclass_feat)
if (scopeNorm  === "subclass_feat" && grpSelect && grpSelect.value) {
  const st = grpSelect.getAttribute("data-system-type") || "";
  show(rows.tier,        st === "modular_linear");
  show(rows.masteryRank, st === "modular_mastery");
}

// If we're NOT in a subclass flow, show level_required normally
if (["subclass_feat", "subclass_choice", "gain_subclass_feat"].indexOf(scopeNorm) === -1) {
  show(rows.levelRequired, true);
}

      // Class trait block
      if (kindVal === "class_trait") {
        show(rows.activity, true);
        show(rows.formulaTarget, true);
        show(rows.formula, true);
        if (actVal === "active") {
          show(rows.uses, true);
          show(rows.action, true);
          show(rows.damage, true);
          show(rows.savingReq, true);
          const saveChk = document.getElementById("id_saving_throw_required");
          if (saveChk && saveChk.checked) {
            show(rows.savingType, true);
            show(rows.savingGran, true);
            const granEl = document.getElementById("id_saving_throw_granularity");
            const gran   = granEl ? granEl.value : "";
            if (gran === "basic") {
              show(rows.basicSuccess, true);
              show(rows.basicFailure, true);
            } else if (gran === "normal") {
              show(rows.normalCritSuccess, true);
              show(rows.normalSuccess, true);
              show(rows.normalFailure, true);
              show(rows.normalCritFailure, true);
            }
          }
        }
      }

      // Gain Resistance
      if (kindVal === "gain_resistance") {
        show(rows.gainResMode,  true);
        show(rows.gainResTypes, true);
        const modeEl = document.getElementById("id_gain_resistance_mode");
        const mode   = modeEl ? modeEl.value : "";
        show(rows.gainResAmt, mode === "reduction");
      }

      // Martial Mastery
      if (kindVal === "martial_mastery") {
        show(rows.mmPoints, true);
        show(rows.mmAvailable, true);
      }

      // Generic Gain/Modify Proficiency
      if (kindVal === "modify_proficiency") {
        show(rows.gmpMode,    true);
        show(rows.profTarget, true);
        const gm = currentGmpMode();
        show(rows.profAmount, gm === "set");
      }

      // Core Proficiency section (only when kind is core_proficiency)
      const coreIds = [
        "id_prof_target_kind",
        "id_armor_group_choice","id_weapon_group_choice",
        "id_armor_item_choice","id_weapon_item_choice",
        "id_gain_proficiency_amount","id_modify_proficiency_amount",
      ];
      coreIds.forEach(id => {
        const el = document.getElementById(id);
        const r  = el && (el.closest(".form-row") || el.closest("div.fieldBox"));
        if (r) r.style.display = (kindVal === "core_proficiency" ? "" : "none");
      });

      // Spell systems
      if (kindVal === "inherent_spell" && inherentInline) {
        inherentInline.style.display = "";
      }
      if (kindVal === "spell_table") {
        show(rows.spellList, true);
        show(rows.cantrips,  true);
        show(rows.known,     true);
        show(rows.prepared,  true);
        if (slotsInline) slotsInline.style.display = "";
      }
  (function toggleOptionsInlineFinal() {
    const optsEl = document.getElementById("id_has_options");
    const optionsInline = getOptionsInline();
    if (optionsInline) {
      optionsInline.style.display = (optsEl && optsEl.checked) ? "" : "none";
    }
  })();
      // Options inline

    }

    // Listeners
    [scopeEl, kindEl, activityEl, optsEl].forEach(el => el && el.addEventListener("change", toggleAll));
    const saveReqEl  = document.getElementById("id_saving_throw_required");
    const saveGranEl = document.getElementById("id_saving_throw_granularity");
    if (saveReqEl)  saveReqEl.addEventListener("change", toggleAll);
    if (saveGranEl) saveGranEl.addEventListener("change", toggleAll);
    const resModeEl = document.getElementById("id_gain_resistance_mode");
    if (resModeEl) resModeEl.addEventListener("change", toggleAll);

// Attach listeners
if (grpSelect) {
  grpSelect.addEventListener("change", function () {
    const map = JSON.parse(this.getAttribute("data-group-types") || "{}");
    this.setAttribute("data-system-type", map[this.value] || "");
    toggleAll(); // repaint after every change
  });

  // ✅ Set the correct system type once on load too (preselect or browser back nav)
  const startMap = JSON.parse(grpSelect.getAttribute("data-group-types") || "{}");
  const startSys = startMap[grpSelect.value] || grpSelect.getAttribute("data-system-type") || "";
  grpSelect.setAttribute("data-system-type", startSys);
}


    // Initial paint
    toggleAll();
  });
})();


// characters/js/classfeature_admin.js
(function () {
  const groupSel = document.querySelector('#id_subclass_group');
  if (!groupSel) return;

  const tierRow  = document.querySelector('.form-row.field-tier');
  const rankRow  = document.querySelector('.form-row.field-mastery_rank');

  function sysType() {
    const map = JSON.parse(groupSel.dataset.groupTypes || '{}');
    return map[groupSel.value] || groupSel.dataset.systemType || '';
  }
  function refresh() {
    const sys = sysType();
    if (tierRow) tierRow.style.display = (sys === 'modular_linear')   ? '' : 'none';
    if (rankRow) rankRow.style.display = (sys === 'modular_mastery') ? '' : 'none';
  }
  groupSel.addEventListener('change', refresh);
  refresh();
})();

function getOptionsInline() {
  // matches the inline group we marked with classes=["featureoption-inline"]
  return document.querySelector(".featureoption-inline")
      || document.querySelector("#featureoption_set-group")
      || document.querySelector("[id$='-featureoption_set-group']");
}

// --- subclass visibility safety net ------------------------------------------
(function () {
  const scopeEl = document.getElementById('id_scope');
  const grpSel  = document.getElementById('id_subclass_group');

  function row(name) {
    return document.querySelector('.form-row.field-' + name)
        || document.querySelector('div.fieldBox.field-' + name);
  }
  function show(el, on) { if (el) el.style.display = on ? '' : 'none'; }
  function sysType() {
    if (!grpSel) return '';
    const map = JSON.parse(grpSel.getAttribute('data-group-types') || '{}');
    const sys = map[grpSel.value] || grpSel.getAttribute('data-system-type') || '';
    grpSel.setAttribute('data-system-type', sys); // keep attribute fresh
    return sys;
  }

  const levelRow     = row('level_required');
  const subgroupRow  = row('subclass_group');
  const subclassesRow= row('subclasses');
  const tierRow      = row('tier');
  const rankRow      = row('mastery_rank');

  function refresh() {
    const S = (scopeEl?.value || '').toLowerCase();

    // tolerate both “…_feat” and “…_feature” spellings
    const isSubclassFeat   = (S === 'subclass_feat'   || S === 'subclass_feature');
    const isSubclassChoice = (S === 'subclass_choice');
    const isGainSubclass   = (S === 'gain_subclass_feat' || S === 'gain_subclass_feature');
    const inSubclassFlow   = isSubclassFeat || isSubclassChoice || isGainSubclass;

    show(subgroupRow,  inSubclassFlow);
    show(subclassesRow, isSubclassFeat || isSubclassChoice);
    show(levelRow,     !inSubclassFlow);

    const sys = sysType();
    const showTier   = (isSubclassFeat || isGainSubclass) && sys === 'modular_linear';
    const showRank   = (isSubclassFeat || isGainSubclass) && sys === 'modular_mastery';
    show(tierRow, showTier);
    show(rankRow, showRank);
  }

  scopeEl && scopeEl.addEventListener('change', refresh);
  grpSel  && grpSel.addEventListener('change', refresh);
  document.addEventListener('DOMContentLoaded', refresh);
  refresh();
})();
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    const groupSel = document.getElementById('id_subclass_group');
    if (!groupSel) return;

    const tierRow = document.querySelector('.form-row.field-tier')
                || document.querySelector('div.fieldBox.field-tier');
    const rankRow = document.querySelector('.form-row.field-mastery_rank')
                || document.querySelector('div.fieldBox.field-mastery_rank');

    function show(el, on) { if (el) el.style.display = on ? '' : 'none'; }

    function currentSystem() {
      // read mapping; if missing, fall back to stored attribute
      let map = {};
      try { map = JSON.parse(groupSel.getAttribute('data-group-types') || '{}'); }
      catch (e) { map = {}; }
      const sys = map[groupSel.value] || groupSel.getAttribute('data-system-type') || '';
      // keep attribute fresh for other scripts
      groupSel.setAttribute('data-system-type', sys);
      return sys;
    }

    function refresh() {
      const sys = currentSystem();
      show(tierRow, sys === 'modular_linear');
      show(rankRow, sys === 'modular_mastery');
    }

    groupSel.addEventListener('change', refresh);
    // initial paint (covers preselected value + back/forward nav)
    refresh();
  });
})();
