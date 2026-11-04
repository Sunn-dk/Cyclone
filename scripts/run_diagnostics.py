"""Capture scheduler, FrameTimeline, GC and app run markers outside the A/D matrix."""
import argparse, json, shutil, subprocess, time
from pathlib import Path
from run_suite import Runner, PKG


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('serial','fixtures','out'):
        p.add_argument('--'+name,required=True)
    p.add_argument('--adb')
    a=p.parse_args();a.repeats=1
    r=Runner(a)
    try:
        config=Path(__file__).with_name('cpu_trace.pbtxt')
        shutil.copyfile(config,r.out/'cpu_trace.pbtxt')
        for variant in ('A','D'):
            r.run('setup_'+variant,config=variant,count=1000,cache='cold',restart=True,capture=False,expected='network')
            pid=r.adbcall('shell','pidof',PKG).strip()
            remote=f'/data/misc/perfetto-traces/cyclone_diag_{r.prefix}_{variant}.perfetto-trace'
            proc=subprocess.Popen([r.adb,'-s',r.serial,'shell','perfetto','--txt','-c','-','-o',remote],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            # Truyền stdin vì Perfetto trên máy thật không đọc được /data/local/tmp.
            proc.stdin.write(config.read_bytes());proc.stdin.close();proc.stdin=None
            try:
                time.sleep(1)
                assert proc.poll() is None,'Perfetto exited before the trial; inspect its log'
                r.run('TRACE_'+variant,config=variant,count=1000,mode='scroll',cache='cold',capture=False,expected='network')
            finally:
                stdout,stderr=proc.communicate(timeout=35)
                (r.out/('perfetto-'+variant+'.log')).write_bytes(stdout+stderr)
            assert proc.returncode==0,(stdout,stderr)
            assert r.adbcall('shell','pidof',PKG).strip()==pid,'Process changed during trace'
            folder=r.out/('TRACE_'+variant)
            r.adbcall('pull',remote,folder/'diagnostic.perfetto-trace')
            assert (folder/'diagnostic.perfetto-trace').stat().st_size>0
            (folder/'capture.json').write_text(json.dumps(dict(pid=int(pid),config=variant,controlled_matrix=False,
                note='Use IMG_BENCH RUN_START/RUN_STOP markers to restrict analysis to the same session. Trace adds overhead; do not merge with the unprofiled matrix.'),indent=2))
    finally:
        r.close()


if __name__=='__main__':
    main()
