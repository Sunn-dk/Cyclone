"""Repeated reload trials, kept separate from cold-load/scroll matrix."""
import argparse
from run_suite import Runner
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--fixtures",required=True);p.add_argument("--out",default="results/reload");p.add_argument("--serial");p.add_argument("--adb");p.add_argument("--repeats",type=int,default=3);a=p.parse_args()
    r=Runner(a)
    try:
        for repeat in range(1,a.repeats+1):
            for config in (("A","D") if repeat%2 else ("D","A")):
                r.run(f"prime_reload_r{repeat}_{config}",config=config,cache="cold",restart=True,capture=False,expected="network")
                r.run(f"TC08_reload_r{repeat}_{config}",config=config,capture=False,expected="memory" if config=="D" else "network")
    finally: r.close()
if __name__=="__main__": main()
