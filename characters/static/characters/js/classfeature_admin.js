// characters/static/characters/js/classfeature_admin.js

window.addEventListener("DOMContentLoaded", function(){
  const ftype    = document.getElementById("id_feature_type");
  const subRow   = document.querySelector(".form-row.field-subclasses");
  const grpRow   = document.querySelector(".form-row.field-subclass_group");
  const canRow   = document.querySelector(".form-row.field-cantrips_formula");
  const knownRow = document.querySelector(".form-row.field-spells_known_formula");
  const slotGrp  = document.getElementById("spell_slot_rows-group");

  // the two new rows for our "Modify Proficiency" fields:
  const profTargetRow = document.querySelector(".form-row.field-modify_proficiency_target");
  const profAmtRow    = document.querySelector(".form-row.field-modify_proficiency_amount");

  function toggleAll(){
    const v = ftype.value;
    const showSubs      = (v === "subclass_feat" || v === "subclass_choice");
    const showTable     = (v === "spell_table");
    const showModify    = (v === "modify_proficiency");

    if (subRow)    subRow.style.display    = showSubs   ? "" : "none";
    if (grpRow)    grpRow.style.display    = showSubs   ? "" : "none";

    if (canRow)    canRow.style.display    = showTable  ? "" : "none";
    if (knownRow)  knownRow.style.display  = showTable  ? "" : "none";
    if (slotGrp)   slotGrp.style.display   = showTable  ? "" : "none";

    // toggle our two new rows
    if (profTargetRow) profTargetRow.style.display = showModify ? "" : "none";
    if (profAmtRow)    profAmtRow.style.display    = showModify ? "" : "none";

    // clear subclass selections if hidden
    if (!showSubs && subRow) {
      subRow.querySelectorAll("select option:checked")
            .forEach(o=>o.selected = false);
    }
  }

  ftype.addEventListener("change", toggleAll);
  toggleAll();

  // auto-submit to refresh subclasses whenever umbrella changes
  const umbrella = document.getElementById("id_subclass_group");
  if (umbrella) umbrella.addEventListener("change", ()=>umbrella.form.submit());
});
