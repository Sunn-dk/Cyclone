"""Isolated cache, downsampling and thumbnail pairs; do not merge with A/D matrix."""
import argparse
from run_suite import Runner

p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--fixtures",required=True);p.add_argument("--out",required=True)
p.add_argument("--serial",required=True);p.add_argument("--adb");p.add_argument("--repeats",type=int,default=3)
a=p.parse_args()
if not 1<=a.repeats<=10:p.error("repeats must be 1..10")
r=Runner(a)
try:
    for repeat in range(1,a.repeats+1):
        for config in (("A","B") if repeat%2 else ("B","A")):
            r.run(f"cache_prime_r{repeat}_{config}",config=config,cache="cold",restart=True,capture=False,expected="network")
            r.run(f"cache_warm_r{repeat}_{config}",config=config,capture=False,expected="cache" if config=="B" else "network")
        for pair,configs in (("decode",("B","C")),("thumbnail",("C","D"))):
            for config in (configs if repeat%2 else configs[::-1]):
                r.run(f"{pair}_cold_r{repeat}_{config}",config=config,cache="cold",restart=True,capture=False,expected="network")
finally:r.close()
