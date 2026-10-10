import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const context = vm.createContext({});
for (const name of ["data.js", "engine.js"])
  vm.runInContext(
    fs.readFileSync(path.join(root, "public-demo", name), "utf8"),
    context,
    { filename: name },
  );
const engine = context.MarchTournamentEngine,
  data = context.MARCH_TOURNAMENT_DATA;
const plain = (value) => JSON.parse(JSON.stringify(value));
let tests = 0;
function test(name, run) {
  run();
  tests++;
  console.log(`PASS ${name}`);
}
function near(actual, expected, tolerance = 1e-12) {
  assert.ok(
    Math.abs(actual - expected) <= tolerance,
    `${actual} != ${expected}`,
  );
}
const scenarios = [
  {},
  { temperature: 100, adjustments: { meadow: 250 } },
  { temperature: 800, adjustments: { harbor: -200, cedar: 120 } },
  { temperature: 1 },
  { temperature: 2000 },
];

test("authored fixture has eight unique fictional teams, fixed seed bracket and separate outcomes", () => {
  assert.equal(engine.validateData(data), true);
  assert.equal(data.teams.length, 8);
  assert.equal(new Set(data.teams.map((team) => team.id)).size, 8);
  assert.deepEqual(
    plain(
      data.bracket.map((id) => data.teams.find((team) => team.id === id).seed),
    ),
    [1, 8, 4, 5, 2, 7, 3, 6],
  );
  assert.equal(data.scoring.requests.length, 16);
  assert.equal(data.scoring.outcomes.length, 16);
  assert.ok(
    data.scoring.requests.every(
      (row) => Object.keys(row).sort().join(",") === "game_id,team_a,team_b",
    ),
  );
  assert.equal(data.provenance.training_fits, 0);
  assert.equal(data.provenance.official_evaluation, false);
});
test("neutral logistic probabilities match hand cases and remain symmetric", () => {
  assert.equal(engine.winProbability(1500, 1500, 400), 0.5);
  near(engine.winProbability(1900, 1500, 400), 10 / 11);
  near(engine.winProbability(1500, 1900, 400), 1 / 11);
  for (const [a, b] of [
    [0, 3000],
    [1700, 1600],
    [1437.5, 1921.25],
    [3000, 0],
  ])
    for (const t of [1, 100, 400, 2000]) {
      const p = engine.winProbability(a, b, t),
        q = engine.winProbability(b, a, t);
      assert.ok(Number.isFinite(p) && p >= 0 && p <= 1);
      near(p + q, 1);
    }
});
test("temperature changes sensitivity without reversing favorites; only rating differences matter", () => {
  const cold = engine.winProbability(1720, 1460, 100),
    warm = engine.winProbability(1720, 1460, 800);
  assert.ok(cold > warm && warm > 0.5);
  near(
    engine.winProbability(1520, 1260, 400),
    engine.winProbability(1720, 1460, 400),
  );
  near(
    engine.winProbability(1720, 1460, 400),
    engine.winProbability(172, 146, 40),
  );
});
test("equal strengths yield exact half, quarter and eighth advancement for every seed", () => {
  const teams = data.teams.map((team) => ({ ...team, rating: 1500 }));
  const result = engine.forecast(teams, data.bracket);
  for (const team of result.teams)
    assert.deepEqual(plain(team.advance), [0.5, 0.25, 0.125]);
  assert.deepEqual(
    plain(result.rounds.map((round) => round.probability_sum)),
    [4, 2, 1],
  );
});
test("one stronger team wins the tournament with the hand-derived p cubed", () => {
  const teams = data.teams.map((team) => ({
    ...team,
    rating: team.id === "harbor" ? 1900 : 1500,
  }));
  const result = engine.forecast(teams, data.bracket),
    strong = result.teams.find((team) => team.id === "harbor");
  near(strong.advance[0], 10 / 11);
  near(strong.advance[1], (10 / 11) ** 2);
  near(strong.advance[2], (10 / 11) ** 3);
});

