"""Run the packaged acceptance suites sequentially on one explicit test device."""
import argparse,subprocess,sys,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ("serial","fixtures","updated-fixtures","out","benchmark-apk","probe-apk"):
    p.add_argument("--"+name,required=True)
p.add_argument("--debug-apk");p.add_argument("--adb",required=True);p.add_argument("--stage",choices=("all","benchmark"),default="all")
a=p.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
scripts=Path(__file__).resolve().parent
completed=[]
def call(label,args):
    print("START "+label,flush=True)
    with (out/(label+".log")).open("w",encoding="utf-8") as f:
        subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True)
    completed.append(label);(out/"completed.json").write_text(json.dumps(completed,indent=2))
    print("PASS "+label,flush=True)
def install(label,path):call(label,[a.adb,"-s",a.serial,"install","-r",path])
def suite(label,script,*extra):
    call(label,[sys.executable,scripts/script,"--serial",a.serial,"--adb",a.adb,"--fixtures",a.fixtures,"--out",out/label,*extra])
if a.stage=="all":
    if not a.debug_apk:p.error("--debug-apk required for all stages")
    install("install-debug",a.debug_apk);suite("debug","check_debug.py")
install("install-benchmark",a.benchmark_apk);install("install-probe",a.probe_apk)
suite("final-suite","run_suite.py","--suite","all","--repeats","3")
suite("regressions","run_regressions.py","--updated-fixtures",a.updated_fixtures)
suite("reload","run_reload.py","--repeats","3")
suite("formats","run_formats.py","--repeats","3")
suite("ablation","run_ablation.py","--repeats","3")
suite("probe","check_share_receiver.py")
suite("cpu-sampling","run_cpu_sampling.py")
