#!/usr/bin/env python3
"""Validate experiment_manifest.json and print its reproducibility status."""
import argparse
import json
from pathlib import Path
from manifest_utils import load_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    print(json.dumps({"valid": True, "experiment_id": manifest["experiment_id"], "reproducibility_status": manifest["reproducibility_status"], "fingerprint": manifest["_manifest_fingerprint"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
