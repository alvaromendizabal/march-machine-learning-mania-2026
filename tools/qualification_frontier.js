/* The offline frontier retains full denominators while focusing and ordering editions. */
(() => {
  "use strict";
  const summary = JSON.parse(document.getElementById("frontier-data").textContent);
  const focus = document.getElementById("frontier-focus");
  const order = document.getElementById("frontier-order");
  const chart = document.getElementById("frontier-chart");
  const live = document.getElementById("frontier-live");
  const nodes = new Map(Array.from(document.querySelectorAll(".frontier-edition"), node => [Number(node.dataset.season), node]));
  const labels = {
    qualified: "court and home context qualified",
    missing_home_only: "court qualified; home context unresolved",
    missing_court_only: "home context qualified; court unresolved",
    missing_both: "court and home context unqualified"
  };
  function render() {
    const state = focus.value;
    const count = row => state === "all" ? row.required - row.qualified : row[state];
    const rows = [...summary.editions].sort((a, b) => order.value === "gap" ? count(b) - count(a) || a.season - b.season : a.season - b.season);
    let shown = 0, selected = 0;
    for (const row of rows) {
      const node = nodes.get(row.season);
      node.hidden = state !== "all" && count(row) === 0;
      if (!node.hidden) { shown += 1; selected += count(row); }
      node.querySelector(".frontier-value").textContent = state === "all" ? `${row.qualified} / ${row.required} qualified` : `${count(row)} / ${row.required} in selected state`;
      for (const segment of node.querySelectorAll(".frontier-segment")) {
        segment.style.opacity = state === "all" || segment.dataset.state === state ? "1" : "0.24";
      }
      chart.appendChild(node);
    }
    const context = `${summary.totals.qualified} of ${summary.totals.required} rows qualified; ${summary.unknown} remain unknown across all nine editions.`;
    live.textContent = state === "all" ? `All ${shown} editions shown. ${context}` : shown ? `${shown} editions shown; ${selected} rows are ${labels[state]}. ${context}` : `No rows are classified as ${labels[state]}. ${context} Zero in this category does not prove the absence of standalone source witnesses.`;
  }
  focus.addEventListener("change", render);
  order.addEventListener("change", render);
  render();
})();
