// characters/static/characters/js/classfeature_admin.js
window.addEventListener("DOMContentLoaded", function(){
  const ftype      = document.getElementById("id_feature_type");
  const subRow     = document.querySelector(".form-row.field-subclasses");
  const groupRow   = document.querySelector(".form-row.field-subclass_group");

  const canRow     = document.querySelector(".form-row.field-cantrips_formula");
  const knownRow   = document.querySelector(".form-row.field-spells_known_formula");
  const slotGroup  = document.getElementById("spell_slot_rows-group");

  function toggleAll(){
    const val       = ftype.value;
    // also show for subclass_choice
    const showSubs  = (val === "subclass_feat"  ||  val === "subclass_choice");
    const showTable = (val === "spell_table");

    if (subRow)   subRow.style.display   = showSubs  ? "" : "none";
    if (groupRow) groupRow.style.display = showSubs  ? "" : "none";

    if (canRow)   canRow.style.display   = showTable ? "" : "none";
    if (knownRow) knownRow.style.display = showTable ? "" : "none";
    if (slotGroup)slotGroup.style.display= showTable ? "" : "none";

    if (!showSubs && subRow) {
      subRow.querySelectorAll("select option:checked")
            .forEach(o=>o.selected = false);
    }
  }

  ftype.addEventListener("change", toggleAll);
  toggleAll();

  const umbrella = document.getElementById("id_subclass_group");
  if (umbrella) umbrella.addEventListener("change", ()=>umbrella.form.submit());
});
