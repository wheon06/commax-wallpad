#!/usr/bin/env python3
"""Extract one proxy connection locally; never print the credential values."""

import argparse
import json
import os
from pathlib import Path

from _bootstrap import core


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, default=Path("commax_connection.json"))
    parser.add_argument(
        "--connection", type=int, help="Zero-based index for captures with multiple connections"
    )
    args = parser.parse_args()
    try:
        connections = core("capture").capture_connections(args.capture)
        if not connections:
            raise ValueError("No supported plaintext gSOAP proxy request found")
        if len(connections) != 1 and args.connection is None:
            raise ValueError(
                f"Found {len(connections)} connections; select one using --connection INDEX"
            )
        index = args.connection if args.connection is not None else 0
        if not 0 <= index < len(connections):
            raise ValueError("Invalid connection index")
        config = connections[index]
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            json.dump(config.as_dict(), handle, indent=2)
        print("Saved private connection file. No network requests were made.")
    except FileExistsError:
        parser.exit(1, "Output already exists; choose a new filename or back it up first.\n")
    except (OSError, ValueError, IndexError):
        parser.exit(
            1,
            "Extraction failed. Check file format and connection selection. No credentials printed.\n",
        )


if __name__ == "__main__":
    main()
