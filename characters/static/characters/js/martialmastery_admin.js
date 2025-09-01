// characters/js/martialmastery_admin.js
(function() {
  function $(sel) { return document.querySelector(sel); }
  function wrap(fieldName) { return document.querySelector('.field-' + fieldName); }
  function show(el, on) { if (el) el.style.display = on ? '' : 'none'; }

  function getBool(id) {
    var el = $(id);
    if (!el) return false;
    // checkbox or radio
    if (el.type === 'checkbox') return !!el.checked;
    // inverse for class restriction synthetic toggle is normal boolean
    return !!el.value;
  }

  function sync() {
    // weapon
    var wOn = getBool('#id_restrict_to_weapons');
    show(wrap('allowed_weapons'), wOn);

    // damage
    var dOn = getBool('#id_restrict_to_damage');
    show(wrap('allowed_damage_types'), dOn);

    // traits (if you still use them)
    var tOn = getBool('#id_restrict_to_traits');
    show(wrap('allowed_traits'), tOn);
    var aOn = getBool('#id_restrict_by_ability');
    show(wrap('required_ability'), aOn);
    show(wrap('required_ability_score'), aOn);

    // classes (synthetic toggle drives visibility; real all_classes is hidden by form)
    var cOn = getBool('#id_restrict_to_classes');
    show(wrap('classes'), cOn);
  }

  function onReady(fn){ if(document.readyState!=='loading'){fn();} else {document.addEventListener('DOMContentLoaded',fn);} }

  onReady(function() {
    // ensure wrappers exist even if fields are in a different fieldset order
    ['allowed_weapons','allowed_damage_types','allowed_traits','classes',,'required_ability','required_ability_score'].forEach(function(n){
      var el = wrap(n); if (el) el.style.transition = 'all 0.15s ease';
    });

    // wire events
    ['#id_restrict_to_weapons','#id_restrict_to_damage','#id_restrict_to_traits','#id_restrict_to_classes', '#id_restrict_by_ability']
      .forEach(function(id){
        var el = $(id);
        if (el) el.addEventListener('change', sync);
      });

    // initial pass
    sync();
  });
})();
