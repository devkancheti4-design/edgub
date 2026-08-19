"""THE PIPELINE. Memory, then the body's data, then inference. Search last.

    1  observe        read the interpreter, mechanically
    2  the LAW        decides which class of repair this fault is
    3  MEMORY         has this shape of fault been solved before? apply it
    4  the BODY       supplies examples of what the function must do
    5  INFERENCE      generalise the repair from those examples
    6  search         only if all of the above come up empty

Steps 3 to 5 involve no enumeration. Step 6 is the old path, kept because
some faults are genuinely a single token and searching for one is cheap -- but
it runs last, not first, and it is the reason this used to take minutes.
"""
import ast, os, time

from . import ACTS, decide, sit, observe_traceback
from . import discover as _d
from .harvest import examples as _examples
from .infer import infer, sentinel_for, synthesise
from .memory import Memory


def solve(repo, module, func, failing, pytest_args=(), mem=None, baseline=None):
    """Return (description, source, route, seconds) or (None, None, route, s)."""
    t0 = time.time()
    mem = mem or Memory()
    path = os.path.join(repo, module.replace(".", os.sep) + ".py")
    src = open(path).read()
    ex = _examples(repo, path, func, failing)
    got = infer(ex, func, module, src=src)
    from .infer import Refusal
    if isinstance(got, Refusal) or not got:
        why = str(got) if got else "no examples the body could supply"
        return None, None, why, time.time() - t0

    sig = Memory.signature({"E_ASSERT"}, "REPAIR_LIBRARY",
                           {"kind": got["kind"], "keyword": got["keyword"]})
    known = mem.get(sig)
    route = "memory" if known else "inference"

    sent = sentinel_for(src, func, got["keyword"])
    if sent is None:
        return None, None, "no sentinel for `%s`" % got["keyword"], time.time() - t0
    # The inference fixes the SHAPE; which statement carries it is the only
    # thing left, and a function has a handful of statements. This is a
    # determined set of a few dozen, not a search over thousands.
    cands = []
    for callee, kw in got["arms"]:
        for cand in synthesise(src, func, got["keyword"], sent, callee, kw):
            cands.append((cand, "%s(..., %s=%s)" % (callee, kw, got["keyword"])))
    return ({"branch_on": got["keyword"], "sentinel": sent,
             "evidence": got["evidence"], "arms": len(got["arms"])},
            cands, route, time.time() - t0)
