"""EVIDENCE ONLY.

This script was run against the private authoring engine to produce the
.log file beside it, which is the measurement being reported. The engine
is not part of this repository, so the script will not run here. It ships
so the method can be read and checked, not re-executed.
"""
"""HOW FAR DOES IT ACTUALLY REACH? — an adversarial capability test.

Two groups, and the second is designed to defeat it:

  IN SCOPE   different domains (strings, dicts, classes, generators, paths),
             same underlying fault families. If the claim "generalises" is
             real these should be repaired despite never being seen.

  OUT OF SCOPE  faults whose repair is NOT in the act set: a wrong operator,
             an off-by-one, a missing return, a mutable default. No amount of
             re-authoring can invent an act, so these should FAIL -- and if
             they silently "pass" something is wrong with the test.
"""
import sys


def s32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v



def _ENGINE_UNAVAILABLE(*a, **k):
    raise SystemExit('the authoring engine is private and not shipped here; '
                     'see the .log beside this file for the measurement')
, json, time
sys.path.insert(0, "."); sys.path.insert(0, "")
import edgub as A

TRAIN = {
 "name":   ("def f(n):\n    return n * SCALE\nprint(f(3))", "0"),
 "module": ("def f(n):\n    return math.floor(n / 2)\nprint(f(7))", "3"),
 "type":   ("def f(n):\n    return n + '1'\nprint(f(4))", "5"),
 "index":  ("D = [1, 2, 3]\ndef f(n):\n    return D[n]\nprint(f(7))", "3"),
 "zero":   ("def f(n):\n    return 12 // (n - 3)\nprint(f(3))", "12"),
 "attr":   ("class C:\n    pass\ndef f():\n    return C().value\nprint(f())", "0"),
 "value":  ("def f(s):\n    return int(s)\nprint(f('12a'))", "12"),
 "assert": ("def f(n):\n    return n * 2\nassert f(3) == 7\nprint(f(3))", "6"),
}
IN_SCOPE = {
 "strings":   ("def initials(name):\n    return name[0] + name.split()[1][0]\n"
               "print(initials('ada'))", "a"),
 "dicts":     ("AGES = {'a': 1}\ndef get(k):\n    return AGES[k]\nprint(get('z'))", "1"),
 "class-deep":("class Base:\n    pass\nclass Kid(Base):\n    pass\n"
               "def g():\n    return Kid().count\nprint(g())", "0"),
 "generator": ("def firsts(rows):\n    return [r[2] for r in rows]\n"
               "print(firsts([[1,2],[3,4]]))", "[2, 4]"),
 "paths":     ("def base(p):\n    return os.path.basename(p)\nprint(base('/a/b.txt'))", "b.txt"),
 "ratio":     ("def pct(a, b):\n    return 100 * a // b\nprint(pct(5, 0))", "500"),
 "parsing":   ("def size(s):\n    return int(s) * 2\nprint(size('7mb'))", "14"),
 "config":    ("def port():\n    return DEFAULT_PORT\nprint(port())", "0"),
}
OUT_OF_SCOPE = {
 "wrong-op":       ("def f(a, b):\n    return a - b\nprint(f(6, 2))", "8"),
 "off-by-one":     ("def total(n):\n    return sum(range(n))\nprint(total(4))", "10"),
 "missing-return": ("def double(n):\n    n * 2\nprint(double(3))", "6"),
 "mutable-default":("def add(x, acc=[]):\n    acc.append(x)\n    return len(acc)\n"
                    "add(1)\nprint(add(2))", "1"),
 "wrong-compare":  ("def big(n):\n    return 'yes' if n < 10 else 'no'\nprint(big(50))", "yes"),
 "swapped-args":   ("def div(a, b):\n    return b // a\nprint(div(2, 10))", "0"),
}

def measure(src, exp):
    for i, a in enumerate(A.ACTS):
        if a in ("SHIP", "AUTHOR_SUCCESSOR"): continue
        rc, out, err = A.run(src)
        if "PASSES" in A.observe(A.repair(a, src, err), exp): return i
    return None

ev = []
for n, (s, e) in TRAIN.items():
    a = measure(s, e)
    if a is not None: ev.append((A.sit(A.observe(s, e)), a))
ev.append((A.sit({"PASSES"}), 0)); ev = sorted(set(ev))

def _ntz(v, m):
    b = s32(v) & m; b &= -b
    return ((b.bit_length()-1) if b else 0) & 15
def _T(inner):
    b="((%s) & (0 - (%s)))"%(inner,inner); v="((%s) - 1)"%b
    v="((%s) - (((%s) >> 1) & 1431655765))"%(v,v)
    v="(((%s) & 858993459) + (((%s) >> 2) & 858993459))"%(v,v)
    v="((((%s) + ((%s) >> 4)) & 252645135))"%(v,v)
    return "(((((%s) * 16843009)) >> 24) & 15)"%v
_OPS.setdefault("ntz_err",(1,_T("(({a}) & 510)"),lambda a,_b:_ntz(a,510)))
_OPS.setdefault("modfield",(1,"(((({a}) >> 13) & 1) << 3)",lambda a,_b:((s32(a)>>13)&1)<<3))
r=None
for size in (1,2,3):
    r = _ENGINE_UNAVAILABLE(ev,intent="mask",max_size=size,consts=(0,1,8),
                        extra_ops=("ntz_err","modfield"))
    if r.found: break
print("law authored: size %s  %s\n" % (r.size, r.note), flush=True)
c=compile(r.expr,"<l>","eval"); law=lambda x: s32(eval(c,{"__builtins__":{}},{"x":x}))%11

def attempt(src, exp, rounds=3):
    for _ in range(rounds):
        rc,out,err = A.run(src)
        obs = A.observe(src, exp)
        if "PASSES" in obs: return True, "-"
        act = A.ACTS[law(A.sit(obs))]
        nxt = A.repair(act, src, err)
        if nxt == src: return False, act + " (no-op)"
        src = nxt
    return "PASSES" in A.observe(src, exp), act

for title, group in (("IN SCOPE — new domains, familiar fault families", IN_SCOPE),
                     ("OUT OF SCOPE — repair not in the act set", OUT_OF_SCOPE)):
    print(title, flush=True)
    ok = 0
    for n, (s, e) in group.items():
        fixed, act = attempt(s, e)
        ok += bool(fixed)
        print("   %-16s %-28s %s" % (n, act, "REPAIRED" if fixed else "not repaired"), flush=True)
    print("   -> %d/%d\n" % (ok, len(group)), flush=True)
