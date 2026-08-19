#!/bin/sh
# Everything a buyer should be able to run from a clean clone. If any line here
# fails, the claim it supports is not backed and should not be in the README.
set -e
cd "$(dirname "$0")"
echo "== decide() speed =="
python3 -c "
import sys, time; sys.path.insert(0,'.')
import edgub
for _ in range(200): edgub.decide(7)
N=20000; t=time.perf_counter()
for i in range(N): edgub.decide(i&255)
print('   %.2f us per call' % ((time.perf_counter()-t)/N*1e6))"
echo "== self-test =="
python3 proof/selftest.py | tail -2
echo "== real-repo, acts as shipped vs corrected =="
echo "   (clones toolz, injects 10 hard bugs, runs the law)"
cd proof/realrepo && python3 inject_hard.py bugged >/dev/null && python3 spec.py hard | tail -3
