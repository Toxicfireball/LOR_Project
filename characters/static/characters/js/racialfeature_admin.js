(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var race = document.getElementById("id_race");
    var subrace = document.getElementById("id_subrace");
    if (!race || !subrace) return;

    // if no race yet, keep Subrace disabled (server also does this)
    if (!race.value) {
      subrace.setAttribute("disabled", "disabled");
    }

    race.addEventListener("change", function () {
      var url = new URL(window.location.href);
      if (race.value) {
        url.searchParams.set("race", race.value);
      } else {
        url.searchParams.delete("race");
      }
      // Clear any previous subrace selection when switching race
      url.searchParams.set("_rf_clear_subrace", "1");
      window.location.href = url.toString();
    });
  });
})();
(function () {
  function rowOf(input) {
    return input && (input.closest('.form-row') || input.closest('div.fieldBox') || input.parentElement);
  }
  function show(inputId, on) {
    var el = document.getElementById(inputId);
    var row = rowOf(el);
    if (row) row.style.display = on ? '' : 'none';
  }

  var kind = document.getElementById('id_prof_target_kind');
  var gainAmt = document.getElementById('id_gain_proficiency_amount'); // may not exist
  var modAmt  = document.getElementById('id_modify_proficiency_amount');
  var modTgt  = document.getElementById('id_modify_proficiency_target');

  function forceSetMode() {
    document.querySelectorAll('input[name="prof_change_mode"]').forEach(function (r) {
      if (r.value === 'progress') {
        r.checked = false;
        r.disabled = true;
        var label = document.querySelector('label[for="' + r.id + '"]');
        if (label) label.style.opacity = 0.5;
      } else if (r.value === 'set') {
        r.checked = true;
      }
    });
  }

  function update() {
    var k = kind ? kind.value : '';
    show('id_armor_group_choice', k === 'armor_group');
    show('id_weapon_group_choice', k === 'weapon_group');
    show('id_armor_item_choice',  k === 'armor_item');
    show('id_weapon_item_choice', k === 'weapon_item');

    forceSetMode();
    if (gainAmt) show('id_gain_proficiency_amount', false);
    show('id_modify_proficiency_amount', true);

    if (modTgt) {
      var row = rowOf(modTgt);
      if (row) row.style.display = '';
      modTgt.disabled = false;
    }
  }

  function bind() {
    if (kind) kind.addEventListener('change', update);
    update();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
