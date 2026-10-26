"""Capture real ART CPU method samples on a dedicated device, separate from performance matrix."""
import argparse,csv,json,struct,time,hashlib
from collections import defaultdict
from pathlib import Path
from run_suite import Runner,PKG

def inspect_trace(path,out):
    data=Path(path).read_bytes()
    end=data.find(b"*end\n")
    assert end>=0,"No ART text header"
    text=data[:end+5].decode("utf-8",errors="replace")
    (out/"art-header.txt").write_text(text,encoding="utf-8")
    binary=data[end+5:]
    assert binary[:4]==b"SLOW","No ART binary magic"
    version,offset=struct.unpack_from("<HH",binary,4)
    assert version in (2,3),("Unsupported ART trace version",version)
    record_size=struct.unpack_from("<H",binary,16)[0] if version==3 else 10
    assert record_size in (10,14)
    assert (len(binary)-offset)%record_size==0,"Incomplete binary record"
    threads={};section="";methods=0
    for line in text.splitlines():
        if line.startswith("*"):section=line;continue
        if section=="*threads" and "\t" in line:
            tid,name=line.split("\t",1);threads[int(tid)]=name
        if section=="*methods" and line.startswith("0x"):methods+=1
    groups=defaultdict(list)
    for pos in range(offset,len(binary),record_size):
        tid=struct.unpack_from("<H",binary,pos)[0]
        # v3 dual clock stores per-thread CPU then wall time in microseconds.
        cpu_us=struct.unpack_from("<I",binary,pos+6)[0]
        groups[tid].append(cpu_us)
    rows=[dict(tid=tid,thread=threads.get(tid,""),records=len(values),
          observed_cpu_delta_ms=(max(values)-min(values))/1000 if "clock=dual" in text else None)
          for tid,values in groups.items()]
    with (out/"cpu_threads.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["tid","thread","records","observed_cpu_delta_ms"]);w.writeheader();w.writerows(rows)
    result=dict(format="ART method sampling",version=version,record_size=record_size,
        records=sum(len(v) for v in groups.values()),threads=len(groups),methods=methods,
        clock="dual" if "clock=dual" in text else "single",
        overflow="data-file-overflow=true" in text,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
        note="5ms sampling; method transitions are sampled, not exact invocation counts. CPU deltas cover observed samples only; not whole-process CPU total.")
    assert result["records"]>0 and methods>0 and not result["overflow"],result
    (out/"trace-validation.json").write_text(json.dumps(result,indent=2))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--fixtures",required=True);p.add_argument("--out",required=True)
    p.add_argument("--serial",required=True);p.add_argument("--adb");a=p.parse_args();a.repeats=1
    r=Runner(a)
    try:
        for config in ("A","D"):
            r.run("CPU_setup_"+config,config=config,cache="cold",restart=True,capture=False,expected="network")
            pid_before=r.adbcall("shell","pidof",PKG).strip()
            remote=f"/data/local/tmp/cyclone_{r.prefix}_{config}.trace"
            started=r.adbcall("shell","am","profile","start","--sampling","5000",PKG,remote)
            assert "Error" not in started and "Exception" not in started,started
            try:
                r.run("CPU_sample_"+config,config=config,mode="scroll",cache="cold",restart=False,capture=False,expected="network")
            finally:
                stopped=r.adbcall("shell","am","profile","stop",PKG,check=False)
            folder=r.out/("CPU_sample_"+config)
            assert r.adbcall("shell","pidof",PKG).strip()==pid_before,"App process changed during profiling"
            # am profile stop is asynchronous: wait for a nonempty, stable file.
            previous=-1;stable=0;deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                raw=r.adbcall("shell","stat","-c","%s",remote,check=False).strip()
                size=int(raw) if raw.isdigit() else 0
                stable=stable+1 if size>32 and size==previous else 0
                if stable>=2:break
                previous=size;time.sleep(.75)
            else:raise RuntimeError("ART profile did not flush")
            local=folder/"cpu.trace";r.adbcall("pull",remote,str(local))
            result=inspect_trace(local,folder)
            result.update(pid=int(pid_before),sampling_interval_us=5000,profile_start_output=started,profile_stop_output=stopped,
                scope="Includes cache preparation, finite scroll measurement and export; separate from unprofiled matrix.")
            (folder/"trace-validation.json").write_text(json.dumps(result,indent=2))
            print(json.dumps(dict(config=config,**result)),flush=True)
    finally:r.close()
if __name__=="__main__":main()
