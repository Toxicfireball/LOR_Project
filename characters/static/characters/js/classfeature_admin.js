document.addEventListener("DOMContentLoaded", function(){
    const clsSelect = document.getElementById("id_character_class"),
          codeInput = document.getElementById("id_code");
    if (!clsSelect || !codeInput) return;
  
    function updateCode(){
      const opt = clsSelect.selectedOptions[0];
      if (opt && opt.dataset.classId) {
        codeInput.value = opt.dataset.classId;
      }
    }
  
    clsSelect.addEventListener("change", updateCode);
    // fire once on load, in case you’re editing:
    updateCode();
  });
  