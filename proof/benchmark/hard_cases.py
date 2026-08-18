"""HARD CASES — where a frontier model can also get it wrong.

Not "more of the same". These are the traps: the traceback points away from
the cause, the bug is latent until a boundary, a builtin is shadowed, a
closure binds late, an alias mutates at a distance, a bare except swallows the
real error. A repair that makes the output match can still be the wrong fix.

Opus 5's repairs are written in full below BEFORE anything is run.
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.request
sys.path.insert(0, "agent"); sys.path.insert(0, "agent/vendor")
import edgub

PY = sys.executable
T = tempfile.mkdtemp()
LAW = json.load(open("law_v3.json"))["law"]
C = compile(LAW, "<l>", "eval")
def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >> 31 else v
law = lambda x: s32(eval(C, {"__builtins__": {}}, {"x": x})) % 11

def run(src):
    p = os.path.join(T, "p.py"); open(p, "w").write(src)
    try:
        r = subprocess.run([PY, p], capture_output=True, text=True, timeout=20)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def ask(prompt, n=400):
    b = json.dumps({"model": "qwen2.5-coder:7b", "prompt": prompt, "stream": False,
                    "options": {"num_predict": n, "temperature": 0}}).encode()
    r = urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/generate", b, {"Content-Type": "application/json"}),
        timeout=240)
    return json.loads(r.read())["response"]

def code(t):
    m = re.search(r"```(?:python)?\n(.*?)```", t, re.S)
    return (m.group(1) if m else t).strip()

CASES = {
 # the traceback names the helper; the cause is the caller's argument order
 "misleading-frame": ("def scale(v, f):\n    return v / f\n"
                      "def apply(items, factor):\n    return [scale(factor, i) for i in items]\n"
                      "print(apply([2, 4], 8))", "[4.0, 2.0]"),
 # latent: correct for every input except the boundary
 "boundary-only":    ("def avg(xs):\n    return sum(xs) // len(xs)\nprint(avg([]))", "0"),
 # a builtin shadowed earlier, failing much later
 "shadowed-builtin": ("list = [3, 1, 2]\ndef top(xs):\n    return list(sorted(xs))[0]\n"
                      "print(top([5, 9]))", "5"),
 # late binding: every closure captures the final value
 "late-binding":     ("fs = [lambda: i for i in range(3)]\nprint([f() for f in fs])",
                      "[0, 1, 2]"),
 # aliasing: mutating one name changes the other
 "aliasing":         ("BASE = [1, 2]\ndef with_extra(x):\n    out = BASE\n    out.append(x)\n"
                      "    return out\nwith_extra(3)\nprint(with_extra(4))", "[1, 2, 4]"),
 # a bare except hides the real error and returns a plausible wrong answer
 "swallowed":        ("def parse(s):\n    try:\n        return int(s)\n    except:\n"
                      "        return 0\nprint(parse('12') + parse('7'))", "19"),
 # float equality that is almost always true
 "float-equality":   ("def near(a, b):\n    return a + b == 0.3\nprint(near(0.1, 0.2))", "True"),
 # integer vs true division, silently wrong only for odd inputs
 "silent-division":  ("def half(n):\n    return n // 2\nprint(half(7))", "3.5"),
}

OPUS5 = {
 "misleading-frame": ("def scale(v, f):\n    return v / f\n"
                     "def apply(items, factor):\n    return [scale(i, factor) for i in items]\n"
                     "print(apply([2, 4], 8))"),
 "boundary-only":    "def avg(xs):\n    return sum(xs) // len(xs) if xs else 0\nprint(avg([]))",
 "shadowed-builtin": "DATA = [3, 1, 2]\ndef top(xs):\n    return sorted(xs)[0]\nprint(top([5, 9]))",
 "late-binding":     "fs = [lambda i=i: i for i in range(3)]\nprint([f() for f in fs])",
 "aliasing":         ("BASE = [1, 2]\ndef with_extra(x):\n    out = list(BASE)\n    out.append(x)\n"
                     "    return out\nwith_extra(3)\nprint(with_extra(4))"),
 "swallowed":        ("def parse(s):\n    try:\n        return int(s)\n    except ValueError:\n"
                     "        return 0\nprint(parse('12') + parse('7'))"),
 "float-equality":   ("def near(a, b):\n    return abs(a + b - 0.3) < 1e-9\nprint(near(0.1, 0.2))"),
 "silent-division":  "def half(n):\n    return n / 2\nprint(half(7))",
}

def cfg_7b(src, exp):
    rc, out, err = run(src)
    p = ("Fix this Python file so running it prints exactly: %s\n"
         "Return ONLY the corrected file.\n\nFILE:\n%s\n\nOBSERVED:\n%s\n"
         % (exp, src, err or "printed %r" % out))
    try:
        return run(code(ask(p)))[1] == exp
    except Exception:
        return False

def cfg_law_7b(src, exp):
    cur = src
    for _ in range(3):
        rc, out, err = run(cur)
        if out == exp:
            return True
        obs = edgub.observe(cur, exp)
        act = edgub.ACTS[law(edgub.sit(obs))]
        nxt = edgub.repair(act, cur, err)
        if nxt == cur:                       # the law has no repair: hands take over
            p = ("Fix this Python file so running it prints exactly: %s\n"
                 "Return ONLY the corrected file.\n\nFILE:\n%s\n\nOBSERVED:\n%s\n"
                 % (exp, cur, err or "printed %r" % out))
            try:
                cur = code(ask(p))
            except Exception:
                return False
        else:
            cur = nxt
    return run(cur)[1] == exp

print("%-19s %-9s %-9s %-9s %s" % ("case", "7B", "law+7B", "opus 5", "expected"))
tot = {"b": 0, "c": 0, "o": 0}
t = {"b": 0.0, "c": 0.0}
for n, (src, exp) in CASES.items():
    t0 = time.time(); b = cfg_7b(src, exp); t["b"] += time.time() - t0
    t0 = time.time(); c = cfg_law_7b(src, exp); t["c"] += time.time() - t0
    o = run(OPUS5[n])[1] == exp
    tot["b"] += b; tot["c"] += c; tot["o"] += o
    print("%-19s %-9s %-9s %-9s %s"
          % (n, "PASS" if b else "fail", "PASS" if c else "fail",
             "PASS" if o else "fail", exp), flush=True)
N = len(CASES)
print()
print("  7B alone   %d/%d   %5.1fs" % (tot["b"], N, t["b"]))
print("  law + 7B   %d/%d   %5.1fs" % (tot["c"], N, t["c"]))
print("  opus 5     %d/%d" % (tot["o"], N))
