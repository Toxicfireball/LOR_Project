// static/characters/js/classlevelfeature_admin.js
document.addEventListener("DOMContentLoaded", function() {
  // 1) Find every “feature” <select> in all inline rows:
  const selects = Array.from(
    document.querySelectorAll("select[name$='-feature']")
  );
  if (!selects.length) return;  // nothing to do

  // 2) Create a single update() that hides dupes and applies filters
  function updateAll() {
    const chosen = selects
      .map(s => s.value)
      .filter(v => v);
    selects.forEach(s => {
      // hide duplicates
      Array.from(s.options).forEach(opt => {
        const dupe = opt.value && chosen.includes(opt.value) && s.value !== opt.value;
        opt.hidden   = dupe;
        opt.disabled = dupe;
      });
      // apply text-filter if we’ve got a filter box just before this select
      const filter = s.previousElementSibling;
      if (filter && filter.classList.contains("filter-box")) {
        const kw = filter.value.trim().toLowerCase();
        Array.from(s.options).forEach(opt => {
          if (opt.disabled) return;
          opt.hidden = kw && !opt.textContent.toLowerCase().includes(kw);
        });
      }
    });
  }

  // 3) Inject a filter‐box before each select and wire events
  selects.forEach(s => {
    // don’t double-add
    if (s.previousElementSibling?.classList.contains("filter-box")) return;

    const filter = document.createElement("input");
    filter.type        = "text";
    filter.placeholder = "Filter features…";
    filter.className   = "filter-box";
    filter.style.width = "100%";
    filter.style.marginBottom = "4px";

    s.parentNode.insertBefore(filter, s);
    filter.addEventListener("input", updateAll);
    s.addEventListener("change", updateAll);
  });

  // 4) Turn every DELETE-checkbox into an ✖
  document.querySelectorAll("input[type=checkbox][name$='-DELETE']").forEach(cb => {
    if (cb.nextSibling?.classList.contains("inline-deletelink")) return;
    cb.style.display = "none";
    const x = document.createElement("span");
    x.textContent   = "✖";
    x.className     = "inline-deletelink";
    x.style.cursor  = "pointer";
    x.title         = "Remove this row";
    cb.parentNode.appendChild(x);
    x.addEventListener("click", e => {
      e.preventDefault();
      cb.checked = true;
      const row = cb.closest("tr");
      if (row) row.style.display = "none";
      updateAll();
    });
  });

  // 5) Initial run
  updateAll();

  // 6) Re-run when Django dynamically adds a new inline
  document.body.addEventListener("formset:added", function(e) {
    // e.target is the <tbody> of the inline
    Array.from(e.target.querySelectorAll("select[name$='-feature']")).forEach(s => {
      // inject filter+events on the new select
      const filter = document.createElement("input");
      filter.type        = "text";
      filter.placeholder = "Filter features…";
      filter.className   = "filter-box";
      filter.style.width = "100%";
      filter.style.marginBottom = "4px";
      s.parentNode.insertBefore(filter, s);
      filter.addEventListener("input", updateAll);
      s.addEventListener("change", updateAll);
    });
    // decorate any new delete‐checkboxes
    document.querySelectorAll(
      ".dynamic-form-row input[type=checkbox][name$='-DELETE']"
    ).forEach(cb => {
      if (cb.nextSibling?.classList.contains("inline-deletelink")) return;
      cb.style.display = "none";
      const x = document.createElement("span");
      x.textContent   = "✖";
      x.className     = "inline-deletelink";
      x.style.cursor  = "pointer";
      x.title         = "Remove this row";
      cb.parentNode.appendChild(x);
      x.addEventListener("click", e => {
        e.preventDefault();
        cb.checked = true;
        const row = cb.closest("tr");
        if (row) row.style.display = "none";
        updateAll();
      });
    });
  });
});
