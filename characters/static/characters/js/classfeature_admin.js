// characters/static/characters/js/classfeature_admin.js
// ----------------------------------------------------------------
// This script hides/shows the “tier” and “mastery_rank” rows based
// on the current “scope” + “data-system-type” of the selected umbrella.
// It no longer relies on the form to have hidden those fields.
// ----------------------------------------------------------------

(function(){
  // Wait for the DOM to be ready (so that all <div class="form-row …"> wrappers exist)
  window.addEventListener("DOMContentLoaded", function(){
    //
    // ─── 1) Grab all the inputs we care about ───────────────────────────────────────
    //
    // “scope” is the <select id="id_scope"> (e.g. “class_trait”, “subclass_feat”, etc.)
    const scopeEl    = document.getElementById("id_scope");
    // “kind” is <select id="id_kind"> (used elsewhere, not directly for tier logic)
    const kindEl     = document.getElementById("id_kind");
    // “Umbrella” is <select id="id_subclass_group"> (we will read data-system-type from it)
    const grpSelect  = document.getElementById("id_subclass_group");
    // “has_options” is the checkbox <input id="id_has_options"> (used elsewhere)
    const optsEl     = document.getElementById("id_has_options");
    // “activity_type” is <select id="id_activity_type"> (used in the class_trait block)
    const activityEl = document.getElementById("id_activity_type");

    //
    // ─── 2) Helper function: find a “.form-row.field-<fieldName>” wrapper ───────────
    //
    function row(fieldName){
      // e.g. row("tier") → document.querySelector(".form-row.field-tier")
      return document.querySelector(".form-row.field-" + fieldName);
    }

    //
    // ─── 3) Helper to grab the spell-table inline (if kind = "spell_table") ──────────
    //
    function inlineSpellTable(){
      return document.querySelector(".spell-slot-inline");
    }

    //
    // ─── 4) Cache _every_ row we might show/hide ──────────────────────────────────
    //
    const rows = {
      // → Subclass pickers:
      subgroup:       row("subclass_group"),   // <div class="form-row field-subclass_group"> … </div>
      subclasses:     row("subclasses"),       // <div class="form-row field-subclasses"> … </div>

      // → Tier / Mastery fields:
      tier:           row("tier"),             // <div class="form-row field-tier"> … </div>
      masteryRank:    row("mastery_rank"),     // <div class="form-row field-mastery_rank"> … </div>

      // → class_trait / formula block:
      activity:       row("activity_type"),
      formulaTarget:  row("formula_target"),
      formula:        row("formula"),
      uses:           row("uses"),
      action:         row("action_type"),
      damage:         row("damage_type"),

      // → saving-throw rows:
      savingReq:          row("saving_throw_required"),
      savingType:         row("saving_throw_type"),
      savingGran:         row("saving_throw_granularity"),
      basicSuccess:       row("saving_throw_basic_success"),
      basicFailure:       row("saving_throw_basic_failure"),
      normalCritSuccess:  row("saving_throw_critical_success"),
      normalSuccess:      row("saving_throw_success"),
      normalFailure:      row("saving_throw_failure"),
      normalCritFailure:  row("saving_throw_critical_failure"),

      // → modify_proficiency rows:
      profTarget:   row("modify_proficiency_target"),
      profAmount:   row("modify_proficiency_amount"),

      // → spell_table rows:
      cantrips:     row("cantrips_formula"),
      known:        row("spells_known_formula"),
      prepared:     row("spells_prepared_formula"),
      slots:        inlineSpellTable(),

      // → “Has Options?” inline block (the M2M widget area):
      optionsInline: document.getElementById("options-group"),
    };

    //
    // ─── 5) The main show/hide function ──────────────────────────────────────────────
    //
    function toggleAll(){
      // Read the current values of “scope”, “kind”, and “activity_type”
      const scopeVal = scopeEl    ? scopeEl.value    : "";
      const kindVal  = kindEl     ? kindEl.value     : "";
      const actVal   = activityEl ? activityEl.value : "";

      // 5a) First, hide _every_ row (so we start from a clean slate)
      Object.values(rows).forEach(el => {
        if (el) {
          el.style.display = "none";
        }
      });

      //
      // 5b) If scope is ANY of the three “subclass” flows,
      //     un-hide “subclass_group” (Umbrella) + “subclasses” (M2M) immediately.
      //
      if (
        scopeVal === "subclass_feat" ||
        scopeVal === "subclass_choice" ||
        scopeVal === "gain_subclass_feat"
      ) {
        if (rows.subgroup)   rows.subgroup.style.display   = "";
        if (rows.subclasses) rows.subclasses.style.display = "";
      }

      //
      // 5c) ONLY IF scope is “subclass_feat” (or “gain_subclass_feat”) 
      //     AND the umbrella‐select has a value, THEN decide between 
      //     tier vs. mastery_rank based on data-system-type:
      //
      if (
        (scopeVal === "subclass_feat" || scopeVal === "gain_subclass_feat")
        && grpSelect && grpSelect.value
      ) {
        // read the injected data‐system‐type attribute (must have been added by Python)
        const systemType = grpSelect.getAttribute("data-system-type") || "";

        if (systemType === "modular_linear") {
          // Show Tier row, hide Mastery Rank row
          if (rows.tier)        rows.tier.style.display        = "";
          if (rows.masteryRank) rows.masteryRank.style.display = "none";
        }
        else if (systemType === "modular_mastery") {
          // Show Mastery Rank row, hide Tier row
          if (rows.masteryRank) rows.masteryRank.style.display = "";
          if (rows.tier)        rows.tier.style.display        = "none";
        }
        else {
          // Either “linear” or empty → hide both tier & mastery_rank
          if (rows.tier)        rows.tier.style.display        = "none";
          if (rows.masteryRank) rows.masteryRank.style.display = "none";
        }
      }

      //
      // 5d) If “kind” = “class_trait”, show the formula / uses / action / damage / saving-throw block:
      //
      if (kindVal === "class_trait") {
        if (rows.activity)      rows.activity.style.display      = "";
        if (rows.formulaTarget) rows.formulaTarget.style.display = "";
        if (rows.formula)       rows.formula.style.display       = "";

        // If “activity = active,” show uses / action_type / damage_type / saving-throw_required
        if (actVal === "active") {
          if (rows.uses)      rows.uses.style.display      = "";
          if (rows.action)    rows.action.style.display    = "";
          if (rows.damage)    rows.damage.style.display    = "";
          if (rows.savingReq) rows.savingReq.style.display = "";

          const saveChk = document.getElementById("id_saving_throw_required");
          if (saveChk && saveChk.checked) {
            if (rows.savingType)       rows.savingType.style.display       = "";
            if (rows.savingGran)       rows.savingGran.style.display        = "";
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

      //
      // 5e) If “kind” = “modify_proficiency”, show those two rows:
      //
      if (kindVal === "modify_proficiency") {
        if (rows.profTarget) rows.profTarget.style.display = "";
        if (rows.profAmount) rows.profAmount.style.display = "";
      }

      //
      // 5f) If “kind” = “spell_table”, show the spell-table rows:
      //
      if (kindVal === "spell_table") {
        if (rows.cantrips) rows.cantrips.style.display = "";
        if (rows.known)    rows.known.style.display    = "";
        if (rows.prepared) rows.prepared.style.display = "";
        if (rows.slots)    rows.slots.style.display    = "";
      }

      //
      // 5g) If “has_options” (the checkbox) is checked, show the options inline:
      //
      if (optsEl && optsEl.checked) {
        if (rows.optionsInline) rows.optionsInline.style.display = "";
      }
    } // end of toggleAll()

    //
    // ─── 6) Wire up change-listeners for any field that can affect our visibility ─
    //
    [ scopeEl, kindEl, activityEl, optsEl ].forEach(el => {
      if (el) el.addEventListener("change", toggleAll);
    });
    const saveReqEl  = document.getElementById("id_saving_throw_required");
    const saveGranEl = document.getElementById("id_saving_throw_granularity");
    if (saveReqEl)  saveReqEl.addEventListener("change", toggleAll);
    if (saveGranEl) saveGranEl.addEventListener("change", toggleAll);

    //
    // ─── 7) Whenever “scope” or “subclass_group” changes, _reload_ with new GET params
    // This is what allows Django’s Python side to re-inject the correct data-system-type.
    //
    function reloadWithParams() {
      const baseURL  = window.location.href.split("?")[0];
      const scopeVal = encodeURIComponent(scopeEl.value || "");
      const grpVal   = encodeURIComponent(grpSelect.value || "");
      window.location.href = baseURL
                          + "?scope=" + scopeVal
                          + "&subclass_group=" + grpVal;
    }

    // Attach reload to “scope” → changing the dropdown forces a full reload
    if (scopeEl) {
      scopeEl.addEventListener("change", reloadWithParams);
    }
    // Attach reload to “umbrella” → changing the Umbrella select forces a full reload
    if (grpSelect) {
      grpSelect.addEventListener("change", reloadWithParams);
    }

    //
    // ─── 8) Finally, run toggleAll() once on initial page load ───────────────────────
    //
    toggleAll();
  });
})();
