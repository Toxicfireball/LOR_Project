(function(){
  document.addEventListener("DOMContentLoaded", function(){
    const typeEl  = document.getElementById("id_range_type");
    const normEl  = document.querySelector(".form-row.field-range_normal");
    const maxEl   = document.querySelector(".form-row.field-range_max");

    function toggleRange(){
      const isRanged = typeEl.value === "ranged";
      normEl.style.display = isRanged ? "" : "none";
      maxEl.style.display  = isRanged ? "" : "none";
    }

    typeEl.addEventListener("change", toggleRange);
    toggleRange();
  });
})();
