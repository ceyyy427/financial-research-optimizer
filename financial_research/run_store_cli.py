#!/usr/bin/env python3
"""Operate the v1 SQLite run store without exposing database internals."""
import argparse
import json
from .sqlite_run_store import SqliteRunStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("migrate", "doctor", "backup", "restore"))
    parser.add_argument("--root", default="artifacts/runs")
    parser.add_argument("--path")
    args = parser.parse_args()
    store = SqliteRunStore(args.root)
    if args.command == "migrate": result = store.migrate()
    elif args.command == "doctor": result = store.doctor()
    elif not args.path: parser.error("--path is required for backup/restore")
    elif args.command == "backup": result = store.backup(args.path)
    else: result = store.restore(args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
