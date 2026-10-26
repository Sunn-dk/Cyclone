"""Run controlled Cyclone trials. Only app test data and adb reverse port are changed."""
import argparse, csv, hashlib, io, json, os, re, shutil, subprocess, sys, time, zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

PKG="com.example.imageopt"
REMOTE=f"/sdcard/Android/data/{PKG}/files/automation"

class Runner:
    def __init__(self,args):
        self.args=args
        self.adb=args.adb or shutil.which("adb") or str(Path(os.environ.get("LOCALAPPDATA",""))/"Android/Sdk/platform-tools/adb.exe")
        listing=subprocess.check_output([self.adb,"devices"],text=True)
        devices=[l.split()[0] for l in listing.splitlines()[1:] if l.endswith("\tdevice")]
        self.serial=args.serial or (devices[0] if len(devices)==1 else None)
        if not self.serial: raise RuntimeError("Select exactly one device with --serial.")
        self.out=Path(args.out).resolve();self.out.mkdir(parents=True,exist_ok=True)
        self.prefix=datetime.now().strftime("%Y%m%d_%H%M%S")
        self.rows=[]
        self.server=None
        self.start_server(args.fixtures)
        self.adbcall("reverse","tcp:8000","tcp:8000")
        info={}
        for name,prop in [("model","ro.product.model"),("android","ro.build.version.release"),("api","ro.build.version.sdk")]:
            info[name]=self.adbcall("shell","getprop",prop).strip()
        info["serial"]=self.serial
        info["boot_id"]=self.adbcall("shell","cat","/proc/sys/kernel/random/boot_id",check=False).strip()
        info["screen"]=self.adbcall("shell","wm","size").strip()
        info["memory"]=self.adbcall("shell","cat","/proc/meminfo").splitlines()[0]
        info["app_package"]=self.adbcall("shell","dumpsys","package",PKG)
        info["battery_before"]=self.adbcall("shell","dumpsys","battery")
        info["fixture_manifest"]=json.loads((Path(args.fixtures)/"manifest.json").read_text())
        info["fixture_index_sha256"]=hashlib.sha256((Path(args.fixtures)/"files.json").read_bytes()).hexdigest() if (Path(args.fixtures)/"files.json").exists() else None
        info["method"]={"repeats":args.repeats,"load_min_ms":2000,"scroll_ms":8000,"scroll_viewports":6,"cache":"cold each performance run; app process restarted","video_during_measurement":False,"trace_during_matrix":False}
        (self.out/"conditions.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")

    def adbcall(self,*args,check=True,timeout=120):
        p=subprocess.run([self.adb,"-s",self.serial,*map(str,args)],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout)
        if check and p.returncode: raise RuntimeError(p.stdout+p.stderr)
        return p.stdout if p.returncode==0 else ""

    def start_server(self,fixtures):
        if self.server:
            self.server.terminate();self.server.wait(timeout=10)
            self.server_log.close()
        self.server_log=(self.out/"server.log").open("a",encoding="utf-8")
        self.server=subprocess.Popen([sys.executable,str(Path(__file__).with_name("image_server.py")),"--dir",str(Path(fixtures).resolve())],stdout=self.server_log,stderr=subprocess.STDOUT)
        time.sleep(.8)
        if self.server.poll() is not None: raise RuntimeError("Server exited; check server.log and port 8000.")

    def run(self,name,config="D",count=100,mode="load",cache="keep",restart=False,position=0,fmt="JPEG",delay=0,error=False,version=1,capture=True,expected=None,max_ms=45000,source="http://127.0.0.1:8000"):
        label=self.prefix+"_"+name
        folder=self.out/name;folder.mkdir(exist_ok=True)
        self.adbcall("shell","input","keyevent",224)
        self.adbcall("shell","wm","dismiss-keyguard",check=False)
        if restart: self.adbcall("shell","am","force-stop",PKG)
        self.adbcall("shell","dumpsys","gfxinfo",PKG,"reset",check=False)
        before=self.adbcall("shell","dumpsys","battery")
        command=["shell","am","start","-W","-n",PKG+"/.MainActivity","--ez","automation","true",
                 "--es","run_label",label,"--es","config",config,"--ei","count",str(count),
                 "--es","source",source,"--es","format",fmt,
                 "--es","mode",mode,"--es","cache",cache,"--ei","position",str(position),
                 "--ei","delay_ms",str(delay),"--ei","url_version",str(version),
                 "--ez","image_error",str(error).lower(),"--ez","capture",str(capture).lower(),
                 "--el","max_ms",str(max_ms),"--el","min_ms","2000"]
        result=self.adbcall(*command)
        (folder/"launch.txt").write_text(result,encoding="utf-8")
        if "Activity: android/com.android.internal.app.ChooserActivity" in result:
            raise RuntimeError("Close the Cyclone share chooser before starting another trial.")
        spec=dict(label=label,name=name,config=config,count=count,mode=mode,cache=cache,restart=restart,position=position,format=fmt,delay_ms=delay,error=error,url_version=version,capture=capture,expected=expected,max_ms=max_ms,source=source)
        (folder/"trial.json").write_text(json.dumps(spec,indent=2),encoding="utf-8")
        deadline=time.monotonic()+max_ms/1000+25
        done=None
        while time.monotonic()<deadline:
            raw=self.adbcall("shell","cat",f"{REMOTE}/{label}.done.json",check=False)
            if raw:
                done=json.loads(raw);break
            failure=self.adbcall("shell","cat",f"{REMOTE}/{label}.error.json",check=False)
            if failure:
                (folder/"error.json").write_text(failure)
                raise RuntimeError(name+": "+failure)
            time.sleep(.5)
        if not done:
            (folder/"logcat-timeout.txt").write_text(self.adbcall("logcat","-d","-s","AndroidRuntime:E","IMG_BENCH:I"),encoding="utf-8")
            raise RuntimeError(name+": no completed export (locked/background/crash). See trial folder.")
        self.adbcall("pull",f"{REMOTE}/{label}.zip",str(folder/"run.zip"))
        if done.get("screenshot"): self.adbcall("pull",f"{REMOTE}/{label}.png",str(folder/"app.png"))
        (folder/"done.json").write_text(json.dumps(done,ensure_ascii=False,indent=2),encoding="utf-8")
        with zipfile.ZipFile(folder/"run.zip") as z:
            assert z.testzip() is None
            summary=json.loads(z.read("summary.json"))
            requests=list(csv.DictReader(io.StringIO(z.read("requests.csv").decode("utf-8"))))
            for file in z.namelist(): (folder/file).write_bytes(z.read(file))
        assert summary["buildType"]==getattr(self.args,"build_type","benchmark"),"Unexpected APK build type."
        assert summary["versionName"]=="3.1"
        assert summary["automation"]["label"]==label
        assert int(summary["automation"]["uniqueRawUrls"])==count
        assert int(summary["automation"]["uniqueThumbUrls"])==count
        assert summary["count"]==count and summary["config"]==config
        counts=Counter(r["source"] for r in requests if r["outcome"]=="OK")
        errors=[r for r in requests if r["outcome"]=="ERROR"]
        checks={"metadata":True,"zip_readable":True}
        if mode=="scroll":
            checks["actual_scroll_progress"]=int(summary["automation"].get("scrollEndMaxPosition",-1))>int(summary["automation"].get("scrollStartMaxPosition",999999)) and int(summary["automation"].get("scrollDistancePx",0))>0
        if expected=="network": checks["network_success"]=counts["NETWORK"]>0 and not errors
        elif expected=="memory": checks["memory_hit"]=counts["MEMORY_CACHE"]>0 and counts["NETWORK"]==0 and not errors
        elif expected=="cache": checks["cache_hit"]=counts["DISK"]+counts["MEMORY_CACHE"]>0 and counts["NETWORK"]==0 and not errors
        elif expected=="disk": checks["disk_hit"]=counts["DISK"]>0 and counts["NETWORK"]==0 and not errors
        elif expected=="offline_error": checks["offline_fallback"]=len(errors)>0 and counts["NETWORK"]==0
        elif expected=="404": checks["http_404"]=any("404" in r["error"] for r in errors)
        elif expected=="timeout": checks["real_timeout"]=any("timeout" in r["error"].lower() or "timed out" in r["error"].lower() for r in errors)
        elif expected=="cancel": checks["cancelled_recycled_requests"]=any(r["outcome"]=="CANCEL" for r in requests)
        elif expected=="slow": checks["slow_network"]=any(r["source"]=="NETWORK" and int(r["fetchMs"])>=1500 for r in requests if r["outcome"]=="OK") and not errors
        checks["pass"]=all(checks.values())
        (folder/"assertions.json").write_text(json.dumps(checks,indent=2))
        epoch=summary["startedAtEpochMs"]/1000
        lines=self.adbcall("logcat","-d","-v","epoch","-s","IMG_BENCH:I").splitlines()
        filtered=[]
        for line in lines:
            try: stamp=float(line.split()[0])
            except (ValueError,IndexError): continue
            if epoch-1 <= stamp <= epoch+summary["durationMs"]/1000+3: filtered.append(line)
        (folder/"logcat.txt").write_text("\n".join(filtered),encoding="utf-8")
        (folder/"gfxinfo.txt").write_text(self.adbcall("shell","dumpsys","gfxinfo",PKG),encoding="utf-8")
        (folder/"battery-before.txt").write_text(before)
        (folder/"battery-after.txt").write_text(self.adbcall("shell","dumpsys","battery"))
        def pct(values,f):
            import math
            return sorted(values)[max(0,math.ceil(len(values)*f)-1)] if values else None
        ok=[r for r in requests if r["outcome"]=="OK"]
        row=dict(name=name,config=config,count=count,mode=mode,cache=cache,restarted=restart,
                 duration_ms=summary["durationMs"],viewport_predraw_ms=summary["viewportTerminalPreDrawMs"],
                 viewport_errors=summary["viewportErrorCount"],success_n=len(ok),error_n=len(errors),
                 cancel_n=sum(r["outcome"]=="CANCEL" for r in requests),incomplete_n=summary["requestsIncompleteAtSnapshot"],
                 network_n=counts["NETWORK"],disk_n=counts["DISK"],memory_n=counts["MEMORY_CACHE"],
                 median_request_ms=pct([int(r["totalMs"]) for r in ok if int(r["totalMs"])>=0],.5),
                 p90_request_ms=pct([int(r["totalMs"]) for r in ok if int(r["totalMs"])>=0],.9),
                 median_decode_ms=pct([int(r["decodeMs"]) for r in ok if int(r["decodeMs"])>=0],.5),
                 sampled_pss_peak_kib=summary["sampledPssPeakKb"],pss_samples=summary["pssSampleCount"],
                 frame_p90_ns=summary["frameP90Ns"],frames_over_period=summary["framesOverDisplayPeriod"],
                 eligible_frames=summary["eligibleFrames"],frames_with_deadline=summary.get("framesWithSystemDeadline"),frames_missing_deadline=summary.get("framesMissingSystemDeadline"),process_id=summary.get("processId"),process_cpu_ms=summary["processCpuMs"],
                 passed=checks["pass"],evidence=name+"/run.zip")
        self.rows.append(row)
        with (self.out/"all_trials.csv").open("w",encoding="utf-8-sig",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader();writer.writerows(self.rows)
        print(json.dumps(row,ensure_ascii=False),flush=True)
        time.sleep(.25)
        return row

    def functional(self):
        self.run("TC01_D_cold",cache="cold",restart=True,expected="network")
        self.run("TC02_D_RAM",expected="memory")
        self.run("TC02_D_disk",cache="memory",expected="disk")
        self.run("TC10_D_restart",restart=True,expected="disk")
        self.adbcall("reverse","--remove","tcp:8000")
        try:
            self.run("TC05_RAM_offline",expected="memory")
            self.run("TC05_disk_offline",cache="memory",expected="disk")
            self.run("TC05_uncached_offline",position=80,expected="offline_error")
            self.run("TC09_clear_offline",cache="cold",expected="offline_error")
        finally: self.adbcall("reverse","tcp:8000","tcp:8000")
        self.run("TC09_recover_network",cache="cold",expected="network")
        self.run("TC06_404",cache="cold",error=True,position=8,expected="404")
        self.run("TC06_slow_2s",cache="cold",delay=2000,expected="slow")
        self.run("TC06_timeout",cache="cold",delay=35000,expected="timeout",max_ms=60000)
        for fmt in ("PNG","WEBP"):
            self.run("TC04_format_"+fmt,cache="cold",fmt=fmt,expected="network")

    def matrix(self):
        for count in (100,500,1000):
            for mode in ("load","scroll"):
                for repeat in range(1,self.args.repeats+1):
                    order=("A","D") if repeat%2 else ("D","A")
                    for config in order:
                        self.run(f"TC08_{count}_{mode}_r{repeat}_{config}",config=config,count=count,mode=mode,cache="cold",restart=True,capture=False,expected="network")
                        time.sleep(1)
    def traces(self):
        for config in ("A","D"):
            remote=f"/data/misc/perfetto-traces/cyclone_{self.prefix}_{config}.perfetto-trace"
            trace=subprocess.Popen([self.adb,"-s",self.serial,"shell","perfetto","-o",remote,"-t","15s","-b","32mb","-a",PKG,"sched","freq","idle","gfx","view","binder_driver","am","wm"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            time.sleep(1)
            self.run("CPU_trace_"+config,config=config,mode="scroll",cache="cold",restart=True,capture=False,expected="network")
            stdout,stderr=trace.communicate(timeout=30)
            (self.out/f"CPU_trace_{config}/perfetto-command.txt").write_bytes(stdout+stderr)
            if trace.returncode: raise RuntimeError("Perfetto failed: "+stderr.decode(errors="replace"))
            self.adbcall("pull",remote,str(self.out/f"CPU_trace_{config}/cpu.perfetto-trace"))
    def close(self):
        self.adbcall("reverse","--remove","tcp:8000",check=False)
        if self.server:
            self.server.terminate();self.server.wait(timeout=10);self.server_log.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb");parser.add_argument("--serial")
    parser.add_argument("--fixtures",required=True)
    parser.add_argument("--out",default="results/v3")
    parser.add_argument("--suite",choices=["smoke","functional","matrix","traces","all"],default="all")
    parser.add_argument("--repeats",type=int,default=3)
    args=parser.parse_args()
    if not 1<=args.repeats<=10: parser.error("repeats must be 1..10; 3 is proposed, not specified by assignment")
    runner=None
    try:
        runner=Runner(args)
        if args.suite=="smoke": runner.run("smoke",cache="cold",restart=True,expected="network")
        if args.suite in ("functional","all"): runner.functional()
        if args.suite in ("matrix","all"): runner.matrix()
        if args.suite in ("traces","all"): runner.traces()
    finally:
        if runner: runner.close()
if __name__=="__main__": main()
