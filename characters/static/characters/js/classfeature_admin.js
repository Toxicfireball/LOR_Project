// characters/static/characters/js/classfeature_admin.js
(function(){
  window.addEventListener("DOMContentLoaded", function(){
    // grab your three selectors + the “has options?” checkbox
    const scopeEl    = document.getElementById("id_scope");
    const kindEl     = document.getElementById("id_kind");
    const activityEl = document.getElementById("id_activity_type");
    const optsEl     = document.getElementById("id_has_options");

    // helper: single‐element lookup by Django’s row CSS
    function row(fieldName){
      return document.querySelector(".form-row.field-" + fieldName);
    }
    // helper: your spell-slot inline is marked with this class
    function inlineSpellTable(){
      return document.querySelector(".spell-slot-inline");
    }

    // cache all the bits we’ll be toggling
    const rows = {
      subgroup:   row("subclass_group"),
      subclasses: row("subclasses"),

      activity:      row("activity_type"),
      formula:       row("formula"),
      formulaTarget: row("formula_target"),
      uses:          row("uses"),
      action:        row("action_type"),

      profTarget:    row("modify_proficiency_target"),
      profAmount:    row("modify_proficiency_amount"),

      cantrips:      row("cantrips_formula"),
      known:         row("spells_known_formula"),
      prepared:      row("spells_prepared_formula"),
      slots:         inlineSpellTable(),

      optionsInline: document.getElementById("options-group"),
    };

    function toggleAll(){
      const s = scopeEl    ? scopeEl.value    : "";
      const k = kindEl     ? kindEl.value     : "";
      const a = activityEl ? activityEl.value : "";

      // first: hide absolutely everything
      Object.values(rows).forEach(el=>{
        if(el) el.style.display = "none";
      });

      // 1) subclass pickers for both subclass_*
      if (s==="subclass_feat" || s==="subclass_choice"){
        rows.subgroup && (rows.subgroup.style.display = "");
        rows.subclasses && (rows.subclasses.style.display = "");
      }

      // 2) dice-based features for class-feats & traits & skill_feat & martial_mastery
      if (["class_feat","class_trait","skill_feat","martial_mastery"].includes(k)){
        rows.activity      && (rows.activity.style.display      = "");
        rows.formulaTarget && (rows.formulaTarget.style.display = "");
        rows.formula       && (rows.formula.style.display       = "");
        if(a==="active"){
          rows.uses  && (rows.uses.style.display  = "");
          rows.action && (rows.action.style.display = "");
        }
      }

      // 3) modify proficiency
      if (k==="modify_proficiency"){
        rows.profTarget && (rows.profTarget.style.display = "");
        rows.profAmount && (rows.profAmount.style.display = "");
      }

      // 4) spell_table
      if (k==="spell_table"){
        rows.cantrips && (rows.cantrips.style.display = "");
        rows.known    && (rows.known.style.display    = "");
        rows.prepared && (rows.prepared.style.display = "");
        rows.slots    && (rows.slots.style.display    = "");
      }

      // 5) FeatureOption inline if “Has options?” is checked
      if (optsEl && optsEl.checked){
        rows.optionsInline && (rows.optionsInline.style.display = "");
      }
    }

    // re‐run whenever any of the four controllers change
    [scopeEl, kindEl, activityEl, optsEl].forEach(el=>{
      if(el) el.addEventListener("change", toggleAll);
    
    });
        const umbrella = document.getElementById("id_subclass_group");
        if (umbrella) {
          umbrella.addEventListener("change", ()=>{
            umbrella.form.submit();
          });
       }
    // initial hide/show
    toggleAll();
  });
})();
