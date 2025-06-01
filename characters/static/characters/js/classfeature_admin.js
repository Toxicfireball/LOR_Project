// characters/static/characters/js/classfeature_admin.js
// ----------------------------------------------------------------
// Revised toggle logic to ensure "kind" is never auto‐hidden,
// and to only show "tier" or "mastery_rank" under exactly the
// two subclass‐related scopes + a valid data‐system‐type.
// ----------------------------------------------------------------

(function(){
  window.addEventListener("DOMContentLoaded", function(){
    // 1) Grab all relevant inputs
    const scopeEl    = document.getElementById("id_scope");
    const kindEl     = document.getElementById("id_kind");
    const grpSelect  = document.getElementById("id_subclass_group");
    const optsEl     = document.getElementById("id_has_options");
    const activityEl = document.getElementById("id_activity_type");

    // Helper to select a ".form-row.field-<fieldName>" row
    function row(fieldName){
      return document.querySelector(".form-row.field-" + fieldName);
    }
    // Helper to grab the “spell-slot-inline” element
    function inlineSpellTable(){
      return document.querySelector(".spell-slot-inline");
    }

    // 2) Cache every single row that we might show/hide
    const rows = {
      // ─── subclass pickers ───────────────────────────────────
      subgroup:       row("subclass_group"),   // the "Umbrella" select
      subclasses:     row("subclasses"),       // the "Chosen Subclasses" multiselect

      // ─── Tier / Mastery fields (no level_required/min_level) ──
      tier:           row("tier"),
      masteryRank:    row("mastery_rank"),

      // ─── class_trait / formula block ──────────────────────────
      activity:      row("activity_type"),
      formulaTarget: row("formula_target"),
      formula:       row("formula"),
      uses:          row("uses"),
      action:        row("action_type"),
      damage:        row("damage_type"),

      // ─── saving throw rows ────────────────────────────────────
      savingReq:          row("saving_throw_required"),
      savingType:         row("saving_throw_type"),
      savingGran:         row("saving_throw_granularity"),
      basicSuccess:       row("saving_throw_basic_success"),
      basicFailure:       row("saving_throw_basic_failure"),
      normalCritSuccess:  row("saving_throw_critical_success"),
      normalSuccess:      row("saving_throw_success"),
      normalFailure:      row("saving_throw_failure"),
      normalCritFailure:  row("saving_throw_critical_failure"),

      // ─── modify_proficiency rows ─────────────────────────────
      profTarget:   row("modify_proficiency_target"),
      profAmount:   row("modify_proficiency_amount"),

      // ─── spell_table rows ────────────────────────────────────
      cantrips:     row("cantrips_formula"),
      known:        row("spells_known_formula"),
      prepared:     row("spells_prepared_formula"),
      slots:        inlineSpellTable(),

      // ─── "Has Options?" inline ────────────────────────────────
      optionsInline: document.getElementById("options-group"),
    };

    // 3) The main show/hide function
    function toggleAll(){
      // read current values
      const scopeVal = scopeEl    ? scopeEl.value    : "";
      const kindVal  = kindEl     ? kindEl.value     : "";
      const actVal   = activityEl ? activityEl.value : "";

      // 3a) First, hide everything
      Object.values(rows).forEach(el=>{
        if (el) el.style.display = "none";
      });
      // Notice: We NO LONGER hide "kind" unconditionally.  "kind" should remain visible
      // unless you have further custom logic.  The user said they want "kind" visible
      // even on subclass features, so we remove that forced‐hide rule.

      // 3b) Show Umbrella ("subclass_group") + "subclasses" IF scope is any subclass flow
      if (scopeVal === "subclass_feat"
          || scopeVal === "subclass_choice"
          || scopeVal === "gain_subclass_feat")
      {
        if (rows.subgroup)   rows.subgroup.style.display   = "";
        if (rows.subclasses) rows.subclasses.style.display = "";
      }

      // 3c) ONLY if scope is "subclass_feat" OR "gain_subclass_feat", AND an umbrella is chosen,
      //       read that umbrella's data‐system‐type and show Tier or Mastery accordingly.
      if ((scopeVal === "subclass_feat" || scopeVal === "gain_subclass_feat")
          && grpSelect && grpSelect.value)
      {
        const systemType = grpSelect.getAttribute("data-system-type");
        if (systemType === "modular_linear") {
          if (rows.tier)        rows.tier.style.display        = "";
          if (rows.masteryRank) rows.masteryRank.style.display = "none";
        }
        else if (systemType === "modular_mastery") {
          if (rows.masteryRank) rows.masteryRank.style.display = "";
          if (rows.tier)        rows.tier.style.display        = "none";
        }
        else {
          // SYSTEM_LINEAR or empty → hide both
          if (rows.tier)        rows.tier.style.display        = "none";
          if (rows.masteryRank) rows.masteryRank.style.display = "none";
        }
      }

      // 3d) If Kind = "class_trait", show the formula/uses block
      if (kindVal === "class_trait") {
        if (rows.activity)      rows.activity.style.display      = "";
        if (rows.formulaTarget) rows.formulaTarget.style.display = "";
        if (rows.formula)       rows.formula.style.display       = "";

        if (actVal === "active") {
          if (rows.uses)       rows.uses.style.display       = "";
          if (rows.action)     rows.action.style.display     = "";
          if (rows.damage)     rows.damage.style.display     = "";
          if (rows.savingReq)  rows.savingReq.style.display  = "";

          const saveChk = document.getElementById("id_saving_throw_required");
          if (saveChk && saveChk.checked) {
            if (rows.savingType)        rows.savingType.style.display        = "";
            if (rows.savingGran)        rows.savingGran.style.display        = "";
            const gran = document.getElementById("id_saving_throw_granularity").value;
            if (gran === "basic") {
              if (rows.basicSuccess)  rows.basicSuccess.style.display  = "";
              if (rows.basicFailure)  rows.basicFailure.style.display  = "";
            } else if (gran === "normal") {
              if (rows.normalCritSuccess) rows.normalCritSuccess.style.display = "";
              if (rows.normalSuccess)     rows.normalSuccess.style.display     = "";
              if (rows.normalFailure)     rows.normalFailure.style.display     = "";
              if (rows.normalCritFailure) rows.normalCritFailure.style.display = "";
            }
          }
        }
      }

      // 3e) If Kind = "modify_proficiency", show those two fields
      if (kindVal === "modify_proficiency") {
        if (rows.profTarget) rows.profTarget.style.display = "";
        if (rows.profAmount) rows.profAmount.style.display = "";
      }

      // 3f) If Kind = "spell_table", show the spell-table rows
      if (kindVal === "spell_table") {
        if (rows.cantrips) rows.cantrips.style.display = "";
        if (rows.known)    rows.known.style.display    = "";
        if (rows.prepared) rows.prepared.style.display = "";
        if (rows.slots)    rows.slots.style.display    = "";
      }

      // 3g) If “Has Options?” is checked, show the options inline
      if (optsEl && optsEl.checked) {
        if (rows.optionsInline) rows.optionsInline.style.display = "";
      }
    }

    // 4) Wire up change‐listeners
    [ scopeEl, kindEl, activityEl, optsEl ].forEach(el=>{
      if (el) el.addEventListener("change", toggleAll);
    });
    const saveReqEl  = document.getElementById("id_saving_throw_required");
    const saveGranEl = document.getElementById("id_saving_throw_granularity");
    if (saveReqEl)  saveReqEl.addEventListener("change", toggleAll);
    if (saveGranEl) saveGranEl.addEventListener("change", toggleAll);

    // 5) Whenever the umbrella (<select id="id_subclass_group">) changes,
    //    force a GET reload so Django can re‐render with the new data-system-type.
   function reloadWithParams() {
     const baseURL  = window.location.href.split("?")[0];
     const scopeVal = encodeURIComponent(scopeEl.value || "");
     const grpVal   = encodeURIComponent(grpSelect.value || "");
     window.location.href = baseURL
                         + "?scope=" + scopeVal
                         + "&subclass_group=" + grpVal;
   }

   if (grpSelect) {
     // when “Scope” changes, reload
     scopeEl.addEventListener("change", reloadWithParams);
     // when “Umbrella” changes, reload
     grpSelect.addEventListener("change", reloadWithParams);
   }

    // 6) Run toggleAll() once on page‐load
    toggleAll();
  });
})();
