/** Run the real Tournament Lab handlers and engine in a small dependency-free DOM. */
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const html = fs.readFileSync(path.join(root, "public-demo/index.html"), "utf8");
const css = fs.readFileSync(path.join(root, "public-demo/styles.css"), "utf8");
const scripts = Object.fromEntries(
  ["data", "engine", "app"].map((name) => [
    name,
    fs.readFileSync(path.join(root, `public-demo/${name}.js`), "utf8"),
  ]),
);
const plain = (value) => JSON.parse(JSON.stringify(value));
const close = (actual, expected, tolerance = 1e-12) =>
  assert.ok(
    Math.abs(actual - expected) <= tolerance,
    `${actual} != ${expected}`,
  );
const percentage = (value) => `${(100 * value).toFixed(1)}%`;
let checks = 0;
async function test(name, run) {
  await run();
  console.log(`ok ${++checks} - ${name}`);
}

function browser({
  missingEngine = false,
  mutateData = null,
  exportFailure = false,
} = {}) {
  const nodes = new Map();
  const timers = [];
  let exportedBlob = null,
    download = null,
    revoked = null;
  class Element {
    constructor(tag = "div") {
      this.tag = tag;
      this.handlers = {};
      this.children = [];
      this.attributes = {};
      this.style = {};
      this.value = "";
      this.hidden = false;
      this.disabled = false;
      this._text = "";
    }
    set id(value) {
      this._id = value;
      nodes.set(value, this);
    }
    get id() {
      return this._id;
    }
    set textContent(value) {
      this._text = String(value);
      this.children = [];
    }
    get textContent() {
      return (
        this._text +
        this.children
          .map((child) =>
            typeof child === "string" ? child : child.textContent,
          )
          .join("")
      );
    }
    append(...children) {
      this.children.push(...children);
    }
    replaceChildren(...children) {
      this._text = "";
      this.children = children;
      if (this.tag === "select") this.value = children[0]?.value ?? "";
    }
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    }
    addEventListener(name, callback) {
      this.handlers[name] = callback;
    }
    remove() {
      this.removed = true;
    }
    click() {
      if (this.disabled) return;
      this.handlers.click?.();
      if (this.download) download = this;
    }
  }
  for (const match of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"[^>]*>/g)) {
    const element = new Element(match[1]);
    element.id = match[2];
    element.hidden = /\bhidden\b/.test(match[0]);
  }
  const sandbox = {
    console,
    Blob,
    URL: {
      createObjectURL(blob) {
        if (exportFailure) throw new Error("fixture download unavailable");
        exportedBlob = blob;
        return "blob:synthetic-fixture";
      },
      revokeObjectURL(url) {
        revoked = url;
      },
    },
    setTimeout(callback) {
      timers.push(callback);
      return timers.length;
    },
    document: {
      getElementById: (id) => nodes.get(id),
      createElement: (tag) => new Element(tag),
      body: new Element("body"),
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(scripts.data, sandbox, { filename: "data.js" });
  if (mutateData) mutateData(sandbox.MARCH_TOURNAMENT_DATA);
  if (!missingEngine)
    vm.runInContext(scripts.engine, sandbox, { filename: "engine.js" });
  vm.runInContext(scripts.app, sandbox, { filename: "app.js" });
  const ui = {
    nodes,
    sandbox,
    el: (id) => {
      assert.ok(nodes.has(id), `Element exists: ${id}`);
      return nodes.get(id);
    },
    click: (id) => {
      ui.el(id).click();
    },
    change: (id, value, event = "change") => {
      const element = ui.el(id);
      element.value = String(value);
      assert.equal(
        typeof element.handlers[event],
        "function",
        `${id} has ${event} handler`,
      );
      element.handlers[event]();
    },
    async export() {
      ui.click("export");
      assert.ok(exportedBlob, "JSON was created");
      return JSON.parse(await exportedBlob.text());
    },
    downloaded: () => download,
    blob: () => exportedBlob,
    finishTimers: () => {
      for (const callback of timers.splice(0)) callback();
      return revoked;
    },
    data: () => sandbox.MARCH_TOURNAMENT_DATA,
    engine: () => sandbox.MarchTournamentEngine,
  };
  return ui;
}
function descendants(node) {
  return [
    node,
    ...node.children.flatMap((child) =>
      typeof child === "string" ? [] : descendants(child),
    ),
  ];
}
function buttonsIn(ui, id) {
  return descendants(ui.el(id)).filter((node) => node.tag === "button");
}

await test("initial bracket renders all eight real marginal probabilities in each of three stages", () => {
  const ui = browser();
  const result = ui.engine().analyze(ui.data());
  assert.equal(ui.el("error").hidden, true);
  assert.equal(buttonsIn(ui, "bracket").length, 24);
  assert.equal(buttonsIn(ui, "probability-bars").length, 8);
  for (const team of result.teams)
    for (let round = 0; round < 3; round++) {
      const button = ui.el(`bracket-${round}-${team.id}`);
      assert.equal(
        button.children[1].textContent,
        percentage(team.advance[round]),
      );
      assert.match(button.attributes["aria-label"], /Select team/);
    }
  assert.equal(ui.el("total-probability").textContent, "100.0%");
  assert.equal(ui.el("export").disabled, false);
});

await test("rating edits preserve the public fixture and only adjust the selected team's input", async () => {
  const ui = browser(),
    original = plain(ui.data());
  ui.change("rating", 120, "input");
  const exported = await ui.export();
  assert.deepEqual(exported.inputs.settings.adjustments, { harbor: 120 });
  assert.equal(
    exported.analysis.teams.find((team) => team.id === "harbor")
      .adjusted_rating,
    1840,
  );
  for (const team of exported.analysis.teams.filter(
    (team) => team.id !== "harbor",
  ))
    assert.equal(team.adjusted_rating, team.rating);
  assert.deepEqual(plain(ui.data()), original);
  assert.equal(ui.el("rating-current").textContent, "1840");
  assert.equal(ui.el("preset-rated").attributes["aria-pressed"], "false");
});

await test("each team's adjustment survives selection changes and native range events", async () => {
  const ui = browser();
  ui.change("rating", 100, "input");
  ui.change("team", "cedar");
  assert.equal(ui.el("rating").value, "0");
  ui.change("rating", -50, "input");
  ui.change("team", "harbor");
  assert.equal(ui.el("rating").value, "100");
  assert.deepEqual((await ui.export()).inputs.settings.adjustments, {
    cedar: -50,
    harbor: 100,
  });
});

await test("both bracket and probability bars select teams through their actual click handlers", () => {
  const ui = browser();
  ui.click("bracket-1-meadow");
  assert.equal(ui.el("team").value, "meadow");
  for (let round = 0; round < 3; round++)
    assert.equal(
      ui.el(`bracket-${round}-meadow`).attributes["aria-pressed"],
      "true",
    );
  assert.equal(ui.el("bar-meadow").attributes["aria-pressed"], "true");
  ui.click("bar-copper");
  assert.equal(ui.el("team").value, "copper");
  assert.match(ui.el("selected-summary").textContent, /^Copper Owls/);
});

await test("the even-field preset yields exact half, quarter and eighth probabilities", async () => {
  const ui = browser();
  ui.click("preset-even");
  const exported = await ui.export();
  for (const team of exported.analysis.teams) {
    assert.equal(team.adjusted_rating, 1590);
    assert.deepEqual(team.advance, [0.5, 0.25, 0.125]);
  }
  assert.equal(ui.el("preset-even").attributes["aria-pressed"], "true");
  assert.equal(ui.el("probability-a").textContent, "50.0%");
});

await test("the challenger preset resets other adjustments and materially changes the selected team's forecast", async () => {
  const ui = browser();
  const before = ui
    .engine()
    .analyze(ui.data())
    .teams.find((team) => team.id === "meadow").champion_probability;
  ui.click("preset-even");
  ui.click("preset-challenger");
  const exported = await ui.export();
  assert.deepEqual(exported.inputs.settings.adjustments, { meadow: 250 });
  assert.equal(ui.el("team").value, "meadow");
  assert.equal(ui.el("rating").value, "250");
  assert.ok(
    exported.analysis.teams.find((team) => team.id === "meadow")
      .champion_probability > before,
  );
});

await test("stage selection uses actual advance probabilities and fixed 0–100% bar scales", async () => {
  const ui = browser();
  for (const round of [0, 1, 2]) {
    ui.change("round", round);
    const exported = await ui.export();
    for (const team of exported.analysis.teams) {
      const bar = ui.el(`bar-${team.id}`);
      close(
        parseFloat(bar.children[1].children[0].style.width),
        100 * team.advance[round],
      );
      assert.equal(
        bar.children[2].textContent,
        percentage(team.advance[round]),
      );
    }
    assert.ok(
      ui.el("round-note").textContent.includes(`${[400, 200, 100][round]}.0%`),
    );
    assert.equal(exported.selection.stage, round);
  }
});

await test("higher temperature softens a non-tied direct matchup without changing team ratings", async () => {
  const ui = browser();
  ui.change("temperature", 100, "input");
  const low = await ui.export();
  ui.change("temperature", 800, "input");
  const high = await ui.export();
  assert.ok(
    Math.abs(high.selected_matchup.probability_a - 0.5) <
      Math.abs(low.selected_matchup.probability_a - 0.5),
  );
  assert.deepEqual(
    low.analysis.teams.map((team) => team.adjusted_rating),
    high.analysis.teams.map((team) => team.adjusted_rating),
  );
  assert.equal(ui.el("temperature-value").textContent, "800");
});

await test("matchup changes obey swap symmetry and have an exact-width accessible comparison bar", async () => {
  const ui = browser();
  const original = await ui.export();
  ui.change("team-a", "copper");
  ui.change("team-b", "harbor");
  const swapped = await ui.export();
  close(
    swapped.selected_matchup.probability_a,
    1 - original.selected_matchup.probability_a,
  );
  close(
    parseFloat(ui.el("matchup-fill").style.width),
    swapped.selected_matchup.probability_a * 100,
  );
  assert.match(
    ui.el("matchup-bar").attributes["aria-label"],
    /Copper Owls.*Harbor Foxes/,
  );
});

await test("invalid same-team matchups hide stale values and block export while preserving the valid bracket", () => {
  const ui = browser();
  ui.change("team-b", "harbor");
  assert.equal(ui.el("matchup-output").hidden, true);
  assert.equal(ui.el("matchup-error").hidden, false);
  assert.equal(ui.el("export").disabled, true);
  assert.equal(buttonsIn(ui, "bracket").length, 24);
  ui.click("export");
  assert.equal(ui.blob(), null);
  ui.change("team-b", "cedar");
  assert.equal(ui.el("matchup-output").hidden, false);
  assert.equal(ui.el("matchup-error").hidden, true);
  assert.equal(ui.el("export").disabled, false);
});

await test("invalid numeric inputs fail closed, remove previous results and recover through reset", () => {
  for (const [id, value] of [
    ["temperature", 0],
    ["temperature", ""],
    ["temperature", "NaN"],
    ["rating", 301],
    ["rating", "Infinity"],
  ]) {
    const ui = browser();
    ui.change(id, value, "input");
    assert.equal(ui.el("error").hidden, false, `${id}=${value}`);
    assert.equal(ui.el("bracket").children.length, 0);
    assert.equal(ui.el("probability-bars").children.length, 0);
    assert.equal(ui.el("total-probability").textContent, "—");
    assert.equal(ui.el("matchup-output").hidden, true);
    assert.equal(ui.el("export").disabled, true);
    ui.click("reset");
    assert.equal(ui.el("error").hidden, true);
    assert.equal(buttonsIn(ui, "bracket").length, 24);
  }
});

await test("reset restores every scenario, stage and matchup control", async () => {
  const ui = browser();
  ui.click("preset-challenger");
  ui.change("temperature", 700, "input");
  ui.change("round", 0);
  ui.change("team-a", "mesa");
  ui.click("reset");
  const exported = await ui.export();
  assert.deepEqual(exported.inputs.settings, {
    temperature: 400,
    adjustments: {},
  });
  assert.deepEqual(exported.selection, {
    team: "harbor",
    stage: 2,
    preset: "rated",
  });
  assert.equal(exported.selected_matchup.team_a, "harbor");
  assert.equal(exported.selected_matchup.team_b, "copper");
});

await test("JSON export replays every exact probability and keeps fictional outcome evidence explicit", async () => {
  const ui = browser();
  ui.change("rating", 70, "input");
  const artifact = await ui.export();
  assert.equal(artifact.evidence_type, "SYNTHETIC_ONLY");
  assert.equal(artifact.analysis.provenance.training_fits, 0);
  assert.equal(artifact.analysis.provenance.private_assets_used, false);
  assert.equal(artifact.analysis.diagnostics.games, 16);
  assert.equal(artifact.analysis.diagnostics.bins.length, 5);
  assert.equal(artifact.illustrative_scoring.outcomes.length, 16);
  assert.deepEqual(Object.keys(artifact.inputs).sort(), [
    "bracket",
    "settings",
    "teams",
  ]);
  assert.deepEqual(
    artifact.analysis,
    plain(ui.engine().analyze(ui.data(), artifact.inputs.settings)),
  );
  assert.equal(ui.downloaded().download, "synthetic-tournament-analysis.json");
  assert.equal(ui.downloaded().removed, true);
  assert.equal(ui.finishTimers(), "blob:synthetic-fixture");
});

await test("changed fictional outcomes affect only scoring diagnostics, never bracket predictions", async () => {
  const original = browser();
  const changed = browser({
    mutateData(data) {
      for (const outcome of data.scoring.outcomes) {
        const request = data.scoring.requests.find(
          (row) => row.game_id === outcome.game_id,
        );
        outcome.winner_id =
          outcome.winner_id === request.team_a
            ? request.team_b
            : request.team_a;
      }
    },
  });
  const before = await original.export(),
    after = await changed.export();
  assert.deepEqual(after.analysis.teams, before.analysis.teams);
  assert.deepEqual(after.selected_matchup, before.selected_matchup);
  assert.deepEqual(
    after.analysis.scoring_predictions,
    before.analysis.scoring_predictions,
  );
  assert.notDeepEqual(after.analysis.diagnostics, before.analysis.diagnostics);
});

await test("missing engine shows a useful error and never enables invented results or export", () => {
  const ui = browser({ missingEngine: true });
  assert.equal(ui.el("error").hidden, false);
  assert.match(ui.el("error").textContent, /local engine/);
  assert.equal(ui.el("export").disabled, true);
  assert.equal(ui.el("bracket").children.length, 0);
});

await test("download failures are visible without corrupting current calculations", () => {
  const ui = browser({ exportFailure: true });
  ui.click("export");
  assert.match(ui.el("status").textContent, /Export unavailable/);
  assert.equal(ui.blob(), null);
  assert.equal(buttonsIn(ui, "bracket").length, 24);
  assert.equal(ui.el("error").hidden, true);
});

await test("fixture display names remain literal text rather than HTML", () => {
  const ui = browser({
    mutateData(data) {
      data.teams[0].name = "<img src=x onerror=alert(1)>";
    },
  });
  assert.equal(ui.el("error").hidden, true);
  assert.ok(
    ui
      .el("bracket-0-harbor")
      .textContent.includes("<img src=x onerror=alert(1)>"),
  );
  assert.equal(
    descendants(ui.el("bracket")).filter((node) => node.tag === "img").length,
    0,
  );
});

await test("hidden states, visible labels, focus styles and local-only assets are preserved", () => {
  assert.match(css, /\[hidden\]\s*\{\s*display\s*:\s*none\s*!important/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /prefers-reduced-motion/);
  for (const match of css.matchAll(/font(?:-size)?\s*:\s*(\d+(?:\.\d+)?)px/g))
    assert.ok(Number(match[1]) >= 12, `Readable font ${match[1]}px`);
  for (const match of html.matchAll(
    /<(?:script|link)\b[^>]*(?:src|href)="([^"]+)"[^>]*>/g,
  )) {
    if (match[0].includes('rel="canonical"')) continue;
    assert.ok(!/^https?:/.test(match[1]), `Local runtime asset: ${match[1]}`);
  }
  assert.doesNotMatch(
    scripts.app,
    /\b(?:fetch|XMLHttpRequest|WebSocket|innerHTML)\b/,
  );
  for (const id of [
    "team",
    "rating",
    "temperature",
    "round",
    "team-a",
    "team-b",
  ])
    assert.ok(html.includes(`for="${id}"`), `Visible label for ${id}`);
  assert.match(html, /role="status"/);
  assert.match(html, /role="alert"/);
});

console.log(
  `PASS: ${checks} Tournament Lab UI checks (real handlers + real engine; no browser renderer).`,
);
