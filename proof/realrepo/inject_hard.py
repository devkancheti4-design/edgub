"""TEN HARD BUGS IN REAL toolz. Not operator swaps.

Each is the kind that survives review: correct on the common path, wrong at a
boundary, or on a branch only some callers take, or using the wrong one of two
variables that are equal most of the time.
"""
import os, shutil, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "toolz-origin")

if not os.path.isdir(SRC):                 # fetch the corpus rather than assume it
    import subprocess
    print("cloning toolz (the corpus these bugs are injected into)...")
    subprocess.run(["git", "clone", "-q", "--depth", "1",
                    "https://github.com/pytoolz/toolz.git", SRC], check=True)

BUGS = [
 ("unique_wrongvar", "toolz/itertoolz.py",
  "wrong variable: keys the item, remembers the item",
  "            if val not in seen:\n                seen_add(val)\n",
  "            if val not in seen:\n                seen_add(item)\n"),
 ("groupby_wrongvar", "toolz/itertoolz.py",
  "wrong variable: collects the key instead of the item",
  "        d[key(item)](item)\n", "        d[key(item)](key(item))\n"),
 ("reduceby_nocontinue", "toolz/itertoolz.py",
  "missing branch exit: the first item is folded into itself",
  "                d[k] = item\n                continue\n", "                d[k] = item\n"),
 ("partition_alwayspad", "toolz/itertoolz.py",
  "branch collapsed: pads even when no pad was asked for",
  "    if pad is no_pad:\n        return zip(*args)\n    else:\n        return zip_longest(*args, fillvalue=pad)\n",
  "    return zip_longest(*args, fillvalue=pad)\n"),
 ("sliding_off", "toolz/itertoolz.py",
  "boundary: the window starts one element late",
  "               for i, it in enumerate(itertools.tee(seq, n))))\n",
  "               for i, it in enumerate(itertools.tee(seq, n), 1)))\n"),
 ("itemfilter_swap", "toolz/dicttoolz.py",
  "unpacking reversed: key and value exchanged",
  "            k, v = item\n", "            v, k = item\n"),
 ("merge_with_order", "toolz/dicttoolz.py",
  "order reversed: only visible when the folding function is not commutative",
  "    for d in dicts:\n        for k, v in d.items():\n            values[k](v)\n",
  "    for d in reversed(list(dicts)):\n        for k, v in d.items():\n            values[k](v)\n"),
 ("diff_nodefault", "toolz/itertoolz.py",
  "branch collapsed: the caller-supplied default is ignored",
  "    if default == no_default:\n        iters = zip(*seqs)\n"
  "    else:\n        iters = zip_longest(*seqs, fillvalue=default)\n",
  "    iters = zip(*seqs)\n"),
 ("join_sides", "toolz/itertoolz.py",
  "pair order reversed on the inner-join branch only",
  "        # Inner Join\n        for item in rightseq:\n            key = rightkey(item)\n"
  "            if key in d:\n                for left_match in d[key]:\n"
  "                    yield (left_match, item)\n",
  "        # Inner Join\n        for item in rightseq:\n            key = rightkey(item)\n"
  "            if key in d:\n                for left_match in d[key]:\n"
  "                    yield (item, left_match)\n"),
 ("get_default_inv", "toolz/itertoolz.py",
  "condition inverted on the TypeError branch only",
  "        elif default != no_default:\n            return default\n",
  "        elif default == no_default:\n            return default\n"),
]

def build(dest_root):
    os.makedirs(dest_root, exist_ok=True); made = []
    for bid, rel, why, old, new in BUGS:
        dest = os.path.join(dest_root, bid)
        if os.path.exists(dest): shutil.rmtree(dest)
        shutil.copytree(SRC, dest, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        p = os.path.join(dest, rel); s = open(p).read()
        if s.count(old) != 1:
            print("  !! %-20s anchor x%d -- SKIPPED" % (bid, s.count(old)))
            shutil.rmtree(dest); continue
        open(p, "w").write(s.replace(old, new))
        made.append({"id": bid, "file": rel, "kind": "hard", "why": why})
        print("  %-20s %s" % (bid, why))
    return made

if __name__ == "__main__":
    root = sys.argv[1]
    print("injecting %d HARD bugs into copies of toolz\n" % len(BUGS))
    made = build(root)
    json.dump(made, open(os.path.join(root, "bugs.json"), "w"), indent=1)
    print("\n%d copies built" % len(made))
