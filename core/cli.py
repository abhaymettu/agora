"""Command line front end.

    python -m core axioms
    python -m core derive --mode swf pareto iia nondictatorial
    python -m core derive --mode scf --voters 3 condorcet anonymous neutral
"""

from __future__ import annotations

import argparse
import json
import sys

from .solve import derive, library


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="core", description="AGORA derivation core")
    sub = parser.add_subparsers(dest="command", required=True)

    listing = sub.add_parser("axioms", help="list the axiom library")
    listing.add_argument("--mode", choices=("scf", "swf"), help="only axioms defined for this kind")

    run = sub.add_parser("derive", help="ask whether a rule exists")
    run.add_argument("axioms", nargs="+", help="axiom names")
    run.add_argument("--mode", choices=("scf", "swf"), default="scf")
    run.add_argument("--voters", type=int, default=2)
    run.add_argument("--candidates", type=int, default=3)
    run.add_argument("--timeout", type=float, default=60.0, help="seconds, default 60")
    run.add_argument("--json", action="store_true", help="machine-readable result")
    run.add_argument("--table", action="store_true", help="print the whole rule, not a preview")

    args = parser.parse_args(argv)

    if args.command == "axioms":
        width = max(len(n) for n in library())
        for name, ax in library().items():
            if args.mode and not ax.supports(args.mode):
                continue
            print(f"{name.ljust(width)}  [{'/'.join(ax.modes)}]  {ax.english}")
        return 0

    try:
        result = derive(
            args.axioms,
            args.voters,
            args.candidates,
            mode=args.mode,
            timeout=args.timeout,
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        print(result)
        if args.table and result.rule is not None:
            print()
            for profile, outcome in result.rule.rows():
                print(f"  {profile}  ->  {outcome}")
    return 0 if result.status != "unknown" else 1
