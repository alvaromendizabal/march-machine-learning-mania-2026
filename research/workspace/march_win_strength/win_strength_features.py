"""Margin-free, pre-tournament Bradley–Terry abilities and Laplace uncertainty.

Only the listed regular-season result columns enter the rating fit. No tournament
outcome, seed, ranking system, score/margin, or future observation enters its
likelihood. This is a feature generator, not a replacement tournament classifier.
"""
from __future__ import annotations

import itertools
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize
from scipy.special import expit, logit, roots_hermitenorm
from scipy.sparse.csgraph import connected_components
from threadpoolctl import threadpool_limits
from strength_io import sf, require

KEYS = ['Gender', 'Season', 'Team1ID', 'Team2ID']
BASE = list(sf.ANCHOR_COLS)
ABILITY = ['bt_logodds_difference']
UNCERTAINTY = ['bt_uncertainty_correction']
ALL = BASE + ABILITY + UNCERTAINTY
RECIPES = {'anchor': BASE, 'anchor_bt': BASE + ABILITY,
           'anchor_bt_uncertainty': ALL}
PARAMETERS = {
    'cutoff_day': 132, 'team_prior_sd': 2.0, 'home_prior_sd': 1.0,
    'optimizer': 'L-BFGS-B', 'maxiter': 500, 'gtol': 1e-8, 'ftol': 1e-13,
    'gradient_acceptance': 1e-4, 'quadrature_order': 64,
    'quadrature_check_order': 128, 'quadrature_tolerance': 1e-7,
    'max_teams': 600, 'season_min': 2013, 'season_max': 2019,
}
# A bounded numerical continuation, not a change to the likelihood or priors.
# PARAMETERS is deliberately unchanged so previously certified fits stay valid.
REFINEMENT = {'max_steps': 8, 'max_backtracks': 20, 'armijo': 1e-4,
              'target_gradient': 1e-8, 'max_initial_gradient': 1e-2}

INPUTS = ['Season', 'DayNum', 'WTeamID', 'LTeamID', 'WLoc']


def legal_results(frame: pd.DataFrame, season: int) -> pd.DataFrame:
    """Filter first, then validate only actual feature inputs (scores are not read)."""
    require(isinstance(season, (int, np.integer)) and 2013 <= season <= 2019,
            'This declared experiment supports seasons 2013–2019 only')
    require(set(INPUTS) <= set(frame), 'Missing win-loss input columns')
    out = frame.loc[(frame.Season == season) & (frame.DayNum <= 132), INPUTS].copy()
    require(len(out) > 0 and not out.isna().any().any(), 'Empty/missing legal win-loss inputs')
    numeric = out[INPUTS[:-1]].to_numpy(dtype=float)
    require(np.isfinite(numeric).all() and (numeric >= 0).all() and
            np.equal(numeric, np.floor(numeric)).all(), 'Invalid integer win-loss inputs')
    require(out.WLoc.isin(['H', 'A', 'N']).all(), 'Invalid location code')
    require(out.WTeamID.ne(out.LTeamID).all(), 'Self match in regular season')
    identity = pd.DataFrame({'day': out.DayNum,
        'a': np.minimum(out.WTeamID, out.LTeamID),
        'b': np.maximum(out.WTeamID, out.LTeamID)})
    require(not identity.duplicated().any(), 'Duplicate physical regular-season game')
    return out.sort_values(['DayNum', 'WTeamID', 'LTeamID']).reset_index(drop=True)


def design(games: pd.DataFrame):
    teams = np.sort(pd.unique(games[['WTeamID', 'LTeamID']].to_numpy().ravel())).astype(int)
    require(2 <= len(teams) <= PARAMETERS['max_teams'], 'Unsupported rating dimension')
    lookup = {int(t): i for i, t in enumerate(teams)}
    a = games.WTeamID.map(lookup).to_numpy(dtype=int)
    b = games.LTeamID.map(lookup).to_numpy(dtype=int)
    n, k = len(games), len(teams)
    h = games.WLoc.map({'H': 1., 'A': -1., 'N': 0.}).to_numpy()
    x = sparse.csr_matrix((np.r_[np.ones(n), -np.ones(n), h],
        (np.tile(np.arange(n), 3), np.r_[a, b, np.full(n, k)])), shape=(n, k + 1))
    precision = np.r_[np.full(k, PARAMETERS['team_prior_sd'] ** -2),
                      PARAMETERS['home_prior_sd'] ** -2]
    return teams, a, b, x, precision


