// static/characters/js/formula_builder.js
(function(){
  // we’ll keep a simple token‐sanity regex, but the real check is a try/catch eval
  const SANITY_RE = /^(\s*(?:[A-Za-z_]\w*|\d+d(?:4|6|8|10|12|20)|\d+|\+|\-|\*|\/|\(|\)|round\s+(?:up|down))\s*)+$/;

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".formula-builder").forEach(initBuilder);
  });

  // classfeature_admin.js
document.addEventListener('DOMContentLoaded', function(){
  const clsSelect = document.getElementById('id_character_class'),
        codeInput = document.getElementById('id_code');
  if (!clsSelect || !codeInput) return;

  function updateCode(){
    const sel = clsSelect.selectedOptions[0];
    if (sel && sel.dataset.classId) {
      codeInput.value = sel.dataset.classId;
    }
  }

  clsSelect.addEventListener('change', updateCode);
  // initialize on page‐load
  updateCode();
});


  function initBuilder(fb) {
    const pillBox = fb.querySelector(".fb-pills"),
          ta      = fb.querySelector("textarea"),
          err     = fb.querySelector(".fb-error"),
          vars    = JSON.parse( ta.getAttribute("data-vars") ),
          dice    = JSON.parse( ta.getAttribute("data-dice") );

    // build pill buttons…
    pillBox.innerHTML = "";
    vars.forEach(v => makePill("fb-var", v, v));
    dice.forEach(d => makePill("fb-dice", d, "1"+d));

    pillBox.addEventListener("click", pillClick);
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
      if (!raw) {
        hideError(); return;
      }
      // quick sanity check
      if (!SANITY_RE.test(raw)) {
        showError();
        return;
      }
      // build a JS‐safe test expression:
      let expr = raw
        // replace dice Ndx with a dummy constant `1`
        .replace(/(\d+)d(4|6|8|10|12|20)/g, "1")
        // swap round up/down → Math.ceil()/Math.floor()
        .replace(/\bround up\b/gi, "Math.ceil")
        .replace(/\bround down\b/gi, "Math.floor");

      // replace every variable name with `1`
      vars.forEach(v => {
        const re = new RegExp("\\b"+v+"\\b","g");
        expr = expr.replace(re, "1");
      });

      // now try to compile+run it
      try {
        // Use the Function constructor instead of eval:
        // wrap in parentheses so things like `(1+1)` parse
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
