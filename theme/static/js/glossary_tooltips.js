(function () {
  if (window.__glossaryTooltipsInitialized) return;
  window.__glossaryTooltipsInitialized = true;
  window.__GLOSSARY_BUILD__ = "bubble-v5";
  console.log("glossary_tooltips:", window.__GLOSSARY_BUILD__);

  const SKIP_TAGS = new Set(["SCRIPT","STYLE","NOSCRIPT","CODE","PRE","TEXTAREA","INPUT","KBD","SAMP"]);
  const MAX_PER_TERM = 20;
  const MAX_TOTAL = 1000;

  // ---- one floating bubble (no HTML injection) ------------------------------
  const bubble = document.createElement("div");
  Object.assign(bubble.style, {
    position: "fixed",
    zIndex: "99999",
    maxWidth: "min(420px, 85vw)",
    background: "#111827",
    color: "#F9FAFB",
    borderRadius: "8px",
    padding: "8px 10px",
    boxShadow: "0 10px 15px -3px rgba(0,0,0,.1), 0 4px 6px -4px rgba(0,0,0,.1)",
    fontSize: "14px",
    lineHeight: "1.25rem",
    pointerEvents: "none",
    display: "none",
    whiteSpace: "pre-wrap"
  });
  document.addEventListener("DOMContentLoaded", () => document.body.appendChild(bubble));

  function showBubble(el, text) {
    if (!text) return;
    bubble.textContent = text; // NO innerHTML
    bubble.style.display = "block";

    const r = el.getBoundingClientRect();
    const vw = window.innerWidth || document.documentElement.clientWidth;
    const vh = window.innerHeight || document.documentElement.clientHeight;

    const margin = 8;
    const belowTop = r.bottom + margin;
    const bottomSpace = vh - r.bottom;

    // position
    if (bottomSpace < 120) {
      bubble.style.top = Math.max(8, r.top - bubble.offsetHeight - margin) + "px"; // above
    } else {
      bubble.style.top = belowTop + "px"; // below
    }
    const left = Math.max(8, Math.min(r.left, vw - bubble.offsetWidth - 8));
    bubble.style.left = left + "px";
  }
  function hideBubble() { bubble.style.display = "none"; }

  // ---- load terms -----------------------------------------------------------
  async function loadTerms() {
    try {
      const res = await fetch("/glossary.json", { credentials: "same-origin" });
      if (!res.ok) return null;
      return await res.json();
    } catch { return null; }
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
        matchers.push({ re: new RegExp(pat, flags), defn });
      });
    });
    // longest first
    matchers.sort((a,b) => {
      const aa = a.re.source.replace(/\\b/g,"");
      const bb = b.re.source.replace(/\\b/g,"");
      return bb.length - aa.length;
    });
    return matchers;
  }

  // ---- text-node safe wrap (no innerHTML) -----------------------------------
  function wrapMatchesInTextNode(textNode, matchers, counters) {
    const parent = textNode.parentNode;
    if (!parent) return;

    const original = textNode.nodeValue;
    let cursor = 0;

    // collect hits
    const hits = [];
    matchers.forEach(({ re, defn }) => {
      re.lastIndex = 0;
      let m, perTerm = 0;
      while ((m = re.exec(original)) && counters.total < MAX_TOTAL) {
        if (perTerm >= MAX_PER_TERM) break;
        hits.push({ start: m.index, end: m.index + m[0].length, text: m[0], defn });
        perTerm++; counters.total++;
      }
    });
    if (!hits.length) return;

    // order + de-overlap
    hits.sort((a,b) => (a.start - b.start) || (b.end - b.start) - (a.end - a.start));
    const kept = [];
    let lastEnd = -1;
    for (const h of hits) {
      if (h.start >= lastEnd) { kept.push(h); lastEnd = h.end; }
    }

    const frag = document.createDocumentFragment();
    for (const h of kept) {
      if (h.start > cursor) {
        frag.appendChild(document.createTextNode(original.slice(cursor, h.start)));
      }
      const span = document.createElement("span");
      span.className = "glossary-term";
      span.dataset.tip = h.defn; // store plain text
      span.appendChild(document.createTextNode(h.text));

      // hover/touch handlers
      span.addEventListener("mouseenter", () => showBubble(span, span.dataset.tip));
      span.addEventListener("mouseleave", hideBubble);
      span.addEventListener("touchstart", (e) => { e.stopPropagation(); showBubble(span, span.dataset.tip); }, { passive: true });

      frag.appendChild(span);
      cursor = h.end;
    }
    if (cursor < original.length) {
      frag.appendChild(document.createTextNode(original.slice(cursor)));
    }

    parent.replaceChild(frag, textNode);
  }

  function scanAndWrap(matchers) {
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode(node) {
          const v = node.nodeValue;
          if (!v || !v.trim()) return NodeFilter.FILTER_REJECT;
          const p = node.parentNode;
          if (!p) return NodeFilter.FILTER_REJECT;
          if (p.nodeType === 1) {
            if (p.classList && p.classList.contains("glossary-term")) return NodeFilter.FILTER_REJECT;
            if (p.closest && p.closest("[data-glossary-skip]")) return NodeFilter.FILTER_REJECT;
            if (p.isContentEditable) return NodeFilter.FILTER_REJECT;
          }
          if (SKIP_TAGS.has(p.nodeName)) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );

    const textNodes = [];
    let n; while ((n = walker.nextNode())) textNodes.push(n);

    const counters = { total: 0 };
    textNodes.forEach(node => {
      if (counters.total >= MAX_TOTAL) return;
      wrapMatchesInTextNode(node, matchers, counters);
    });

    // hide bubble on outside tap/scroll
    document.addEventListener("touchstart", hideBubble, { passive: true });
    document.addEventListener("scroll", hideBubble, { passive: true });
  }

  (async function main() {
    const data = await loadTerms();
    if (!data || !data.terms || !data.terms.length) return;
    const matchers = buildMatchers(data);
    scanAndWrap(matchers);
  })();
})();
