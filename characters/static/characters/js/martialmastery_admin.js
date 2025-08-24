// characters/static/characters/js/martialmastery_admin.js
(function () {
  function rowFor(fieldName) {
    // Django admin wraps each field in a .form-row.field-<name> (or .field-<name> depending on version)
    return document.querySelector('.form-row.field-' + fieldName) ||
           document.querySelector('.field-' + fieldName);
  }
  function setVisible(fieldName, visible) {
    const row = rowFor(fieldName);
    if (row) row.style.display = visible ? '' : 'none';
  }
  function bindToggle(toggleId, targetField) {
    const box = document.getElementById(toggleId);
    if (!box) return;
    const update = () => setVisible(targetField, box.checked);
    box.addEventListener('change', update);
    update(); // initial
  }

  // Wire up:
  bindToggle('id_restrict_to_weapons', 'allowed_weapons');
  bindToggle('id_restrict_to_traits',  'allowed_traits');
})();