// Independent exhaustive enumerator: materialize all 128 complete seven-game
// outcomes and their path products, rather than using the engine's DP recurrence.
function enumerate(teams, bracket, settings) {
  const ratings = new Map(
    teams.map((team) => [
      team.id,
      team.rating + (settings.adjustments?.[team.id] ?? 0),
    ]),
  );
  const t = settings.temperature ?? 400;
  function visit(ids) {
    if (ids.length === 1) return [{ winner: ids[0], weight: 1, wins: {} }];
    const middle = ids.length / 2,
      left = visit(ids.slice(0, middle)),
      right = visit(ids.slice(middle)),
      paths = [];
    for (const a of left)
      for (const b of right) {
        const p =
          1 / (1 + 10 ** ((ratings.get(b.winner) - ratings.get(a.winner)) / t));
        for (const [winner, conditional] of [
          [a.winner, p],
          [b.winner, 1 - p],
        ]) {
          const wins = { ...a.wins, ...b.wins };
          wins[winner] = (wins[winner] ?? 0) + 1;
          paths.push({
            winner,
            weight: a.weight * b.weight * conditional,
            wins,
          });
        }
      }
    return paths;
  }
  return visit(bracket);
}
test("dynamic programming equals an independent enumeration of all 128 tournament outcomes", () => {
  for (const settings of scenarios.slice(0, 3)) {
    const result = engine.forecast(data.teams, data.bracket, settings),
      paths = enumerate(data.teams, data.bracket, settings);
    assert.equal(paths.length, 128);
    near(
      paths.reduce((sum, item) => sum + item.weight, 0),
      1,
    );
    for (const team of result.teams)
      for (let round = 1; round <= 3; round++) {
        const expected = paths
          .filter((item) => (item.wins[team.id] ?? 0) >= round)
          .reduce((sum, item) => sum + item.weight, 0);
        near(team.advance[round - 1], expected);
      }
  }
});
test("round totals conserve four, two and one survivors and probabilities decrease by round", () => {
  for (const settings of scenarios) {
    const result = engine.analyze(data, settings);
    result.rounds.forEach((round, index) =>
      near(round.probability_sum, [4, 2, 1][index]),
    );
    assert.equal(result.checks.algorithm, "exact_dynamic_programming");
    assert.equal(result.matchups.length, 56);
    for (const team of result.teams) {
      assert.ok(
        team.advance[0] >= team.advance[1] &&
          team.advance[1] >= team.advance[2],
      );
      assert.ok(
        team.advance.every((p) => p >= 0 && p <= 1 && Number.isFinite(p)),
      );
    }
  }
});
test("a rating intervention changes its forecast while preserving the fixed bracket", () => {
  const baseline = engine.analyze(data),
    adjusted = engine.analyze(data, { adjustments: { meadow: 250 } });
  assert.deepEqual(plain(adjusted.bracket), plain(baseline.bracket));
  assert.ok(
    adjusted.teams.find((team) => team.id === "meadow").champion_probability >
      baseline.teams.find((team) => team.id === "meadow").champion_probability,
  );
  for (const team of adjusted.teams)
    assert.equal(
      team.adjusted_rating,
      team.rating + (team.id === "meadow" ? 250 : 0),
    );
  near(
    engine.matchup(data, "meadow", "harbor", { adjustments: { meadow: 250 } }),
    adjusted.matchups.find(
      (row) => row.team_a === "meadow" && row.team_b === "harbor",
    ).probability_a,
  );
});
test("changing every synthetic outcome leaves all forecasts and game predictions unchanged", () => {
  const changed = plain(data);
  changed.scoring.outcomes = changed.scoring.outcomes.map((row) => {
    const request = changed.scoring.requests.find(
      (game) => game.game_id === row.game_id,
    );
    return {
      ...row,
      winner_id:
        row.winner_id === request.team_a ? request.team_b : request.team_a,
    };
  });
  const original = engine.analyze(data),
    modified = engine.analyze(changed);
  assert.deepEqual(plain(original.teams), plain(modified.teams));
  assert.deepEqual(plain(original.matchups), plain(modified.matchups));
  assert.deepEqual(
    plain(original.scoring_predictions),
    plain(modified.scoring_predictions),
  );
  assert.notEqual(original.diagnostics.brier, modified.diagnostics.brier);
  assert.throws(
    () =>
      engine.predictGames(data.teams, [
        { ...data.scoring.requests[0], winner_id: "harbor" },
      ]),
    /Identifier-only/,
  );
});
test("Brier, log loss and empirical bins agree with a two-game hand calculation", () => {
  const predictions = [
    { game_id: "hand-a", team_a: "alpha", team_b: "beta", probability_a: 0.75 },
    { game_id: "hand-b", team_a: "alpha", team_b: "beta", probability_a: 0.25 },
  ];
  const outcomes = [
    { game_id: "hand-b", winner_id: "beta" },
    { game_id: "hand-a", winner_id: "alpha" },
  ];
  const metrics = engine.score(predictions, outcomes);
  assert.equal(metrics.games, 2);
  assert.equal(metrics.brier, 0.0625);
  near(metrics.log_loss, -Math.log(0.75));
  assert.equal(metrics.bins[1].mean_probability, 0.25);
  assert.equal(metrics.bins[1].observed_frequency, 0);
  assert.equal(metrics.bins[3].mean_probability, 0.75);
  assert.equal(metrics.bins[3].observed_frequency, 1);
  assert.equal(metrics.bins[0].mean_probability, null);
  assert.equal(metrics.bins[0].observed_frequency, null);
  const flipped = predictions.map((row) => ({
    ...row,
    team_a: row.team_b,
    team_b: row.team_a,
    probability_a: 1 - row.probability_a,
  }));
  near(engine.score(flipped, outcomes).brier, metrics.brier);
  near(engine.score(flipped, outcomes).log_loss, metrics.log_loss);
});
test("empirical bins include exact boundary probabilities once and log loss clips only its diagnostic", () => {
  const probabilities = [0, 0.2, 0.4, 0.6, 0.8, 1];
  const predictions = probabilities.map((p, index) => ({
    game_id: `boundary-${index}`,
    team_a: "alpha",
    team_b: "beta",
    probability_a: p,
  }));
  const outcomes = predictions.map((row) => ({
    game_id: row.game_id,
    winner_id: "alpha",
  }));
  const metrics = engine.score(predictions, outcomes);
  assert.deepEqual(
    plain(metrics.bins.map((bin) => bin.count)),
    [1, 1, 1, 1, 2],
  );
  near(
    metrics.brier,
    probabilities.reduce((sum, p) => sum + (p - 1) ** 2, 0) / 6,
  );
  assert.ok(Number.isFinite(metrics.log_loss));
  assert.equal(metrics.log_loss_epsilon, 1e-15);
  assert.equal(predictions[0].probability_a, 0);
  assert.equal(predictions[5].probability_a, 1);
});
test("game keys align by identity, reject duplicates or missing outcomes and preserve request order", () => {
  const predictions = engine.predictGames(
    data.teams,
    [...data.scoring.requests].reverse(),
  );
  assert.deepEqual(
    plain(predictions.map((row) => row.game_id)),
    plain([...data.scoring.requests].reverse().map((row) => row.game_id)),
  );
  near(
    engine.score(predictions, data.scoring.outcomes).brier,
    engine.analyze(data).diagnostics.brier,
  );
  for (const outcomes of [
    [],
    data.scoring.outcomes.slice(1),
    [...data.scoring.outcomes, data.scoring.outcomes[0]],
    data.scoring.outcomes.map((row, i) =>
      i ? row : { ...row, winner_id: "unknown" },
    ),
  ])
    assert.throws(() => engine.score(predictions, outcomes));
  for (const rows of [
    [],
    predictions.slice(1),
    [...predictions, predictions[0]],
    predictions.map((row, i) => (i ? row : { ...row, probability_a: NaN })),
    predictions.map((row, i) => (i ? row : { ...row, probability_a: 1.1 })),
  ])
    assert.throws(() => engine.score(rows, data.scoring.outcomes));
});
test("invalid teams, partitions, settings and attached outcome fields reject visibly", () => {
  for (const mutate of [
    (d) => d.teams.pop(),
    (d) => (d.teams[1].id = d.teams[0].id),
    (d) => (d.teams[1].seed = 1),
    (d) => (d.teams[0].rating = Infinity),
    (d) => (d.teams[0].rating = "1700"),
    (d) => d.bracket.reverse(),
    (d) => (d.bracket[0] = d.bracket[1]),
    (d) => (d.provenance.private_assets_used = true),
    (d) => (d.scoring.requests[0].outcome = 1),
    (d) => (d.scoring.requests[0].team_b = d.scoring.requests[0].team_a),
    (d) => (d.scoring.requests[0] = d.scoring.requests[1]),
  ]) {
    const bad = plain(data);
    mutate(bad);
    assert.throws(() => engine.analyze(bad));
  }
  for (const settings of [
    { temperature: 0 },
    { temperature: NaN },
    { temperature: 2001 },
    { adjustments: { harbor: 301 } },
    { adjustments: { unknown: 1 } },
    { adjustments: { harbor: "20" } },
    { temperature: 400, hidden_recipe: 1 },
  ])
    assert.throws(() => engine.analyze(data, settings));
  assert.throws(() => engine.matchup(data, "harbor", "harbor"));
  assert.throws(() => engine.matchup(data, "harbor", "missing"));
  for (const args of [
    [NaN, 1500, 400],
    [1500, Infinity, 400],
    [-1, 1500, 400],
    [1500, 1500, 0],
  ])
    assert.throws(() => engine.winProbability(...args));
});
test("deterministic forecasts do not mutate inputs or invoke randomness, network or hidden model assets", () => {
  const before = JSON.stringify(data),
    one = JSON.stringify(
      engine.analyze(data, { temperature: 350, adjustments: { summit: 125 } }),
    );
  assert.equal(
    JSON.stringify(
      engine.analyze(data, { temperature: 350, adjustments: { summit: 125 } }),
    ),
    one,
  );
  assert.equal(JSON.stringify(data), before);
  assert.ok(
    JSON.parse(one).limitations.some((text) =>
      text.includes("not fitted or selected"),
    ),
  );
  const source = fs.readFileSync(
    path.join(root, "public-demo/engine.js"),
    "utf8",
  );
  assert.doesNotMatch(
    source,
    /\bfetch\s*\(|XMLHttpRequest|WebSocket|Math\.random|\beval\s*\(/,
  );
  assert.ok(
    fs.statSync(path.join(root, "public-demo/data.js")).size +
      Buffer.byteLength(source) <
      200000,
  );
});
console.log(
  JSON.stringify(
    {
      status: "PASS",
      tests,
      scope:
        "Exact DP versus exhaustive 128-path enumeration and independent hand cases; synthetic forecasts and diagnostics only.",
    },
    null,
    2,
  ),
);
