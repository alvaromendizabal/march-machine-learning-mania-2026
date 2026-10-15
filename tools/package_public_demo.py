"""Build an offline HTML and deterministic ZIP from the allowlisted public demo only."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from check_public_demo import REQUIRED, verify


def artifacts(source: Path) -> dict[str, bytes]:
    """Validate first; never package the repository, research files, or adjacent assets."""
    report = verify(source)
    html = (source / "index.html").read_text(encoding="utf-8")
    html, count = re.subn(
        r'<link\s+rel="stylesheet"\s+href="styles\.css"\s*/>',
        lambda _: "<style>\n" + (source / "styles.css").read_text() + "\n</style>",
        html,
    )
    if count != 1:
        raise ValueError("Expected exactly one local stylesheet")
    for name in ("data.js", "engine.js", "app.js"):
        script = (source / name).read_text(encoding="utf-8")
        if re.search(r"</script", script, re.IGNORECASE):
            raise ValueError("Unsafe script closing sequence")
        html, count = re.subn(
            rf'<script\s+defer\s+src="{re.escape(name)}"></script>',
            lambda _: "<script>\n" + script + "\n</script>",
            html,
        )
        if count != 1:
            raise ValueError("Expected exactly one local script: " + name)
    # The original scripts are deferred. Inline scripts must execute after the DOM exists.
    blocks = re.findall(r"<script>.*?</script>", html, re.DOTALL)
    html = re.sub(r"<script>.*?</script>", "", html, flags=re.DOTALL)
    if len(blocks) != 3 or html.count("</body>") != 1:
        raise ValueError("Unexpected HTML entry structure")
    html = html.replace("</body>", "\n".join(blocks) + "\n</body>")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(REQUIRED):
            entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, (source / name).read_bytes())
    outputs = {"Tournament_Lab.html": html.encode(), "Tournament_Lab.zip": buffer.getvalue()}
    manifest = {
        "schema": 1, "scope": "PUBLIC_SYNTHETIC_DEMO_ONLY",
        "source_boundary": report,
        "outputs": {name: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                    for name, raw in sorted(outputs.items())},
        "private_assets_used": False,
    }
    outputs["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = args.output or root / "outputs/public-demo"
    source = root / "public-demo"
    if destination.resolve().is_relative_to(source.resolve()):
        raise ValueError("Build output cannot be inside source")
    content = artifacts(source)
    if content != artifacts(source):
        raise ValueError("Non-deterministic build")
    destination.mkdir(parents=True, exist_ok=True)
    for name, raw in content.items():
        (destination / name).write_bytes(raw)
    print(json.dumps({"status": "PASS", "scope": "PUBLIC_SYNTHETIC_DEMO_ONLY",
                      "output": str(destination), "files": sorted(content)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
