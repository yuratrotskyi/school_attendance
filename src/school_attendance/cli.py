"""CLI entrypoint for school attendance app."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="school-attendance")
    parser.add_argument("--version", action="store_true", help="Show version")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print("school-attendance 0.1.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
