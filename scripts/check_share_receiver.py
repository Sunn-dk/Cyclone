"""Verify the real ACTION_SEND FileProvider URI using a separate local test app."""
import argparse,json,hashlib,time,re,xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote,urlparse
from run_suite import Runner,PKG
from run_regressions import tap,bounds,save

p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--fixtures",required=True);p.add_argument("--out",required=True);p.add_argument("--serial",required=True);p.add_argument("--adb")
a=p.parse_args();a.repeats=1
r=Runner(a)
try:
    r.run("share_session",cache="cold",restart=True,expected="network")
    tap(r,"btnExperiment");tap(r,"btnShare",scroll=True);time.sleep(1)
    for attempt in range(5):
        r.adbcall("shell","uiautomator","dump","/data/local/tmp/cyclone-share.xml")
        root=ET.fromstring(r.adbcall("shell","cat","/data/local/tmp/cyclone-share.xml"))
        matches=[n for n in root.iter("node") if n.get("text")=="Kiểm tra ZIP Cyclone"]
        if len(matches)==1:break
        header=next((dict(n.attrib) for n in root.iter("node") if n.get("resource-id")=="android:id/chooser_header"),None)
        assert header is not None,"Android chooser is not visible"
        b=bounds(header)
        # Sony mở bảng chia sẻ thu gọn; kéo tiêu đề lên để thấy app nhận ZIP.
        if b[1]>400:
            x=(b[0]+b[2])//2;start=(b[1]+b[3])//2;end=max(100,b[1]//4)
        else:
            listing=next(dict(n.attrib) for n in root.iter("node") if n.get("resource-id")=="android:id/resolver_list")
            b=bounds(listing);x=b[2]-10;start=int(b[1]+(b[3]-b[1])*.8);end=int(b[1]+(b[3]-b[1])*.3)
        r.adbcall("shell","input","swipe",x,start,x,end,650)
        time.sleep(.5)
    assert len(matches)==1,"Dedicated test receiver absent from Android chooser"
    parents={child:parent for parent in root.iter() for child in parent}
    target=matches[0]
    while True:
        box=bounds(dict(target.attrib))
        if len(box)==4 and box[2]>box[0] and box[3]>box[1] and target.get("clickable")=="true":break
        target=parents[target]
    save(r.out/"chooser-target.json",dict(label="Kiểm tra ZIP Cyclone",target=dict(target.attrib)))
    x1,y1,x2,y2=box;r.adbcall("shell","input","tap",(x1+x2)//2,(y1+y2)//2)
    time.sleep(1)
    # Some Android resolver variants require a one-time choice.
    r.adbcall("shell","uiautomator","dump","/data/local/tmp/cyclone-share.xml")
    second=ET.fromstring(r.adbcall("shell","cat","/data/local/tmp/cyclone-share.xml"))
    once=next((dict(n.attrib) for n in second.iter("node") if n.get("resource-id")=="android:id/button_once"),None)
    if once:
        x1,y1,x2,y2=bounds(once);r.adbcall("shell","input","tap",(x1+x2)//2,(y1+y2)//2);time.sleep(1)
    expected=json.loads((r.out/"share_session/summary.json").read_text())
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        raw=r.adbcall("shell","cat","/sdcard/Android/data/com.example.cycloneprobe/files/result.json",check=False)
        if raw:
            actual=json.loads(raw)
            if actual.get("summary",{}).get("automation",{}).get("label")==expected["automation"]["label"]:break
        time.sleep(.5)
    else:raise RuntimeError("Receiver did not finish reading this session ZIP")
    dest=r.out/"receiver-result.json"
    r.adbcall("pull","/sdcard/Android/data/com.example.cycloneprobe/files/result.json",str(dest))
    result=json.loads(dest.read_text())
    assert result["grant_flag"] and result["read_ok"],result
    assert result["summary"]["versionName"]=="3.2"
    expected=json.loads((r.out/"share_session/summary.json").read_text())
    assert result["summary"]["automation"]["label"]==expected["automation"]["label"],"Stale receiver result"
    uri_path=unquote(urlparse(result["uri"]).path)
    assert uri_path.startswith("/results/") and Path(uri_path).name.endswith(".zip")
    original=r.out/"shared-original.zip"
    r.adbcall("pull",f"/sdcard/Android/data/{PKG}/files/measurements/"+Path(uri_path).name,str(original))
    def uid(package):
        return int(re.search(r"uid:(\d+)",r.adbcall("shell","pm","list","packages","-U",package)).group(1))
    main_uid=uid(PKG);receiver_uid=uid("com.example.cycloneprobe")
    checks=dict(read_grant=True,separate_uid=main_uid!=receiver_uid,main_uid=main_uid,receiver_uid=receiver_uid,zip_read_ok=True,
        sha256_matches=hashlib.sha256(original.read_bytes()).hexdigest()==result["sha256"],
        version_3_2=True)
    assert checks["sha256_matches"] and checks["separate_uid"]
    save(r.out/"assertions.json",checks);print(json.dumps(checks),flush=True)
finally:r.close()
