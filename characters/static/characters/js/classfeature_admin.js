// characters/static/characters/js/classfeature_admin.js
// ----------------------------------------------------------------
// This script hides/shows the “tier” and “mastery_rank” rows based
// on the current “scope” + “data-system-type” of the selected umbrella.
// It no longer relies on the form to have hidden those fields.
// ----------------------------------------------------------------

(function(){
  window.addEventListener("DOMContentLoaded", function(){
    //
    // ─── 1) Grab all the inputs we care about ───────────────────────────────────────
    //
    const scopeEl    = document.getElementById("id_scope");
    const kindEl     = document.getElementById("id_kind");
    const grpSelect  = document.getElementById("id_subclass_group");
    const optsEl     = document.getElementById("id_has_options");
    const activityEl = document.getElementById("id_activity_type");

    //
    // ─── 2) Helper function: find a “.form-row.field-<fieldName>” wrapper ───────────
    //
    function row(fieldName){
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

        const spellInline = (() => {
      const fs = document.querySelector("fieldset.spell-inline");
      return fs && fs.closest(".inline-group");
    })();
    const rows = {
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
      optionsInline: document.getElementById("options-group"),
      savingReq:          row("saving_throw_required"),
      savingType:         row("saving_throw_type"),
      savingGran:         row("saving_throw_granularity"),
      basicSuccess:       row("saving_throw_basic_success"),
      basicFailure:       row("saving_throw_basic_failure"),
      normalCritSuccess:  row("saving_throw_critical_success"),
      normalSuccess:      row("saving_throw_success"),
      normalFailure:      row("saving_throw_failure"),
      normalCritFailure:  row("saving_throw_critical_failure"),

      profTarget:   row("modify_proficiency_target"),
      profAmount:   row("modify_proficiency_amount"),

      cantrips:     row("cantrips_formula"),
      known:        row("spells_known_formula"),
      prepared:     row("spells_prepared_formula"),
      slots:        inlineSpellTable(),
      spellList:    row("spell_list"),
      gainSubskills: row("gain_subskills"),
      optionsInline: document.getElementById("options-group"),
      gainResMode:  row("gain_resistance_mode"),
      gainResTypes: row("gain_resistance_types"),
      gainResAmt:   row("gain_resistance_amount"),
  };

    //
    // ─── 5) The main show/hide function ──────────────────────────────────────────────
    //
    function toggleAll(){

      const scopeVal = scopeEl ? scopeEl.value : "";
      const kindVal  = kindEl  ? kindEl.value  : "";
      const actVal   = activityEl ? activityEl.value : "";
        //
  // 5i) Show/hide the SpellInline when kind="inherent_spell"
   Object.values(rows).forEach(el => el && (el.style.display = "none"));
  //


if (kindVal === "gain_resistance") {
  // always show mode selector + type checkboxes
  if (rows.gainResMode)  rows.gainResMode.style.display  = "";
  if (rows.gainResTypes) rows.gainResTypes.style.display = "";

  // only show “amount” when in flat‐reduction mode
  const mode = document.getElementById("id_gain_resistance_mode").value;
  if (rows.gainResAmt) {
    rows.gainResAmt.style.display = (mode === "reduction" ? "" : "none");
  }
}
if (rows.spellInline) rows.spellInline.style.display = "none";


  
  if (spellInline) {
    spellInline.style.display = kindVal === "inherent_spell" ? "" : "none";
  }




      // ─── 5a) Special short-circuit: if “Gain Subclass Feature” is selected,
      //            hide every row _except_ “tier” (and leave Code/Name/Description visible).
     if (scopeVal === "gain_subclass_feat") {
       // Hide all cached rows:
       Object.values(rows).forEach(el => {
         if (el) { el.style.display = "none"; }
       });
       // Also explicitly hide the “kind” row wrapper:
       const kindRow = document.querySelector(".form-row.field-kind");
       if (kindRow) { kindRow.style.display = "none"; }
       // Un-hide only the “tier” row:
       if (rows.tier) { rows.tier.style.display = ""; }
       // Done—skip all other logic
       return;
     }

  if (kindVal === "gain_proficiency") {
    if (rows.gainSubskills) rows.gainSubskills.style.display = "";
    if (rows.profTarget)   rows.profTarget.style.display   = "";
    if (rows.profAmount)   rows.profAmount.style.display   = "";
  }
      if (
        scopeVal === "subclass_feat" ||
        scopeVal === "subclass_choice"
      ) {
        if (rows.subgroup)   rows.subgroup.style.display   = "";
        if (rows.subclasses) rows.subclasses.style.display = "";
      }

      //
      // ─── 5d) If scope is “subclass_feat” AND an umbrella is chosen, decide Tier vs. Mastery ─
      //
      if (
        scopeVal === "subclass_feat" &&
        grpSelect && grpSelect.value
      ) {
        const systemType = grpSelect.getAttribute("data-system-type") || "";
        if (systemType === "modular_linear") {
          if (rows.tier)        rows.tier.style.display        = "";
          if (rows.masteryRank) rows.masteryRank.style.display = "none";
        }
        else if (systemType === "modular_mastery") {
          if (rows.masteryRank) rows.masteryRank.style.display = "";
          if (rows.tier)        rows.tier.style.display        = "none";
        }
        else {
          if (rows.tier)        rows.tier.style.display        = "none";
          if (rows.masteryRank) rows.masteryRank.style.display = "none";
        }
      }

      //
      // ─── 5e) If kind = “class_trait”, show the formula/uses/action/damage/saving-throw fields ─
      //
      if (kindVal === "class_trait") {
        if (rows.activity)      rows.activity.style.display      = "";
        if (rows.formulaTarget) rows.formulaTarget.style.display = "";
        if (rows.formula)       rows.formula.style.display       = "";

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
      // ─── 5f) If kind = “modify_proficiency”, show those two rows ─────────────────
      //
      if (kindVal === "modify_proficiency") {
        if (rows.profTarget) rows.profTarget.style.display = "";
        if (rows.profAmount) rows.profAmount.style.display = "";
      }

      //
      // ─── 5g) If kind = “spell_table”, show the spell-table rows ───────────────────
      //
      if (kindVal === "spell_table") {
        if (rows.spellList) rows.spellList.style.display = "";
        if (rows.cantrips)  rows.cantrips.style.display  = "";
        if (rows.known)     rows.known.style.display     = "";
        if (rows.prepared)  rows.prepared.style.display  = "";
        if (rows.slots)     rows.slots.style.display     = "";
      }

      //
      // ─── 5h) If “Has Options?” is checked, show the options inline ──────────────────
      //
      if (optsEl && optsEl.checked) {
        if (rows.optionsInline) rows.optionsInline.style.display = "";
      }
    } // end of toggleAll()

    //
    // ─── 6) Wire up change-listeners for any field that can affect visibility ──────
    //
    [ scopeEl, kindEl, activityEl, optsEl ].forEach(el => {
      if (el) el.addEventListener("change", toggleAll);
    });
    const saveReqEl  = document.getElementById("id_saving_throw_required");
    const saveGranEl = document.getElementById("id_saving_throw_granularity");
    if (saveReqEl)  saveReqEl.addEventListener("change", toggleAll);
    if (saveGranEl) saveGranEl.addEventListener("change", toggleAll);
// ─── Also re-run when user flips Resistance vs Reduction ────────────────
const resModeEl = document.getElementById("id_gain_resistance_mode");
if (resModeEl) resModeEl.addEventListener("change", toggleAll);

    //
    // ─── 7) Whenever “scope” or “subclass_group” changes, reload with new GET params ─
    //

    //
    // ─── 8) Run toggleAll() once on initial page load ────────────────────────────────
    //
    toggleAll();
  });
})();


