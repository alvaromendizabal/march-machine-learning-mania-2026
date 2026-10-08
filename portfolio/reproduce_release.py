"""Reproduce public aggregate evidence; never read predictions or train private models.

The default command uses only Python's standard library. ``--build-notebook``
additionally uses the repository's locked notebook and plotting dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("portfolio/release_evidence.json")
REPORT = Path("reports/verified_result/reproduction.json")
SVG = Path("reports/verified_result/score_comparison.svg")
NOTEBOOK = Path("portfolio/verified_result.ipynb")
PUBLICATION = Path("reports/verified_result/notebook_execution.json")


class EvidenceError(ValueError):
    """Evidence failed an integrity, scope, or arithmetic check."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def sha256(value: Any) -> str:
    require(
        isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None,
        "Expected a lowercase SHA-256 digest",
    )
    return value


def probability(value: Any) -> Decimal:
    require(isinstance(value, str), "Scores must be exact decimal strings")
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise EvidenceError("Invalid decimal score") from error
    require(
        number.is_finite() and Decimal(0) <= number <= Decimal(1),
        "Brier score must be finite and between zero and one",
    )
    return number


def positive_count(value: Any, name: str, *, allow_zero: bool = False) -> int:
    require(
        type(value) is int and value >= (0 if allow_zero else 1), f"{name} must be an integer count"
    )
    return value


def public_path(root: Path, relative: Any) -> Path:
    require(isinstance(relative, str) and relative != "", "Missing public evidence path")
    part = Path(relative)
    require(
        not part.is_absolute() and ".." not in part.parts,
        "Public evidence path must stay within the repository",
    )
    path = root / part
    require(
        path.is_file() and path.resolve().is_relative_to(root.resolve()),
        "Missing public evidence or path escapes the repository",
    )
    return path


