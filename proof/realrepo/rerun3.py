"""THE THREE MISSES, RERUN. edgub.decide() is untouched. Only my supply changed:
act 2 may now reach `name`, `cmp`, `attr`; and my 4,001 candidate cap is gone.

If they resolve, the attribution is settled by measurement: they were mine.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "..", "..")))
import sys, os, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edgub_repair as R
import harness as F, edgub

cfg = F.REPOS["hard"]
work = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work_rerun3")
if os.path.exists(work):
    shutil.rmtree(work)
os.makedirs(work)
print("RERUN OF THE THREE MISSES — law untouched, only my supply changed\n")
print("%-20s %-14s %-6s %-28s %s" % ("bug", "observation", "act#", "authored", "tried"))
ok = 0
import sys as _s
for bid in (_s.argv[1:] or ["unique_wrongvar", "get_default_inv", "diff_nodefault"]):
    repo = os.path.join(work, bid)
    if os.path.exists(repo):
        shutil.rmtree(repo)
    shutil.copytree(os.path.join(cfg["root"], bid), repo,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    failed, out = F.run_suite(repo, cfg["ignore"])
    obs = R.observe(out)
    idx = edgub.decide(edgub.sit(obs))          # UNCHANGED
    classes, tier = R.ACT_CLASSES.get(idx, (R.SEMANTIC, 3))
    tg = F.targets(repo, out, cfg)
    red = F.failing_nodes(out)
    label, tried = None, 0
    for mod, func in tg[:2]:
        label, tried = R.search(repo, mod, func, classes, tier, cfg, red)
        if label:
            break
    ok += bool(label)
    print("%-20s %-14s %-6d %-28s %d" % (bid, "+".join(sorted(obs))[:14], idx,
          label or "-- none --", tried), flush=True)
print("\n  three misses, my supply corrected: %d/3" % ok)
print("  (unique_wrongvar already resolved separately: unwrap call, 13 tried)")
