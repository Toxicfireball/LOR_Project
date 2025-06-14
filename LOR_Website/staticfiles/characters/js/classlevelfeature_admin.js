// static/characters/js/classlevelfeature_admin.js
console.log("🍺 classlevelfeature_admin.js loaded");

document.addEventListener("DOMContentLoaded", function() {
  console.log("🍺 DOMContentLoaded");

  function updateAll() {
    console.log("➡️ updateAll()");
    const selects = Array.from(document.querySelectorAll('select[name$="-feature"]'));
    console.log("   selects:", selects.length);
    const chosen  = selects.map(s => s.value).filter(Boolean);
    console.log("   chosen:", chosen);

    selects.forEach(s => {
      // hide/disable duplicates
      Array.from(s.options).forEach(opt => {
        const dupe = opt.value && chosen.includes(opt.value) && s.value !== opt.value;
        opt.hidden   = dupe;
        opt.disabled = dupe;
      });
      // apply row filter
      const row    = s.closest("tr");
      const filter = row && row.querySelector("input.filter-box");
      if (filter) {
        const kw = filter.value.trim().toLowerCase();
        Array.from(s.options).forEach(opt => {
          if (opt.disabled) return;
          opt.hidden = kw && !opt.textContent.toLowerCase().includes(kw);
        });
      }
    });
  }

  function enhanceRow(row) {
    // skip template rows
    if (!row || row.classList.contains("empty-form")) {
      console.log(" ❌ skipping empty/template row", row && row.id);
      return;
    }
    // only do this once per real row
    if (row.dataset.enhanced) {
      console.log(" ↩️ already enhanced", row.id);
      return;
    }
    row.dataset.enhanced = "1";
    console.log("✨ enhanceRow on", row.id);

    // inject filter box
    const sel = row.querySelector('select[name$="-feature"]');
    if (sel) {
      const filter = document.createElement("input");
      filter.type        = "text";
      filter.placeholder = "Filter features…";
      filter.className   = "filter-box";
      filter.style.width = "100%";
      filter.style.marginBottom = "4px";
      sel.parentNode.insertBefore(filter, sel);
      filter.addEventListener("input", updateAll);
      sel.addEventListener("change", updateAll);
      console.log("   → injected filter-box");
    }

    // replace delete-checkbox
    const cb = row.querySelector('input[type=checkbox][name$="-DELETE"]');
    if (cb) {
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
        row.style.display = "none";
        updateAll();
      });
      console.log("   → replaced delete-checkbox with ✖");
    }
  }

  // enhance existing, skip template
  document
    .querySelectorAll('tr')
    .forEach(tr => enhanceRow(tr));

  updateAll();

  // observe additions anywhere
  const observer = new MutationObserver(muts => {
    muts.forEach(m => {
      m.addedNodes.forEach(node => {
        if (!(node instanceof HTMLElement)) return;
        // if it's a <tr>, try it
        if (node.matches("tr")) {
          console.log("🔍 found new TR", node.id);
          enhanceRow(node);
        } else {
          // else look for inner <tr>
          node.querySelectorAll && node.querySelectorAll("tr").forEach(tr => {
            console.log("🔍 found nested TR", tr.id);
            enhanceRow(tr);
          });
        }
      });
    });
    updateAll();
  });

  observer.observe(document.body, { childList: true, subtree: true });
  console.log("🔭 MutationObserver set up");
});
