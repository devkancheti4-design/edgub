"""LAW vs 7B vs LAW+7B — the architecture question, measured.

Three configurations, same broken programs, same oracle (does it run and print
the expected output):

  A  LAW ONLY      the authored policy picks a repair; AST transforms apply it.
                   Free, 2.5us, no model.
  B  7B ONLY       the local model sees the source and the traceback and
                   rewrites the file. No law.
  C  LAW + 7B      the law picks the repair KIND; the model supplies only the
                   CONTENT when the kind needs authoring (a value, a body).
                   The model never chooses what to do.

The cases are chosen to separate them: some the law repairs alone, some need
content it cannot invent, some have no matching act at all.
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.request
sys.path.insert(0, "agent"); sys.path.insert(0, "agent/vendor")
import edgub
_L3 = json.load(open("law_v3.json"))["law"]
_C3 = compile(_L3, "<l>", "eval")

PY = "python"
MODEL = "qwen2.5-coder:7b"
TMP = tempfile.mkdtemp(prefix="threeway_")


def ask(prompt, n=220):
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "options": {"num_predict": n, "temperature": 0}}).encode()
    r = urllib.request.urlopen(
        urllib.request.Request("http://localhost:11434/api/generate", body,
                               {"Content-Type": "application/json"}), timeout=180)
    return json.loads(r.read())["response"]


def code_only(t):
    m = re.search(r"```(?:python)?\n(.*?)```", t, re.S)
    return (m.group(1) if m else t).strip()


def run(src):
    p = os.path.join(TMP, "p.py"); open(p, "w").write(src)
    try:
        r = subprocess.run([PY, p], capture_output=True, text=True, timeout=20)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


CASES = {
 # the law repairs these alone
 "missing-import":  ("def f(p):\n    return os.path.basename(p)\nprint(f('/a/b'))", "b"),
 "index-range":     ("L=[1,2]\ndef f(i):\n    return L[i]\nprint(f(9))", "2"),
 "int-of-junk":     ("def f(s):\n    return int(s)\nprint(f('9kg'))", "9"),
 # the ACT is right but the CONTENT must be invented
 "name-needs-value":("def area(w):\n    return w * HEIGHT\nprint(area(5))", "20"),
 "name-needs-ctor": ("class Grammar:\n    def __init__(self): self.n = 7\n"
                     "def f():\n    return DEFAULT.n\nprint(f())", "7"),
 # no matching act at all
 "wrong-op":        ("def f(a,b):\n    return a - b\nprint(f(6,2))", "8"),
 "off-by-one":      ("def total(n):\n    return sum(range(n))\nprint(total(4))", "10"),
 "missing-return":  ("def double(n):\n    n * 2\nprint(double(3))", "6"),
}


def cfg_law(src, expect):
    for _ in range(3):
        rc, out, err = run(src)
        if out == expect:
            return True, src
        obs = edgub.observe(src, expect)
        act = edgub.ACTS[eval(_C3, {"__builtins__": {}}, {"x": edgub.sit(obs)}) % 11]
        nxt = edgub.repair(act, src, err)
        if nxt == src:
            return False, src
        src = nxt
    return run(src)[1] == expect, src


def cfg_7b(src, expect):
    rc, out, err = run(src)
    p = ("Fix this Python file so that running it prints exactly: %s\n"
         "Return ONLY the corrected file, no explanation.\n\n"
         "FILE:\n%s\n\nERROR:\n%s\n" % (expect, src, err or "(no error; wrong output: %s)" % out))
    try:
        new = code_only(ask(p, 300))
    except Exception as e:
        return False, "model error: %s" % e
    return run(new)[1] == expect, new


def cfg_law_7b(src, expect):
    """The law decides WHAT; the model supplies only CONTENT it cannot invent."""
    for _ in range(3):
        rc, out, err = run(src)
        if out == expect:
            return True, src
        obs = edgub.observe(src, expect)
        act = edgub.ACTS[eval(_C3, {"__builtins__": {}}, {"x": edgub.sit(obs)}) % 11]
        if act == "DEFINE_NAME":
            m = re.search(r"name '(\w+)' is not defined", err)
            if m:
                p = ("A Python file fails with: NameError: name '%s' is not defined.\n"
                     "Reply with ONLY the Python EXPRESSION to assign to %s -- a "
                     "constructor call, literal or expression -- so the file runs and "
                     "prints %s. Reply with the expression alone: no name, no '=', no "
                     "explanation, no code fence.\n\nFILE:\n%s"
                     % (m.group(1), m.group(1), expect, src))
                try:
                    val = ask(p, 40).strip().splitlines()[0].strip().strip("`")
                except Exception:
                    val = "0"
                cand = edgub.repair("DEFINE_NAME", src, err, value=val)
                if cand != src:
                    src = cand
                    continue
        elif act in ("SHIP",) or edgub.repair(act, src, err) == src:
            # no act applies -- author the body from the one example we have
            p = ("Rewrite ONLY the body of the function in this file so that running "
                 "it prints exactly %s. Return the whole corrected file, nothing else."
                 "\n\n%s" % (expect, src))
            try:
                src = code_only(ask(p, 300))
            except Exception:
                return False, src
            continue
        nxt = edgub.repair(act, src, err)
        if nxt == src:
            return False, src
        src = nxt
    return run(src)[1] == expect, src


print("%-18s %-12s %-12s %s" % ("case", "A: law", "B: 7B", "C: law+7B"))
tot = {"A": 0, "B": 0, "C": 0}
times = {"A": 0.0, "B": 0.0, "C": 0.0}
for name, (src, exp) in CASES.items():
    row = []
    for key, fn in (("A", cfg_law), ("B", cfg_7b), ("C", cfg_law_7b)):
        t = time.time()
        ok, _ = fn(src, exp)
        times[key] += time.time() - t
        tot[key] += bool(ok)
        row.append("PASS" if ok else "fail")
    print("%-18s %-12s %-12s %s" % (name, row[0], row[1], row[2]), flush=True)
n = len(CASES)
print()
for k, label in (("A", "law only      "), ("B", "7B only       "), ("C", "law + 7B      ")):
    print("  %s %d/%d   %6.1fs total" % (label, tot[k], n, times[k]))
json.dump({"n": n, **tot}, open("threeway.json", "w"), indent=1)
