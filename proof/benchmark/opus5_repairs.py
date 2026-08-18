"""OPUS 5's SIDE of the same eight cases — written here, then run.

Same programs, same oracle: does it run and print the expected output. My
repairs are written in full below rather than selected from a menu, which is
the whole difference between a frontier model and a routing policy.
"""
import os, subprocess, sys, tempfile, time
PY = sys.executable
T = tempfile.mkdtemp()

def run(src):
    p = os.path.join(T, "p.py"); open(p, "w").write(src)
    r = subprocess.run([PY, p], capture_output=True, text=True, timeout=20)
    return r.stdout.strip()

CASES = {
 "missing-import":  ("def f(p):\n    return os.path.basename(p)\nprint(f('/a/b'))", "b"),
 "index-range":     ("L=[1,2]\ndef f(i):\n    return L[i]\nprint(f(9))", "2"),
 "int-of-junk":     ("def f(s):\n    return int(s)\nprint(f('9kg'))", "9"),
 "name-needs-value":("def area(w):\n    return w * HEIGHT\nprint(area(5))", "20"),
 "name-needs-ctor": ("class Grammar:\n    def __init__(self): self.n = 7\n"
                     "def f():\n    return DEFAULT.n\nprint(f())", "7"),
 "wrong-op":        ("def f(a,b):\n    return a - b\nprint(f(6,2))", "8"),
 "off-by-one":      ("def total(n):\n    return sum(range(n))\nprint(total(4))", "10"),
 "missing-return":  ("def double(n):\n    n * 2\nprint(double(3))", "6"),
}

OPUS5 = {
 "missing-import":  "import os\ndef f(p):\n    return os.path.basename(p)\nprint(f('/a/b'))",
 "index-range":     "L=[1,2]\ndef f(i):\n    return L[min(i, len(L)-1)]\nprint(f(9))",
 "int-of-junk":     ("import re\ndef f(s):\n    return int(re.match(r'\\d+', s).group())\n"
                     "print(f('9kg'))"),
 "name-needs-value":"HEIGHT = 4\ndef area(w):\n    return w * HEIGHT\nprint(area(5))",
 "name-needs-ctor": ("class Grammar:\n    def __init__(self): self.n = 7\n"
                     "def f():\n    return DEFAULT.n\nDEFAULT = Grammar()\nprint(f())"),
 "wrong-op":        "def f(a,b):\n    return a + b\nprint(f(6,2))",
 "off-by-one":      "def total(n):\n    return sum(range(n + 1))\nprint(total(4))",
 "missing-return":  "def double(n):\n    return n * 2\nprint(double(3))",
}

if __name__ == "__main__":
    ok = 0
    t0 = time.time()
    for n, (src, exp) in CASES.items():
        got = run(OPUS5[n])
        good = got == exp
        ok += good
        print("  %-18s %-8s got %-6s want %s" % (n, "PASS" if good else "fail", got, exp))
    print("\n  opus 5: %d/%d   (wall time to RUN them: %.1fs; the reasoning that "
          "wrote them is not counted here)" % (ok, len(CASES), time.time() - t0))