def objective(theta, x, precision):
    """Sum of physical-game log losses plus fixed proper Gaussian prior."""
    z = np.asarray(x @ theta)
    value = np.logaddexp(0., -z).sum() + .5 * np.sum(precision * theta ** 2)
    gradient = np.asarray(x.T @ (-expit(-z))).ravel() + precision * theta
    return float(value), gradient


def hessian(theta, x, precision):
    p = expit(x @ theta)
    return (x.T @ x.multiply((p * (1. - p))[:, None])).toarray() + np.diag(precision)


def certify_solution(result, x, precision):
    """Continue an ftol-stopped solution only when its gradient still needs work.

    A successful L-BFGS-B status can result from an objective-reduction stopping
    rule, independently of the strict gradient certificate. Keep accepted
    solutions byte-identical. Otherwise use at most eight damped Newton steps
    on the SAME penalized objective and retain the original 1e-4 acceptance.
    """
    theta = np.asarray(result.x, dtype=float).copy()
    require(bool(result.success) and np.isfinite(theta).all(),
            f'BT optimizer failed: {result.message}; nonfinite or unsuccessful solution')
    value, gradient = objective(theta, x, precision)
    initial = float(np.max(np.abs(gradient)))
    require(np.isfinite(value) and np.isfinite(gradient).all(), 'Nonfinite BT objective/gradient')
    info = {'optimizer_message': str(result.message), 'initial_gradient_max_abs': initial,
            'newton_steps': 0, 'line_search_evaluations': 0,
            'objective_before_refinement': value, 'solver_path': 'L-BFGS-B'}
    if initial <= PARAMETERS['gradient_acceptance']:
        return theta, value, initial, info
    require(initial <= REFINEMENT['max_initial_gradient'],
            f'BT optimizer failed: gradient {initial} is outside bounded near-solution refinement')
    info['solver_path'] = 'L-BFGS-B + bounded damped Newton'
    for iteration in range(REFINEMENT['max_steps']):
        norm = float(np.max(np.abs(gradient)))
        if norm <= REFINEMENT['target_gradient']:
            break
        H = hessian(theta, x, precision)
        direction = cho_solve(cho_factor(H, lower=True), gradient)
        descent = float(gradient @ direction)
        require(np.isfinite(direction).all() and np.isfinite(descent) and descent > 0,
                'BT refinement direction is not a finite descent direction')
        accepted = False
        slack = 64 * np.finfo(float).eps * max(1.0, abs(value))
        for backtrack in range(REFINEMENT['max_backtracks']):
            step = 0.5 ** backtrack
            candidate = theta - step * direction
            nv, ng = objective(candidate, x, precision)
            info['line_search_evaluations'] += 1
            if not np.isfinite(nv) or not np.isfinite(ng).all():
                continue
            ngnorm = float(np.max(np.abs(ng)))
            armijo = nv <= value - REFINEMENT['armijo'] * step * descent
            # Near an optimum, the objective change can be below floating-point
            # resolution. Accept a roundoff tie only with a reduced gradient.
            rounding_tie = abs(nv - value) <= slack and ngnorm < norm
            if nv <= value + slack and (armijo or rounding_tie):
                theta, value, gradient = candidate, nv, ng
                accepted = True
                break
        require(accepted, 'BT bounded Newton line search failed; no tolerance was relaxed')
        info['newton_steps'] = iteration + 1
    final = float(np.max(np.abs(gradient)))
    require(np.isfinite(theta).all() and final <= PARAMETERS['gradient_acceptance'],
            f'BT optimizer failed after bounded refinement; max gradient={final}')
    return theta, value, final, info


