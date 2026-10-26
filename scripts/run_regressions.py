"""Extra UI/cache/version regressions. Run after run_suite.py, not during performance trials."""
import argparse,csv,hashlib,json,re,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from run_suite import Runner,PKG

def ui(r):
    r.adbcall("shell","uiautomator","dump","/data/local/tmp/cyclone-ui.xml")
    raw=r.adbcall("shell","cat","/data/local/tmp/cyclone-ui.xml")
    return [dict(n.attrib) for n in ET.fromstring(raw).iter("node") if n.get("package")==PKG]
def bounds(n):
    return list(map(int,re.findall(r"\d+",n.get("bounds",""))))
def locate(nodes,key):
    for n in nodes:
        b=bounds(n)
        if (n.get("resource-id")==PKG+":id/"+key or n.get("text")==key) and len(b)==4 and b[2]>b[0] and b[3]>b[1]:
            return n,b
    return None
def tap(r,key,scroll=False):
    for direction in ((1,-1) if scroll else (1,)):
        for attempt in range(10 if scroll else 1):
            nodes=ui(r)
            found=locate(nodes,key)
            if found and (not scroll or found[1][3]-found[1][1]>=60):
                n,b=found
                r.adbcall("shell","input","tap",(b[0]+b[2])//2,(b[1]+b[3])//2)
                return
            containers=[n for n in nodes if n.get("scrollable")=="true"]
            candidate=containers[0] if containers else next(n for n in nodes if n.get("resource-id")==PKG+":id/content")
            box=bounds(candidate);x=(box[0]+box[2])//2
            low=int(box[1]+(box[3]-box[1])*.78);high=int(box[1]+(box[3]-box[1])*.40)
            if key=="btnRefresh" and locate(nodes,"tvStats"):direction=-1
            start,end=(low,high) if direction==1 else (high,low)
            r.adbcall("shell","input","swipe",x,start,x,end,650)
    raise RuntimeError("Control not visible: "+key)
def save(path,value): Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--fixtures",required=True);p.add_argument("--updated-fixtures",required=True);p.add_argument("--out",default="results/regressions");p.add_argument("--serial");p.add_argument("--adb");a=p.parse_args()
    a.repeats=1;r=Runner(a);checks={}
    try:
        r.run("B_original_cache",config="B",cache="cold",restart=True,expected="network")
        r.run("C_downsample_raw",config="C",cache="cold",restart=True,expected="network")
        r.run("TC03_cancel_pressure",mode="scroll",cache="cold",restart=True,delay=2000,expected="cancel")
        r.run("TC03_scroll_visual",count=1000,mode="scroll",cache="cold",restart=True,expected="network")
        before=ui(r);names=[n for n in before if n.get("resource-id")==PKG+":id/name" and bounds(n)[1]>800]
        selected=names[0]["text"];tap(r,selected);time.sleep(1)
        detail=ui(r);checks["detail_correct_id"]=locate(detail,"name")[0]["text"]==selected
        save(r.out/"detail-ui.json",detail)
        tap(r,"btnBack");time.sleep(.7)
        after=ui(r)
        before_names=[(n["text"],n["bounds"]) for n in before if n.get("resource-id")==PKG+":id/name"]
        after_names=[(n["text"],n["bounds"]) for n in after if n.get("resource-id")==PKG+":id/name"]
        checks["back_restores_scroll"]=before_names==after_names
        save(r.out/"back-position.json",dict(before=before_names,after=after_names))
        tap(r,"btnExperiment");time.sleep(.3)
        tap(r,"btnClearMemory",scroll=True);time.sleep(.7)
        tap(r,"btnMeasureStart",scroll=True);time.sleep(2)
        tap(r,"btnExperiment");time.sleep(.3)
        tap(r,"btnExport",scroll=True);time.sleep(1)
        files=r.adbcall("shell","ls","-t",f"/sdcard/Android/data/{PKG}/files/requests_*.csv").splitlines()
        target=r.out/"manual-export.csv";r.adbcall("pull",files[0],str(target))
        rows=list(csv.DictReader(target.open(encoding="utf-8")))
        checks["manual_clear_ram_then_disk"]=any(x["source"]=="DISK" for x in rows) and all(x["source"]!="NETWORK" for x in rows)
        checks["manual_csv_export"]=bool(rows)
        tap(r,"btnShare",scroll=True);time.sleep(.7)
        focus=r.adbcall("shell","dumpsys","activity","activities")
        selected_lines=[l for l in focus.splitlines() if "mResumedActivity" in l]
        checks["share_chooser_opened"]=any("ChooserActivity" in l or "ResolverActivity" in l for l in selected_lines)
        save(r.out/"share-chooser.json",selected_lines)
        chooser_focus=[]
        for attempt in range(3):
            focus=r.adbcall("shell","dumpsys","activity","activities")
            active=[line for line in focus.splitlines() if "mResumedActivity" in line]
            chooser_focus.append(active)
            if not any("ChooserActivity" in line or "ResolverActivity" in line for line in active):break
            r.adbcall("shell","input","keyevent",4);time.sleep(.5)
        save(r.out/"chooser-dismiss.json",chooser_focus)
        focus=r.adbcall("shell","dumpsys","activity","activities")
        assert not any("ChooserActivity" in line or "ResolverActivity" in line for line in focus.splitlines() if "mResumedActivity" in line),"Share chooser still active"
        r.run("E_polish",config="E",cache="cold",restart=True,expected="network")
        tap(r,"name");time.sleep(1);save(r.out/"E-detail-ui.json",ui(r))
        tap(r,"btnBack");time.sleep(.5)
        r.run("TC11_content_v1",cache="cold",restart=True,expected="network")
        r.start_server(a.updated_fixtures)
        r.run("TC11_old_URL_cached",expected="memory")
        r.run("TC11_new_URL_v2",version=2,expected="network")
        from urllib.request import urlopen
        url="http://127.0.0.1:8000/seed/item1/480/720?format=JPEG&v=2&delay_ms=0"
        response=urlopen(url);payload=response.read()
        old=(Path(a.fixtures)/"item1/480x720.jpeg").read_bytes()
        new=(Path(a.updated_fixtures)/"item1/480x720.jpeg").read_bytes()
        checks["server_content_changed"]=old!=new and payload==new and response.headers["X-ImageOpt-Content-Version"]=="2"
        checks["all_assertions"]=all(checks.values())
        save(r.out/"regression-assertions.json",checks)
        print(json.dumps(checks),flush=True)
        assert checks["all_assertions"],checks
    finally: r.close()
if __name__=="__main__": main()
