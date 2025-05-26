document.addEventListener('DOMContentLoaded', function() {
  // grab every “feature” dropdown in the inline
  const selects = Array.from(
    document.querySelectorAll('select[name$="-feature"]')
  );

  function updateDisabledOptions() {
    // build a set of all currently selected values
    const chosen = new Set(selects.map(s => s.value).filter(v => v));

    selects.forEach(sel => {
      Array.from(sel.options).forEach(opt => {
        // disable if it’s been chosen *elsewhere*, but keep your own selection enabled
        opt.disabled =
          opt.value &&
          chosen.has(opt.value) &&
          sel.value !== opt.value;
      });
    });
  }

  // hook up and kick off
  selects.forEach(s => s.addEventListener('change', updateDisabledOptions));
  updateDisabledOptions();
});
