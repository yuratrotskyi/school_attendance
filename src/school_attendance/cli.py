"""CLI entrypoint for school attendance app."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Optional

from .config import load_config
from .pipeline import run_daily
from .session_bootstrap import bootstrap_session


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="school-attendance")
    parser.add_argument("--version", action="store_true", help="Show version")

    subparsers = parser.add_subparsers(dest="command")
    run_daily_parser = subparsers.add_parser("run-daily", help="Run daily attendance pipeline")
    run_daily_parser.add_argument("--run-date", default=datetime.now().date().isoformat(), help="Run date (YYYY-MM-DD)")
    run_daily_parser.add_argument("--dry-run", action="store_true", help="Use only local files")
    run_daily_parser.add_argument("--skip-collect", action="store_true", help="Skip nz.ua data collection")
    run_daily_parser.add_argument("--raw-file", action="append", default=[], help="Path to raw CSV export")
    run_daily_parser.add_argument("--class", action="append", default=[], dest="classes", help="Collect only specified class (repeatable)")
    run_daily_parser.add_argument("--env-file", default=".env", help="Path to .env file")

    bootstrap_parser = subparsers.add_parser(
        "bootstrap-session",
        help="Open browser for manual nz.ua login and save session",
    )
    bootstrap_parser.add_argument("--env-file", default=".env", help="Path to .env file")
    bootstrap_parser.add_argument("--timeout-seconds", type=int, default=300, help="Wait timeout for auth state")

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("school-attendance 0.1.0")
        return 0

    if args.command == "run-daily":
        config = load_config(Path(args.env_file))
        run_date = datetime.strptime(args.run_date, "%Y-%m-%d").date()

        result = run_daily(
            config=config,
            run_date=run_date,
            dry_run=args.dry_run,
            skip_collect=args.skip_collect,
            raw_files=[Path(p) for p in args.raw_file],
            include_classes=args.classes,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "bootstrap-session":
        config = load_config(Path(args.env_file))
        path = bootstrap_session(config=config, timeout_seconds=args.timeout_seconds)
        print(json.dumps({"session_state_path": str(path)}, ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
