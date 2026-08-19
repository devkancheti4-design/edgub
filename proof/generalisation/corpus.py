"""A CORPUS NEITHER SIDE CAN HAVE MEMORISED.

WHY NOT toolz. toolz and more-itertools are famous public repositories. A
frontier model repairing `nth` is recalling `nth`, not generalising. That
measures memory, and the claim under test is about generalisation.

So: functions composed at random, with opaque names, no docstrings, no
provenance. One random single-edit mutation each, from the same generic edit
classes the law's search uses -- so neither side is handed an easier space.

WHAT EACH SIDE GETS, IDENTICALLY
    the broken source
    6 (input, correct output) examples

WHAT NEITHER SIDE GETS
    the original source, the name of the mutation, the held-out inputs

JUDGED on 20 held-out inputs. Matching the 6 examples is not the score --
generalising to the 20 is.
"""
import random, ast, json, sys, itertools

R = random.Random(20260819)
NAMES = ["q", "w", "e", "r", "t", "y", "u", "p", "a", "s", "d", "g", "h", "j"]

BODIES = [
 "    {v} = x * {a} + {b}\n    if {v} > {c}:\n        {v} = {v} - {c}\n    return {v}",
 "    {v} = 0\n    for i in range({a}):\n        {v} = {v} + x % ({b} + i)\n    return {v}",
 "    {v} = x\n    while {v} > {c}:\n        {v} = {v} // {a}\n    return {v} + {b}",
 "    {v} = [x % {a}, x // {b}, x + {c}]\n    return sum({v}) - {a}",
 "    if x % {a} == 0:\n        return x // {a} + {b}\n    return x * {b} - {c}",
 "    {v} = abs(x - {c})\n    return {v} * {a} if {v} < {b} else {v} + {a}",
 "    {v} = 1\n    for i in range(1, {a}):\n        {v} = ({v} * x + i) % {c}\n    return {v}",
 "    {v} = [i for i in range({a}) if (x + i) % {b} == 0]\n    return len({v}) * {a} + x % {b}",
 "    {v} = x\n    for i in range({a}):\n        {v} = {v} + i * {b}\n    return {v} % {c}",
 "    {v} = min(x, {c})\n    {v} = {v} + max(x - {c}, {b})\n    return {v} * {a}",
]

def gen(i):
    body = BODIES[i % len(BODIES)]
    src = "def f(x):\n" + body.format(v=R.choice(NAMES) + str(R.randint(1, 9)),
                                     a=R.randint(2, 7), b=R.randint(1, 9),
                                     c=R.randint(5, 40))
    return src

def call(src, xs):
    ns = {}
    try:
        exec(src, ns)
    except Exception:
        return None
    out = []
    for x in xs:
        try:
            v = ns["f"](x)
        except Exception:
            v = "ERR"
        out.append(v)
    return out

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import harvest

def mutate(src):
    tree = ast.parse(src)
    fn = tree.body[0]
    ms = harvest.mutants(fn)
    R.shuffle(ms)
    return [(name, "def " + ast.unparse(m).split("def ", 1)[1]) for name, m in ms]

EX  = [0, 3, 7, 12, 25, 41]
HOLD = [1, 2, 4, 5, 6, 8, 9, 10, 11, 13, 15, 17, 19, 21, 23, 28, 33, 37, 44, 50]

if __name__ == "__main__":
    items, i = [], 0
    while len(items) < 20 and i < 400:
        i += 1
        good = gen(i)
        gv = call(good, EX + HOLD)
        if gv is None or "ERR" in gv or len(set(gv)) < 3:
            continue
        for name, bad in mutate(good):
            bv = call(bad, EX + HOLD)
            if bv is None or "ERR" in bv:
                continue
            if bv == gv:                      # a mutation that changes nothing
                continue
            nex = sum(1 for a, b in zip(gv[:len(EX)], bv[:len(EX)]) if a != b)
            if nex == 0:                      # must be visible in the DATA given
                continue
            items.append({"id": "P%02d" % len(items), "broken": bad,
                          "mutation": name,
                          "examples": list(zip(EX, gv[:len(EX)])),
                          "hold_in": HOLD, "hold_out": gv[len(EX):],
                          "_good": good})
            break
    json.dump(items, open(sys.argv[1], "w"), indent=1)
    print("%d novel programs" % len(items))
    print("examples per program: %d   held-out inputs: %d" % (len(EX), len(HOLD)))
    print("\nsample (P00), as BOTH sides will see it:\n")
    print(items[0]["broken"])
    print("\nexamples: %s" % items[0]["examples"])