def validate(evidence: dict[str, Any], root: Path) -> dict[str, Any]:
    """Validate the disclosed release without implying third-party authentication."""
    try:
        require(evidence["schema"] == 1, "Unsupported aggregate evidence schema")
        scored = evidence["scored"]
        require(
            scored["metric"] == "brier" and scored["lower_is_better"] is True,
            "Unsupported score definition",
        )
        accepted, reference = scored["accepted"], scored["reference"]
        score, baseline = probability(accepted["score"]), probability(reference["score"])
        require(baseline > 0, "Reference score must be positive")
        require(accepted["status"] == "COMPLETE", "Submission is not confirmed complete")
        require(
            re.fullmatch(r"[0-9]+", accepted["submission_id"]) is not None,
            "Invalid accepted submission identifier",
        )
        rows = positive_count(accepted["rows"], "Submission rows")
        sha256(accepted["sha256"])
        require(reference["scope"] == "official_competition", "Unknown reference scope")
        require(
            isinstance(reference["label"], str) and bool(reference["label"]),
            "Reference needs a descriptive label",
        )
        require(reference["source_url"].startswith("https://"), "Reference needs an HTTPS source")
        historical = evidence["historical"]
        games = positive_count(historical["games"], "Historical games")
        for prefix in ("legacy", "prior_v81"):
            included = positive_count(historical[f"{prefix}_eligible"], prefix, allow_zero=True)
            excluded = positive_count(historical[f"{prefix}_ineligible"], prefix, allow_zero=True)
            require(included + excluded == games, f"{prefix} coverage loses or duplicates games")
        require(
            historical["consumed"] is True,
            "The reused historical cohort cannot be called an untouched holdout",
        )
        disclosure = evidence["disclosure"]
        require(disclosure["late_submission"] is True, "The submission is post-competition")
        for field in (
            "original_rank_claim",
            "private_training_reproduced",
            "2027_prospectively_validated",
        ):
            require(disclosure[field] is False, f"Unsupported disclosure claim: {field}")
        provenance = evidence["provenance"]
        sha256(provenance["owner_return_sha256"])
        documents = provenance["source_documents"]
        require(
            isinstance(documents, list) and len(documents) > 0,
            "At least one disclosed evidence document is required",
        )
        verified = []
        receipts = []
        seen = set()
        for document in documents:
            path = public_path(root, document["path"])
            require(document["path"] not in seen, "Duplicate provenance document")
            seen.add(document["path"])
            expected = sha256(document["sha256"])
            require(digest(path) == expected, f"Evidence checksum mismatch: {document['path']}")
            verified.append({"path": document["path"], "sha256": expected})
            if path.suffix == ".json":
                content = json.loads(path.read_text(encoding="utf-8"))
                if content.get("kind") == "sanitized_owner_delivery_receipt":
                    receipts.append(content)
        require(len(receipts) == 1, "Exactly one sanitized submission receipt is required")
        receipt = receipts[0]
        for field, value in {
            "submission_id": accepted["submission_id"],
            "remote_status": accepted["status"],
            "public_score": accepted["score"],
            "private_score": accepted["score"],
            "prediction_rows": accepted["rows"],
            "prediction_sha256": accepted["sha256"],
            "source_return_sha256": provenance["owner_return_sha256"],
            "late_submission": True,
            "row_level_predictions_published": False,
        }.items():
            require(receipt[field] == value, f"Submission receipt disagrees on {field}")
        matched = evidence["matched_reconstruction"]
        total = positive_count(matched["evaluation_games"], "Matched evaluation games")
        men = positive_count(matched["men_games"], "Matched men's games")
        women = positive_count(matched["women_games"], "Matched women's games")
        require(men + women == total, "Matched evaluation loses or duplicates games")
        matched_baseline = probability(matched["reference_method_brier"])
        matched_project = probability(matched["project_brier"])
        require(matched_baseline > 0, "Matched reference must be positive")
        for prefix, aggregate in (("reference", matched_baseline), ("project", matched_project)):
            weighted = (
                probability(matched[f"{prefix}_men_brier"]) * men
                + probability(matched[f"{prefix}_women_brier"]) * women
            ) / total
            require(
                abs(aggregate - weighted) < Decimal("0.00000000000001"),
                "Matched aggregate disagrees with game-weighted group scores",
            )
        sha256(matched["source_audit_sha256"])
        require(
            evidence["scope"]["source_foundation_is_causal_score_attribution"] is False,
            "Source coverage does not establish causal score attribution",
        )
        with localcontext() as context:
            context.prec = 40
            reduction = baseline - score
            relative = reduction / baseline * 100
            matched_reduction = matched_baseline - matched_project
            matched_relative = matched_reduction / matched_baseline * 100
        return {
            "schema": 1,
            "status": "PASS",
            "scope": "Public aggregate arithmetic and provenance consistency only",
            "accepted_submission_id": accepted["submission_id"],
            "submission_rows": rows,
            "accepted_brier": str(score),
            "reference_brier": str(baseline),
            "absolute_brier_reduction": str(reduction),
            "relative_brier_reduction_percent": str(relative),
            "relative_brier_reduction_percent_display": format(relative, ".4f"),
            "matched_reconstruction": {
                "evaluation_games": total,
                "men_games": men,
                "women_games": women,
                "reference_method_brier": str(matched_baseline),
                "project_brier": str(matched_project),
                "absolute_brier_reduction": str(matched_reduction),
                "relative_brier_reduction_percent": str(matched_relative),
                "relative_brier_reduction_percent_display": format(matched_relative, ".4f"),
                "source_audit_sha256": matched["source_audit_sha256"],
                "fresh_holdout": False,
            },
            "historical_coverage": historical,
            "source_documents_verified": verified,
            "owner_return_sha256": provenance["owner_return_sha256"],
            "private_predictions_read": False,
            "model_fits": 0,
            "network_requests": 0,
            "fresh_generalization_test": False,
            "statistical_significance_established": False,
            "official_competition_placement_claim": False,
            "private_model_reproduced": False,
        }
    except (KeyError, TypeError, AttributeError) as error:
        raise EvidenceError(f"Malformed aggregate evidence: {error}") from error


def reproduce(root: Path = ROOT, evidence_path: Path = EVIDENCE) -> dict[str, Any]:
    path = public_path(root, str(evidence_path))
    evidence = json.loads(path.read_text(encoding="utf-8"))
    result = validate(evidence, root)
    result["evidence_sha256"] = digest(path)
    result["reproducer_sha256"] = digest(Path(__file__))
    return result


