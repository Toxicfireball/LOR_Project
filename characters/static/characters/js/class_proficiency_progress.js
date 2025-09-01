// static/characters/js/class_proficiency_progress.js
(function() {
  function toggle(row) {
    const typ = row.querySelector('select[name$="proficiency_type"]').value;
    const armorRow  = row.querySelector('select[name$="armor_group"]').closest('.form-row, .field-armor_group, td');
    const weaponRow = row.querySelector('select[name$="weapon_group"]').closest('.form-row, .field-weapon_group, td');
    if (armorRow && weaponRow) {
      armorRow.style.display  = (typ === 'armor')  ? '' : 'none';
      weaponRow.style.display = (typ === 'weapon') ? '' : 'none';
    }
  }
  function init() {
    document.querySelectorAll('.dynamic-classproficiencyprogress').forEach(function(row) {
      const sel = row.querySelector('select[name$="proficiency_type"]');
      if (!sel) return;
      sel.addEventListener('change', function(){ toggle(row); });
      toggle(row);
    });
  }
  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);
})();
