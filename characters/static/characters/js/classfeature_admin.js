// characters/static/characters/js/classfeature_admin.js
window.addEventListener("DOMContentLoaded", function(){
  console.log("▶️ toggleSubs init");

  // 1) find the <select> and the wrapping <div>
  const ftype  = document.getElementById("id_feature_type");
  const subRow = document.querySelector(".form-row.field-subclasses");

  console.log(" feature_type select:", ftype);
  console.log(" subclasses wrapper:", subRow);

  if (!ftype || !subRow) {
    console.warn("Toggle script couldn't find the elements.");
    return;
  }

  // 2) show/hide and clear the M2M if needed
  function toggleSubclasses(){
    console.log(" toggleSubclasses() →", ftype.value);
    if (ftype.value === "subclass_feat") {
      subRow.style.display = "";
    } else {
      subRow.style.display = "none";
      // clear any chosen options
      subRow.querySelectorAll("select option[selected]").forEach(opt => {
        opt.selected = false;
      });
    }
  }

  // 3) wire it up
  ftype.addEventListener("change", toggleSubclasses);

  // 4) initial run
  toggleSubclasses();
});
