"""WHAT IT LEARNED. The part that makes the second time instantaneous.

A derived repair is not thrown away. It is stored as a RULE -- a situation
signature and the transformation that resolved it -- so the next occurrence is
a lookup, not a derivation, and the one after that is free.

    first time   the body supplies examples; the rule is DERIVED from them
    every time   the signature matches; the rule is APPLIED
    after        nothing is searched, ever

The signature deliberately excludes the project, the file and the function.
What is stored is the SHAPE of the fault -- "a keyword's presence lengthens the
output, and the branch that honours it is missing" -- which is why a rule
learned in one library fires in the next.
"""
import json, os, time

DEFAULT = os.path.expanduser("~/.edgub/rules.json")


class Memory:
    def __init__(self, path=DEFAULT):
        self.path = path
        self.rules = {}
        if os.path.exists(path):
            try:
                self.rules = json.load(open(path))
            except Exception:
                self.rules = {}

    @staticmethod
    def signature(observation, act, evidence):
        """The SHAPE of the fault. No project, file or function name in it."""
        return "|".join([
            "+".join(sorted(observation)),
            act,
            "|".join("%s=%s" % (k, v) for k, v in sorted(evidence.items())),
        ])

    def get(self, sig):
        r = self.rules.get(sig)
        if r:
            r["hits"] = r.get("hits", 0) + 1
            return r
        return None

    def learn(self, sig, kind, detail, derived_in):
        self.rules[sig] = {"kind": kind, "detail": detail, "hits": 0,
                           "derived_in_seconds": round(derived_in, 3),
                           "learned": time.strftime("%Y-%m-%d")}
        self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        json.dump(self.rules, open(self.path, "w"), indent=1, sort_keys=True)

    def __len__(self):
        return len(self.rules)
