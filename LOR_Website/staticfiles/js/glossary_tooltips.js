(function () {
  const SKIP_TAGS = new Set(["SCRIPT","STYLE","NOSCRIPT","CODE","PRE","TEXTAREA","INPUT","KBD","SAMP"]);
  const MAX_PER_TERM = 20;     // cap replacements per term per page
  const MAX_TOTAL = 1000;      // global cap to avoid heavy pages

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c =>
      ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}[c])
    );
  }

  function buildMatchers(data) {
    const matchers = [];
    (data.terms || []).forEach(item => {
      const defn = item.defn || "";
      const flags = item.cs ? "g" : "gi";
      (item.aliases || []).forEach(word => {
        if (!word) return;
        const esc = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const pat = item.ww ? `\\b${esc}\\b` : esc;
        matchers.push({
          re: new RegExp(pat, flags),
          word,
          defn
        });
      });
    });
    // Favor longer terms first (so “On-hit” beats “hit”)
    matchers.sort((a,b) => b.word.length - a.word.length);
    return matchers;
  }

  async function loadTerms() {
    try {
      const res = await fetch("/glossary.json", { credentials: "same-origin" });
      if (!res.ok) return null;
      return await res.json();
    } catch { return null; }
  }

  function scanAndWrap(matchers) {
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode(node) {
          if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
          if (SKIP_TAGS.has(node.parentNode?.nodeName)) return NodeFilter.FILTER_REJECT;
          if (node.parentElement?.closest?.("[data-glossary-skip]")) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );

    const textNodes = [];
    let n; while ((n = walker.nextNode())) textNodes.push(n);

    let total = 0;
    textNodes.forEach(node => {
      let txt = node.nodeValue;
      let replaced = false;

      for (const {re, defn} of matchers) {
        let count = 0;
        txt = txt.replace(re, (m) => {
          if (count >= MAX_PER_TERM || total >= MAX_TOTAL) return m;
          count++; total++;
          replaced = true;
          return `<span class="glossary-term" data-tip="${escapeHtml(defn)}">${m}</span>`;
        });
      }

      if (replaced) {
        const span = document.createElement("span");
        span.innerHTML = txt;
        node.replaceWith(span);
      }
    });

    // Simple viewport edge heuristic: flip tooltip upwards if near bottom
    const els = document.querySelectorAll(".glossary-term[data-tip]");
    const vh = window.innerHeight || document.documentElement.clientHeight;
    els.forEach(el => {
      const r = el.getBoundingClientRect();
      if (vh - r.bottom < 120) {
        el.setAttribute("data-tip-pos", "top");
      }
    });
  }

  (async function main() {
    const data = await loadTerms();
    if (!data || !data.terms?.length) return;
    const matchers = buildMatchers(data);
    scanAndWrap(matchers);
  })();
})();
