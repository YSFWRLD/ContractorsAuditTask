"""Command-line entry point. Knows about the domain registry, never about a domain's internals."""

import argparse
import sys

from contractor_audit.domains import REGISTRY, get_domain
from contractor_audit.shared import paths, submission
from contractor_audit.shared.domain import RunContext


def _check_sources(names: list[str]) -> int:
    data_root = paths.task_data_root()
    print(f"task data root: {data_root}")
    missing = 0
    for name in names:
        for path in get_domain(name).required_sources(data_root):
            ok = path.exists()
            missing += not ok
            print(f"  [{name}] {'ok     ' if ok else 'MISSING'} {path}")
    return 1 if missing else 0


def _build_artifacts(name: str) -> int:
    ctx = RunContext.for_domain(name)
    try:
        written = get_domain(name).build_artifacts(ctx)
    except NotImplementedError as exc:
        print(f"{name}: {exc}", file=sys.stderr)
        return 2
    for path in written:
        print(f"  wrote {path}")
    return 0


def _run(name: str) -> int:
    ctx = RunContext.for_domain(name)
    try:
        results = get_domain(name).run(ctx)
    except NotImplementedError as exc:
        print(f"{name}: {exc}", file=sys.stderr)
        return 2
    print(f"{name}: {len(results)} invoices audited")
    return 0


def _submission() -> int:
    """Join every domain's frozen draft predictions onto the upstream template; write the root submission.csv."""
    sources = [submission.Source(name, paths.outputs_dir(name) / "draft_predictions.csv") for name in sorted(REGISTRY)]
    try:
        rows = submission.write(paths.template_path(), sources, paths.submission_path())
    except submission.SubmissionError as exc:
        print(f"submission not written: {exc}", file=sys.stderr)
        return 1
    flagged = sum(r["flagged"] == "1" for r in rows)
    print(f"wrote {paths.submission_path()}: {len(rows)} rows, {flagged} flagged, "
          f"{sum(not r['expected_total_cents'] for r in rows)} blank expected totals")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contractor-audit")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("domains", help="list registered contract domains")
    check = sub.add_parser("check-sources", help="verify the raw task files are present")
    check.add_argument("--domain", choices=sorted(REGISTRY), help="default: all domains")
    build = sub.add_parser("build-artifacts", help="regenerate a domain's derived artifacts from raw data")
    build.add_argument("--domain", choices=sorted(REGISTRY), required=True)
    run = sub.add_parser("run", help="audit one domain")
    run.add_argument("--domain", choices=sorted(REGISTRY), required=True)
    sub.add_parser("submission", help="combine every domain's frozen draft predictions into the root submission.csv")
    args = parser.parse_args(argv)

    if args.command == "domains":
        print("\n".join(sorted(REGISTRY)))
        return 0
    if args.command == "check-sources":
        return _check_sources([args.domain] if args.domain else sorted(REGISTRY))
    if args.command == "build-artifacts":
        return _build_artifacts(args.domain)
    if args.command == "submission":
        return _submission()
    return _run(args.domain)


if __name__ == "__main__":
    raise SystemExit(main())