def fit_season(frame: pd.DataFrame, season: int):
    games = legal_results(frame, season)
    teams, a, b, x, precision = design(games)
    with threadpool_limits(limits=2):
        result = minimize(objective, np.zeros(len(teams) + 1), args=(x, precision),
            jac=True, method=PARAMETERS['optimizer'], options={
                'maxiter': PARAMETERS['maxiter'], 'gtol': PARAMETERS['gtol'],
                'ftol': PARAMETERS['ftol'], 'maxls': 50})
        theta, value, grad, solver_info = certify_solution(result, x, precision)
        H = hessian(theta, x, precision)
        covariance = cho_solve(cho_factor(H, lower=True), np.eye(len(H)))
        covariance = (covariance + covariance.T) / 2
        inverse_error = float(np.max(np.abs(H @ covariance - np.eye(len(H)))))
        require(np.isfinite(covariance).all() and inverse_error < 1e-7,
                'BT covariance numerical certificate failed')
    graph = sparse.csr_matrix((np.ones(2 * len(games)),
        (np.r_[a, b], np.r_[b, a])), shape=(len(teams), len(teams)))
    count, component = connected_components(graph, directed=False)
    appearances = np.bincount(np.r_[a, b], minlength=len(teams))
    wins = np.bincount(a, minlength=len(teams))
    unique_opponents = np.asarray((graph > 0).sum(axis=1)).ravel()
    table = pd.DataFrame({'Gender': 'M', 'Season': season, 'TeamID': teams,
        'bt_ability': theta[:-1], 'bt_marginal_sd': np.sqrt(np.diag(covariance)[:-1]),
        'regular_games': appearances, 'regular_wins': wins, 'unique_opponents': unique_opponents,
        'component': component})
    diagnostic = {'Season': season, 'Gender': 'M', 'regular_games': len(games),
        'teams': len(teams), 'graph_components': int(count), 'max_day': int(games.DayNum.max()),
        'home_logodds': float(theta[-1]), 'iterations': int(result.nit),
        'gradient_max_abs': grad, 'covariance_inverse_error': inverse_error,
        'negative_log_posterior': value, 'input_columns': INPUTS, **solver_info,
        'scores_used': False, 'tournament_labels_used': False,
        'uncertainty_scope': 'Laplace approximation conditional on fixed priors and model assumptions'}
    model = {'Gender': 'M', 'Season': season, 'team_ids': teams.tolist(),
        'theta': theta.tolist(), 'covariance': covariance.tolist(),
        'parameters': dict(PARAMETERS), 'diagnostics': diagnostic}
    return model, table, diagnostic


def uncertainty_features(delta, variance):
    """Neutral pair log odds plus change induced by Gaussian posterior averaging.

    Probability integration uses Gauss–Hermite quadrature; approximation error is
    checked at twice the fixed order. This does not validate the Laplace assumption.
    """
    d, v = np.broadcast_arrays(np.asarray(delta, dtype=float), np.asarray(variance, dtype=float))
    require(np.isfinite(d).all() and np.isfinite(v).all() and (v >= -1e-10).all(),
            'Invalid pair mean or variance')
    v = np.maximum(v, 0.)
    z = np.abs(d)
    def integrate(order):
        nodes, weights = roots_hermitenorm(order)
        return expit(z[..., None] + np.sqrt(v)[..., None] * nodes) @ (weights / np.sqrt(2 * np.pi))
    p = integrate(PARAMETERS['quadrature_order'])
    check = integrate(PARAMETERS['quadrature_check_order'])
    error = float(np.max(np.abs(p - check))) if p.size else 0.
    require(error <= PARAMETERS['quadrature_tolerance'], 'Quadrature accuracy check failed')
    require(((p > 0) & (p < 1)).all(), 'Integrated probability reached numeric boundary')
    adjusted = np.sign(d) * logit(p)
    correction = adjusted - d
    return correction, error


