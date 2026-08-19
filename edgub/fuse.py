"""Bolt edgub onto the model you already run.

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


def _extract(text):
    """The function source out of a model reply."""
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.S)
    body = m.group(1) if m else text
    for i, line in enumerate(body.splitlines()):
        if line.lstrip().startswith("def "):
            return "\n".join(body.splitlines()[i:])
    return None


class Fused:
    def __init__(self, model):
        self.model = model

    def fix(self, repo=".", package=None, pytest_args=(), apply=True):
        t0 = time.time()
        rep = _fix(repo, package=package, pytest_args=pytest_args, apply=apply)
        out = Fixed(free=list(rep.repaired))
        from . import discover as _d
        for u in rep.unrepaired:
            if not u.prompt or not u.module:
                out.unfixed.append(u)
                continue
            text, ti, to = self.model(u.prompt)
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


def fuse(model):
    """One call. The model you already run goes in; a model that is asked far
    less often comes out."""
    return Fused(model)
