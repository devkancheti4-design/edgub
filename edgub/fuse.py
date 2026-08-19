"""Bolt edgub onto the model you already run.

INTERFACE CREDIT. The shape of this module -- `fuse(Adapter(...))`, the
`Callable_` / `Anthropic` adapter names, and the "one call, the model you
already run goes in" framing -- is taken from proven-reason's FUSE.md
(github.com/devkancheti4-design/proven-reason, Apache-2.0, (c) 2026 Devi Eswar
Kancheti). No code was copied; the API design was, and it should be said.

    import edgub
    from edgub.fuse import fuse, Anthropic

    rz = fuse(Anthropic("claude-opus-5"))
    r = rz.fix(".")
    r.tokens          # what the model actually cost
    r.saved_estimate  # what it would have cost without the pre-pass

edgub repairs what your repository's own tests determine, for zero tokens. What
it cannot reach becomes a MINIMAL prompt -- the failing tests and the one
function -- instead of your agent shipping a repo into context. The model still
decides everything edgub could not.

The failure mode is a passthrough, never a wrong answer: anything edgub does not
repair goes to the model exactly as it would have without edgub.
"""
import ast, os, re, time
from dataclasses import dataclass, field

from .repair import repair as _fix


# --------------------------------------------------------------- adapters --
class Callable_:
    """Anything that turns a prompt into source. Use this to test without a key."""

    def __init__(self, fn, name="callable"):
        self.fn, self.name = fn, name

    def __call__(self, prompt):
        return self.fn(prompt), 0, 0


class Anthropic:
    """The Claude API. Adaptive thinking; streaming so long repairs do not
    hit a request timeout."""

    def __init__(self, model="claude-opus-5", max_tokens=4096, client=None):
        self.model, self.max_tokens, self.name = model, max_tokens, model
        self._client = client

    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def __call__(self, prompt):
        with self.client().messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        ) as s:
            msg = s.get_final_message()
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return text, msg.usage.input_tokens, msg.usage.output_tokens


# ------------------------------------------------------------------ fused --
@dataclass
class Fixed:
    free: list = field(default_factory=list)      # repaired by edgub, 0 tokens
    by_model: list = field(default_factory=list)  # repaired by the model
    unfixed: list = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    seconds: float = 0.0
    material_rounds: int = 0   # times the body supplied material and it derived
    tied_out: int = 0          # times the loop hit the direct-ask budget

    @property
    def tokens(self):
        return self.tokens_in + self.tokens_out

    def __str__(self):
        n = len(self.free) + len(self.by_model)
        s = ["%d repaired (%d free, %d by the model), %d unfixed, %d tokens, %.1fs"
             % (n, len(self.free), len(self.by_model), len(self.unfixed),
                self.tokens, self.seconds)]
        for r in self.free:
            s.append("  free   %s.%s  %s" % (r.module.split(".")[-1], r.function, r.edit))
        for r in self.by_model:
            s.append("  model  %s" % r)
        return "\n".join(s)


def _material_prompt(refusal, func, module, examples):
    """Ask the model for MATERIAL, not for a fix.

    The algorithm has already named what is absent. This asks the body to
    supply exactly that -- more examples that separate the cases -- and nothing
    else. It is a far smaller request than "repair this function", which is the
    whole point: the model is used as a source of DATA, and the derivation
    stays with the algorithm."""
    shown = "\n".join("  %s  ->  %s" % (c, w) for c, w in examples[:6])
    return ("A repair could not be derived for `%s` in %s.\n\n%s\n\n"
            "Existing examples:\n%s\n\n"
            "Do NOT fix the function. Supply 3-6 ADDITIONAL examples of `%s` "
            "that would separate the cases -- calls that differ in whether an "
            "optional argument is passed, and whose results differ. One per "
            "line, exactly:\n\n  <call>  ->  <expected result>\n"
            % (func, module, refusal, shown, func))


def _parse_examples(text):
    out = []
    for line in text.splitlines():
        if "->" not in line:
            continue
        call, _, want = line.partition("->")
        call, want = call.strip().strip("`"), want.strip().strip("`")
        if call and want and "(" in call:
            out.append((call, want))
    return out


