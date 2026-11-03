"""Smoke debug on a dedicated emulator, including empty CSV and visible metrics."""
import argparse,json,time
from run_suite import Runner,PKG
from run_regressions import ui,tap,save
p=argparse.ArgumentParser(description=__doc__);p.add_argument("--fixtures",required=True);p.add_argument("--out",required=True);p.add_argument("--serial",required=True);p.add_argument("--adb");a=p.parse_args()
a.repeats=1;a.build_type="debug"
r=Runner(a);checks={}
r.adbcall("shell","am","force-stop",PKG)
r.adbcall("shell","am","start","-W","-n",PKG+"/.MainActivity")
time.sleep(1)
try:
    before=r.adbcall("shell","find",f"/sdcard/Android/data/{PKG}/files","-maxdepth","1","-name","requests_*.csv",check=False)
    tap(r,"btnExperiment");tap(r,"btnExport",scroll=True);time.sleep(.5)
    after=r.adbcall("shell","find",f"/sdcard/Android/data/{PKG}/files","-maxdepth","1","-name","requests_*.csv",check=False)
    checks["empty_csv_not_created"]=before==after
    save(r.out/"empty-export-ui.json",ui(r))
    r.run("debug_smoke",cache="cold",restart=False,expected="network")
    summary=json.loads((r.out/"debug_smoke/summary.json").read_text())
    checks["debug_build_confirmed"]=summary["buildType"]=="debug" and summary["versionName"]=="3.2"
    checks["successful_viewport_separate"]=summary["viewportSuccessfulPreDrawMs"] is not None
    tap(r,"btnExperiment");tap(r,"btnRefresh",scroll=True)
    tap(r,"tvStats",scroll=True)
    nodes=ui(r);save(r.out/"metrics-ui.json",nodes)
    stats=next(n["text"] for n in nodes if n.get("resource-id")==PKG+":id/tvStats")
    checks["cpu_visible"]="CPU toàn tiến trình" in stats
    checks["system_deadline_visible"]="Frame trễ hạn hệ thống" in stats
    checks["all_passed"]=all(checks.values())
    save(r.out/"assertions.json",checks);print(json.dumps(checks),flush=True)
    assert checks["all_passed"],checks
finally:r.close()
