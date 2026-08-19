#!/bin/sh
# Every claim in the README, from a clean clone. If a line fails, the claim it
# Set PYTHON=/path/to/python if your pytest lives in a virtualenv.
# supports is not backed and does not belong there.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE"
echo "== 1. decide() speed =="
"${PYTHON:-python3}" -c "
import sys, time; sys.path.insert(0,'.')
import edgub
for _ in range(200): edgub.decide(7)
N=20000; t=time.perf_counter()
for i in range(N): edgub.decide(i&255)
print('   %.2f us per call, law is %d chars' % ((time.perf_counter()-t)/N*1e6, len(edgub.LAW)))"
echo "== 2. self-test on toy programs =="
"${PYTHON:-python3}" proof/selftest.py | tail -2
echo "== 3. how much of it is a lookup table =="
"${PYTHON:-python3}" proof/realrepo/not_a_lookup.py | grep -E "length:|entries stored|answered but never|1:1|reproduces every"
echo "== 4. THE PRODUCT, on a repository it has never seen =="
D=$(mktemp -d)
git clone -q --depth 1 https://github.com/pytoolz/toolz.git "$D/t"
"${PYTHON:-python3}" - "$D/t" <<'PY'
import sys
p = sys.argv[1] + "/toolz/itertoolz.py"
s = open(p).read()
old = "            val = key(item)\n            if val not in seen:\n                seen_add(val)\n"
new = "            val = key(item)\n            if val not in seen:\n                seen_add(item)\n"
assert s.count(old) == 1
open(p, "w").write(s.replace(old, new))
print("   injected a wrong-variable bug into unique(), then:")
PY
cd "$D/t" && PYTHONPATH="$HERE" "${PYTHON:-python3}" -m edgub . --package toolz || true
rm -rf "$D"
