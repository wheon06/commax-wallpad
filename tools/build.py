#!/usr/bin/env python3
"""Build allowlisted source and HACS artifacts without runtime settings or captures."""

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "commax_wallpad"
ROOT_FILES = {
    "README.md",
    "README.en.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "hacs.json",
    "pyproject.toml",
    "requirements-dev.txt",
    ".gitignore",
}
FOLDERS = {"custom_components", "tools", "tests", "docs", "examples", ".github"}
EXTENSIONS = {".py", ".json", ".md", ".txt", ".toml", ".yaml", ".yml", ".svg", ".png"}


def public_files():
    for file in sorted(ROOT.rglob("*")):
        rel = file.relative_to(ROOT)
        if not file.is_file() or file.is_symlink():
            continue
        if file.name.startswith("commax_connection") or file.suffix in {".pcap", ".pcapng", ".log"}:
            continue
        if any(part.startswith(".") for part in rel.parts[1:-1]):
            continue
        if "__pycache__" in rel.parts:
            continue
        if len(rel.parts) == 1:
            if file.name in ROOT_FILES:
                yield file
        elif rel.parts[0] in FOLDERS and file.suffix in EXTENSIONS:
            yield file


def main():
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    if "OWNER" in json.dumps(manifest) or not manifest["codeowners"]:
        raise SystemExit("Set repository metadata before building a public release")
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    artifacts = [
        destination / "commax_wallpad.zip",
        destination / f"commax-wallpad-{manifest['version']}-source.zip",
    ]
    with zipfile.ZipFile(artifacts[0], "w", zipfile.ZIP_DEFLATED) as archive:
        for file in public_files():
            if file.is_relative_to(INTEGRATION):
                archive.write(file, file.relative_to(INTEGRATION))
    with zipfile.ZipFile(artifacts[1], "w", zipfile.ZIP_DEFLATED) as archive:
        for file in public_files():
            archive.write(file, Path("commax-wallpad") / file.relative_to(ROOT))
    checksums = destination / "SHA256SUMS"
    checksums.write_text(
        "".join(
            f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.name}\n" for file in artifacts
        )
    )
    for file in artifacts:
        print(file.name)


if __name__ == "__main__":
    main()
