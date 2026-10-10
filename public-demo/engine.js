/* Transparent synthetic tournament probabilities. No fitted model or private assets. */
(function (root) {
  "use strict";
  const DEFAULT_TEMPERATURE = 400;
  const LOG_LOSS_EPSILON = 1e-15;
  const SEED_ORDER = [1, 8, 4, 5, 2, 7, 3, 6];
  const ROUND_NAMES = ["Semifinal", "Final", "Champion"];
  function fail(message) {
    throw new Error(message);
  }
  function object(value, label) {
    if (!value || typeof value !== "object" || Array.isArray(value))
      fail(`${label} must be an object`);
  }
  function exactKeys(value, keys, label) {
    object(value, label);
    if (Object.keys(value).sort().join("|") !== [...keys].sort().join("|"))
      fail(`${label} keys do not match the public contract`);
  }
  function id(value, label) {
    if (typeof value !== "string" || !/^[a-z][a-z0-9-]{0,31}$/.test(value))
      fail(`${label} must be a short public identifier`);
    return value;
  }
  function finite(value, label) {
    if (typeof value !== "number" || !Number.isFinite(value))
      fail(`${label} must be finite`);
    return value;
  }
  function rating(value) {
    finite(value, "Rating");
    if (value < 0 || value > 3000) fail("Rating must be in 0..3000");
    return value;
  }
  function temperature(value) {
    finite(value, "Temperature");
    if (value < 1 || value > 2000) fail("Temperature must be in 1..2000");
    return value;
  }
  function winProbability(ratingA, ratingB, scale = DEFAULT_TEMPERATURE) {
    rating(ratingA);
    rating(ratingB);
    temperature(scale);
    const z = ((ratingA - ratingB) * Math.LN10) / scale;
    // Sign-specific evaluation avoids overflow at large rating differences.
    if (z >= 0) return 1 / (1 + Math.exp(-z));
    const exponential = Math.exp(z);
    return exponential / (1 + exponential);
  }
  function validateTeams(teams, bracket) {
    if (!Array.isArray(teams) || teams.length !== 8)
      fail("Exactly eight fictional teams are required");
    const ids = new Set(),
      seeds = new Set();
    for (const team of teams) {
      exactKeys(
        team,
        ["id", "name", "short", "seed", "rating", "color"],
        "Team",
      );
      id(team.id, "Team ID");
      if (ids.has(team.id)) fail("Team IDs must be unique");
      ids.add(team.id);
      if (
        !Number.isInteger(team.seed) ||
        team.seed < 1 ||
        team.seed > 8 ||
        seeds.has(team.seed)
      )
        fail("Seeds must be unique integers 1..8");
      seeds.add(team.seed);
      if (
        typeof team.name !== "string" ||
        !team.name.trim() ||
        team.name.length > 60 ||
        typeof team.short !== "string" ||
        !/^[A-Z]{2,4}$/.test(team.short)
      )
        fail("Team display labels are invalid");
      if (typeof team.color !== "string" || !/^#[0-9a-f]{6}$/i.test(team.color))
        fail("Team color must be a six-digit hex value");
      rating(team.rating);
    }
    if (
      !Array.isArray(bracket) ||
      bracket.length !== 8 ||
      new Set(bracket).size !== 8 ||
      bracket.some((value) => !ids.has(value))
    )
      fail("Bracket must contain every team exactly once");
    const byId = new Map(teams.map((team) => [team.id, team]));
    if (
      bracket.some((value, index) => byId.get(value).seed !== SEED_ORDER[index])
    )
      fail("Bracket must preserve the fixed 1–8, 4–5, 2–7, 3–6 seed order");
    return byId;
  }
  function resolveSettings(settings, byId) {
    object(settings, "Settings");
    if (
      Object.keys(settings).some(
        (key) => !["temperature", "adjustments"].includes(key),
      )
    )
      fail("Unknown scenario setting");
    const scale = temperature(settings.temperature ?? DEFAULT_TEMPERATURE);
    const adjustments = settings.adjustments ?? {};
    object(adjustments, "Rating adjustments");
    const resolved = Object.create(null);
    for (const key of Object.keys(adjustments).sort()) {
      if (!byId.has(key)) fail("Rating adjustment references an unknown team");
      const delta = finite(adjustments[key], "Rating adjustment");
      if (Math.abs(delta) > 300) fail("Rating adjustment must be in −300..300");
      rating(byId.get(key).rating + delta);
      resolved[key] = delta;
    }
    return { temperature: scale, adjustments: resolved };
  }
  function forecast(teams, bracket, settings = {}) {
    const byId = validateTeams(teams, bracket),
      resolved = resolveSettings(settings, byId);
    const adjusted = new Map(
      teams.map((team) => [
        team.id,
        team.rating + (resolved.adjustments[team.id] ?? 0),
      ]),
    );
    const p = (a, b) =>
      winProbability(adjusted.get(a), adjusted.get(b), resolved.temperature);
    const advance = new Map(teams.map((team) => [team.id, []]));
    let previous = new Map(teams.map((team) => [team.id, 1]));
    // For each team, integrate over mutually exclusive opponent winners from
    // the other half of its bracket block, then multiply by its reach chance.
    for (let round = 0; round < 3; round++) {
      const size = 2 ** (round + 1),
        half = size / 2,
        current = new Map();
      bracket.forEach((team, index) => {
        const block = Math.floor(index / size) * size;
        const opponentStart = index - block < half ? block + half : block;
        let winGivenReach = 0;
        for (let other = opponentStart; other < opponentStart + half; other++) {
          const opponent = bracket[other];
          winGivenReach += previous.get(opponent) * p(team, opponent);
        }
        const probability = previous.get(team) * winGivenReach;
        current.set(team, probability);
        advance.get(team).push(probability);
      });
      previous = current;
    }
    const results = teams.map((team) => ({
      ...team,
      adjusted_rating: adjusted.get(team.id),
      advance: [...advance.get(team.id)],
      champion_probability: advance.get(team.id)[2],
    }));
    const rounds = ROUND_NAMES.map((name, index) => ({
      round: index + 1,
      name,
      probability_sum: results.reduce(
        (sum, team) => sum + team.advance[index],
        0,
      ),
      expected_survivors: 2 ** (2 - index),
    }));
    const matchups = [];
    for (const first of teams)
      for (const second of teams)
        if (first.id !== second.id)
          matchups.push({
            team_a: first.id,
            team_b: second.id,
            probability_a: p(first.id, second.id),
          });
    const checks = {
      probabilities_valid: results.every((team) =>
        team.advance.every(
          (value) => Number.isFinite(value) && value >= 0 && value <= 1,
        ),
      ),
      round_conservation: rounds.every(
        (round) =>
          Math.abs(round.probability_sum - round.expected_survivors) < 1e-12,
      ),
      advance_nonincreasing: results.every((team) =>
        team.advance.every(
          (value, index) =>
            index === 0 || value <= team.advance[index - 1] + 1e-15,
        ),
      ),
      champion_sum_one: Math.abs(rounds[2].probability_sum - 1) < 1e-12,
      outcomes_not_passed_to_forecast: true,
      algorithm: "exact_dynamic_programming",
    };
    if (
      !checks.probabilities_valid ||
      !checks.round_conservation ||
      !checks.advance_nonincreasing
    )
      fail("Tournament probability invariants failed");
    return {
      settings: resolved,
      teams: results,
      bracket: [...bracket],
      rounds,
      matchups,
      checks,
    };
  }
  function matchup(data, teamA, teamB, settings = {}) {
    const byId = validateTeams(data.teams, data.bracket),
      resolved = resolveSettings(settings, byId);
    if (!byId.has(teamA) || !byId.has(teamB) || teamA === teamB)
      fail("Matchup needs two distinct known teams");
    return winProbability(
      byId.get(teamA).rating + (resolved.adjustments[teamA] ?? 0),
      byId.get(teamB).rating + (resolved.adjustments[teamB] ?? 0),
      resolved.temperature,
    );
  }
  function predictGames(teams, requests, settings = {}) {
    // Build canonical seed order from public team records, without any outcomes.
    const bracket = [...teams]
      .sort((a, b) => SEED_ORDER.indexOf(a.seed) - SEED_ORDER.indexOf(b.seed))
      .map((team) => team.id);
    const byId = validateTeams(teams, bracket),
      resolved = resolveSettings(settings, byId);
    if (!Array.isArray(requests) || !requests.length || requests.length > 10000)
      fail("Scoring requests must contain 1..10000 games");
    const seen = new Set();
    return requests.map((request) => {
      exactKeys(
        request,
        ["game_id", "team_a", "team_b"],
        "Identifier-only matchup request",
      );
      id(request.game_id, "Game ID");
      if (seen.has(request.game_id)) fail("Game IDs must be unique");
      seen.add(request.game_id);
      if (
        !byId.has(request.team_a) ||
        !byId.has(request.team_b) ||
        request.team_a === request.team_b
      )
        fail("Game needs two distinct known teams");
      return {
        ...request,
        probability_a: winProbability(
          byId.get(request.team_a).rating +
            (resolved.adjustments[request.team_a] ?? 0),
          byId.get(request.team_b).rating +
            (resolved.adjustments[request.team_b] ?? 0),
          resolved.temperature,
        ),
      };
    });
  }
  function score(predictions, outcomes) {
    if (
      !Array.isArray(predictions) ||
      !predictions.length ||
      !Array.isArray(outcomes) ||
      !outcomes.length ||
      predictions.length > 10000 ||
      outcomes.length > 10000
    )
      fail(
        "Scoring requires nonempty bounded prediction and outcome populations",
      );
    const truth = new Map();
    for (const outcome of outcomes) {
      exactKeys(outcome, ["game_id", "winner_id"], "Synthetic outcome");
      id(outcome.game_id, "Game ID");
      id(outcome.winner_id, "Winner ID");
      if (truth.has(outcome.game_id)) fail("Duplicate outcome game ID");
      truth.set(outcome.game_id, outcome.winner_id);
    }
    const seen = new Set(),
      bins = Array.from({ length: 5 }, (_, index) => ({
        lower: index / 5,
        upper: (index + 1) / 5,
        count: 0,
        sum_probability: 0,
        wins: 0,
      }));
    let squared = 0,
      logLoss = 0;
    for (const prediction of predictions) {
      exactKeys(
        prediction,
        ["game_id", "team_a", "team_b", "probability_a"],
        "Game prediction",
      );
      id(prediction.game_id, "Game ID");
      id(prediction.team_a, "Team A");
      id(prediction.team_b, "Team B");
      if (
        prediction.team_a === prediction.team_b ||
        seen.has(prediction.game_id) ||
        !truth.has(prediction.game_id)
      )
        fail("Prediction game IDs must match outcomes exactly once");
      seen.add(prediction.game_id);
      const probability = finite(prediction.probability_a, "Probability");
      if (probability < 0 || probability > 1)
        fail("Probability must be in 0..1");
      const winner = truth.get(prediction.game_id);
      if (winner !== prediction.team_a && winner !== prediction.team_b)
        fail("Winner must belong to the predicted matchup");
      const target = winner === prediction.team_a ? 1 : 0,
        clipped = Math.max(
          LOG_LOSS_EPSILON,
          Math.min(1 - LOG_LOSS_EPSILON, probability),
        );
      squared += (probability - target) ** 2;
      logLoss -= target ? Math.log(clipped) : Math.log1p(-clipped);
      const bin = bins[Math.min(4, Math.floor(probability * 5))];
      bin.count++;
      bin.sum_probability += probability;
      bin.wins += target;
    }
    if (seen.size !== truth.size)
      fail("Predictions must cover every outcome game");
    return {
      games: predictions.length,
      brier: squared / predictions.length,
      log_loss: logLoss / predictions.length,
      bins: bins.map((bin) => ({
        lower: bin.lower,
        upper: bin.upper,
        count: bin.count,
        mean_probability: bin.count ? bin.sum_probability / bin.count : null,
        observed_frequency: bin.count ? bin.wins / bin.count : null,
      })),
      log_loss_epsilon: LOG_LOSS_EPSILON,
      definitions: {
        brier:
          "Mean squared error of team A win probability across physical games",
        log_loss:
          "Mean binary cross-entropy in natural-log units; only this diagnostic clips p to [1e-15,1−1e-15]",
        bins: "Five fixed intervals; upper boundary excluded except final bin includes 1",
      },
      scope:
        "Authored outcomes illustrate scoring; not an untouched holdout or a real tournament evaluation.",
    };
  }
  function validateData(data) {
    object(data, "Fixture");
    if (data.schema_version !== 1 || data.evidence_type !== "SYNTHETIC_ONLY")
      fail("Unsupported public synthetic fixture");
    validateTeams(data.teams, data.bracket);
    if (
      !data.provenance ||
      data.provenance.evidence_type !== "SYNTHETIC_ONLY" ||
      data.provenance.training_fits !== 0 ||
      data.provenance.private_assets_used !== false ||
      data.provenance.official_evaluation !== false
    )
      fail("Synthetic provenance is required");
    exactKeys(data.scoring, ["requests", "outcomes"], "Scoring fixture");
    return true;
  }
  function analyze(data, settings = {}) {
    validateData(data);
    const result = forecast(data.teams, data.bracket, settings);
    const predictions = predictGames(
      data.teams,
      data.scoring.requests,
      settings,
    );
    const diagnostics = score(predictions, data.scoring.outcomes);
    return {
      schema_version: 1,
      evidence_type: "SYNTHETIC_ONLY",
      ...result,
      diagnostics,
      scoring_predictions: predictions,
      provenance: { ...data.provenance },
      probability_rule:
        "P(A wins) = 1 / (1 + 10^((rating B − rating A) / temperature))",
      assumptions: [
        "Neutral court and fixed team strength for every game.",
        "Outcomes of disjoint bracket branches are independent under the fixed probabilities.",
        "No reseeding, injuries, changing form, or correlated tournament effects.",
      ],
      limitations: [
        "Fictional teams, ratings and outcomes; no real 2026 predictions or private model assets.",
        "Exact means all bracket paths are integrated under this illustrative model; it does not mean the probabilities are calibrated.",
        "Scenario controls are interactive sensitivity exploration, not fitted or selected parameters.",
        "Repeatedly inspecting the same small synthetic scoring sample is not an independent evaluation.",
      ],
    };
  }
  const api = {
    DEFAULT_TEMPERATURE,
    winProbability,
    forecast,
    matchup,
    predictGames,
    score,
    validateData,
    analyze,
  };
  root.MarchTournamentEngine = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
