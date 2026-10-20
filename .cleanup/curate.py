"""Retire only inspected legacy copies; retain active science, tests and AWS state."""
from pathlib import Path
import shutil,subprocess
ROOT=Path.cwd()
BASE='54ce7dce1efad2de3ff55fd9e9fb6182c76df1cd'
if subprocess.check_output(['git','rev-parse','origin/main'],text=True).strip()!=BASE:
    raise RuntimeError('Main advanced; reconcile before modifying source')
subprocess.run(['git','diff','--exit-code',BASE,'HEAD','--','.',':(exclude).cleanup',':(exclude).github/workflows/zz-sweep-apply.yml'],check=True)
for name in ['reports/feature_engineering','reports/final_2026','tools/consolidation','docs/research_audit.md','docs/completion_plan.md','docs/assets/tournament-lab-hero.svg','configs/model_recipe.yaml']:
    p=ROOT/name
    if p.is_dir():shutil.rmtree(p)
    elif p.is_file():p.unlink()
    else:raise ValueError('Inspected retirement path missing: '+name)
keep={'03_model_comparison/matched_season_model_comparison.csv','03_model_comparison/winner_summary.csv'}
for p in (ROOT/'reports/modeling').rglob('*'):
    if p.is_file() and str(p.relative_to(ROOT/'reports/modeling')) not in keep:p.unlink()
for name in keep:
    if not (ROOT/'reports/modeling'/name).is_file():raise ValueError('Required historical input missing')
p=ROOT/'reports/model_comparison/README.md'
s=p.read_text();old='[completion audit](../../docs/research_audit.md) records the final execution gates.'
if s.count(old)!=1:raise ValueError('Model comparison navigation changed')
p.write_text(s.replace(old,'[maintained scope](../../docs/PROJECT_SCOPE.md) identifies the retained execution gates.'))
p=ROOT/'reports/prediction_portfolio/README.md';s=p.read_text()
s=s[:s.index('## Next release')]+'''## Historical catalogue and current delivery

This is a recorded development catalogue, not the current private execution plan.
The [featured scored artifact](../../docs/champion_result.md) has a separate identity
and evidence. The [maintained scope](../../docs/PROJECT_SCOPE.md) explains public
reproduction and ongoing private AWS work. Cleanup changes neither the catalogue's
original metrics nor the recorded historical generation status in its manifest.
''';p.write_text(s)
(ROOT/'docs/PROJECT_SCOPE.md').write_text('''# What this repository maintains

**NCAA probability forecasting, with independent evaluation and a runnable public reference.**

The [featured scored artifact](champion_result.md), the historical public framework,
and the authored bracket demonstration have distinct identities. A successful
public example is not a reproduction of a private competition score.

| Review path | Maintained components | Evidence boundary |
|---|---|---|
| Featured delivery | `portfolio/reproduce_release.py`, the scored receipt and acceptance checks | Recorded retrospective result; not a prospective win-rate claim |
| Forecasting framework | `src/march_mania/`, the six canonical notebooks and their consumed aggregate inputs | Training-only features, season-forward comparisons and recoverable execution |
| Interactive analysis | `public-demo/`, public reproduction, packaging and browser tests | Authored team strengths and scenarios, not live odds or forecasts |
| Ongoing research | Existing private AWS workspace, data and checkpoint lineages | Not closed, restarted or synchronized by repository presentation changes |

## What was retired from the current tree

Unreferenced legacy feature-engineering/final-export report copies, an unused large
feature-audit export, an obsolete model-recipe duplicate, one-time consolidation
scripts, and completed branch-specific publication jobs are not part of this
maintained review. Two old model-comparison CSVs remain because the canonical
notebook and protocol actually consume or cite them. Essential baseline comparisons,
negative outcomes, attribution, fitted-reference code and active test gates remain.
Git history preserves retired material without advertising it as the current system.

## Reproduce without private assets

Start with [the technical walkthrough](../START_HERE.md) and
[public reproduction](public_reproduction.md). The full framework uses the pinned
Python environment and retains its original tests, type/lint gates, native notebook
execution, score-ledger checks and independent browser evaluation. The repository
hygiene check also verifies Markdown links inside notebooks and rejects tracked
runtime caches and temporary run handoffs.

Private models, exact tuned recipes, licensed source records, secrets and raw
forecast arrays are not added by this publication. AWS is still the scientific
execution environment. Do not reset a running workspace or delete its checkpoints
to make a GitHub directory smaller.
''')
p=ROOT/'START_HERE.md';s=p.read_text();p.write_text(s.replace('## Full framework review','[Maintained scope and publication boundary](docs/PROJECT_SCOPE.md) distinguish the active framework from retired one-time report copies.\n\n## Full framework review'))
print('Legacy copies retired; active source, scientific tests and retained notebook definitions unchanged')
