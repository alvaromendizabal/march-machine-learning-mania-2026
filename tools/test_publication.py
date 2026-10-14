"""Adversarial checks for changed-blob publication review, without private inputs."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from check_publication import inspect_blob, review


class ContentTests(unittest.TestCase):
    def test_private_artifacts(self):
        for name in ("runner.pyz", "return.zip", "data.csv.gz", "fit.joblib", "rows.parquet"):
            with self.subTest(name=name):
                self.assertTrue(inspect_blob(name, b"private"))

    def test_renamed_prediction_csv_is_rejected(self):
        self.assertIn(
            "row-level submission probabilities",
            inspect_blob("reports/result.csv", b"ID,Pred\n2026_1_2,0.5\n"),
        )

    def test_prediction_json_is_rejected(self):
        raw = json.dumps({"rows": [{"ID": "2026_1_2", "Pred": 0.5}]}).encode()
        self.assertIn(
            "row-level submission probabilities", inspect_blob("reports/result.json", raw)
        )

    def test_renamed_private_columns_are_rejected(self):
        columns = ["ID", "Owned" + "V155P", "Kalshi" + "TitleRatio"]
        self.assertIn(
            "private source/prediction columns",
            inspect_blob("safe.csv", (",".join(columns) + "\n2026_1_2,0.5,0.7\n").encode()),
        )

    def test_known_original_source_inventory_rejected(self):
        self.assertTrue(inspect_blob("target_23_injury_and_bpr_source_inventory.json", b"{}"))

    def test_credential_detection_does_not_print_value(self):
        token = "ghp_" + "a" * 36
        findings = inspect_blob("README.md", token.encode())
        self.assertTrue(findings)
        self.assertNotIn(token, str(findings))

    def test_cloud_key_and_signed_link(self):
        for value in ("AKIA" + "A" * 16, "https://example.test/?X-Amz-Signature=" + "f" * 64):
            self.assertTrue(inspect_blob("notes.md", value.encode()))

    def test_aggregate_evidence_allowed(self):
        self.assertEqual(
            inspect_blob("reports/metrics.csv", b"season,brier,n_games\n2026,0.1,126\n"), []
        )
        raw = json.dumps(
            {"submission_id": "123", "score": 0.1, "forecast_sha256": "a" * 64}
        ).encode()
        self.assertEqual(inspect_blob("portfolio/release.json", raw), [])

    def test_existing_public_recipe_allowed(self):
        raw = json.dumps(
            {"weights": [0.25, 0.75], "feature_names": ["seed", "elo"], "threshold": 0.6}
        ).encode()
        self.assertEqual(inspect_blob("configs/model_recipe.json", raw), [])

    def test_explicit_authored_example_allowed(self):
        raw = b"ID,Pred,scope\nsynthetic_a_b,0.5,SYNTHETIC_ONLY\n"
        self.assertEqual(inspect_blob("examples/scoring.csv", raw), [])
        self.assertTrue(inspect_blob("reports/scoring.csv", raw))

    def test_synthetic_label_cannot_mask_real_ids(self):
        raw = b"ID,Pred,scope\n2026_1_2,0.5,SYNTHETIC_ONLY\n"
        self.assertTrue(inspect_blob("examples/scoring.csv", raw))

    def test_binary_figure_allowed_but_symlink_rejected(self):
        self.assertEqual(inspect_blob("docs/assets/figure.png", b"\x89PNG\xff"), [])
        self.assertTrue(inspect_blob("docs/receipt", b"../private", symlink=True))

    def test_malformed_json_fails_closed(self):
        self.assertTrue(inspect_blob("portfolio/release.json", b"{"))


class GitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.test")
        self.git("config", "user.name", "Test Fixture")
        (self.root / "README.md").write_text("public baseline\n")
        # Existing historical rows are not reclassified or deleted by this guard.
        (self.root / "history.csv").write_text("ID,Pred\n2020_1_2,0.5\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").decode().strip()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.PIPE)

    def test_index_not_worktree_is_reviewed(self):
        path = self.root / "result.csv"
        path.write_text("ID,Pred\n2026_1_2,0.5\n")
        self.git("add", "result.csv")
        path.write_text("season,brier\n2026,0.1\n")
        result = review(self.root)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["files_checked"], 1)

    def test_exact_commit_not_worktree_is_reviewed(self):
        (self.root / "README.md").write_text("Reviewed public work\n")
        self.git("add", "README.md")
        self.git("commit", "-qm", "reviewed")
        head = self.git("rev-parse", "HEAD").decode().strip()
        (self.root / "README.md").write_text("ghp_" + "a" * 36)
        result = review(self.root, base=self.base, head=head)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["source"], head)
        self.assertEqual(result["files_checked"], 1)

    def test_renamed_private_file_is_reviewed(self):
        self.git("mv", "history.csv", "renamed.csv")
        self.assertEqual(review(self.root)["status"], "FAIL")

    def test_deletions_do_not_republish_content(self):
        self.git("rm", "history.csv")
        self.assertEqual(review(self.root)["files_checked"], 0)

    def test_file_changed_to_symlink_is_reviewed(self):
        path = self.root / "README.md"
        path.unlink()
        path.symlink_to("../private")
        self.git("add", "README.md")
        result = review(self.root)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["files_checked"], 1)


if __name__ == "__main__":
    unittest.main()