def _extract(text):
    """The function source out of a model reply."""
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.S)
    body = m.group(1) if m else text
    for i, line in enumerate(body.splitlines()):
        if line.lstrip().startswith("def "):
            return "\n".join(body.splitlines()[i:])
    return None


class Fused:
    def __init__(self, model, widen=True, max_rounds=3):
        self.model = model
        self.widen = widen          # ask for MATERIAL before asking for a fix
        self.max_rounds = max_rounds

    def fix(self, repo=".", package=None, pytest_args=(), apply=True):
        t0 = time.time()
        rep = _fix(repo, package=package, pytest_args=pytest_args, apply=apply)
        out = Fixed(free=list(rep.repaired))
        from . import discover as _d
        from .harvest import examples as _harvest
        from .infer import infer as _infer_rule
        for u in rep.unrepaired:
            if not u.prompt or not u.module:
                out.unfixed.append(u)
                continue
            # ---------------------------------------------------------------
            # THE LOOP. The algorithm refused and NAMED what was missing, so ask
            # the body for exactly that material, re-derive, and repeat.
            #
            # THE STOPPING RULE: a direct "repair this" ask costs roughly
            # len(u.prompt)/4 tokens. The loop is only worth running while it
            # has spent LESS than that. The moment it ties, stop asking for
            # material and ask directly -- so this can never cost more than not
            # having used it at all.
            # ---------------------------------------------------------------
            budget = max(len(u.prompt) // 4, 1)
            spent = 0
            src_new, ti, to = None, 0, 0
            if u.module and u.function and self.widen:
                path0 = os.path.join(os.path.abspath(repo),
                                     u.module.replace(".", os.sep) + ".py")
                ex = _harvest(os.path.abspath(repo), path0, u.function,
                              [n for n in u.test.split(", ") if n])
                for _round in range(self.max_rounds):
                    if spent >= budget:
                        break                       # tied with asking directly
                    ask = _material_prompt(u.reason, u.function, u.module, ex)
                    text, a, b = self.model(ask)
                    spent += a + b
                    out.tokens_in += a
                    out.tokens_out += b
                    fresh = _parse_examples(text)
                    if not fresh:
                        break
                    ex = ex + [e for e in fresh if e not in ex]
                    got = _infer_rule(ex, u.function, u.module,
                                      src=open(path0).read())
                    if isinstance(got, dict):
                        out.material_rounds += 1
                        break                       # derivable now
                if spent >= budget:
                    out.tied_out += 1
            text, a, b = self.model(u.prompt)       # the direct ask
            ti, to = a, b
            out.tokens_in += ti
            out.tokens_out += to
            src_new = _extract(text)
            path = os.path.join(os.path.abspath(repo),
                                u.module.replace(".", os.sep) + ".py")
            if not src_new or not os.path.exists(path):
                out.unfixed.append(u)
                continue
            orig = open(path).read()
            try:
                fn = next(n for n in ast.walk(ast.parse(orig))
                          if isinstance(n, ast.FunctionDef) and n.name == u.function)
            except StopIteration:
                out.unfixed.append(u)
                continue
            lines = orig.splitlines(keepends=True)
            cand = ("".join(lines[:fn.lineno - 1]) + src_new + "\n"
                    + "".join(lines[fn.end_lineno:]))
            try:
                compile(cand, "<c>", "exec")
            except SyntaxError:
                out.unfixed.append(u)
                continue
            open(path, "w").write(cand)
            failed, _ = _d.run_tests(os.path.abspath(repo), pytest_args)
            if failed == 0:
                out.by_model.append("%s.%s" % (u.module.split(".")[-1], u.function))
            else:
                open(path, "w").write(orig)
                out.unfixed.append(u)
        out.seconds = time.time() - t0
        return out


def fuse(model, widen=True, max_rounds=3):
    """One call. The model you already run goes in; a model that is asked far
    less often comes out.

    widen=True asks the body for the MATERIAL the algorithm named as missing
    before asking it for a fix, and stops the moment that has cost as much as
    asking directly would have."""
    return Fused(model, widen=widen, max_rounds=max_rounds)