def pair_candidates(model, pairs):
    require(model['parameters'] == PARAMETERS, 'BT parameter identity mismatch')
    require(set(KEYS) <= set(pairs), 'Missing matchup keys')
    require(pairs.Gender.eq('M').all() and pairs.Season.eq(model['Season']).all(), 'Wrong rating population/season')
    require(not pairs.duplicated(KEYS).any() and pairs.Team1ID.ne(pairs.Team2ID).all(), 'Invalid matchup identities')
    ids = model['team_ids'];lookup = {int(t): i for i, t in enumerate(ids)}
    a = pairs.Team1ID.map(lookup); b = pairs.Team2ID.map(lookup)
    require(a.notna().all() and b.notna().all(), 'Requested team has no legal rating')
    a, b = a.to_numpy(dtype=int), b.to_numpy(dtype=int)
    theta, cov = np.asarray(model['theta']), np.asarray(model['covariance'])
    require(cov.shape == (len(ids) + 1, len(ids) + 1) and len(theta) == len(ids) + 1,
            'BT model dimension mismatch')
    require(np.isfinite(theta).all() and np.isfinite(cov).all(), 'Invalid BT model')
    d = theta[a] - theta[b]
    v = cov[a, a] + cov[b, b] - 2 * cov[a, b]
    adjustment, error = uncertainty_features(d, v)
    result = pairs[KEYS].reset_index(drop=True).copy()
    result[ABILITY[0]] = d; result[UNCERTAINTY[0]] = adjustment
    diag = result[KEYS].copy()
    diag['bt_logodds_difference'] = d; diag['pair_variance'] = v
    diag['bt_point_probability'] = expit(d)
    diag['bt_averaged_probability'] = expit(d + adjustment)
    diag['quadrature_error_bound_check'] = error
    return result, diag, error


def build_matchups(base, model, ratings):
    """Features for all seeded pairs, created BEFORE any tournament labels are read."""
    year = int(model['Season'])
    require(base.Gender.eq('M').all() and base.Season.eq(year).all() and not base.TeamID.duplicated().any(),
            'Invalid base snapshot population')
    selected = base.loc[base.seed.notna()].sort_values('TeamID').copy()
    require(len(selected) >= 2 and selected.seed.between(1, 16).all(), 'Invalid/missing seeded cohort')
    require(np.isfinite(selected[sf.CONTROL].to_numpy(dtype=float)).all(), 'Missing reference features')
    lookup = ratings.set_index('TeamID')
    require(selected.TeamID.isin(lookup.index).all(), 'Seeded team absent from win-loss graph')
    require(lookup.loc[selected.TeamID, 'component'].nunique() == 1,
            'Seeded teams span disconnected schedule components: cross-component contrasts prior-determined')
    pairs = pd.DataFrame(itertools.combinations(selected.TeamID.tolist(), 2), columns=['Team1ID','Team2ID'])
    pairs.insert(0, 'Season', year); pairs.insert(0, 'Gender', 'M')
    ref = pairs.copy(); b = base.set_index('TeamID')
    for c in sf.CONTROL: ref['diff_' + c] = b.loc[pairs.Team1ID, c].to_numpy() - b.loc[pairs.Team2ID, c].to_numpy()
    new, diag, error = pair_candidates(model, pairs)
    ref = ref.merge(new, on=KEYS, validate='one_to_one')
    reverse_pairs = pairs.copy(); reverse_pairs[['Team1ID','Team2ID']] = reverse_pairs[['Team2ID','Team1ID']]
    reverse, _, _ = pair_candidates(model, reverse_pairs)
    require(np.max(np.abs(new[ABILITY+UNCERTAINTY].to_numpy() + reverse[ABILITY+UNCERTAINTY].to_numpy())) < 1e-12,
            'Feature team-swap check failed')
    support = {'Season': year, 'Gender': 'M', 'seeded_teams': len(selected),
        'candidate_pairs': len(ref), 'pair_variance_min': float(diag.pair_variance.min()),
        'pair_variance_max': float(diag.pair_variance.max()), 'quadrature_max_error': error,
        'labels_used_to_build_pairs': False}
    return ref, diag, support


def registry():
    rows = [{'feature': c, 'family': 'frozen_reference', 'new_candidate': False,
             'description': 'Unchanged round02 reference; original raw-file provenance preserved'} for c in BASE]
    rows += [{'feature': ABILITY[0], 'family': 'win_loss_ability', 'new_candidate': True,
        'description': 'Joint schedule-adjusted regular-season win ability, team A minus B; ignores score margin'},
       {'feature': UNCERTAINTY[0], 'family': 'rating_uncertainty', 'new_candidate': True,
        'description': 'logit(E sigmoid(N(d,v))) minus d; v includes pair covariance, approximate Laplace uncertainty'}]
    for row in rows:
        row.update(availability='After field announcement; regular season day <=132',
                   swap_parity=-1, promotion='Requires controlled historical and later-era evidence')
    return pd.DataFrame(rows)
