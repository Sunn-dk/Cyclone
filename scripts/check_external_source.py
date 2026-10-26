"""Connectivity/UI smoke for the supported public Picsum source, outside controlled experiments."""
import argparse,json
from run_suite import Runner
p=argparse.ArgumentParser(description=__doc__);p.add_argument("--fixtures",required=True);p.add_argument("--out",required=True);p.add_argument("--serial",required=True);p.add_argument("--adb");a=p.parse_args();a.repeats=1
r=Runner(a)
try:
    conditions=json.loads((r.out/"conditions.json").read_text())
    conditions["method"]["controlled_performance"]=False
    conditions["method"]["note"]="Public Picsum connectivity only; Internet/CDN uncontrolled; exclude from A/D and format comparisons."
    (r.out/"conditions.json").write_text(json.dumps(conditions,ensure_ascii=False,indent=2),encoding="utf-8")
    r.run("Picsum_Internet_smoke",source="https://picsum.photos",cache="cold",restart=True,expected="network",max_ms=60000)
finally:r.close()
