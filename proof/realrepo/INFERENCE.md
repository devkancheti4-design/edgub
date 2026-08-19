# Inference, not enumeration

The law decides which class of repair a fault is. The repair itself is
**generalised from the examples the body supplies** — the function's own
doctests and the failing test's assertions. Enumeration runs only if that
yields nothing.

```
edgub: 1 repaired, 1 left for a model, 3.5s, 0 tokens
  repaired  itertoolz.diff  INFER/inference via zip_longest(..., fillvalue=default)
            4 candidates
```

`diff` is the bug enumeration exhausted **25,057 candidates** on and never
solved. Inference reaches it in **4**, because the examples state the answer:

```
list(diff([1,2,3],[1,2,10,100]))                -> [(3,10)]
list(diff([1,2,3],[1,2,10,100], default=None))  -> [(3,10),(None,100)]

2 examples pass `default` and produce longer output; 6 do not
   -> the function BRANCHES on `default`.          Read, not searched.
one callable in scope accepts a padding keyword
   -> that is the other arm.                       Read, not searched.
```

The derived rule is stored, keyed by the *shape* of the fault with no project,
file or function name in it, so the next occurrence is a lookup:

```
E_ASSERT|REPAIR_LIBRARY|keyword=default|kind=missing_branch
```

## Honestly unresolved

`partition_alwayspad` is **not** repaired. Every inference candidate either
fails to improve the suite or breaks the module at import.

An earlier draft of this file claimed it was repaired. That was wrong: the
standalone harness checked `"failed" not in output`, and a pytest *collection
error* prints no `"failed"`, so a module that would not import was read as a
pass. The product caught what my test of the product did not.

## Defects this path exposed, all in the plumbing

```
inference was built and never wired in -- the product ran enumeration
the damage gate counted comments file-wide, so any target function
  containing one had every candidate vetoed
a candidate breaking the import aborted the whole run instead of being
  rejected as a bad candidate
```
