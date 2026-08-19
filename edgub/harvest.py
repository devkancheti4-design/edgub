"""THE BODY'S JOB: supply data and examples. Not repairs.

A body -- a model, or the repository itself -- can read a broken function and
say what it is SUPPOSED to do, as (call, expected) pairs. That is data, and the
engine generalises from data. It is not the same as handing over a fix.

Three sources, all mechanical, none of them a repair:
  the function's own doctests     the author's worked examples
  the failing test's assertions   what the test demands
  the docstring's prose           ignored -- only executable claims count
"""
import ast, doctest, os, re


def from_doctests(src, func):
    out = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.FunctionDef) and n.name == func:
            for ex in doctest.DocTestParser().get_examples(ast.get_docstring(n) or ""):
                if ex.want.strip() and "SKIP" not in ex.source:
                    out.append((ex.source.strip(), ex.want.strip()))
    return out


def from_failing_test(repo, node, func):
    """Assertions in the failing test that mention the function."""
    path, _, tname = node.partition("::")
    tname = tname.split("::")[-1]
    full = os.path.join(repo, path)
    if not os.path.exists(full):
        return []
    try:
        tree = ast.parse(open(full).read())
    except SyntaxError:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == tname:
            for a in ast.walk(n):
                if isinstance(a, ast.Assert) and isinstance(a.test, ast.Compare) \
                   and len(a.test.ops) == 1 and isinstance(a.test.ops[0], ast.Eq):
                    left = ast.unparse(a.test.left)
                    right = ast.unparse(a.test.comparators[0])
                    if func + "(" in left:
                        out.append((left, right))
    return out


def examples(repo, module_path, func, failing_nodes):
    src = open(module_path).read()
    ex = from_doctests(src, func)
    for node in failing_nodes:
        ex += from_failing_test(repo, node, func)
    seen, out = set(), []
    for c, w in ex:
        if c not in seen:
            seen.add(c); out.append((c, w))
    return out
