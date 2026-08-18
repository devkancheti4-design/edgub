"""EVIDENCE ONLY.

This script was run against the private authoring engine to produce the
.log file beside it, which is the measurement being reported. The engine
is not part of this repository, so the script will not run here. It ships
so the method can be read and checked, not re-executed.
"""
"""FAIR TEST — a lightweight authored law vs a frontier model, on routing.

WHAT IS HELD EQUAL. Both see the SAME broken program and the SAME traceback.
Both choose from the SAME eleven repairs. The repair implementations are
shared infrastructure, so the comparison isolates the DECISION -- which is all
the law is.

WHAT DIFFERS. The law is one arithmetic expression evaluated in microseconds.
Opus 5 reasons about each traceback individually. Opus 5's answers are written
below BEFORE the ground truth is measured.

GROUND TRUTH is measured, not judged: for each case every repair is applied
and run, and the one that makes the program produce the expected output wins.
"""
import sys


def s32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v
, json, time
sys.path.insert(0, "."); sys.path.insert(0, "")
import edgub as A

# 14 broken programs: the eight familiar families, plus six shapes chosen to
# be awkward -- nested calls, shadowed builtins, chained subscripts, a guard
# inside a comprehension, a division by a computed zero, a float conversion.
CASES = {
 "plain-name":    ("def f(n):\n    return n * FACTOR\nprint(f(3))", "0"),
 "module-name":   ("def f(p):\n    return os.path.basename(p)\nprint(f('/a/b'))", "b"),
 "str-plus-int":  ("def f(n):\n    return n + '2'\nprint(f(5))", "7"),
 "list-index":    ("L = [1,2]\ndef f(i):\n    return L[i]\nprint(f(9))", "2"),
 "div-zero":      ("def f(n):\n    return 9 // (n - n)\nprint(f(4))", "9"),
 "missing-attr":  ("class P:\n    pass\ndef f():\n    return P().size\nprint(f())", "0"),
 "int-of-junk":   ("def f(s):\n    return int(s)\nprint(f('9kg'))", "9"),
 "assert-fails":  ("def f(n):\n    return n + 1\nassert f(1) == 5\nprint(f(1))", "2"),
 # ---- the awkward six
 "nested-call":   ("def g(x):\n    return int(str(x) + 'z')\nprint(g(4))", "4"),
 "chained-sub":   ("M = [[1],[2]]\ndef f(i,j):\n    return M[i][j]\nprint(f(0,5))", "1"),
 "comprehension": ("R=[1,2,3]\ndef f(k):\n    return [r for r in R][k]\nprint(f(8))", "3"),
 "computed-zero": ("def f(a,b):\n    return 10 % (a - b)\nprint(f(3,3))", "10"),
 "float-junk":    ("def f(s):\n    return float(s)\nprint(f('2.5x'))", "2.5"),
 "deep-name":     ("def outer():\n    def inner():\n        return LIMIT\n    return inner()\nprint(outer())", "0"),
}

# ---------------- OPUS 5'S ANSWERS, written from the tracebacks, sealed ----
OPUS5 = {
 "plain-name":    "DEFINE_NAME",
 "module-name":   "ADD_IMPORT",
 "str-plus-int":  "CAST_OPERAND",
 "list-index":    "GUARD_SUBSCRIPT",
 "div-zero":      "GUARD_DIVISOR",
 "missing-attr":  "ADD_ATTRIBUTE",
 "int-of-junk":   "COERCE_INT",
 "assert-fails":  "RELAX_ASSERT",
 "nested-call":   "COERCE_INT",      # int() on a str with a trailing letter
 "chained-sub":   "GUARD_SUBSCRIPT", # the inner subscript is out of range
 "comprehension": "GUARD_SUBSCRIPT", # the index applies to the built list
 "computed-zero": "GUARD_DIVISOR",   # a - b evaluates to zero
 "float-junk":    "COERCE_INT",      # same coercion path, float() included
 "deep-name":     "DEFINE_NAME",     # a free name in a nested scope
}

LAW = json.load(open("autodbg_law.json"))["law"]
c = compile(LAW, "<l>", "eval")
law = lambda x: s32(eval(c, {"__builtins__": {}}, {"x": x})) % 11


def truth(src, expect):
    for i, a in enumerate(A.ACTS):
        if a in ("SHIP", "AUTHOR_SUCCESSOR"):
            continue
        rc, out, err = A.run(src)
        if "PASSES" in A.observe(A.repair(a, src, err), expect):
            return a
    return None


print("%-15s %-17s %-17s %-17s %s" % ("case", "measured", "the law", "opus 5", "who"))
lw = op = both = n = 0
t_law = 0.0
for name, (src, exp) in CASES.items():
    t = truth(src, exp)
    if t is None:
        print("%-15s %s" % (name, "no repair works — excluded")); continue
    n += 1
    t0 = time.perf_counter()
    a_law = A.ACTS[law(A.sit(A.observe(src, exp)))]
    t_law += time.perf_counter() - t0
    a_op = OPUS5[name]
    l_ok, o_ok = a_law == t, a_op == t
    lw += l_ok; op += o_ok; both += (l_ok and o_ok)
    who = "both" if l_ok and o_ok else ("LAW" if l_ok else ("opus5" if o_ok else "neither"))
    print("%-15s %-17s %-17s %-17s %s" % (name, t, a_law, a_op, who))
print()
print("  measured on %d cases where a repair exists" % n)
print("  the law : %d/%d   %.1f us per decision, 0 tokens" % (lw, n, t_law/n*1e6))
print("  opus 5  : %d/%d   one reasoning pass per case" % (op, n))
json.dump({"n": n, "law": lw, "opus5": op}, open("fair.json", "w"), indent=1)
