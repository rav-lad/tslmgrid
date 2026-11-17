"""Copy the annotation pipeline into the TimeNet connector, which must be self-contained.

Run: ``uv run python scripts/sync_connector.py [--check]``. ``swissgrid_cot`` stays the single source
of truth; the copy under ``_pipeline/`` only rewrites the import paths. ``--check`` fails if the copy
is stale (the test suite runs it).
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "swissgrid_cot"
CONNECTOR = (
    REPO / "ext" / "TimeNet" / "packages" / "timenet-connectors" / "src" / "timenet_connectors" / "datasets"
    / "scooby_team" / "swiss_grid_anomaly_cot"
)  # fmt: skip
TIMENET = REPO / "ext" / "TimeNet"
MODULES = {
    "stations.py": SRC / "ingest" / "stations.py",
    "swissgrid.py": SRC / "ingest" / "swissgrid.py",
    "meteoswiss.py": SRC / "ingest" / "meteoswiss.py",
    "calendar_ch.py": SRC / "ingest" / "calendar_ch.py",
    "baseline.py": SRC / "annotate" / "baseline.py",
    "anomalies.py": SRC / "annotate" / "anomalies.py",
    "causes.py": SRC / "annotate" / "causes.py",
    "rationales.py": SRC / "annotate" / "rationales.py",
    "qa.py": SRC / "annotate" / "qa.py",
    "timefields.py": SRC / "ingest" / "timefields.py",
    "assemble.py": SRC / "ingest" / "assemble.py",
    "run.py": SRC / "annotate" / "run.py",
}
INIT = '"""The annotation pipeline, copied from the swissgrid_cot project by its sync script."""\n'


def rendered() -> dict[Path, str]:
    out = {CONNECTOR / "_pipeline" / "__init__.py": INIT}
    for name, src in MODULES.items():
        text = src.read_text(encoding="utf-8")
        # Relative imports: the copy lives in a private package of the connector.
        for sub in ("ingest", "annotate"):
            text = text.replace(f"from swissgrid_cot.{sub} import ", "from . import ")
            text = text.replace(f"from swissgrid_cot.{sub}.", "from .")
        if "swissgrid_cot" in text:
            raise SystemExit(f"{name}: an import of swissgrid_cot is left after rewriting")
        target = CONNECTOR / "_pipeline" / name
        out[target] = ruff(["format", "--stdin-filename", str(target), "-"], ruff(
            ["check", "--fix", "--select", "I", "--stdin-filename", str(target), "-"], text))  # fmt: skip
    return out


def ruff(args: list[str], text: str) -> str:
    """Run TimeNet's ruff, with TimeNet's config, on text passed through stdin."""
    done = subprocess.run(
        ["uv", "run", "--no-sync", "ruff", *args], cwd=TIMENET, input=text.encode("utf-8"),
        capture_output=True, check=False,
    )  # fmt: skip
    if done.returncode not in (0, 1):
        raise SystemExit(done.stderr.decode())
    return done.stdout.decode("utf-8").replace("\r\n", "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for path, text in rendered().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != text:
            stale.append(path)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8", newline="\n")
    if args.check and stale:
        print("stale:", *[str(p.relative_to(REPO)) for p in stale], sep="\n  ", file=sys.stderr)
        sys.exit(1)
    print(f"{'checked' if args.check else 'synced'} {len(rendered())} files")


if __name__ == "__main__":
    main()
