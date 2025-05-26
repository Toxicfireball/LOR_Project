document.addEventListener('DOMContentLoaded', function() {
  // 1) grab ALL of your “feature” selects
  const selects = Array.from(
    document.querySelectorAll('select[name$="-feature"]')
  );

  // 2) for each one, inject a tiny filter‐box above it...
  selects.forEach(sel => {
    const filter = document.createElement('input');
    filter.type        = 'text';
    filter.placeholder = 'Filter features…';
    filter.style.width = '100%';
    filter.style.marginBottom = '4px';
    sel.parentNode.insertBefore(filter, sel);

    // 3) update function: hides duplicates & applies filter text
    function update() {
      // a) build set of all currently chosen feature-IDs
      const chosen = new Set(
        selects.map(s => s.value).filter(v => v)
      );

      // b) hide/disable duplicates in *all* selects
      selects.forEach(s => {
        Array.from(s.options).forEach(opt => {
          const isDupe = opt.value
                      && chosen.has(opt.value)
                      && s.value !== opt.value;
          opt.hidden   = isDupe;
          opt.disabled = isDupe;
        });
      });

      // c) now apply the search‐filter to *this* select
      const kw = filter.value.trim().toLowerCase();
      Array.from(sel.options).forEach(opt => {
        // if it’s already hidden as a dupe, leave it hidden
        if (opt.disabled) return;
        // otherwise hide if it doesn’t match the filter text
        const txt = opt.textContent.toLowerCase();
        opt.hidden = kw && !txt.includes(kw);
      });
    }

    // 4) wire up events
    filter.addEventListener('input', update);
    sel.addEventListener('change', update);

    // and run once at load
    update();
  });
});
