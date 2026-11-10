#!/usr/bin/env python3
"""Remove only the known COMMAX WAN Test YAML entry; dry-run unless --apply."""

import argparse
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def remove_test_bridge(text):
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if re.match(r"^homekit\s*:", line)]
    if not starts:
        return text, False
    if len(starts) != 1 or not re.fullmatch(r"homekit\s*:\s*(?:#.*)?\n?", lines[starts[0]]):
        raise ValueError("Non-inline HomeKit configuration; inspect manually")
    start = starts[0]
    end = next(
        (i for i in range(start + 1, len(lines)) if re.match(r"^[^\s#][^:]*:", lines[i])),
        len(lines),
    )
    items = [i for i in range(start + 1, end) if re.match(r"^  -\s", lines[i])]
    if not items:
        raise ValueError("Expected a HomeKit bridge list; inspect manually")
    removed = set()
    for n, index in enumerate(items):
        stop = items[n + 1] if n + 1 < len(items) else end
        block = "".join(lines[index:stop])
        name = re.search(r"(?m)^\s*(?:-\s*)?name:\s*['\"]?COMMAX WAN Test['\"]?\s*$", block)
        port = re.search(r"(?m)^\s+port:\s*21065\s*$", block)
        if name and port:
            removed.update(range(index, stop))
    if not removed:
        return text, False
    # Only remove the parent key when all of its bridge entries were removed.
    if all(index in removed for index in items):
        removed.add(start)
    return "".join(line for i, line in enumerate(lines) if i not in removed), True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    path = args.config_dir / "configuration.yaml"
    try:
        text = path.read_text()
        updated, changed = remove_test_bridge(text)
        if not changed:
            print("No matching COMMAX WAN Test on port 21065. No changes made.")
            return
        if not args.apply:
            print("Would remove COMMAX WAN Test on port 21065 only. Run with --apply to save.")
            return
        backup_dir = args.config_dir / "commax_backups"
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        shutil.copy2(path, backup_dir / f"configuration-{stamp}.yaml")
        temporary = path.with_suffix(".yaml.commax-tmp")
        with temporary.open("x") as file:
            file.write(updated)
        shutil.copystat(path, temporary)
        temporary.replace(path)
        print(
            "Removed test YAML and backed up configuration. Restart HA, then remove the test bridge in the HA and Apple Home UIs."
        )
    except (OSError, ValueError):
        parser.exit(
            1, "Could not safely edit this configuration. No settings content was printed.\n"
        )


if __name__ == "__main__":
    main()
