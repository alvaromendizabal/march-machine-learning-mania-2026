"""Round 07: unchanged women's temporal-change replication and gated components.

All existing models are replayed from numeric JSON (never pickle). The main
repository and upstream research directories are read-only. No feature or rating
fits are performed. Only two replication classifiers and, conditionally, eight
component classifiers may be fitted by this workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import zipfile

import numpy as np
import pandas as pd

import reference_form_workflow as ref

KIT = Path(__file__).resolve().parent
wf, sf, ff = ref.wf, ref.sf, ref.ff
require = ref.require
sha, atomic_json, atomic_csv = ref.sha, ref.atomic_json, ref.atomic_csv
read_json, read_csv, safe_file = ref.read_json, ref.read_csv, ref.safe_file
verify_checkpoint, seal, event = ref.verify_checkpoint, ref.seal, ref.event
ANCHOR = list(ref.ANCHOR)
CHANGE = list(ff.CHANGE_COLS)
SEASONS = [2016, 2017, 2018, 2019]
DISCOVERY = [2017, 2019]
REPLICATION = [2016, 2018]
RECIPES = {'anchor': ANCHOR, 'anchor_change': ANCHOR + CHANGE}
DROPS = {'drop_offense_change': ANCHOR + [CHANGE[1]],
         'drop_defense_change': ANCHOR + [CHANGE[0]]}
CONFIG = {
    'round': '07-womens-temporal-change-replication', 'gender': 'W',
    'seasons': SEASONS, 'discovery_seasons': DISCOVERY,
    'replication_seasons': REPLICATION, 'snapshot_seasons': list(range(2013, 2020)),
    'recipes': {**RECIPES, **DROPS}, 'feature_parameters': ff.PARAMETERS,
    'C': 0.1, 'seed': 20260911, 'max_iter': 2000, 'threads': 2,
    'first_training_season': 2013, 'main_draw_only': True,
    'gate': {'mean_delta_at_most': -0.0005, 'both_additional_seasons_improve': True,
             'discovery_seasons_excluded': True},
    'maximum_replication_fits': 2, 'maximum_component_fits': 8,
    'new_rating_fits': 0, 'new_feature_definitions': 0,
    'scope': 'Previously-used exploratory historical main draws; not untouched tests or leaderboard',
    'automatic_promotion': False,
}
SOURCES = ['validation_workflow.py', 'validation_plots.py', 'run_round07.py',
           'reference_form_workflow.py', 'form_features.py',
           'frozen/research_workflow.py', 'frozen/shot_features.py']
FIT_FILES = ['model.json', 'metrics.json', 'predictions.csv']
REPLICATION_OUTPUTS = ['replication_metrics.csv', 'replication_predictions.csv',
                       'replication_receipt.json', 'gate.json', 'coefficients.csv',
                       'training_redundancy.csv']


def source_identity(kit: Path) -> dict:
    return {n: sha(safe_file(kit, n)) for n in SOURCES}


def output_dir(path: Path) -> None:
    """Never follow a symlink while creating an output directory."""
    require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents),
            'Symlinked output path')
    path.mkdir(parents=True, exist_ok=True)


def seal_stage(out: Path, stage: str, names: list[str]) -> None:
    atomic_json(out / f'{stage}_hashes.json', {n: sha(safe_file(out, n)) for n in names})


def check_stage(out: Path, stage: str, expected: list[str]) -> None:
    saved = read_json(safe_file(out, f'{stage}_hashes.json'))
    require(set(saved) == set(expected), 'Stage receipt scope changed: ' + stage)
    for n, digest in saved.items():
        require(sha(safe_file(out, n)) == digest, 'Stage output changed: ' + n)


def preflight(kit: Path, repo: Path, temporal: Path, shooting: Path,
              record: Path, schedule: Path) -> dict:
    paths = [Path(p).expanduser() for p in (kit, repo, temporal, shooting, record, schedule)]
    for p in paths:
        require(p.is_dir() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents),
                'Missing or symlinked directory: ' + str(p))
    kit, repo, temporal, shooting, record, schedule = [p.resolve() for p in paths]
    for i, a in enumerate([kit, repo, temporal, shooting, record, schedule]):
        for b in [kit, repo, temporal, shooting, record, schedule][i + 1:]:
            require(not a.is_relative_to(b) and not b.is_relative_to(a), 'Keep project and kits beside each other')
    m06 = read_json(safe_file(kit, 'evidence/manifest.json'))
    m05 = read_json(safe_file(kit, 'evidence05/manifest.json'))
    require(sha(safe_file(kit, 'evidence05/manifest.json')) == m06['evidence_sha256']['manifest.json'],
            'Broken returned evidence chain')
    require(m05['fingerprint'] == m06['prior_fingerprint'] and
            m05['upstream_fingerprint'] == m06['upstream_fingerprint'], 'Broken upstream fingerprint chain')
    for n, old in [('reference_form_workflow.py', 'form_workflow.py'), ('form_features.py', 'form_features.py'),
                   ('frozen/research_workflow.py', 'frozen/research_workflow.py'),
                   ('frozen/shot_features.py', 'frozen/shot_features.py')]:
        require(sha(safe_file(kit, n)) == m06['source'][old], 'Frozen implementation changed: ' + n)
    require(RECIPES == {n: m06['config']['recipes'][n] for n in RECIPES}, 'Reference columns changed')
    require(CONFIG['feature_parameters'] == m06['config']['parameters'], 'Feature formulas changed')
    for k in ('C', 'seed', 'max_iter', 'threads'):
        require(CONFIG[k] == m06['config'][k], 'Classifier settings changed: ' + k)
    require(ref.environment() == m06['environment'], 'Environment changed; do not reinstall blindly')
    state = wf.repository_state(repo)
    require(state == read_json(safe_file(kit, 'evidence/preflight.json'))['state'],
            'Repository differs from returned report; preserve local work, do not reset')
    raw = repo / 'data/kaggle/raw'
    for n, digest in m06['data'].items():
        require(sha(safe_file(raw, n)) == digest, 'Raw input changed: ' + n)
    roots = {'temporal': temporal / 'private_runs' / m06['fingerprint'],
             'shooting': shooting / 'private_runs' / m06['upstream_fingerprint'],
             'record': record / 'private_runs' / m05['fingerprint'],
             'schedule': schedule / 'private_runs' / m05['prior_fingerprint']}
    for p in roots.values():
        require(p.is_dir() and not p.is_symlink(), 'Prior private cache missing; no automatic rebuild: ' + str(p))
    require(read_json(safe_file(roots['temporal'], 'manifest.json')) == m06, 'Temporal manifest mismatch')
    require(read_json(safe_file(roots['record'], 'manifest.json')) == m05, 'Record manifest mismatch')
    upstream = {}

    def remember(prefix: str, name: str, expected: str | None = None) -> None:
        digest = sha(safe_file(roots[prefix], name))
        require(expected is None or digest == expected, 'Upstream evidence differs: ' + prefix + '/' + name)
        upstream[prefix + '/' + name] = digest

    for n in ['manifest.json', 'summary.json', 'metrics.csv', 'decisions.json', 'prepare.json',
              'evaluation_receipt.json', 'preflight.json', 'feature_registry.csv', 'coverage.csv']:
        remember('temporal', n, sha(safe_file(kit, 'evidence/' + n)))
    for n in ['manifest.json', 'replication_metrics.csv', 'preflight.json']:
        remember('record', n, sha(safe_file(kit, 'evidence05/' + n)))
    for s in range(2013, 2020):
        r = f'snapshots/W_{s}'
        require(verify_checkpoint(roots['shooting'] / r, ['teams.csv', 'coverage.json', 'opponent_exclusion_audit.csv']),
                'Missing base snapshot')
        for n in ['teams.csv', 'coverage.json', 'opponent_exclusion_audit.csv', 'complete.json']:
            remember('shooting', r + '/' + n, m06['upstream_files']['shooting/' + r + '/' + n])
        require(verify_checkpoint(roots['temporal'] / r, ['features.csv', 'coverage.json', 'late_residuals.csv']),
                'Missing temporal snapshot')
        for n in ['features.csv', 'coverage.json', 'late_residuals.csv', 'complete.json']:
            remember('temporal', r + '/' + n)
        early = f'early_ratings/W_{s}'
        require(verify_checkpoint(roots['temporal'] / early, ['model.json']), 'Missing early-rating receipt')
        remember('temporal', early + '/model.json'); remember('temporal', early + '/complete.json')
        coverage = read_json(roots['temporal'] / r / 'coverage.json')
        require(coverage['early_model_sha256'] == upstream['temporal/' + early + '/model.json'],
                'Snapshot does not match recorded early ratings')
    origins = {(2016, 'anchor'): ('record', 'fits/W_2016_anchor'),
               (2017, 'anchor'): ('record', 'fits/W_2017_anchor'),
               (2017, 'anchor_change'): ('temporal', 'fits/W_2017_anchor_change'),
               (2018, 'anchor'): ('schedule', 'fits/W_2018_anchor'),
               (2019, 'anchor'): ('shooting', 'fits/W_2019_anchor'),
               (2019, 'anchor_change'): ('temporal', 'fits/W_2019_anchor_change')}
    for prefix, r in origins.values():
        require(verify_checkpoint(roots[prefix] / r, FIT_FILES), 'Missing existing classifier: ' + r)
        for n in FIT_FILES + ['complete.json']:
            key = prefix + '/' + r + '/' + n
            pin = m06['upstream_files'].get(key, m05['upstream_files'].get(key))
            remember(prefix, r + '/' + n, pin)
    identity = {'config': CONFIG, 'source': source_identity(kit), 'data': m06['data'],
                'environment': ref.environment(), 'reference_commit': m06['reference_commit'],
                'evidence_sha256': {str(p.relative_to(kit)): sha(p) for sub in ('evidence', 'evidence05')
                                    for p in sorted((kit / sub).iterdir()) if p.is_file()},
                'upstream_files': upstream, 'temporal_fingerprint': m06['fingerprint'],
                'shooting_fingerprint': m06['upstream_fingerprint'],
                'record_fingerprint': m05['fingerprint'], 'schedule_fingerprint': m05['prior_fingerprint']}
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    out = kit / 'private_runs' / fingerprint
    output_dir(out); output_dir(kit / 'reports')
    manifest = dict(identity, fingerprint=fingerprint)
    if (out / 'manifest.json').exists():
        require(read_json(safe_file(out, 'manifest.json')) == manifest, 'Existing output manifest differs')
    else:
        atomic_json(out / 'manifest.json', manifest)
    atomic_json(kit / 'reports/latest_run.json', {'fingerprint': fingerprint, 'run_dir': str(out)})
    atomic_json(out / 'preflight.json', {'status': 'PASS', 'state': state,
        'base_snapshots_verified': 7, 'temporal_snapshots_verified': 7,
        'early_rating_receipts_verified': 7, 'existing_classifiers_verified': 6,
        'raw_files_verified': len(m06['data']), 'repository_source_imported': False,
        'known_notebook_edits_preserved': True})
    event('preflight_pass',cached_temporal_snapshots=7,cached_reference_snapshots=7,existing_classifiers=6)
    return {'kit': kit, 'repo': repo, 'raw': raw, **roots, 'directory': out, 'identity': identity,
            'state': state, 'fingerprint': fingerprint, 'origins': origins}


def preservation(ctx: dict) -> None:
    require(wf.repository_state(ctx['repo']) == ctx['state'], 'Repository changed during execution')
    require(source_identity(ctx['kit']) == ctx['identity']['source'], 'Kit source changed during execution')
    for n, digest in ctx['identity']['data'].items():
        require(sha(safe_file(ctx['raw'], n)) == digest, 'Raw bytes changed during execution')
    for n, digest in ctx['identity']['upstream_files'].items():
        prefix, rel = n.split('/', 1)
        require(sha(safe_file(ctx[prefix], rel)) == digest, 'Upstream bytes changed: ' + n)
    for n, digest in ctx['identity']['evidence_sha256'].items():
        require(sha(safe_file(ctx['kit'], n)) == digest, 'Bundled evidence changed')
    event('preservation_pass', raw=True, repository=True, upstream=True)


def matrices(ctx: dict) -> tuple:
    # The reference builder only joins verified snapshots; it never fits ratings.
    return ref.matrices({'directory': ctx['temporal'], 'shooting': ctx['shooting'], 'raw': ctx['raw']}, 'W')


def expected_old_brier(ctx: dict, season: int, recipe: str) -> float:
    if season in DISCOVERY:
        evidence = read_csv(ctx['kit'] / 'evidence/metrics.csv')
    else:
        evidence = read_csv(ctx['kit'] / 'evidence05/replication_metrics.csv')
    rows = evidence.loc[(evidence.Gender == 'W') & (evidence.Season == season) & (evidence.recipe == recipe)]
    require(len(rows) == 1, 'Missing/ambiguous returned model metric')
    return float(rows.brier.iloc[0])


def replay_existing(ctx: dict, season: int, recipe: str, bundle: tuple) -> tuple:
    prefix, name = ctx['origins'][season, recipe]
    result = ref.score_checkpoint(ctx[prefix] / name, 'W', season, recipe, RECIPES[recipe], bundle, 'upstream_replay')
    require(abs(result[0]['brier'] - expected_old_brier(ctx, season, recipe)) < 1e-12,
            'Existing model does not replay its returned score')
    return result


def prepare(ctx: dict) -> None:
    bundle = matrices(ctx); rows = []
    for s, recipe in ctx['origins']:
        row, _, _ = replay_existing(ctx, s, recipe, bundle)
        rows.append(row)
        event('existing_model_verified', season=s, recipe=recipe, completed=len(rows), total=6)
    out = ctx['directory']
    atomic_csv(out / 'prior_replay.csv', pd.DataFrame(rows))
    registry = read_csv(ctx['kit'] / 'evidence/feature_registry.csv')
    registry = registry.loc[registry.feature.isin(ANCHOR + CHANGE)].copy()
    require(set(registry.feature) == set(ANCHOR + CHANGE), 'Registry scope mismatch')
    registry['new_this_milestone'] = False
    registry['evidence'] = 'Unchanged replication; not promoted'
    atomic_csv(out / 'feature_registry.csv', registry)
    coverage = read_csv(ctx['kit'] / 'evidence/coverage.csv').query("Gender == 'W'")
    atomic_csv(out / 'coverage.csv', coverage)
    atomic_json(out / 'prepare.json', {'status': 'COMPLETE', 'base_snapshots_reused': 7,
        'temporal_snapshots_reused': 7, 'early_rating_receipts_verified': 7,
        'prior_classifier_replays': 6, 'new_rating_fits': 0, 'new_classifier_fits': 0,
        'new_feature_definitions': 0, 'new_feature_snapshots': 0,
        'feature_swap_error': 0.0})
    seal_stage(out, 'prepare', ['prepare.json', 'prior_replay.csv', 'feature_registry.csv', 'coverage.csv'])


def obtain_fit(ctx: dict, season: int, recipe: str, columns: list[str], bundle: tuple,
               remaining_fits: int) -> tuple:
    if (season, recipe) in ctx['origins']:
        return (*replay_existing(ctx, season, recipe, bundle), 'upstream')
    folder = ctx['directory'] / f'fits/W_{season}_{recipe}'
    if verify_checkpoint(folder, FIT_FILES):
        return (*ref.score_checkpoint(folder, 'W', season, recipe, columns, bundle, 'checkpoint_replay'), 'reused')
    require(remaining_fits > 0, 'Classifier budget exhausted before fit')
    pairs, y, x, _ = bundle
    ti, vi = ref.split(x, season)
    event('classifier_started', season=season, recipe=recipe, train_games=len(ti), validation_games=len(vi))
    model = wf.fitted_model(x.iloc[ti], y[ti], columns)
    model['train_seasons'] = list(range(2013, season))
    prob = wf.predict(model, x.iloc[vi])
    require(np.isfinite(prob).all() and ((prob > 0) & (prob < 1)).all(), 'Invalid probabilities')
    pred = pairs.iloc[vi].copy(); pred['y'] = y[vi]
    pred['probability'] = prob; pred['squared_error'] = (prob - y[vi]) ** 2
    atomic_json(folder / 'model.json', model)
    atomic_csv(folder / 'predictions.csv', pred)
    atomic_json(folder / 'metrics.json', {'brier': float(np.mean((prob - y[vi]) ** 2))})
    seal(folder, FIT_FILES)
    return (*ref.score_checkpoint(folder, 'W', season, recipe, columns, bundle, 'new_fit'), 'new')


def replication_gate(metrics: pd.DataFrame) -> dict:
    selected = metrics.loc[(metrics.Gender == 'W') & (metrics.recipe == 'anchor_change') & metrics.Season.isin(REPLICATION)]
    require(len(selected) == 2 and set(selected.Season) == set(REPLICATION), 'Gate needs exactly 2016 and 2018 once each')
    d = selected.delta_vs_anchor.to_numpy(float)
    require(np.isfinite(d).all(), 'Invalid replication deltas')
    passed = bool((d < 0).all() and d.mean() <= CONFIG['gate']['mean_delta_at_most'])
    return {'decision': 'RUN_BOUNDED_COMPONENTS' if passed else 'STOP_EXPANSION',
            'proceed_to_components': passed, 'replication_seasons': REPLICATION,
            'discovery_seasons_excluded': DISCOVERY, 'mean_delta_replication_only': float(d.mean()),
            'worst_replication_delta': float(d.max()), 'improved_replication_seasons': int((d < 0).sum()),
            'thresholds': CONFIG['gate'], 'automatic_promotion': False,
            'statistical_significance_claim': False,
            'meaning': 'Compute-allocation rule on already-used historical seasons; not significance or production selection'}


def replicate(ctx: dict) -> None:
    out = ctx['directory']
    check_stage(out, 'prepare', ['prepare.json', 'prior_replay.csv', 'feature_registry.csv', 'coverage.csv'])
    bundle = matrices(ctx); x = bundle[2]
    rows, predictions, coefficients, redundancy = [], [], [], []
    counts = {'new': 0, 'reused': 0, 'upstream': 0}
    for s in SEASONS:
        ti, _ = ref.split(x, s)
        corr = x.iloc[ti][ANCHOR + CHANGE].corr()
        for c in CHANGE:
            r = corr.loc[c, ANCHOR].abs().dropna()
            redundancy.append({'Season': s, 'feature': c, 'train_last_season': s-1,
                'max_abs_anchor_correlation': float(r.max()) if len(r) else 0.,
                'most_correlated_anchor': str(r.idxmax()) if len(r) else '', 'selection_changed': False})
        for recipe, columns in RECIPES.items():
            row, pred, model, origin = obtain_fit(ctx, s, recipe, columns, bundle, 2 - counts['new'])
            counts[origin] += 1
            rows.append(row); predictions.append(pred.assign(recipe=recipe))
            if recipe == 'anchor_change':
                weights = dict(zip([columns[i] for i in model['active_indices']], model['coefficients']))
                coefficients.extend({'Season': s, 'feature': c, 'coefficient': weights.get(c, 0.),
                                     'training_supported': c in weights} for c in CHANGE)
            event('replication_progress', completed=len(rows), total=8, new=counts['new'], replayed=counts['upstream']+counts['reused'])
    metrics = pd.DataFrame(rows)
    anchor = metrics.query("recipe == 'anchor'")[['Season', 'brier']].rename(columns={'brier': 'anchor_brier'})
    metrics = metrics.merge(anchor, on='Season', validate='many_to_one')
    metrics['delta_vs_anchor'] = metrics.brier - metrics.anchor_brier
    metrics['role'] = np.where(metrics.Season.isin(DISCOVERY), 'discovery / selection', 'additional exploratory replication')
    atomic_csv(out / 'replication_metrics.csv', metrics)
    atomic_csv(out / 'replication_predictions.csv', pd.concat(predictions, ignore_index=True))
    atomic_csv(out / 'coefficients.csv', pd.DataFrame(coefficients))
    atomic_csv(out / 'training_redundancy.csv', pd.DataFrame(redundancy))
    atomic_json(out / 'gate.json', replication_gate(metrics))
    atomic_json(out / 'replication_receipt.json', {'status': 'COMPLETE', 'new_classifier_fits': counts['new'],
        'local_checkpoint_reuses': counts['reused'], 'upstream_classifier_replays': counts['upstream'],
        'total_comparisons': 8, 'new_rating_fits': 0})
    seal_stage(out, 'replication', REPLICATION_OUTPUTS)


def checked_replication(out: Path) -> None:
    check_stage(out, 'replication', REPLICATION_OUTPUTS)
    require(read_json(out / 'gate.json') == replication_gate(read_csv(out / 'replication_metrics.csv')),
            'Gate does not match recorded results')


def components(ctx: dict) -> None:
    out = ctx['directory']; checked_replication(out)
    gate = read_json(out / 'gate.json')
    rows = []; counts = {'new': 0, 'reused': 0, 'upstream': 0}
    columns = ['Gender', 'Season', 'recipe', 'removed_feature', 'brier', 'delta_vs_full', 'delta_vs_anchor', 'games']
    if gate['proceed_to_components']:
        bundle = matrices(ctx)
        scores = read_csv(out / 'replication_metrics.csv').pivot(index='Season', columns='recipe', values='brier')
        for s in SEASONS:
            for recipe, inputs in DROPS.items():
                row, _, _, origin = obtain_fit(ctx, s, recipe, inputs, bundle, 8 - counts['new'])
                counts[origin] += 1
                removed = [c for c in CHANGE if c not in inputs]
                require(len(removed) == 1, 'Not a controlled drop-one comparison')
                rows.append({**row, 'removed_feature': removed[0],
                    'delta_vs_full': row['brier'] - float(scores.loc[s, 'anchor_change']),
                    'delta_vs_anchor': row['brier'] - float(scores.loc[s, 'anchor'])})
                event('component_progress', completed=len(rows), total=8, new=counts['new'], reused=counts['reused'])
    else:
        event('components_skipped', reason=gate['decision'])
    atomic_csv(out / 'component_metrics.csv', pd.DataFrame(rows) if rows else pd.DataFrame(columns=columns))
    atomic_json(out / 'component_receipt.json', {'status': 'COMPLETE' if rows else 'SKIPPED_BY_GATE',
        'new_classifier_fits': counts['new'], 'local_checkpoint_reuses': counts['reused'],
        'total_comparisons': len(rows), 'automatic_feature_selection': False})
    seal_stage(out, 'components', ['component_metrics.csv', 'component_receipt.json'])


def report(ctx: dict) -> None:
    from validation_plots import make_report
    out = ctx['directory']; checked_replication(out)
    check_stage(out, 'components', ['component_metrics.csv', 'component_receipt.json'])
    metrics = read_csv(out / 'replication_metrics.csv')
    changes = metrics.query("recipe == 'anchor_change'")
    sensitivity = [{'omitted_season': s, 'remaining_mean_delta': float(changes.loc[changes.Season != s, 'delta_vs_anchor'].mean()),
                    'interpretation': 'Descriptive leave-one-season-out average, not independent resampling'} for s in SEASONS]
    atomic_csv(out / 'season_sensitivity.csv', pd.DataFrame(sensitivity))
    rep = read_json(out / 'replication_receipt.json'); comp = read_json(out / 'component_receipt.json')
    gate = read_json(out / 'gate.json')
    preservation(ctx)
    summary = {'status': 'COMPLETE', 'phase': 'womens_temporal_change_replication', 'fingerprint': ctx['fingerprint'],
        'gender': 'W', 'validation_seasons': SEASONS, 'replication_seasons': REPLICATION,
        'discovery_seasons': DISCOVERY, 'gate': gate, 'component_status': comp['status'],
        'new_feature_definitions': 0, 'unchanged_candidate_features_tested': 2,
        'base_snapshots_reused': 7, 'temporal_snapshots_reused': 7, 'new_rating_fits': 0,
        'new_classifier_fits_this_execution': rep['new_classifier_fits'] + comp['new_classifier_fits'],
        'new_replication_fits_this_execution': rep['new_classifier_fits'],
        'new_component_fits_this_execution': comp['new_classifier_fits'],
        'upstream_classifier_replays': rep['upstream_classifier_replays'],
        'local_checkpoint_reuses': rep['local_checkpoint_reuses'] + comp['local_checkpoint_reuses'],
        'current_submitted_brier': 0.1222672, 'research_target_brier': 0.1097454, 'new_leaderboard_score': None,
        'automatic_promotion': False, 'github_updated': False, 'aws_resources_modified': False,
        'repository_modified': False, 'raw_modified': False, 'upstream_modified': False,
        'limitations': ['Discovery years excluded from gate; all seasons previously used in project research',
            'Overlapping training sets, few seasons and prior feature searches preclude independent-test or significance claims',
            'Fixed reference classifier is not the final submitted production recipe',
            'Late-game surprise changes do not identify injuries, causal improvement, or momentum',
            'No leaderboard gain is established; further temporal-era checks and production transfer needed']}
    atomic_json(out / 'summary.json', summary)
    html, figure_count = make_report(out, ctx['kit'] / 'evidence')
    preservation(ctx)
    names = ['summary.json', 'replication_metrics.csv', 'gate.json', 'replication_receipt.json',
             'component_metrics.csv', 'component_receipt.json', 'coefficients.csv', 'training_redundancy.csv',
             'season_sensitivity.csv', 'feature_registry.csv', 'coverage.csv', 'prior_replay.csv',
             'prepare.json', 'preflight.json', 'manifest.json']
    target = ctx['kit'] / 'reports/milestone_07_return.zip'; tmp = target.with_suffix('.partial')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in names: z.write(safe_file(out, n), n)
    os.replace(tmp, target)
    atomic_json(ctx['kit'] / 'reports/latest_report.json', {'html': str(html), 'return_zip': str(target),
        'run_dir': str(out), 'plotly_figures': figure_count})
    event('report_complete', figures=figure_count, return_zip=str(target))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['prepare', 'replicate', 'components', 'report'])
    for name, env, default in [('repo', 'MARCH_REPO', 'march-machine-learning-mania-2026'),
        ('temporal', 'MARCH_TEMPORAL_KIT', 'march_temporal_form'),
        ('shooting', 'MARCH_SHOOTING_KIT', 'march_shooting_research'),
        ('record', 'MARCH_RECORD_KIT', 'march_record_validation'),
        ('schedule', 'MARCH_SCHEDULE_KIT', 'march_schedule_research')]:
        parser.add_argument('--'+name, type=Path, default=Path(os.getenv(env, str(Path.home()/default))))
    args = parser.parse_args()
    try:
        ctx = preflight(KIT, args.repo, args.temporal, args.shooting, args.record, args.schedule)
        globals()[args.stage](ctx); preservation(ctx)
        atomic_json(KIT / 'reports' / f'{args.stage}_receipt.json', {'status': 'PASS', 'stage': args.stage,
                      'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'fingerprint': ctx['fingerprint']})
    except Exception as exc:
        atomic_json(KIT / 'reports/failure.json', {'status': 'STOP', 'stage': args.stage,
            'exception': type(exc).__name__, 'message': str(exc), 'checkpoints_preserved': True, 'automatic_retry': False})
        raise

if __name__ == '__main__':
    main()
