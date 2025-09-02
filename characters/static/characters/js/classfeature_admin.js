(function () {
  window.addEventListener("DOMContentLoaded", function () {
    // ── Inputs ─────────────────────────────────────────────────────────────────────
    const scopeEl    = document.getElementById("id_scope");
    const kindEl     = document.getElementById("id_kind");
    const grpSelect  = document.getElementById("id_subclass_group");
    const optsEl     = document.getElementById("id_has_options");
    const activityEl = document.getElementById("id_activity_type");

    // ── Helpers ────────────────────────────────────────────────────────────────────
    function row(name) { return document.querySelector(".form-row.field-" + name); }
    function show(el, on) { if (el) el.style.display = on ? "" : "none"; }
    function currentGmpMode() {
      const r = document.querySelector('input[name="gmp_mode"]:checked');
      return r ? r.value : "";
    }
    function getInherentSpellInline() {
      const el = document.querySelector(".spell-inline");
      return el && (el.classList.contains("inline-group") ? el : (el.closest(".inline-group") || el));
    }
    function getSpellTableInline() {
      return document.querySelector(
        ".spell-slot-inline, " +                 // custom class on Inline group
        "[id$='-spellslotrow_set-group'], " +    // common id pattern for tabular inline
        "#spellslotrow_set-group"                // fallback id
      );
    }

    // Rows we toggle
    const rows = {
      subgroup:       row("subclass_group"),
      subclasses:     row("subclasses"),
      tier:           row("tier"),
      masteryRank:    row("mastery_rank"),
      activity:       row("activity_type"),
      formulaTarget:  row("formula_target"),
      formula:        row("formula"),
      uses:           row("uses"),
      action:         row("action_type"),
      damage:         row("damage_type"),
      savingReq:      row("saving_throw_required"),
      savingType:     row("saving_throw_type"),
      savingGran:     row("saving_throw_granularity"),
      basicSuccess:   row("saving_throw_basic_success"),
      basicFailure:   row("saving_throw_basic_failure"),
      normalCritSuccess: row("saving_throw_critical_success"),
      normalSuccess:     row("saving_throw_success"),
      normalFailure:     row("saving_throw_failure"),
      normalCritFailure: row("saving_throw_critical_failure"),
      mmPoints:       row("martial_points_formula"),
      mmAvailable:    row("available_masteries_formula"),
      gmpMode:        row("gmp_mode"),
      profTarget:     row("modify_proficiency_target"),
      profAmount:     row("modify_proficiency_amount"),
      spellList:      row("spell_list"),
      cantrips:       row("cantrips_formula"),
      known:          row("spells_known_formula"),
      prepared:       row("spells_prepared_formula"),
      optionsInline:  document.getElementById("options-group"),
      gainSubskills:  row("gain_subskills"),
      gainResMode:    row("gain_resistance_mode"),
      gainResTypes:   row("gain_resistance_types"),
      gainResAmt:     row("gain_resistance_amount"),
    };

    function toggleAll() {
      const scopeVal = scopeEl ? scopeEl.value : "";
      const kindVal  = kindEl  ? kindEl.value  : "";
      const actVal   = activityEl ? activityEl.value : "";

      // Always re-resolve inline containers (they may or may not be present)
      const inherentInline = getInherentSpellInline();
      const slotsInline    = getSpellTableInline();

      // Hide everything we control
      Object.values(rows).forEach(el => el && (el.style.display = "none"));
      if (inherentInline) inherentInline.style.display = "none";
      if (slotsInline)    slotsInline.style.display    = "none";

      // Gain Subclass Feature ⇒ only Tier, also hide the Kind row itself
      if (scopeVal === "gain_subclass_feat") {
        show(rows.tier, true);
        const kindRow = document.querySelector(".form-row.field-kind");
        if (kindRow) kindRow.style.display = "none";
        return;
      }

      // Subclass scaffolding
      if (scopeVal === "subclass_feat" || scopeVal === "subclass_choice") {
        show(rows.subgroup, true);
        show(rows.subclasses, true);
      }

      // Tier vs Mastery (only for subclass_feat)
      if (scopeVal === "subclass_feat" && grpSelect && grpSelect.value) {
        const st = grpSelect.getAttribute("data-system-type") || "";
        show(rows.tier,        st === "modular_linear");
        show(rows.masteryRank, st === "modular_mastery");
      }

      // Class trait block
      if (kindVal === "class_trait") {
        show(rows.activity, true);
        show(rows.formulaTarget, true);
        show(rows.formula, true);
        if (actVal === "active") {
          show(rows.uses, true);
          show(rows.action, true);
          show(rows.damage, true);
          show(rows.savingReq, true);
          const saveChk = document.getElementById("id_saving_throw_required");
          if (saveChk && saveChk.checked) {
            show(rows.savingType, true);
            show(rows.savingGran, true);
            const granEl = document.getElementById("id_saving_throw_granularity");
            const gran   = granEl ? granEl.value : "";
            if (gran === "basic") {
              show(rows.basicSuccess, true);
              show(rows.basicFailure, true);
            } else if (gran === "normal") {
              show(rows.normalCritSuccess, true);
              show(rows.normalSuccess, true);
              show(rows.normalFailure, true);
              show(rows.normalCritFailure, true);
            }
          }
        }
      }

      // Gain Resistance
      if (kindVal === "gain_resistance") {
        show(rows.gainResMode,  true);
        show(rows.gainResTypes, true);
        const modeEl = document.getElementById("id_gain_resistance_mode");
        const mode   = modeEl ? modeEl.value : "";
        show(rows.gainResAmt, mode === "reduction");
      }

      // Martial Mastery
      if (kindVal === "martial_mastery") {
        show(rows.mmPoints, true);
        show(rows.mmAvailable, true);
      }

      // Generic Gain/Modify Proficiency
      if (kindVal === "modify_proficiency") {
        show(rows.gmpMode,    true);
        show(rows.profTarget, true);
        const gm = currentGmpMode();
        show(rows.profAmount, gm === "set");
      }

      // Core Proficiency section (only when kind is core_proficiency)
      const coreIds = [
        "id_prof_target_kind",
        "id_armor_group_choice","id_weapon_group_choice",
        "id_armor_item_choice","id_weapon_item_choice",
        "id_gain_proficiency_amount","id_modify_proficiency_amount",
      ];
      coreIds.forEach(id => {
        const el = document.getElementById(id);
        const r  = el && (el.closest(".form-row") || el.closest("div.fieldBox"));
        if (r) r.style.display = (kindVal === "core_proficiency" ? "" : "none");
      });

      // Spell systems
      if (kindVal === "inherent_spell" && inherentInline) {
        inherentInline.style.display = "";
      }
      if (kindVal === "spell_table") {
        show(rows.spellList, true);
        show(rows.cantrips,  true);
        show(rows.known,     true);
        show(rows.prepared,  true);
        if (slotsInline) slotsInline.style.display = "";
      }

      // Options inline
      if (optsEl && optsEl.checked && rows.optionsInline) {
        rows.optionsInline.style.display = "";
      }
    }

    // Listeners
    [scopeEl, kindEl, activityEl, optsEl].forEach(el => el && el.addEventListener("change", toggleAll));
    const saveReqEl  = document.getElementById("id_saving_throw_required");
    const saveGranEl = document.getElementById("id_saving_throw_granularity");
    if (saveReqEl)  saveReqEl.addEventListener("change", toggleAll);
    if (saveGranEl) saveGranEl.addEventListener("change", toggleAll);
    const resModeEl = document.getElementById("id_gain_resistance_mode");
    if (resModeEl) resModeEl.addEventListener("change", toggleAll);

    if (grpSelect) {
      grpSelect.addEventListener("change", function () {
        const map = JSON.parse(this.getAttribute("data-group-types") || "{}");
        this.setAttribute("data-system-type", map[this.value] || "");
        toggleAll();
      });
    }

    // Initial paint
    toggleAll();
  });
})();