def score_svg(report: dict[str, Any]) -> str:
    """Accessible deterministic plot with a zero baseline and exact score labels."""
    colors = ("#536b83", "#047a70")
    labels = ("Published winning benchmark", "Accepted post-competition release")
    values = (report["reference_brier"], report["accepted_brier"])
    elements = []
    for index, (label, value, color) in enumerate(zip(labels, values, colors, strict=True)):
        y = 105 + index * 100
        width = float(Decimal(value) / Decimal("0.12")) * 530
        elements.extend(
            [
                f'<text x="28" y="{y}" class="label">{html.escape(label)}</text>',
                f'<rect x="28" y="{y + 13}" width="{width:.3f}" height="29" fill="{color}"/>',
                f'<text x="{38 + width:.3f}" y="{y + 34}" class="value">{value}</text>',
            ]
        )
    return (
        "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="780" height="380" '
                'viewBox="0 0 780 380" role="img" aria-labelledby="title description">',
                '<title id="title">Brier score: official competition winner '
                "and accepted post-competition release</title>",
                '<desc id="description">Lower is better. Both bars start at zero. '
                "This is a post-competition comparison, "
                "not an official competition placement.</desc>",
                "<style>text{font-family:Arial,sans-serif;fill:#203449}.label{font-size:17px}"
                ".value{font-size:19px;font-weight:700}.note{font-size:15px}</style>",
                '<rect width="780" height="380" fill="#fff"/>',
                '<text x="28" y="38" font-size="25" font-weight="700">'
                "Official winner vs. accepted late release</text>",
                '<text x="28" y="67" class="note">'
                "Brier score · lower is better · zero baseline</text>",
                *elements,
                '<text x="28" y="308" class="value">'
                f"{report['absolute_brier_reduction']} lower Brier · "
                f"{report['relative_brier_reduction_percent_display']}% relative reduction</text>",
                '<text x="28" y="342" class="note">Post-competition research; '
                "not an original rank or a fresh generalization test.</text>",
                "</svg>",
            ]
        )
        + "\n"
    )


def write_report(root: Path = ROOT) -> dict[str, Any]:
    result = reproduce(root)
    (root / REPORT).parent.mkdir(parents=True, exist_ok=True)
    (root / REPORT).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (root / SVG).write_text(score_svg(result), encoding="utf-8")
    return result


def check_report(root: Path = ROOT) -> dict[str, Any]:
    result = reproduce(root)
    require(
        json.loads((root / REPORT).read_text(encoding="utf-8")) == result,
        "Saved reproduction report differs from current evidence or code",
    )
    require(
        (root / SVG).read_text(encoding="utf-8") == score_svg(result),
        "Saved score figure differs from current evidence",
    )
    return result


def execute_in_process(notebook: Any, root: Path) -> None:
    """Execute real IPython cells where sandbox policy prevents a separate kernel."""
    import os

    import nbformat
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output

    original = Path.cwd()
    shell = InteractiveShell.instance()
    count = 0
    try:
        os.chdir(root)
        for cell in notebook.cells:
            if cell.cell_type != "code":
                continue
            count += 1
            with capture_output() as captured:
                executed = shell.run_cell(cell.source, store_history=True, silent=False)
            if executed.error_before_exec or executed.error_in_exec:
                raise EvidenceError(f"Notebook cell {count} failed")
            outputs = []
            for name in ("stdout", "stderr"):
                text = getattr(captured, name)
                if text:
                    outputs.append(nbformat.v4.new_output("stream", name=name, text=text))
            for output in captured.outputs:
                outputs.append(
                    nbformat.v4.new_output(
                        "display_data", data=output.data, metadata=output.metadata
                    )
                )
            cell.execution_count = count
            cell.outputs = outputs
    finally:
        os.chdir(original)


