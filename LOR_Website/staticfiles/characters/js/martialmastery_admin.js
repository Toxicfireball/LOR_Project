// characters/js/martialmastery_admin.js
(function() {
  function $(sel) { return document.querySelector(sel); }
  function wrap(name) { return document.querySelector('.form-row.field-' + name + ', .field-' + name); }
  function show(el, on) { if (el) el.style.display = on ? '' : 'none'; }

  function getBool(id) {
    var el = $(id);
    if (!el) return false;
    // checkbox or radio
    if (el.type === 'checkbox') return !!el.checked;
    return !!el.value;
  }

  function ensureDefaultTraitMode() {
    var sel = $('#id_trait_match_mode');
    if (sel && !sel.value) sel.value = 'any';
  }

  function sync() {
    // weapons
    var wOn = getBool('#id_restrict_to_weapons');
    show(wrap('allowed_weapons'), wOn);
    var rOn = getBool('#id_restrict_to_range');
    show(wrap('allowed_range_types'), rOn);
    // damage
    var dOn = getBool('#id_restrict_to_damage');
    show(wrap('allowed_damage_types'), dOn);

    // traits
    var tOn = getBool('#id_restrict_to_traits');
    show(wrap('allowed_traits'), tOn);
    show(wrap('trait_match_mode'), tOn);   // ← NEW: toggle ANY/ALL select
    if (tOn) ensureDefaultTraitMode();     // ← optional: set UI default

    // ability gate
    var aOn = getBool('#id_restrict_by_ability');
    show(wrap('required_ability'), aOn);
    show(wrap('required_ability_score'), aOn);

    // classes (synthetic toggle)
    var cOn = getBool('#id_restrict_to_classes');
    show(wrap('classes'), cOn);
  }

  function onReady(fn){ 
    if(document.readyState !== 'loading'){ fn(); } 
    else { document.addEventListener('DOMContentLoaded', fn); } 
  }

  onReady(function() {
    // add smooth show/hide for relevant rows (fixed the stray comma and added trait_match_mode)
    ['allowed_weapons','allowed_damage_types','allowed_range_types','allowed_traits','trait_match_mode','classes','required_ability','required_ability_score']
      .forEach(function(n){
        var el = wrap(n); 
        if (el) el.style.transition = 'all 0.15s ease';
      });

    // wire toggles
    ['#id_restrict_to_weapons','#id_restrict_to_damage','#id_restrict_to_range','#id_restrict_to_traits','#id_restrict_to_classes','#id_restrict_by_ability']
      .forEach(function(id){
        var el = $(id);
        if (el) el.addEventListener('change', sync);
      });

    // initial pass
    sync();
  });
})();
