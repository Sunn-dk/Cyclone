"""Three interleaved format trials; same D/100/thumbnail workload and cold app caches."""
import argparse
from run_suite import Runner
p=argparse.ArgumentParser(description=__doc__);p.add_argument("--fixtures",required=True);p.add_argument("--out",default="results/formats");p.add_argument("--serial");p.add_argument("--adb");p.add_argument("--repeats",type=int,default=3);a=p.parse_args()
r=Runner(a)
try:
    for repeat in range(1,a.repeats+1):
        for fmt in (("JPEG","PNG","WEBP") if repeat%2 else ("WEBP","PNG","JPEG")):
            r.run(f"TC04_format_r{repeat}_{fmt}",fmt=fmt,cache="cold",restart=True,capture=False,expected="network")
finally:r.close()
