"""LARGE MIXED CORPUS — free rate, token cost, DAMAGE, and open bugs.

A realistic repository is not all bugs. It is mostly working code, some
routine faults, a few that need judgement, and a residue nobody fixes. So the
corpus is mixed, and three things are measured that a bug-only test cannot
show:

  FREE      what fraction the law finishes with no model call at all
  DAMAGE    how often a config BREAKS a program that was already correct
  OPEN      what neither config solves

DAMAGE is the "smarter" question. A model asked to fix working code will often
change it. The law reads PASSES and returns SHIP. That is the only place a
router can beat a frontier body, and it is measurable.
"""
import json, os, random, re, subprocess, sys, tempfile, time
sys.path.insert(0, "."); sys.path.insert(0, "agent/vendor")
import edgub

PY = sys.executable
T = tempfile.mkdtemp()
rng = random.Random(818)
tok = lambda s: max(1, len(s) // 4)

def run(src):
    p = os.path.join(T, "p.py"); open(p, "w").write(src)
    try:
        r = subprocess.run([PY, p], capture_output=True, text=True, timeout=15)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception:
        return 1, "", "timeout"

FN = ["calc","total","score","value","amount","rate","size","count","depth","width"]
AR = ["n","x","k","v","i","m","q","t"]
CONST = ["SCALE","FACTOR","BASE_N","OFFSET","MAX_N","STEP_N"]
MOD = ["math","os","re","json","random","string"]
CLS = ["Box","Node","Item","Cell","Unit","Slot"]
FLD = ["size","value","count","depth","width","rank"]

def make():
    """Mixed: 40% already-correct, 45% routine faults, 15% needing judgement."""
    f, a = rng.choice(FN), rng.choice(AR)
    r = rng.random()
    if r < 0.40:                                   # ALREADY CORRECT
        shape = rng.choice(["fold","guard","pick","swap"])
        if shape == "fold":
            src = "def %s(%s, w):\n    return %s / w\ndef outer(items, d):\n" \
                  "    return [%s(d, i) for i in items]\nprint(outer([2,4], 8))" % (f,a,a,f)
        elif shape == "guard":
            L = [rng.randint(1,20) for _ in range(3)]
            src = "D=%r\ndef %s(%s):\n    return D[min(%s, len(D)-1)]\nprint(%s(%d))" % (
                L,f,a,a,f,rng.randint(4,9))
        elif shape == "pick":
            src = "def %s(%s):\n    return (%s or 1) * 2\nprint(%s(0))" % (f,a,a,f)
        else:
            src = "def %s(a, b):\n    return b - a\nprint(%s(2, 9))" % (f,f)
        rc, out, err = run(src)
        return src, out, "already-correct"
    if r < 0.85:                                   # ROUTINE FAULT
        k = rng.choice(["name","module","index","zero","attr","value"])
        if k == "name":
            return ("def %s(%s):\n    return %s * %s\nprint(%s(%d))"
                    % (f,a,a,rng.choice(CONST),f,rng.randint(2,9)), "0", "routine")
        if k == "module":
            m = rng.choice(MOD)
            call = {"math":"math.floor(%s/2)","os":"os.path.basename(str(%s))",
                    "re":"len(re.findall('a',str(%s)))","json":"len(json.dumps(%s))",
                    "random":"(random.seed(%s) or 1)","string":"len(string.digits)-%s*0"}[m] % a
            src = "def %s(%s):\n    return %s\nprint(%s(4))" % (f,a,call,f)
            return src, run("import %s\n%s" % (m,src))[1], "routine"
        if k == "index":
            L=[rng.randint(1,20) for _ in range(rng.randint(2,4))]
            return ("D=%r\ndef %s(%s):\n    return D[%s]\nprint(%s(%d))"
                    % (L,f,a,a,f,len(L)+rng.randint(1,6)), str(L[-1]), "routine")
        if k == "zero":
            c=rng.randint(2,9)
            return ("def %s(%s):\n    return %d // (%s - %d)\nprint(%s(%d))"
                    % (f,a,rng.randint(6,30),a,c,f,c), None, "routine")
        if k == "attr":
            return ("class %s:\n    pass\ndef %s():\n    return %s().%s\nprint(%s())"
                    % (rng.choice(CLS),f,CLS[0] if False else rng.choice(CLS),
                       rng.choice(FLD),f), "0", "routine")
        return ("def %s(s):\n    return int(s)\nprint(%s('%d%s'))"
                % (f,f,rng.randint(1,99),rng.choice(["kg","x","mb"])), None, "routine")
    k = rng.choice(["wrong-op","missing-return","off-by-one"])   # JUDGEMENT
    if k == "wrong-op":
        A,B = rng.randint(3,9), rng.randint(1,3)
        return ("def %s(a,b):\n    return a - b\nprint(%s(%d,%d))" % (f,f,A,B),
                str(A+B), "judgement")
    if k == "missing-return":
        v=rng.randint(2,6)
        return ("def %s(%s):\n    %s * 2\nprint(%s(%d))" % (f,a,a,f,v), str(v*2), "judgement")
    n=rng.randint(3,6)
    return ("def %s(%s):\n    return sum(range(%s))\nprint(%s(%d))" % (f,a,a,f,n),
            str(n*(n+1)//2), "judgement")

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
print("building a %d-program corpus (mixed: correct, routine, judgement)..." % N, flush=True)
corpus, t0 = [], time.time()
while len(corpus) < N:
    src, exp, cat = make()
    if exp is None:
        continue
    rc, out, err = run(src)
    broken = not (rc == 0 and out == exp)
    corpus.append((src, exp, cat, broken, err, out))
    if len(corpus) % 250 == 0:
        print("  %d (%.0fs)" % (len(corpus), time.time()-t0), flush=True)
nb = sum(1 for c in corpus if c[3])
print("corpus %d: %d broken, %d already correct  (%.0fs)\n"
      % (len(corpus), nb, len(corpus)-nb, time.time()-t0), flush=True)

SYS = "You are a debugging assistant. Return the corrected program.\n"
SYSN = "The class of fix is decided. Return only the corrected line.\n"
free = damage_law = 0
A_tok = B_tok = 0
law_fixed = 0
open_bugs = []
t1 = time.perf_counter()
for src, exp, cat, broken, err, out in corpus:
    # ---------- config A: every program goes to the model, broken or not
    A_tok += tok(SYS + src + (err or out)) + tok(src)
    # ---------- config B: the law looks first
    obs = set()
    for nm, bit in (("NameError","E_NAME"),("TypeError","E_TYPE"),("IndexError","E_INDEX"),
                    ("ZeroDivisionError","E_ZERO"),("AttributeError","E_ATTR"),
                    ("ValueError","E_VALUE"),("AssertionError","E_ASSERT")):
        if nm in err: obs.add(bit)
    m = re.search(r"name '(\w+)' is not defined", err)
    if m and m.group(1) in getattr(sys, "stdlib_module_names", ()): obs.add("N_MODULE")
    ln = None
    for mm in re.finditer(r'File "[^"]*", line (\d+)', err): ln = int(mm.group(1))
    if ln: obs |= edgub.line_syntax(src, ln)
    if not obs: obs.add("PASSES" if not broken else "OUT_WRONG")
    act = edgub.ACTS[edgub.decide(edgub.sit(obs))]
    if not broken:
        if act == "SHIP":
            free += 1                          # correct code, untouched, 0 tokens
        else:
            cand = edgub.repair(act, src, err)
            if cand != src and run(cand)[1] != exp:
                damage_law += 1                # the law broke working code
            B_tok += tok(SYSN + src[:600])
        continue
    cand = edgub.repair(act, src, err)
    if cand != src and run(cand)[1] == exp:
        free += 1; law_fixed += 1              # repaired for nothing
    else:
        bad = src.splitlines()[ln-1] if ln and ln <= len(src.splitlines()) else ""
        B_tok += tok(SYSN + "act=%s exp=%s err=%s line=%s ctx=%s"
                     % (act, exp, err[-160:], bad, src[:600])) + tok(bad or "line")
        if cat == "judgement":
            open_bugs.append(cat)
t_law = time.perf_counter() - t1

PIN, POUT = 5.0/1e6, 25.0/1e6
print("THE LAW, over all %d" % N)
print("  finished with NO model call   %d  (%.1f%%)" % (free, 100.0*free/N))
print("     of which repairs of broken code: %d" % law_fixed)
print("     of which correct code left alone: %d" % (free-law_fixed))
print("  DAMAGE: working code it broke   %d  (%.2f%%)" % (damage_law, 100.0*damage_law/N))
print("  routing time for all %d          %.1f ms" % (N, t_law*1e3))
print()
print("TOKENS (estimated, 4 chars each -- counts of what is SENT are exact)")
print("  A opus 5 alone      %12s   $%.2f" % (format(A_tok, ","), A_tok*(PIN*0.8+POUT*0.2)))
print("  B edgub + opus 5    %12s   $%.2f" % (format(B_tok, ","), B_tok*(PIN*0.8+POUT*0.2)))
print("  reduction           %11.0f%%   (%.1fx)" % (100*(1-B_tok/A_tok), A_tok/max(1,B_tok)))
print()
for k in (10_000, 1_000_000):
    a = A_tok*k/N; b = B_tok*k/N
    print("  at %-9s programs: A %14s tok / $%-8s   B %14s tok / $%s"
          % (format(k,","), format(int(a),","), format(int(a*(PIN*0.8+POUT*0.2)),","),
             format(int(b),","), format(int(b*(PIN*0.8+POUT*0.2)),",")))
print()
print("  OPEN: judgement bugs reaching the model in both configs: %d" % len(open_bugs))
json.dump({"n": N, "free": free, "damage": damage_law, "A": A_tok, "B": B_tok},
          open("bigrun.json","w"), indent=1)
