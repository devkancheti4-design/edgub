"""EVIDENCE ONLY — this script calls the private authoring engine
and therefore cannot run outside it. Its output is the .log file
beside it, which is the measurement being reported.
"""
"""THE DEBUGGER GAINS AN ACT THAT CREATES: REAUTHOR_BODY.

Selecting a repair cannot fix a wrong operator -- there is no menu entry for
it. But a repo has TESTS, and tests are examples. So when the program runs
clean and prints the wrong thing, the debugger can stop repairing and instead
AUTHOR A NEW BODY from the examples, then install it.

That act belongs to the debugger, and the law decides when to use it.
"""
import ast, sys, re, os, json, subprocess, tempfile, time
sys.path.insert(0, "."); sys.path.insert(0, "")
import edgub as A

for k in (1,2,3,4,5,16):
    _OPS.setdefault(">>%d"%k,(1,"({a} >> %d)"%k,lambda a,_b,k=k: s32(s32(a)>>k)))
CONSTS = tuple(range(0,17))+(31,63,255,65535)

# the DATA a repo supplies: a function name and example pairs from its tests
CASES = {
 "wrong-op":      ("def f(a, b):\n    return a - b\nprint(f(6, 2))", "8",
                   "f", [((6,2),8), ((1,1),2), ((5,3),8), ((0,4),4), ((7,2),9)]),
 "off-by-one":    ("def total(n):\n    return sum(range(n))\nprint(total(4))", "10",
                   "total", [((4,),10), ((1,),1), ((2,),3), ((3,),6), ((5,),15)]),
 "missing-return":("def double(n):\n    n * 2\nprint(double(3))", "6",
                   "double", [((3,),6), ((0,),0), ((1,),2), ((5,),10), ((7,),14)]),
 "swapped-args":  ("def div(a, b):\n    return b // a\nprint(div(2, 10))", "0",
                   "div", [((2,10),0), ((10,2),5), ((9,3),3), ((8,4),2), ((6,6),1)]),
 "wrong-compare": ("def big(n):\n    return 'yes' if n < 10 else 'no'\nprint(big(50))", "yes",
                   "big", None),          # returns strings -- not an int function
 "mutable-default":("def add(x, acc=[]):\n    acc.append(x)\n    return len(acc)\n"
                    "add(1)\nprint(add(2))", "1", "add", None),   # stateful
}

pack1 = lambda t: t[0]
pack2 = lambda t: (t[0] & 0xFFFF) | ((t[1] & 0xFFFF) << 16)


def reauthor_body(src, fname, examples):
    """THE CREATING ACT. Author a body from the examples and install it."""
    if not examples:
        return src, "no examples -- cannot author"
    arity = len(examples[0][0])
    # the authored expression is written in terms of x; the function's own
    # parameters have other names. Bind them, or the installed body raises
    # NameError -- which is what happened before this line existed.
    tree0 = ast.parse(src)
    params = []
    for nd in tree0.body:
        if isinstance(nd, ast.FunctionDef) and nd.name == fname:
            params = [a.arg for a in nd.args.args]
    if arity == 1:
        rows = [(pack1(a), y) for a, y in examples]
        head = params[0] if params else "x"
    elif arity == 2:
        rows = [(pack2(a), y) for a, y in examples]
        head = "((%s) & 65535) | (((%s) & 65535) << 16)" % (params[0], params[1])
    else:
        return src, "arity %d unsupported" % arity
    r = None
    for size in (1, 2, 3):
    r = _ENGINE_UNAVAILABLE(sorted(set(rows)), intent="any", max_size=size,
                              consts=CONSTS, extra_ops=tuple(">>%d"%k for k in (1,2,3,4,16)))
        if r.found:
            break
    if not r.found:
        return src, "engine abstained: %s" % r.note
    body = re.sub(r"\bx\b", "(%s)" % head, r.expr)
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == fname:
            node.body = [ast.Return(value=ast.parse(body, mode="eval").body)]
    ast.fix_missing_locations(tree)
    return ast.unparse(tree), "authored: %s" % r.expr[:46]


if __name__ == "__main__":
    print("REAUTHOR_BODY — the debugger creates a body from the repo's tests\n")
    print("%-17s %-9s %-46s %s" % ("case", "result", "what the engine did", "output"))
    ok = 0
    for name, (src, expect, fname, ex) in CASES.items():
        t = time.time()
        new, why = reauthor_body(src, fname, ex)
        rc, out, err = A.run(new)
        good = (out == expect)
        ok += good
        print("%-17s %-9s %-46s %s"
              % (name, "FIXED" if good else "no", why[:46], out or err.split(":")[0][:18]),
              flush=True)
    print("\n  %d/6 repaired by AUTHORING A NEW BODY from the tests" % ok)
    print("  (the other cases: one returns strings, one is stateful --")
    print("   neither is an int->int function, so the engine cannot express it)")
