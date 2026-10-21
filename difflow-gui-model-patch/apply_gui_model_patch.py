"""Apply the local GUI patch after checking the exact base and target files."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone


def digest(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    bundle = Path(__file__).resolve().parent
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    head = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != manifest["base_commit"]:
        raise RuntimeError("HEAD differs from base 086c56e. No files changed.")
    todo = []
    for entry in manifest["files"]:
        relative = entry["path"]
        target = root / relative
        payload = (bundle / "payload" / relative).read_bytes()
        if digest(payload) != entry["after"]:
            raise RuntimeError("Corrupt patch payload: " + relative)
        current = target.read_bytes() if target.exists() else None
        if current is not None and digest(current) == entry["after"]:
            continue
        if entry["before"] is None:
            if current is not None:
                raise RuntimeError("New target already exists: " + relative)
        elif current is None or digest(current) != entry["before"]:
            raise RuntimeError("Target has other changes: " + relative)
        todo.append((relative, current, payload))
    print("Base and file checks passed. Files to update:", len(todo))
    if args.check or not todo:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = root.parent / "difflow-gui-model-backups" / stamp
    backup.mkdir(parents=True)
    for relative, current, _ in todo:
        if current is not None:
            dest = backup / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(current)
    (backup / "new-files.json").write_text(
        json.dumps([p for p, old, _ in todo if old is None], indent=2), encoding="utf-8"
    )
    try:
        for relative, _, payload in todo:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    except Exception:
        for relative, current, _ in todo:
            target = root / relative
            if current is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(current)
        raise
    print("Applied GUI model patch. Backup:", backup)
    print("Restart difflow GUI and hard-reload the browser (Ctrl+F5).")
    print("No commits, branch switches or pushes were performed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Patch stopped:", exc, file=sys.stderr)
        sys.exit(1)
