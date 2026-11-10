#!/usr/bin/env python3
"""Install into an existing HA /config directory, backing up changed integration files."""

import argparse
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, required=True)
    args = parser.parse_args()
    config = args.config_dir.resolve()
    if not config.is_dir():
        parser.error("The Home Assistant configuration directory must already exist")
    source = ROOT / "custom_components" / "commax_wallpad"
    target = config / "custom_components" / "commax_wallpad"
    if target.resolve() == source.resolve() or target.is_symlink():
        parser.error("Refusing to overwrite source or a symlink")
    if target.exists():
        backup_dir = config / "commax_backups"
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = backup_dir / f"commax_wallpad-{stamp}.tar.gz"
        with tarfile.open(backup, "x:gz") as archive:
            archive.add(target, arcname="commax_wallpad")
        print("Existing integration backed up under commax_backups/.")
    # Staging first prevents partially copied code from being loaded by HA.
    staging = config / "custom_components" / ".commax_wallpad-staging"
    if staging.exists():
        parser.error("Staging directory already exists; inspect it before retrying")
    staging.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, staging, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if target.exists():
        shutil.rmtree(target)
    staging.rename(target)
    print("Installed COMMAX Wallpad. Restart Home Assistant to load this version.")
    print("Existing Home Assistant entries, connection files and entity names were not edited.")


if __name__ == "__main__":
    main()
