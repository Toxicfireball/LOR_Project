// static/characters/js/formula_builder.js
(function(){
  // allow optional digits before dN (so `d6` or `2d6`),
  // and still allow variables, numbers, parens, operators, round up/down
  const SANITY_RE = /^(\s*(?:[A-Za-z_]\w*|\d*d(?:4|6|8|10|12|20)|\d+|\+|\-|\*|\/|\(|\)|round\s+(?:up|down))\s*)+$/;

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".formula-builder").forEach(initBuilder);
  });

  function initBuilder(fb) {
    const pillBox = fb.querySelector(".fb-pills"),
          ta      = fb.querySelector("textarea"),
          err     = fb.querySelector(".fb-error"),
          vars    = JSON.parse( ta.getAttribute("data-vars") ),
          dice    = JSON.parse( ta.getAttribute("data-dice") );

    // build pill buttons…


    // **NEW: wire up the variable dropdown if you rendered it in your widget**
    const varDropdown = fb.querySelector(".fb-var-dropdown");
    if (varDropdown) {
      varDropdown.addEventListener("change", e => {
        const tok = e.target.value;
        if (vars.includes(tok)) {
          const s  = ta.selectionStart,
                e2 = ta.selectionEnd;
          ta.value = ta.value.slice(0,s) + tok + ta.value.slice(e2);
          ta.focus();
          validate();
        }
        e.target.value = "";
      });
    }
    ta.addEventListener("input", validate);
    validate();  // initial

    function makePill(cls, text, token){
      const b = document.createElement("button");
      b.type = "button";
      b.className = "fb-pill " + cls;
      b.textContent = text;
      b.dataset.token = token;
      pillBox.appendChild(b);
    }

    function pillClick(e){
      if (!e.target.matches(".fb-pill")) return;
      const tok = e.target.dataset.token,
            s   = ta.selectionStart,
            e2  = ta.selectionEnd;
      ta.value = ta.value.slice(0,s) + tok + ta.value.slice(e2);
      ta.focus();
      validate();
    }

    function validate(){
      const raw = ta.value.trim();
      if (!raw) { hideError(); return; }
      if (!SANITY_RE.test(raw)) { showError(); return; }

      let expr = raw
        // catch `(foo-3)d6`, `d6`, or `2d6`
        .replace(/(?:\b\d+|\b[A-Za-z_]\w*|\([^)]*\))d(4|6|8|10|12|20)/g, "1")
        .replace(/\bround up\b/gi, "Math.ceil")
        .replace(/\bround down\b/gi, "Math.floor");

      vars.forEach(v => {
        expr = expr.replace(new RegExp("\\b"+v+"\\b","g"), "1");
      });

      try {
        Function(`"use strict"; return (${expr});`)();
        hideError();
      } catch(_) {
        showError();
      }
    }

    function showError(){
      err.style.display = "";
      ta.setCustomValidity("Invalid or unparsable formula");
    }
    function hideError(){
      err.style.display = "none";
      ta.setCustomValidity("");
    }
  }
})();
