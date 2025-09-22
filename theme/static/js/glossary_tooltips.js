(function () {
  if (window.__glossaryTooltipsInitialized) return;
  window.__glossaryTooltipsInitialized = true;

  const SKIP_TAGS = new Set(["SCRIPT","STYLE","NOSCRIPT","CODE","PRE","TEXTAREA","INPUT","KBD","SAMP"]);
  const MAX_PER_TERM = 20;
  const MAX_TOTAL = 1000;

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
        matchers.push({ re: new RegExp(pat, flags), word, defn });
      });
    });
    // Longest first
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
          const p = node.parentNode;
          if (!p) return NodeFilter.FILTER_REJECT;
          if (p.nodeType === 1) {
            if (p.classList && p.classList.contains("glossary-term")) return NodeFilter.FILTER_REJECT;
            if (p.closest && p.closest("[data-glossary-skip]")) return NodeFilter.FILTER_REJECT;
          }
          if (SKIP_TAGS.has(p.nodeName)) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );

    const textNodes = [];
    let n; while ((n = walker.nextNode())) textNodes.push(n);

    let total = 0;
    let gid = 0;

    textNodes.forEach(node => {
      let txt = node.nodeValue;
      let replaced = false;

      // token map for this node only
      const tokens = Object.create(null);

      for (const {re, defn} of matchers) {
        let count = 0;
        txt = txt.replace(re, (m) => {
          if (count >= MAX_PER_TERM || total >= MAX_TOTAL) return m;
          count++; total++; gid++;
          const key = `[[GID${gid}]]`;        // unique token that no matcher will hit
          tokens[key] = { visible: m, tip: defn };
          replaced = true;
          return key;                         // drop token, not the word/defn
        });
      }

      if (replaced) {
        // Now expand tokens to real spans (single pass).
        const tokenRe = /\[\[GID(\d+)\]\]/g;
        const html = txt.replace(tokenRe, (full) => {
          const rec = tokens[full];
          if (!rec) return full; // should not happen
          return `<span class="glossary-term" data-tip="${escapeHtml(rec.tip)}">${rec.visible}</span>`;
        });

        const wrapper = document.createElement("span");
        wrapper.innerHTML = html;
        node.replaceWith(wrapper);
      }
    });

    // Flip tooltip up if near bottom edge
    const els = document.querySelectorAll(".glossary-term[data-tip]");
    const vh = window.innerHeight || document.documentElement.clientHeight;
    els.forEach(el => {
      const r = el.getBoundingClientRect();
      if (vh - r.bottom < 120) el.setAttribute("data-tip-pos", "top");
    });
  }

  (async function main() {
    const data = await loadTerms();
    if (!data || !data.terms?.length) return;
    const matchers = buildMatchers(data);
    scanAndWrap(matchers);
  })();
})();
