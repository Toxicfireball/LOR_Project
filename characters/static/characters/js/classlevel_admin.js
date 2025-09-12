document.addEventListener('DOMContentLoaded', function() {
  const sel = document.getElementById('id_character_class');
  if (!sel) return;

  // capture the actual starting value
  const initial = sel.value;

  sel.addEventListener('change', function() {
    const picked = sel.value;
    // Only reload if it’s truly different
    if (picked === initial) return;

    // Build a new URL object to preserve any other params
    const url = new URL(window.location.href);
    url.searchParams.set('character_class', picked);

    // Navigate
    window.location.href = url.toString();
  });
});
(function($) {
  function toggleForSelect($sel) {
    var map = {};
    try { map = JSON.parse($sel.attr('data-mm-gainer-map') || '{}'); } catch(e) {}

    var isGainer = !!map[$sel.val()];
    // Find the matching num_picks input in the same inline row
    var name = $sel.attr('name').replace(/feature$/, 'num_picks');
    var $input = $('[name="' + name.replace(/([[\]])/g, '\\$1') + '"]');
    if (!$input.length) return;

    var $cell = $input.closest('td'); // tabular inline
    if (isGainer) {
      $cell.show();
      $input.prop('required', true).attr('min', 1);
      if (($input.val() || '') === '') $input.val(1);
    } else {
      $input.prop('required', false).attr('min', 0);
      if ($input.val() === '1') $input.val(0);
      $cell.hide();
    }
  }

  function wireRow(row) {
    var $row = $(row);
    var $sel = $row.find('select[name$="-feature"]');
    if (!$sel.length) return;
    // Initial state + change handler
    toggleForSelect($sel);
    $sel.on('change', function(){ toggleForSelect($(this)); });
  }

  // Initial rows
  $(function() {
    $('.inline-group tbody tr').each(function(){ wireRow(this); });
  });

  // New rows added (“Add another Class level feature”)
  $(document).on('formset:added', function(event, $row/*, formsetName */){
    wireRow($row);
  });
})(django.jQuery);
