"""Portable publication and evidence-type contracts; no cloud or private-data access."""
import hashlib
import io
import json
import re
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from package_public_demo import artifacts

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_identical_source_produces_identical_artifacts(self):
        first = artifacts(ROOT / "public-demo")
        self.assertEqual(first, artifacts(ROOT / "public-demo"))
        manifest = json.loads(first["manifest.json"])
        self.assertFalse(manifest["private_assets_used"])
        for name, expected in manifest["outputs"].items():
            self.assertEqual(hashlib.sha256(first[name]).hexdigest(), expected["sha256"])

    def test_zip_contains_exactly_five_reviewed_files(self):
        output = artifacts(ROOT / "public-demo")
        with zipfile.ZipFile(io.BytesIO(output["Tournament_Lab.zip"])) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()),
                             {"index.html", "engine.js", "app.js", "data.js", "styles.css"})

    def test_standalone_has_local_code_at_end_and_visible_synthetic_scope(self):
        html = artifacts(ROOT / "public-demo")["Tournament_Lab.html"].decode()
        self.assertNotRegex(html, r'<script[^>]+src=')
        self.assertNotIn('rel="stylesheet"', html)
        self.assertIn("SYNTHETIC SCENARIOS", html)
        self.assertIn("Duke", html)
        self.assertGreater(html.index("<script>"), html.index('id="price-a"'))
        self.assertEqual(html.count("<script>"), 3)

    def test_adjacent_private_blob_is_never_packaged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "public-demo", root / "public-demo")
            (root / "private-model.pkl").write_bytes(b"NEVER_PUBLIC")
            output = artifacts(root / "public-demo")
            self.assertNotIn(b"NEVER_PUBLIC", output["Tournament_Lab.zip"])
            (root / "public-demo/private-model.pkl").write_bytes(b"NEVER_PUBLIC")
            with self.assertRaisesRegex(ValueError, "Unreviewed public"):
                artifacts(root / "public-demo")

    def test_review_snapshot_separates_receipt_from_inherited_score(self):
        snapshot = json.loads((ROOT / "portfolio/review_snapshot.json").read_text())
        receipt = json.loads((ROOT / snapshot["direct_receipt"]).read_text())
        self.assertEqual(snapshot["directly_published_earlier_brier"], float(receipt["public_score"]))
        self.assertEqual(snapshot["score_evidence_class"],
                         "INHERITED_OWNER_EXECUTION_RECORD_NOT_FRESH_KAGGLE_RECEIPT")
        self.assertFalse(snapshot["latest_inspected_activity"]["full_private_replay_complete"])
        self.assertFalse(snapshot["public_demo"]["private_assets_used"])
        for key in ("source_zip_sha256", "manifest_sha256", "summary_sha256"):
            self.assertRegex(snapshot["provenance"][key], r"^[0-9a-f]{64}$")
        self.assertNotRegex(json.dumps(snapshot), r"s3://|arn:aws|/home/|/mnt/")


if __name__ == "__main__":
    unittest.main()
