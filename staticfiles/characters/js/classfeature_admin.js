// characters/static/characters/js/classfeature_admin.js

window.addEventListener("DOMContentLoaded", function(){
  const ftype              = document.getElementById("id_feature_type");
  const activitySelect     = document.getElementById("id_activity_type");
  const hasOptionsCheckbox = document.getElementById("id_has_options");

  const subRow           = document.querySelector(".form-row.field-subclasses");
  const grpRow           = document.querySelector(".form-row.field-subclass_group");

  const activityRow      = document.querySelector(".form-row.field-activity_type");
  const usesRow          = document.querySelector(".form-row.field-uses");
  const formulaRow       = document.querySelector(".form-row.field-formula");
  const formulaTargetRow = document.querySelector(".form-row.field-formula_target");

  const canRow           = document.querySelector(".form-row.field-cantrips_formula");
  const knownRow         = document.querySelector(".form-row.field-spells_known_formula");
  const slotGrp          = document.getElementById("spell_slot_rows-group");

  const profTargetRow    = document.querySelector(".form-row.field-modify_proficiency_target");
  const profAmtRow       = document.querySelector(".form-row.field-modify_proficiency_amount");

  // your options inline wrapper
  const optionsGrp       = document.getElementById("options-group");

  function toggleAll(){
    const v = ftype.value;
    const isTraitChoice = (v==="class_trait" || v==="subclass_choice");
    const isTable       = (v==="spell_table");
    const isModify      = (v==="modify_proficiency");

    // 1) hide everything
    [
      subRow, grpRow,
      activityRow, usesRow,
      formulaRow, formulaTargetRow,
      canRow, knownRow, slotGrp,
      profTargetRow, profAmtRow
    ].forEach(el => el && (el.style.display="none"));

    // always hide FeatureOption inline
    optionsGrp && (optionsGrp.style.display="none");

    // 2) class_trait / subclass_choice
    if (isTraitChoice) {
      activityRow.style.display      = "";
      formulaRow.style.display       = "";
      formulaTargetRow.style.display = "";
      if (activitySelect.value === "active") {
        usesRow.style.display = "";
      }
      subRow.style.display = "";
      grpRow.style.display = "";

    // 3) spell_table
    } else if (isTable) {
      canRow.style.display   = "";
      knownRow.style.display = "";
      slotGrp.style.display  = "";

    // 4) modify_proficiency
    } else if (isModify) {
      profTargetRow.style.display = "";
      profAmtRow.style.display    = "";
    }

    // 5) FeatureOption inline only if has_options
    if (optionsGrp && hasOptionsCheckbox.checked) {
      optionsGrp.style.display = "";
    }
  }

  ftype.addEventListener("change", toggleAll);
  activitySelect.addEventListener("change", toggleAll);
  hasOptionsCheckbox.addEventListener("change", toggleAll);

  // initial
  toggleAll();
});
