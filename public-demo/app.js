/* Browser-local view for the fictional Tournament Lab. No network or persistence. */
(function (root) {
  "use strict";
  const doc = root.document;
  const el = (id) => doc.getElementById(id);
  const engine = root.MarchTournamentEngine;
  const data = root.MARCH_TOURNAMENT_DATA;
  const state = {
    team: "harbor",
    temperature: 400,
    adjustments: {},
    preset: "rated",
    round: 2,
    teamA: "harbor",
    teamB: "copper",
    result: null,
    matchup: null,
  };
  const stageNames = ["Reach semifinals", "Reach final", "Win tournament"];
  const pct = (value) => `${(100 * value).toFixed(1)}%`;
  const signed = (value) => `${value >= 0 ? "+" : ""}${value}`;
  const node = (tag, className, text) => {
    const element = doc.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  };
  function fail(message) {
    state.result = null;
    state.matchup = null;
    el("bracket").replaceChildren();
    el("probability-bars").replaceChildren();
    el("selected-summary").textContent =
      "No current forecast. Correct the controls or reset the field.";
    el("round-note").textContent = "";
    el("total-probability").textContent = "—";
    el("rating-current").textContent = "—";
    el("matchup-output").hidden = true;
    el("matchup-error").hidden = true;
    el("export").disabled = true;
    el("error").textContent = message;
    el("error").hidden = false;
    el("status").textContent =
      "Calculation unavailable; no previous results are being displayed.";
  }
  function settings() {
    return {
      temperature: state.temperature,
      adjustments: { ...state.adjustments },
    };
  }
  function chooseTeam(id) {
    if (!data.teams.some((team) => team.id === id))
      throw new Error("Select a known fictional team.");
    state.team = id;
    refresh();
  }
  function teamButton(team, round, id, className) {
    const button = node(
      "button",
      `${className}${state.team === team.id ? " selected" : ""}`,
    );
    button.id = id;
    button.type = "button";
    button.setAttribute("aria-pressed", String(state.team === team.id));
    button.setAttribute(
      "aria-label",
      `${team.name}, ${stageNames[round].toLowerCase()}: ${pct(team.advance[round])}. Select team.`,
    );
    button.title = `${team.name}: ${pct(team.advance[round])}`;
    button.addEventListener("click", () => chooseTeam(team.id));
    return button;
  }
  function renderBracket() {
    const byId = new Map(state.result.teams.map((team) => [team.id, team]));
    const columns = stageNames.map((name, round) => {
      const column = node("section", "round-column");
      const heading = node("h3", "round-heading", name);
      const survivors = state.result.rounds[round].expected_survivors;
      heading.append(
        node(
          "small",
          "",
          `${survivors} ${survivors === 1 ? "champion" : "teams advance"}`,
        ),
      );
      const groups = node("div", "round-nodes");
      const size = 2 ** (round + 1);
      for (let start = 0; start < data.bracket.length; start += size) {
        const group = node(
          "div",
          `bracket-node${round === 2 ? " championship" : ""}`,
        );
        const groupLabel =
          round === 0
            ? `PAIR ${start / size + 1} · ONE SURVIVOR`
            : round === 1
              ? `HALF ${start / size + 1} · ONE FINALIST`
              : "EIGHT PATHS · ONE CHAMPION";
        group.append(node("p", "node-label", groupLabel));
        for (const id of data.bracket.slice(start, start + size)) {
          const team = byId.get(id);
          const button = teamButton(
            team,
            round,
            `bracket-${round}-${id}`,
            "team-row",
          );
          const label = node("span", "team-name");
          label.append(
            node("span", "seed-number", team.seed),
            node("span", "", team.name),
          );
          button.append(
            label,
            node("span", "team-probability", pct(team.advance[round])),
          );
          group.append(button);
        }
        groups.append(group);
      }
      column.append(heading, groups);
      return column;
    });
    el("bracket").replaceChildren(...columns);
    const selected = byId.get(state.team);
    el("selected-summary").textContent =
      `${selected.name} · Semifinal ${pct(selected.advance[0])} → Final ${pct(selected.advance[1])} → Champion ${pct(selected.advance[2])}`;
    el("total-probability").textContent = pct(
      state.result.teams.reduce(
        (sum, team) => sum + team.champion_probability,
        0,
      ),
    );
  }
  function renderBars() {
    const round = state.round;
    const teams = [...state.result.teams].sort(
      (a, b) => b.advance[round] - a.advance[round] || a.seed - b.seed,
    );
    el("probability-bars").replaceChildren(
      ...teams.map((team) => {
        const button = teamButton(
          team,
          round,
          `bar-${team.id}`,
          "probability-row",
        );
        const track = node("span", "bar-track");
        const fill = node("span", "bar-fill");
        fill.style.width = `${team.advance[round] * 100}%`;
        track.append(fill);
        button.append(
          node("span", "", team.name),
          track,
          node("span", "bar-value", pct(team.advance[round])),
        );
        return button;
      }),
    );
    const roundResult = state.result.rounds[round];
    el("round-note").textContent =
      `${roundResult.expected_survivors} ${round === 2 ? "team wins" : "teams advance"}. These eight marginal probabilities sum to ${pct(roundResult.probability_sum)}. Each bar is one team’s chance, on a 0–100% scale.`;
  }
  function renderControls() {
    const team = data.teams.find((entry) => entry.id === state.team);
    el("team").value = state.team;
    el("rating").value = String(state.adjustments[state.team] ?? 0);
    el("rating-value").textContent = signed(state.adjustments[state.team] ?? 0);
    el("rating-base").textContent = `Starting rating ${team.rating}`;
    el("rating-current").textContent = String(
      team.rating + (state.adjustments[state.team] ?? 0),
    );
    el("temperature").value = String(state.temperature);
    el("temperature-value").textContent = String(state.temperature);
    el("round").value = String(state.round);
    for (const preset of ["rated", "even", "challenger"]) {
      const button = el(`preset-${preset}`);
      button.className = `preset${state.preset === preset ? " active" : ""}`;
      button.setAttribute("aria-pressed", String(state.preset === preset));
    }
  }
  function renderMatchup() {
    state.matchup = null;
    el("team-a").value = state.teamA;
    el("team-b").value = state.teamB;
    try {
      const probabilityA = engine.matchup(
        data,
        state.teamA,
        state.teamB,
        settings(),
      );
      const a = state.result.teams.find((team) => team.id === state.teamA);
      const b = state.result.teams.find((team) => team.id === state.teamB);
      state.matchup = {
        team_a: a.id,
        team_b: b.id,
        probability_a: probabilityA,
        probability_b: 1 - probabilityA,
      };
      el("probability-a").textContent = pct(probabilityA);
      el("probability-b").textContent = pct(1 - probabilityA);
      el("name-a").textContent = a.name;
      el("name-b").textContent = b.name;
      el("rating-a").textContent = `Rating ${a.adjusted_rating}`;
      el("rating-b").textContent = `Rating ${b.adjusted_rating}`;
      el("matchup-fill").style.width = `${100 * probabilityA}%`;
      el("matchup-bar").setAttribute(
        "aria-label",
        `${a.name} ${pct(probabilityA)}; ${b.name} ${pct(1 - probabilityA)}`,
      );
      el("matchup-explanation").textContent =
        `A direct meeting at the current ratings and scale ${state.temperature}. Bracket placement has no effect on this two-team calculation.`;
      el("matchup-output").hidden = false;
      el("matchup-error").hidden = true;
      el("export").disabled = false;
      el("status").textContent =
        "Updated on this device. Displayed percentages are rounded; JSON preserves full precision.";
    } catch (error) {
      el("matchup-output").hidden = true;
      el("matchup-error").textContent =
        `Choose two distinct fictional teams. ${error.message}`;
      el("matchup-error").hidden = false;
      el("export").disabled = true;
      el("status").textContent =
        "Bracket is current. Choose a valid matchup to enable export.";
    }
  }
  function refresh() {
    const focusedId = doc.activeElement?.id;
    try {
      if (
        !Number.isFinite(state.temperature) ||
        state.temperature < 100 ||
        state.temperature > 800
      )
        throw new Error("Uncertainty scale must be between 100 and 800.");
      if (!Number.isInteger(state.round) || state.round < 0 || state.round > 2)
        throw new Error("Choose one of the three tournament stages.");
      state.result = engine.analyze(data, settings());
      el("error").hidden = true;
      renderControls();
      renderBracket();
      renderBars();
      renderMatchup();
      if (/^(?:bracket-[0-2]-|bar-)/.test(focusedId || "")) {
        el(focusedId)?.focus();
      }
    } catch (error) {
      fail(`Unable to calculate this scenario. ${error.message}`);
    }
  }
  function preset(name) {
    state.temperature = 400;
    state.adjustments = {};
    state.preset = name;
    if (name === "even") {
      const average =
        data.teams.reduce((sum, team) => sum + team.rating, 0) /
        data.teams.length;
      for (const team of data.teams)
        state.adjustments[team.id] = average - team.rating;
    } else if (name === "challenger") {
      state.adjustments.meadow = 250;
      state.team = "meadow";
    }
    refresh();
  }
  function exportAnalysis() {
    if (!state.result || !state.matchup || el("export").disabled) return;
    try {
      const artifact = {
        schema_version: 1,
        evidence_type: "SYNTHETIC_ONLY",
        purpose:
          "Educational fixed-rating bracket; separate from historical results and the private forecasting system.",
        selection: {
          team: state.team,
          stage: state.round,
          preset: state.preset,
        },
        inputs: {
          teams: data.teams,
          bracket: data.bracket,
          settings: state.result.settings,
        },
        analysis: state.result,
        selected_matchup: state.matchup,
        illustrative_scoring: data.scoring,
      };
      const blob = new root.Blob([JSON.stringify(artifact, null, 2)], {
        type: "application/json",
      });
      const url = root.URL.createObjectURL(blob);
      const link = node("a");
      link.href = url;
      link.download = "synthetic-tournament-analysis.json";
      doc.body.append(link);
      link.click();
      link.remove();
      root.setTimeout(() => root.URL.revokeObjectURL(url), 1000);
      el("status").textContent =
        "JSON exported with exact probabilities, settings and separately labeled fictional scoring examples.";
    } catch (error) {
      el("status").textContent =
        `Export unavailable: ${error.message}. The current calculations remain visible.`;
    }
  }
  try {
    if (!engine || !data)
      throw new Error(
        "The local engine or fictional fixture did not load. Reload the complete demo files.",
      );
    engine.validateData(data);
    for (const id of ["team", "team-a", "team-b"]) {
      el(id).replaceChildren(
        ...data.teams.map((team) => {
          const option = node("option", "", `${team.seed}. ${team.name}`);
          option.value = team.id;
          return option;
        }),
      );
    }
    el("team").addEventListener("change", () => {
      try {
        chooseTeam(el("team").value);
      } catch (error) {
        fail(error.message);
      }
    });
    el("rating").addEventListener("input", () => {
      state.adjustments[state.team] = Number(el("rating").value);
      state.preset = "custom";
      refresh();
    });
    el("temperature").addEventListener("input", () => {
      state.temperature = Number(el("temperature").value);
      state.preset = "custom";
      refresh();
    });
    el("round").addEventListener("change", () => {
      state.round = Number(el("round").value);
      refresh();
    });
    for (const [id, property] of [
      ["team-a", "teamA"],
      ["team-b", "teamB"],
    ]) {
      el(id).addEventListener("change", () => {
        state[property] = el(id).value;
        if (state.result) renderMatchup();
      });
    }
    for (const name of ["rated", "even", "challenger"])
      el(`preset-${name}`).addEventListener("click", () => preset(name));
    el("reset").addEventListener("click", () => {
      state.team = "harbor";
      state.teamA = "harbor";
      state.teamB = "copper";
      state.round = 2;
      preset("rated");
    });
    el("export").addEventListener("click", exportAnalysis);
    refresh();
  } catch (error) {
    fail(error.message);
  }
})(typeof globalThis !== "undefined" ? globalThis : window);
