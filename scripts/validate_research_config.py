#!/usr/bin/env python3
"""Validate a financial-research-optimizer JSON configuration."""
import argparse
import json
from pathlib import Path
try:
    from .config_utils import load_config
except ImportError:
    from config_utils import load_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    print(json.dumps({"valid": True, "config_path": config["_config_path"], "fingerprint": config["_config_fingerprint"], "universe": config["universe"], "cutoff": config["cutoff"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
