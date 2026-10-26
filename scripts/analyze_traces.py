"""Parse CPU scheduling for each trace's actual app PID using official Perfetto wrapper."""
import argparse,csv,json,hashlib,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',required=True);p.add_argument('--processor',required=True);a=p.parse_args()
failed=[]
for config in ('A','D'):
    folder=Path(a.evidence)/'final-suite'/('CPU_trace_'+config)
    pid=json.loads((folder/'summary.json').read_text())['processId']
    sql=f"""SELECT p.pid,p.name AS process,t.name AS thread,ROUND(SUM(s.dur)/1e6,3) AS running_cpu_ms,COUNT(*) AS scheduling_slices
FROM sched s JOIN thread t ON s.utid=t.utid JOIN process p ON t.upid=p.upid
WHERE p.pid={int(pid)} AND s.dur>0
GROUP BY p.pid,p.name,t.utid,t.name ORDER BY running_cpu_ms DESC;"""
    (folder/'cpu_sched.sql').write_text(sql,encoding='utf-8')
    proc=subprocess.run([sys.executable,a.processor,'query','-f',str(folder/'cpu_sched.sql'),str(folder/'cpu.perfetto-trace')],capture_output=True)
    (folder/'cpu_sched.csv').write_bytes(proc.stdout);(folder/'processor.log').write_bytes(proc.stderr)
    assert proc.returncode==0,proc.stderr
    with (folder/'cpu_sched.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    result=dict(pid=pid,thread_rows=len(rows),scheduler_cpu_ms=sum(float(r['running_cpu_ms']) for r in rows),
        trace_bytes=(folder/'cpu.perfetto-trace').stat().st_size,
        sha256=hashlib.sha256((folder/'cpu.perfetto-trace').read_bytes()).hexdigest(),window='Whole 15-second trace, not finite app measurement window')
    (folder/'trace-validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(config=config,**result)),flush=True)
    if not rows or result['scheduler_cpu_ms']<=0:failed.append(config)
assert not failed, 'Missing scheduler data for '+str(failed)+'; use run_cpu_sampling.py or a supported system trace device.'