def build_notebook(
    root: Path = ROOT, kernel: str = "python3", *, in_process: bool = False
) -> dict[str, Any]:
    import nbformat
    from nbclient import NotebookClient

    markdown, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    notebook = nbformat.v4.new_notebook(
        cells=[
            markdown(
                "# NCAA tournament forecasting: verified release\n"
                "**Alvaro Mendizabal · evidence-led ML engineering**\n\n"
                "This executable public review reconstructs the score comparison, checks "
                "disclosed evidence hashes, and preserves the complete historical cohort. "
                "It does not train or disclose the private forecasting recipe."
            ),
            code(
                "from pathlib import Path\nimport json, sys\n"
                "root = Path.cwd()\n"
                "if not (root / 'portfolio').is_dir(): root = root.parent\n"
                "sys.path.insert(0, str(root / 'portfolio'))\n"
                "from reproduce_release import write_report\n"
                "result = write_report(root)\n"
                "print(json.dumps({key: result[key] for key in [\n"
                "    'accepted_submission_id', 'submission_rows', 'accepted_brier',\n"
                "    'reference_brier', 'absolute_brier_reduction',\n"
                "    'relative_brier_reduction_percent_display']}, indent=2))"
            ),
            markdown(
                "## Size of the observed improvement\n"
                "The comparison uses exact decimal inputs and reports both absolute and "
                "relative Brier reduction. Lower Brier means lower mean squared probability "
                "error on the scored games. The measured reduction is useful evidence of "
                "progress; score arithmetic alone does not establish statistical significance "
                "or isolate a causal contribution from any single technique."
            ),
            code(
                "import base64, io\nimport matplotlib.pyplot as plt\n"
                "import plotly.graph_objects as go\nfrom IPython.display import display\n"
                "labels = ['Published winning benchmark', 'Accepted late release']\n"
                "values = [float(result['reference_brier']), float(result['accepted_brier'])]\n"
                "colors = ['#536b83', '#047a70']\n"
                "figure = go.Figure(go.Bar(x=labels, y=values, marker_color=colors,\n"
                "    text=[f'{value:.7f}' for value in values], textposition='outside'))\n"
                "figure.update_layout(title='Brier score comparison — lower is better',\n"
                "    width=960, height=530, yaxis_range=[0, 0.125],\n"
                "    yaxis_title='Brier score', template='plotly_white', font_size=16)\n"
                "static, axis = plt.subplots(figsize=(10, 5.5), layout='constrained')\n"
                "bars = axis.bar(labels, values, color=colors, width=0.55)\n"
                "axis.bar_label(bars, labels=[f'{value:.7f}' for value in values], padding=5)\n"
                "axis.set_ylim(0, 0.125)\naxis.set_ylabel('Brier score (lower is better)')\n"
                "axis.set_title('Published benchmark and accepted post-competition release')\n"
                "stream = io.BytesIO()\nstatic.savefig(stream, format='png', dpi=140)\n"
                "plt.close(static)\n"
                "png_path = root / 'reports/verified_result/score_comparison.png'\n"
                "png_path.write_bytes(stream.getvalue())\n"
                "display({'application/vnd.plotly.v1+json': json.loads(figure.to_json()),\n"
                "    'image/png': base64.b64encode(stream.getvalue()).decode()}, raw=True)"
            ),
            markdown(
                "## Complete cohort, separate eligibility histories\n"
                "All historical games remain visible, including unavailable-source cases. "
                "Legacy source eligibility and the prior player-model eligibility are distinct "
                "masks; neither is represented as a newly untouched validation set. These are "
                "aggregate retained counts, not a reconstruction of private per-game outcomes."
            ),
            code(
                "coverage = result['historical_coverage']\n"
                "print(json.dumps(coverage, indent=2))\n"
                "assert (coverage['legacy_eligible'] + coverage['legacy_ineligible']\n"
                "        == coverage['games'])\n"
                "assert (coverage['prior_v81_eligible'] + coverage['prior_v81_ineligible']\n"
                "        == coverage['games'])\n"
                "print('Every game is retained; eligibility masks remain separately identified.')"
            ),
            markdown(
                "## Separate matched reconstruction\n"
                "The 126-game matched audit is a different comparison from the published "
                "winning score above. Its reference is a reconstruction of the reference "
                "method on 63 men's and 63 women's games. Keeping the two denominators "
                "separate prevents conflating an official leaderboard score with a "
                "locally reconstructed method. The aggregate change is concentrated in "
                "the men's forecasts; the women's probabilities were reconciled to the "
                "reference. These outcomes had already been inspected."
            ),
            code("print(json.dumps(result['matched_reconstruction'], indent=2))"),
            markdown(
                "## Evidence integrity and limits\n"
                "The verifier checks the SHA-256 of each disclosed evidence document. "
                "Those hashes demonstrate consistency with this release, not independent "
                "authentication by Kaggle. The acceptance receipt is an owner-supplied "
                "aggregate, and the reference links to the published competition result.\n\n"
                "The accepted result was produced after the competition. It is numerically "
                "below the published winning score, but it is not an original competition "
                "placement or a prospective 2027 result. Consumed historical outcomes and "
                "post-competition research limit generalization claims."
            ),
            code(
                "print(json.dumps(result['source_documents_verified'], indent=2))\n"
                "print('Evidence SHA-256:', result['evidence_sha256'])\n"
                "print('Private model reproduced:', result['private_model_reproduced'])\n"
                "print('Model fits:', result['model_fits'])\n"
                "print('Network requests:', result['network_requests'])\n"
                "print('VERIFIED_PUBLIC_REVIEW_COMPLETE')"
            ),
            markdown(
                "## Public reproduction boundary\n"
                "The repository includes runnable public baseline and review code. This "
                "notebook is the compact verification path for the latest accepted release. "
                "Private predictions, model binaries, exact blend choices, and the current "
                "private feature recipe are intentionally excluded. A credible next "
                "generalization claim requires timestamped source inputs and frozen "
                "predictions recorded before future tournament outcomes."
            ),
        ],
        metadata={"kernelspec": {"name": kernel, "display_name": "Python 3", "language": "python"}},
    )
    if in_process:
        execute_in_process(notebook, root)
    else:
        NotebookClient(
            notebook, timeout=120, kernel_name=kernel, resources={"metadata": {"path": str(root)}}
        ).execute()
    notebook.metadata["execution_engine"] = "ipython_in_process" if in_process else "jupyter_kernel"
    (root / NOTEBOOK).write_text(nbformat.writes(notebook), encoding="utf-8")
    receipt = inspect_notebook(root)
    (root / PUBLICATION).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def inspect_notebook(root: Path = ROOT) -> dict[str, Any]:
    notebook = json.loads((root / NOTEBOOK).read_text(encoding="utf-8"))
    cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    outputs = [output for cell in cells for output in cell.get("outputs", [])]
    require(
        len(cells) == 5
        and [cell["execution_count"] for cell in cells] == list(range(1, len(cells) + 1)),
        "Notebook cells were not executed in order",
    )
    require(not any(output["output_type"] == "error" for output in outputs), "Notebook has errors")
    require("VERIFIED_PUBLIC_REVIEW_COMPLETE" in str(outputs), "Notebook lacks completion marker")
    plots = sum("application/vnd.plotly.v1+json" in output.get("data", {}) for output in outputs)
    images = sum("image/png" in output.get("data", {}) for output in outputs)
    require(plots == 1 and images == 1, "Notebook needs Plotly and static PNG output")
    check_report(root)
    return {
        "status": "PASS",
        "notebook_sha256": digest(root / NOTEBOOK),
        "evidence_sha256": digest(root / EVIDENCE),
        "reproducer_sha256": digest(Path(__file__)),
        "code_cells": len(cells),
        "plotly_outputs": plots,
        "png_outputs": images,
        "execution_engine": notebook["metadata"]["execution_engine"],
        "png_sha256": digest(root / "reports/verified_result/score_comparison.png"),
        "model_fits": 0,
        "private_model_reproduced": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify saved report and SVG")
    parser.add_argument(
        "--build-notebook", "--execute-notebook", action="store_true", help="Execute public review"
    )
    parser.add_argument("--check-notebook", action="store_true", help="Verify notebook receipt")
    parser.add_argument("--kernel", default="python3")
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Use real sequential IPython cells without a separate kernel",
    )
    args = parser.parse_args()
    if args.build_notebook:
        report = build_notebook(kernel=args.kernel, in_process=args.in_process)
    elif args.check_notebook:
        report = inspect_notebook()
        require(
            report == json.loads((ROOT / PUBLICATION).read_text(encoding="utf-8")),
            "Notebook publication receipt differs from current outputs",
        )
    else:
        report = check_report() if args.check else write_report()
        if args.check:
            inspected = inspect_notebook()
            require(
                inspected == json.loads((ROOT / PUBLICATION).read_text(encoding="utf-8")),
                "Notebook publication receipt differs from current outputs",
            )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
