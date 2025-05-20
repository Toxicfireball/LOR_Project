// characters/static/characters/js/classfeature_admin.js
(function(){
  window.addEventListener("DOMContentLoaded", function(){
    const scopeEl     = document.getElementById("id_scope");
    const kindEl      = document.getElementById("id_kind");
    const activityEl  = document.getElementById("id_activity_type");
    const optsEl      = document.getElementById("id_has_options");

    function row(fieldName){
      return document.querySelector(".form-row.field-" + fieldName);
    }
    function inlineSpellTable(){
      return document.querySelector(".spell-slot-inline");
    }

    const rows = {
      // subclass pickers
      subgroup: row("subclass_group"),
      subclasses: row("subclasses"),

      // trait formula rows
      activity:      row("activity_type"),
      formulaTarget: row("formula_target"),
      formula:       row("formula"),
      uses:          row("uses"),
      action:        row("action_type"),
      damage:        row("damage_type"),

      // saving throw rows
      savingReq:             row("saving_throw_required"),
      savingType:            row("saving_throw_type"),
      savingGran:            row("saving_throw_granularity"),
      basicSuccess:          row("saving_throw_basic_success"),
      basicFailure:          row("saving_throw_basic_failure"),
      normalCritSuccess:     row("saving_throw_critical_success"),
      normalSuccess:         row("saving_throw_success"),
      normalFailure:         row("saving_throw_failure"),
      normalCritFailure:     row("saving_throw_critical_failure"),

      // other kinds
      profTarget:   row("modify_proficiency_target"),
      profAmount:   row("modify_proficiency_amount"),

      // spell table
      cantrips:     row("cantrips_formula"),
      known:        row("spells_known_formula"),
      prepared:     row("spells_prepared_formula"),
      slots:        inlineSpellTable(),

      // options inline
      optionsInline: document.getElementById("options-group"),
    };

    function toggleAll(){
      const scope = scopeEl    ? scopeEl.value    : "";
      const kind  = kindEl     ? kindEl.value     : "";
      const act   = activityEl ? activityEl.value : "";

      // 1) hide everything first
      Object.values(rows).forEach(el=>{
        if(el) el.style.display = "none";
      });

      // 2) show the subclass pickers based on *scope*
      if (scope==="subclass_feat" || scope==="subclass_choice"){
        rows.subgroup.style.display   = "";
        rows.subclasses.style.display = "";
      }

      // 3) now your class_trait formula block (unchanged)
      if (kind === "class_trait"){
        rows.activity.style.display      = "";
        rows.formulaTarget.style.display = "";
        rows.formula.style.display       = "";

        if (act === "active"){
          rows.uses.style.display        = "";
          rows.action.style.display      = "";
          rows.damage.style.display      = "";
          rows.savingReq.style.display   = "";

          const saveChk = document.getElementById("id_saving_throw_required");
          if (saveChk && saveChk.checked){
            rows.savingType.style.display            = "";
            rows.savingGran.style.display            = "";
            const gran = document.getElementById("id_saving_throw_granularity").value;
            if (gran === "basic"){
              rows.basicSuccess.style.display         = "";
              rows.basicFailure.style.display         = "";
            } else if (gran === "normal"){
              rows.normalCritSuccess.style.display    = "";
              rows.normalSuccess.style.display        = "";
              rows.normalFailure.style.display        = "";
              rows.normalCritFailure.style.display    = "";
            }
          }
        }
      }

      // 4) modify_proficiency kind
      if (kind==="modify_proficiency"){
        rows.profTarget.style.display = "";
        rows.profAmount.style.display = "";
      }

      // 5) spell_table kind
      if (kind==="spell_table"){
        rows.cantrips.style.display = "";
        rows.known   .style.display = "";
        rows.prepared.style.display = "";
        rows.slots   .style.display = "";
      }

      // 6) FeatureOption inline
      if (optsEl && optsEl.checked){
        rows.optionsInline.style.display = "";
      }
    }

    // wire up all dependencies
    [ scopeEl, kindEl, activityEl, optsEl ].forEach(el=>{
      if (el) el.addEventListener("change", toggleAll);
    });
    // also watch the save throw checkbox + granularity dropdown
    const saveReqEl  = document.getElementById("id_saving_throw_required");
    const saveGranEl = document.getElementById("id_saving_throw_granularity");
    if (saveReqEl)  saveReqEl .addEventListener("change", toggleAll);
    if (saveGranEl) saveGranEl.addEventListener("change", toggleAll);

    // auto-submit umbrella changes
    const umbrella = document.getElementById("id_subclass_group");
    if (umbrella) umbrella.addEventListener("change", ()=>umbrella.form.submit());

    // kick it off on initial load
    toggleAll();
  });
})();
