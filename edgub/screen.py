"""IN-PROCESS CANDIDATE VALIDATION. The harness fix, not a law change.

Every candidate was validated by SPAWNING A FRESH PYTEST: 0.229s of interpreter
startup per candidate, 25,047 candidates for one function, 2.5 hours. The law
takes 2.16 microseconds to decide; the validation was six orders of magnitude
slower and it was all process launch.

This imports the library and the failing test module ONCE, then for each
candidate rebinds the repaired function and calls the failing test directly.
A candidate that survives still faces the FULL pytest suite -- the bar is
unchanged, only the cost of getting to it.
"""
import ast, importlib, os, sys, types


class Fast:
    def __init__(self, repo, modname, funcname, nodes):
        self.repo, self.modname, self.funcname = repo, modname, funcname
        sys.path.insert(0, repo)
        os.chdir(repo)
        self.mod = importlib.import_module(modname)
        self.orig = getattr(self.mod, funcname)
        self.tests = []              # (callable, owner_namespace_list)
        for node in nodes:
            path, _, rest = node.partition("::")
            tmod = path[:-3].replace("/", ".")
            try:
                tm = importlib.import_module(tmod)
            except Exception:
                continue
            parts = [p for p in rest.split("::") if p]
            if len(parts) == 1:
                fn = getattr(tm, parts[0], None)
                if fn:
                    self.tests.append((fn, tm))
            elif len(parts) == 2:
                cls = getattr(tm, parts[0], None)
                if cls:
                    inst = cls()
                    m = getattr(inst, parts[1], None)
                    if m:
                        self.tests.append((m, tm))

    def ok(self, src):
        """Does this candidate satisfy the tests that are currently red?"""
        g = dict(self.mod.__dict__)
        try:
            exec(compile(src, "<cand>", "exec"), g)
        except Exception:
            return False
        new = g.get(self.funcname)
        if new is None:
            return False
        setattr(self.mod, self.funcname, new)
        # tests usually did `from toolz.itertoolz import diff` at import time,
        # so the test module holds its OWN reference -- rebind that too
        touched = []
        for _, tm in self.tests:
            if getattr(tm, self.funcname, None) is not None:
                touched.append((tm, getattr(tm, self.funcname)))
                setattr(tm, self.funcname, new)
        try:
            for fn, _ in self.tests:
                fn()
            return True
        except Exception:
            return False
        finally:
            setattr(self.mod, self.funcname, self.orig)
            for tm, old in touched:
                setattr(tm, self.funcname, old)
