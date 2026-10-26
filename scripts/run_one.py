"""Run a declared baseline/optimized configuration once."""
import argparse,json
from pathlib import Path
from run_suite import Runner
p=argparse.ArgumentParser(description=__doc__);p.add_argument("--config",required=True);p.add_argument("--fixtures",required=True);p.add_argument("--out",required=True);p.add_argument("--serial");p.add_argument("--adb");a=p.parse_args()
a.repeats=1
spec=json.loads(Path(a.config).read_text())
if spec["source"]!="http://127.0.0.1:8000": raise ValueError("This controlled runner expects the loopback fixture server.")
r=Runner(a)
try:
    r.run(Path(a.config).stem,config=spec["config"],count=spec["count"],mode=spec["mode"],cache=spec["cache"],restart=True,fmt=spec["format"],version=spec["url_version"],max_ms=spec["max_ms"],expected="network")
finally:r.close()
