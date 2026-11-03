# Evidence you can trace all the way to the bytes

An executed notebook is useful evidence only if a reviewer can locate the exact
body behind its receipt. This project now packages the public CI source,
native notebook outputs and validation records as a **closed, independently
checkable bundle**. Verification uses Python's standard library and does not
execute anything from the archive.

[Pure verifier](../src/march_mania/publication/evidence_bundle.py) ·
[CLI](../tools/evidence_bundle.py) ·
[Adversarial tests](../tools/test_evidence_bundle.py) ·
[Workflow](../.github/workflows/ci.yml)

## The concrete gap this closes

The preceding publication retained all six canonical notebooks and every
declared dependency body. However, the separately regenerated five-cell
scored-result receipt referenced a notebook body that was not retained in the
CI artifacts. Its evidence, reproducer and PNG hashes had matching bodies;
its notebook hash did not. A passing receipt was not enough to close that gap.

The workflow now retains the generated notebook and PNG alongside their
receipt, then checks the entire chain before publishing a closed bundle.
Historical artifacts are not retroactively relabeled complete.

| Link in the evidence chain | What the verifier checks |
|---|---|
| Externally obtained identity → bundle | Exact byte count and SHA-256, repository, workflow/run/attempt/job, event, reviewed head, checked source commit and tree |
| Bundle → every retained payload | Safe unique regular names, complete CRC checks, byte counts, SHA-256 and exact manifest set closure; no unregistered validation path |
| Source archive → reviewed code | Every Git blob and nested tree is reconstructed in memory; the exact root tree and archive commit must match |
| Six canonical notebooks → checkpoints | Actual notebook bodies, checkpoint output set, all input hashes, notebook definitions and every declared dependency body |
| Cold execution → warm reuse | Exact notebook/cell identities and successful cell events, with one cold run and one whole-notebook reuse run |
| Five-cell result receipt → native output | All four body pins; reviewed code and narrative; five ordered code cells; no errors/warnings; matching embedded and standalone PNG |
| Quality job → tests | All five quality gates pass; JUnit totals reconcile with unique cases and no failures, errors or skips |

Dependency counts are measured from each exact source tree; they are not held
artificially at an older release's count. The six canonical notebooks currently
contain 57 code cells. The separate result notebook has five. The verifier
executes **zero** of those cells, fits **zero** models and scores **zero** forecasts.

## Two job scopes, not one interchangeable claim

| Bundle | New execution in that CI job | Separate five-cell result body |
|---|---|---|
| `research-evidence-bundle` / `quality` | Full quality gates, canonical notebook execution and warm reuse | Actual regenerated Jupyter-kernel output, retained with its matching receipt and PNG |
| `notebook-evidence-bundle` / `notebook-publication` | Canonical notebook execution and warm reuse | Exact committed input body; explicitly **not** claimed as a new five-cell execution |

Both jobs retain their raw validation artifacts as well. Failed or interrupted
checks remain failures; raw diagnostic uploads do not turn into successful
bundles. No protective rule is disabled to obtain a green check.

## Audit a downloaded bundle

Open the exact **Research quality** workflow run for the commit being reviewed
and download its named evidence-bundle artifact. It contains
`evidence_bundle.zip`, `external_binding.json` and `verification.json`.

Before treating the binding as trusted, check the artifact's provider-reported
digest and its association with the exact repository, workflow run, attempt,
head and checked source tree. A pull-request job often checks a **virtual merge
commit**, not the PR head commit itself. The binding keeps both identities;
neither may be silently substituted for the other. The companion binding file
is transport metadata, not an independent signature or proof of authorship.

After those external identity checks, run from the repository root:

```bash
python tools/evidence_bundle.py verify --bundle /path/to/evidence_bundle.zip --binding /path/to/external_binding.json
```

The report records measured notebook, cell and dependency counts, verified
nested pins, exact source identity and explicit limits. No credentials,
scientific dependencies or service connection are needed. Archive content is
never extracted or imported as executable code. The verifier rejects missing
bodies, changed inputs, unsafe names, duplicate JSON keys, nonfinite JSON,
cross-run bindings, unexecuted cells and failed test records.

## Trust and privacy boundaries

- SHA-256 and a closed manifest prove byte consistency with a trusted external
  pin. They do not establish who authored the file or when a private provider
  made a feature available.
- A native output can be inspected without executing its code. Evidence of the
  actual CI run comes from the separately checked workflow and artifact records.
- The archive is limited to public source, sanitized aggregate evidence and
  public review outputs. Private owner Returns, source bodies, cloud locations,
  competition models and competitive recipes do not enter this publication path.
- This is release-engineering evidence, not a new predictive improvement,
  deployment, prospective holdout, source-debt closure or private-model replay.
- The focused test coverage applies to this verifier module, not the entire
  project. The full quality report retains the explicitly selected coverage scope.

[Return to the employer review](../START_HERE.md) ·
[Reproducibility boundaries](reproduction_matrix.md) ·
[Publication policy](REPOSITORY_POLICY.md)
