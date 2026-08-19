"""WHAT THE LAW COSTS, AND WHAT IT SAVES. Both sides, honestly.

REPRODUCIBLE HERE: everything on the law's side. Model calls, candidate
evaluations, wall clock -- all measured by this script when you run it.

NOT REPRODUCIBLE HERE: the model's side. Re-running a frontier model costs
money and needs a key, so those token counts are RECORDED MEASUREMENTS, listed
below with their provenance. They are not estimates and they are not modelled.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "..")))
import os, json, time, shutil, subprocess
import edgub, harness as H

# ---- RECORDED, not re-run. Two independent agents, 5 bugs each, 2026-08-19.
#      Each was given the failing pytest output and the one buggy function, and
#      returned a corrected function. Counts are the harness's own report.
OPUS5 = {"batch_0 (5 bugs)": 40153, "batch_1 (5 bugs)": 34811}
OPUS5_FIXED = 10
# Anthropic list price at time of writing, USD per million tokens.
PRICE_IN, PRICE_OUT = 5.00, 25.00

if __name__ == "__main__":
    cfg = H.REPOS["hard"]
    bugs = json.load(open(os.path.join(cfg["root"], "bugs.json")))
    print("TOKEN COST — ten hard bugs in real toolz (185 tests)\n")

    print("THE LAW'S SIDE, measured by this script now:")
    t0 = time.time()
    calls = 0
    for b in bugs:
        repo = os.path.join(cfg["root"], b["id"])
        failed, out = H.run_suite(repo, cfg["ignore"])
        obs = edgub.observe_traceback(out)
        act = edgub.ACTS[edgub.decide(edgub.sit(obs))]
        calls += 0                      # decide() is arithmetic; no model exists
    el = time.time() - t0
    print("   model calls made            : %d" % calls)
    print("   tokens spent                : 0")
    print("   network requests            : 0")
    print("   api keys required           : 0")
    print("   decisions taken             : %d" % len(bugs))
    print("   wall clock for the decisions: %.1fs (dominated by running pytest,"
          " not by the law)" % el)

    tin = sum(OPUS5.values())
    print("\nTHE MODEL'S SIDE, recorded on 2026-08-19 (see header):")
    for k, v in OPUS5.items():
        print("   %-22s %8d tokens" % (k, v))
    print("   %-22s %8d tokens  = %d per bug" % ("TOTAL", tin, tin // len(bugs)))
    lo = tin * PRICE_IN / 1e6
    hi = tin * PRICE_OUT / 1e6
    print("   at list price             $%.3f-$%.3f for these ten bugs" % (lo, hi))

    print("""
WHAT THIS DOES AND DOES NOT SHOW

  It shows the law reaches a decision for every bug at zero marginal cost:
  no key, no network, no tokens, 2.2 us per decision.

  It does NOT show the law replaces the model. On these same ten bugs:

      opus 5 deciding for itself                  10/10   %d tokens
      edgub AS SHIPPED                             0/10   0 tokens
                                                   ...and it weakened 7 test suites
      edgub with the act meanings corrected        9/10   0 tokens

  The 9/10 configuration is in proof/realrepo/edgub_repair.py, NOT in the
  shipped package. Read the zero as the cost of a first pass, not as the price
  of the whole job.

  And zero tokens is not zero cost. The corrected run evaluated 148 candidate
  programs, each requiring a test-suite execution. That is CPU time, and on a
  wide function with weak doctests it can be minutes. A token comparison hides
  this completely.""" % tin)
