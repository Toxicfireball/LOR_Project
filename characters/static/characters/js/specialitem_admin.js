// characters/static/characters/js/specialitem_admin.js
(function(){
  window.addEventListener("DOMContentLoaded", function(){
    // ─── 1) ITEM TYPE TOGGLE ────────────────────────────────────────────────
    const typeEl = document.getElementById("id_item_type");
    const sets = {
      weapon:   document.querySelector("fieldset.weapon-group"),
      armor:    document.querySelector("fieldset.armor-group"),
      wearable: document.querySelector("fieldset.wearable-group"),
    };
    function toggleItemType(){
      const t = typeEl.value;
      Object.entries(sets).forEach(([k,fs])=>{
        if(!fs) return;
        fs.style.display = (k === t ? "" : "none");
      });
    }
    if(typeEl){
      typeEl.addEventListener("change", toggleItemType);
      toggleItemType();
    }

    // ─── 2) TRAIT INLINE SHOW/HIDE ──────────────────────────────────────────
    // find all of your SpecialItemTraitValue inlines
    const inlineGroup = document.querySelector(".specialitemtraitvalue-inline");
    const blocks = inlineGroup
      ? Array.from(inlineGroup.querySelectorAll(".inline-related"))
      : [];

    const ALWAYS  = ["name","active","description"];
    const ACTIVE  = [
      "formula_target","formula","uses","action_type","damage_type",
      "saving_throw_required"
    ];
    const SAVE    = [
      "saving_throw_type","saving_throw_granularity",
      "saving_throw_basic_success","saving_throw_basic_failure",
      "saving_throw_critical_success","saving_throw_success",
      "saving_throw_failure","saving_throw_critical_failure"
    ];
    const PASSIVE = [
      "modify_proficiency_target","modify_proficiency_amount",
      "gain_resistance_mode","gain_resistance_types"
    ];
    const RES_AMT = ["gain_resistance_amount"];

    // helper to show/hide one field row
    function showField(block, field, show) {
      const row = block.querySelector(".form-row.field-" + field);
      if (row) row.style.display = show ? "" : "none";
    }

    // for each block, decide what's visible
    function toggleBlock(block){
      // hide everything first
      ALWAYS.concat(ACTIVE, SAVE, PASSIVE, RES_AMT).forEach(f => showField(block, f, false));
      // always show these
      ALWAYS.forEach(f => showField(block, f, true));

      const isActive = !!block.querySelector("input[name$='-active']")?.checked;
      if (isActive) {
        // show all Active‐only fields
        ACTIVE.forEach(f => showField(block, f, true));

        // if Saving Throw? is checked
        const req = block.querySelector("input[name$='-saving_throw_required']");
        if (req?.checked) {
          // show the two dropdowns
          showField(block, "saving_throw_type", true);
          showField(block, "saving_throw_granularity", true);

          // then sub‐fields based on granularity
          const gran = block.querySelector("select[name$='-saving_throw_granularity']")?.value;
          if (gran === "basic") {
            ["saving_throw_basic_success","saving_throw_basic_failure"]
              .forEach(f => showField(block, f, true));
          }
          else if (gran === "normal") {
            ["saving_throw_critical_success","saving_throw_success",
             "saving_throw_failure","saving_throw_critical_failure"]
              .forEach(f => showField(block, f, true));
          }
        }
      } else {
        // Passive mode: show passive fields
        PASSIVE.forEach(f => showField(block, f, true));
        // only show reduction amount when mode is "reduction"
        const mode = block.querySelector("select[name$='-gain_resistance_mode']")?.value;
        if (mode === "reduction") {
          showField(block, "gain_resistance_amount", true);
        }
      }
    }

    // run on every block
    function toggleAll(){
      blocks.forEach(toggleBlock);
    }

    // re-run whenever relevant inputs change
    document.body.addEventListener("change", function(e){
      if (
           e.target.name?.endsWith("-active") ||
           e.target.name?.endsWith("-saving_throw_required") ||
           e.target.name?.endsWith("-saving_throw_granularity") ||
           e.target.name?.endsWith("-gain_resistance_mode")
      ) {
        toggleAll();
      }
    });

    // initial pass
    toggleAll();
  });
})();