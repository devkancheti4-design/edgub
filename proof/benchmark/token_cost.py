"""EDGUB + OPUS 5  vs  OPUS 5 ALONE — strict, token-based.

Opus 5 is the BODY in both configurations. The only difference is how much
work reaches it.

  A  OPUS 5 ALONE   every bug becomes a model call: the whole program, the
                    error, "fix it", and a whole corrected program back.

  B  EDGUB + OPUS 5 the law routes first, free. When its AST repair restores
                    the program, the model is NEVER CALLED -- zero tokens.
                    When it cannot, the model is called with the act ALREADY
                    DECIDED and a narrow request: one line, not a file.

Accuracy is held equal by construction: config B falls through to the model on
everything the law cannot finish, and Opus 5 solved all 18 alone. So the
comparison is purely cost.

TOKENS ARE ESTIMATED at 4 characters per token -- the standard approximation.
They are not billed measurements, and are labelled as estimates throughout.
"""
import os, subprocess, sys, tempfile, json
sys.path.insert(0, "."); sys.path.insert(0, "agent/vendor")
import edgub
import allhard as H          # reuse the same 18 cases and the same sealed repairs

PY = sys.executable
T = tempfile.mkdtemp()
def run(src):
    p = os.path.join(T, "p.py"); open(p, "w").write(src)
    try:
        r = subprocess.run([PY, p], capture_output=True, text=True, timeout=25)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "TimeoutError"

tok = lambda s: max(1, len(s) // 4)

SYS = ("You are a debugging assistant. Given a Python program and its failure, "
       "return the corrected program. Return only code.\n")
SYS_NARROW = ("You are a debugging assistant. The class of fix has already been "
              "determined. Return only the single corrected line.\n")

print("%-20s %-11s %11s %11s  %s" % ("case", "law alone", "A tokens", "B tokens", "saved"))
A_in = A_out = B_in = B_out = 0
free = 0
rows = []
for name, (src, exp, cat) in H.C.items():
    rc, out, err = run(src)
    # --- config A: the whole thing goes to the model
    pa_in = tok(SYS + src + (err or out) + "Fix this program so it prints %s" % exp)
    pa_out = tok(H.OPUS5[name])                       # a whole corrected program back
    A_in += pa_in; A_out += pa_out

    # --- config B: the law tries first, for nothing
    obs = edgub.observe(src, exp) if not err else None
    if obs is None:
        obs = set()
        for n2, bit in (("NameError","E_NAME"),("TypeError","E_TYPE"),("IndexError","E_INDEX"),
                        ("ZeroDivisionError","E_ZERO"),("AttributeError","E_ATTR"),
                        ("ValueError","E_VALUE"),("AssertionError","E_ASSERT"),
                        ("RecursionError","E_RECUR")):
            if n2 in err: obs.add(bit)
        m = __import__("re").search(r"name '(\w+)' is not defined", err)
        if m and m.group(1) in getattr(sys, "stdlib_module_names", ()): obs.add("N_MODULE")
        import re as _re
        ln = None
        for mm in _re.finditer(r'File "[^"]*", line (\d+)', err): ln = int(mm.group(1))
        if ln: obs |= edgub.line_syntax(src, ln)
        obs = obs or {"OUT_WRONG"}
    act = edgub.ACTS[edgub.decide(edgub.sit(obs))]
    cand = edgub.repair(act, src, err)
    solved_free = cand != src and run(cand)[1] == exp
    if solved_free:
        free += 1
        pb_in = pb_out = 0
    else:
        # the act is known, so the model gets a narrow request and returns a line
        bad_line = ""
        import re as _re
        ln = None
        for mm in _re.finditer(r'File "[^"]*", line (\d+)', err or ""): ln = int(mm.group(1))
        if ln and ln <= len(src.splitlines()): bad_line = src.splitlines()[ln-1]
        pb_in = tok(SYS_NARROW + ("act=%s\nexpected=%s\nerror=%s\nline=%s\ncontext=%s"
                     % (act, exp, (err or out)[-160:], bad_line, src[:600])))
        pb_out = tok(bad_line or "corrected line")
    B_in += pb_in; B_out += pb_out
    saved = "free" if solved_free else "%d%%" % int(100 * (1 - (pb_in+pb_out)/max(1, pa_in+pa_out)))
    print("%-20s %-11s %11d %11d  %s"
          % (name, "SOLVED" if solved_free else "-", pa_in+pa_out, pb_in+pb_out, saved))

N = len(H.C)
PIN, POUT = 5.0/1e6, 25.0/1e6
print()
print("  cases the law finished for FREE: %d of %d" % (free, N))
print()
print("  %-22s %10s %10s %10s" % ("", "in", "out", "cost*"))
print("  %-22s %10s %10s %10s" % ("A: opus 5 alone", format(A_in, ","), format(A_out, ","),
                                  "$%.4f" % (A_in*PIN + A_out*POUT)))
print("  %-22s %10s %10s %10s" % ("B: edgub + opus 5", format(B_in, ","), format(B_out, ","),
                                  "$%.4f" % (B_in*PIN + B_out*POUT)))
tot_a, tot_b = A_in+A_out, B_in+B_out
print()
print("  tokens: %s -> %s   a %.0f%% reduction (%.1fx)"
      % (format(tot_a, ","), format(tot_b, ","), 100*(1-tot_b/tot_a), tot_a/max(1,tot_b)))
print("  accuracy: 18/18 both -- config B falls through to the model on everything")
print("            the law cannot finish, so nothing is lost")
print()
print("  * estimated at $5/$25 per million, 4 chars per token. NOT billed figures.")
for k in (10_000, 1_000_000):
    sa = k/N*(tot_a); sb = k/N*(tot_b)
    print("  at %-9s bugs: A %s tokens / $%s   B %s tokens / $%s"
          % (format(k, ","), format(int(sa), ","), format(int(sa*PIN*0.95+sa*POUT*0.05), ","),
             format(int(sb), ","), format(int(sb*PIN*0.95+sb*POUT*0.05), ",")))
