"""Self-test: runs anywhere, needs nothing but the standard library.

Proves the shipped law routes eleven real failures correctly, by RUNNING each
broken program, reading its traceback, asking the law, applying the repair and
running again.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "..")))
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import edgub

CASES = [
 ("def f(n):\n    return n * FACTOR\nprint(f(3))", "0"),
 ("def f(p):\n    return os.path.basename(p)\nprint(f('/a/b'))", "b"),
 ("def f(n):\n    return n + '2'\nprint(f(5))", "7"),
 ("L = [1,2]\ndef f(i):\n    return L[i]\nprint(f(9))", "2"),
 ("def f(n):\n    return 9 // (n - n)\nprint(f(4))", "9"),
 ("class P:\n    pass\ndef f():\n    return P().size\nprint(f())", "0"),
 ("def f(s):\n    return int(s)\nprint(f('9kg'))", "9"),
 ("def f(n):\n    return n + 1\nassert f(1) == 5\nprint(f(1))", "2"),
 ("def g(x):\n    return int(str(x) + 'z')\nprint(g(4))", "4"),
 ("R=[1,2,3]\ndef f(k):\n    return [r for r in R][k]\nprint(f(8))", "3"),
 ("def outer():\n    def inner():\n        return LIMIT\n    return inner()\nprint(outer())", "0"),
]

if __name__ == "__main__":
    ok = 0
    for src, expect in CASES:
        obs = edgub.observe(src, expect)
        act = edgub.ACTS[edgub.decide(edgub.sit(obs))]
        rc, out, err = edgub.run(src)
        fixed = edgub.repair(act, src, err)
        good = "PASSES" in edgub.observe(fixed, expect)
        ok += good
        print("  %-34s %-17s %s" % ("+".join(sorted(obs))[:34], act,
                                    "repaired" if good else "NOT repaired"))
    print("\n  %d/%d repaired by the authored law" % (ok, len(CASES)))
    raise SystemExit(0 if ok == len(CASES) else 1)
