window.addEventListener("DOMContentLoaded", function(){
  const ftype               = document.getElementById("id_feature_type");
  const activitySelect      = document.getElementById("id_activity_type");
  const hasOptionsCheckbox  = document.getElementById("id_has_options");
  const subRow              = document.querySelector(".form-row.field-subclasses");
  const grpRow              = document.querySelector(".form-row.field-subclass_group");
  const activityRow         = document.querySelector(".form-row.field-activity_type");
  const usesRow             = document.querySelector(".form-row.field-uses");
  const formulaRow          = document.querySelector(".form-row.field-formula");
  const formulaTargetRow    = document.querySelector(".form-row.field-formula_target");
  const canRow              = document.querySelector(".form-row.field-cantrips_formula");
  const knownRow            = document.querySelector(".form-row.field-spells_known_formula");
  const slotGrp             = document.getElementById("spell_slot_rows-group");
  const profTargetRow       = document.querySelector(".form-row.field-modify_proficiency_target");
  const profAmtRow          = document.querySelector(".form-row.field-modify_proficiency_amount");
  const optionsGrp          = document.getElementById("options-group");
  const umbrella            = document.getElementById("id_subclass_group");

  function toggleAll(){
    const v       = ftype.value;
    const isTrait = (v === "class_trait");
    const isChoice= (v === "subclass_choice");
    const isFeat  = (v === "subclass_feat");
    const isTable = (v === "spell_table");
    const isMod   = (v === "modify_proficiency");

    // 1) hide everything
    [
      subRow, grpRow,
      activityRow, usesRow,
      formulaRow, formulaTargetRow,
      canRow, knownRow, slotGrp,
      profTargetRow, profAmtRow
    ].forEach(el => el && (el.style.display = "none"));
    optionsGrp && (optionsGrp.style.display = "none");

    // 2) class_trait
    if (isTrait) {
      activityRow.style.display      = "";
      formulaRow.style.display       = "";
      formulaTargetRow.style.display = "";
      if (activitySelect.value === "active") {
        usesRow.style.display = "";
      }
    }

    // 3) subclass_choice
    if (isChoice) {
      activityRow.style.display      = "";
      formulaRow.style.display       = "";
      formulaTargetRow.style.display = "";
      if (activitySelect.value === "active") {
        usesRow.style.display = "";
      }
      grpRow.style.display = "";
      subRow.style.display = "";
    }

    // 4) subclass_feat
    if (isFeat) {
      grpRow.style.display = "";
      subRow.style.display = "";
    }

    // 5) spell_table
    if (isTable) {
      canRow.style.display  = "";
      knownRow.style.display= "";
      slotGrp.style.display = "";
    }

    // 6) modify_proficiency
    if (isMod) {
      profTargetRow.style.display = "";
      profAmtRow.style.display    = "";
    }

    // 7) feature options inline
    if (optionsGrp && hasOptionsCheckbox.checked) {
      optionsGrp.style.display = "";
    }
  }

  // listeners
  ftype.addEventListener("change", toggleAll);
  activitySelect.addEventListener("change", toggleAll);
  hasOptionsCheckbox.addEventListener("change", toggleAll);

  // auto-submit on umbrella change so server can refill the subclass queryset
  if (umbrella) {
    umbrella.addEventListener("change", ()=> umbrella.form.submit());
  }

  // initial run
  toggleAll();
});
