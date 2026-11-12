"""Download every source file and check it against ``sources.lock.json``.

Usage::

    uv run sgcot-download                 # fetch missing files, verify all digests
    uv run sgcot-download --update-lock   # record the digests of the files on disk

A digest mismatch means the publisher revised a file (Swissgrid and MeteoSwiss both do). The run
then stops, so a revision is a deliberate decision, never a silent change of the data.
"""

import argparse
import hashlib
import json
import sys

import requests

from swissgrid_cot.sources import BFS_POPULATION, BFS_QUERY, LOCK_PATH, SourceFile, all_sources

_HEADERS = {"User-Agent": "swissgrid-cot/0.1 (research dataset build)"}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(source: SourceFile) -> None:
    source.path.parent.mkdir(parents=True, exist_ok=True)
    if source is BFS_POPULATION:
        response = requests.post(source.url, json=BFS_QUERY, headers=_HEADERS, timeout=120)
    else:
        response = requests.get(source.url, headers=_HEADERS, timeout=300)
    response.raise_for_status()
    tmp = source.path.with_suffix(source.path.suffix + ".part")
    tmp.write_bytes(response.content)
    tmp.replace(source.path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--update-lock", action="store_true", help="write the digests of the files on disk")
    args = parser.parse_args()

    lock = json.loads(LOCK_PATH.read_text()) if LOCK_PATH.exists() else {}
    problems = []
    for source in all_sources():
        if not source.path.exists():
            print(f"downloading {source.key} <- {source.url}")
            fetch(source)
        digest = sha256(source.path)
        if args.update_lock:
            lock[source.key] = {"url": source.url, "sha256": digest}
        elif source.key not in lock:
            problems.append(f"{source.key}: not in {LOCK_PATH.name}; run with --update-lock")
        elif lock[source.key]["sha256"] != digest:
            problems.append(f"{source.key}: sha256 {digest} differs from the lock {lock[source.key]['sha256']}")
        else:
            print(f"ok {source.key}")
    if args.update_lock:
        LOCK_PATH.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
        print(f"wrote {LOCK_PATH}")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
