"""edgub <repo> -- repair what the repository's own tests determine."""
import sys, argparse
from .repair import repair as _fix


def main():
    ap = argparse.ArgumentParser(prog="edgub",
        description="Repair a repository from its own failing tests. No model, "
                    "no key, no network.")
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--package", default=None, help="importable package name")
    ap.add_argument("--dry-run", action="store_true", help="do not write repairs")
    ap.add_argument("--max-candidates", type=int, default=40000)
    ap.add_argument("--prompts", action="store_true",
                    help="print the ready-to-send prompt for each unrepaired fault")
    a = ap.parse_args()
    from .discover import EnvironmentProblem
    try:
        rep = _fix(a.repo, package=a.package, apply=not a.dry_run,
                   max_candidates=a.max_candidates)
    except EnvironmentProblem as e:
        print("edgub: cannot run.\n  %s" % e, file=sys.stderr)
        return 2
    print(rep)
    if a.prompts:
        for u in rep.unrepaired:
            print("\n" + "=" * 70)
            print(u.prompt)
    return 0 if not rep.unrepaired else 1


if __name__ == "__main__":
    sys.exit(main())
