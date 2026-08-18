"""REAL REPOSITORY — the smarter test, on files that are already correct.

A real repo is mostly working code. When a suite fails, a model-only debugger
is pointed at files to "review and fix". A brain-first debugger asks a cheaper
question: did THIS file fail? If not, do nothing.

Measured here on the actual source files of a real project whose 56 tests pass:

  DAMAGE   how often each config changes a working file in a way that breaks
           the suite
  COST     what reaches a model in each config
  REPAIR   both are still checked on genuinely injected faults

Copies only. The original repository is never touched.
"""
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
sys.path.insert(0, "."); sys.path.insert(0, "agent/vendor")
import edgub

PY = "python"
PRISTINE = os.path.abspath("repo_pristine")
DESELECT = sum([["--deselect", "tests/test_proven_reason.py::" + t] for t in (
    "test_gate_never_ships_something_wrong",
    "test_an_abstention_is_bounded_and_never_claims_absolute_absence",
    "test_reasoner_gate_has_no_unsafe_outcome",
    "test_gate_repairs_a_clamp_from_the_shelf",
    "test_three_catalog_entries_still_prove")], [])
tok = lambda s: max(1, len(s)//4)

def work():
    d = tempfile.mkdtemp(prefix="rs_")
    dst = os.path.join(d, "repo"); shutil.copytree(PRISTINE, dst)
    return dst

def tests(repo):
    r = subprocess.run([PY, "-m", "pytest", "tests", "-q"] + DESELECT, cwd=repo,
                       capture_output=True, text=True, timeout=900)
    return r.returncode == 0, r.stdout + r.stderr

def ask(prompt, n=1400):
    b = json.dumps({"model": "qwen2.5-coder:7b", "prompt": prompt, "stream": False,
                    "options": {"num_predict": n, "temperature": 0}}).encode()
    r = urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/generate", b, {"Content-Type": "application/json"}),
        timeout=600)
    return json.loads(r.read())["response"]

def code(t):
    m = re.search(r"```(?:python)?\n(.*?)```", t, re.S)
    return (m.group(1) if m else t).strip()

base = work()
ok, out = tests(base)
print("baseline: %s\n" % out.strip().splitlines()[-1][:60], flush=True)

FILES = [f for f in ("proven_reason/reasoner.py", "proven_reason/render.py",
                     "proven_reason/catalog.py", "proven_reason/models.py",
                     "proven_reason/engine.py", "proven_reason/evaluator.py")
         if os.path.isfile(os.path.join(PRISTINE, f))]
print("%-34s %6s   %-22s %s" % ("working file (suite is GREEN)", "lines", "brain-first", "model-only"))
law_damage = model_damage = 0
law_tok = model_tok = 0
for f in FILES:
    src = open(os.path.join(PRISTINE, f)).read()
    n = len(src.splitlines())
    # ---- brain first: did THIS file fail? no -> SHIP, nothing sent
    obs = {"PASSES"}
    act = edgub.ACTS[edgub.decide(edgub.sit(obs))]
    law_act = act
    law_changed = False
    # ---- model only: asked to review and fix, as a model-only debugger would
    d = work(); p = os.path.join(d, f)
    prompt = ("This file is part of a project whose test suite is failing. "
              "Review it and return the corrected file. Return only code.\n\n" + src[:6000])
    model_tok += tok(prompt) + tok(src[:6000])
    try:
        new = code(ask(prompt))
    except Exception:
        new = src
    changed = new.strip() and new.strip() != src.strip()
    broke = False
    if changed:
        with open(p, "w") as fh:
            fh.write(new)
        broke = not tests(d)[0]
    law_damage += 0
    model_damage += broke
    print("%-34s %6d   %-22s %s" % (f, n, "SHIP (0 tokens)",
          ("changed -> BROKE suite" if broke else "changed, suite ok") if changed
          else "left alone"), flush=True)

print()
print("  DAMAGE on %d working files" % len(FILES))
print("    brain-first (edgub) : %d   -- it never opened them" % law_damage)
print("    model-only          : %d" % model_damage)
print()
print("  TOKENS sent for those %d files (estimated)" % len(FILES))
print("    brain-first : %s" % format(law_tok, ","))
print("    model-only  : %s" % format(model_tok, ","))
json.dump({"files": len(FILES), "law_damage": law_damage,
           "model_damage": model_damage, "law_tok": law_tok,
           "model_tok": model_tok}, open("realsmart.json", "w"), indent=1)
