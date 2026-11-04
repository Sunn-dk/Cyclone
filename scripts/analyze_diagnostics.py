"""Align app run markers with scheduler, FrameTimeline and app-thread slices."""
import argparse, csv, io, json, subprocess, sys
from collections import Counter
from decimal import Decimal
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',required=True);p.add_argument('--processor',required=True)
    a=p.parse_args()
    for variant in ('A','D'):
        folder=Path(a.evidence)/('TRACE_'+variant)
        summary=json.loads((folder/'summary.json').read_text())
        pid=int(summary['processId']);run_id=int(summary['runId'])
        trace=folder/'diagnostic.perfetto-trace'
        def query(name,sql):
            path=folder/(name+'.sql');path.write_text(sql,encoding='utf-8')
            result=subprocess.run([sys.executable,a.processor,'query','-f',str(path),str(trace)],capture_output=True)
            (folder/(name+'.csv')).write_bytes(result.stdout)
            (folder/(name+'.log')).write_bytes(result.stderr)
            if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
            return list(csv.DictReader(io.StringIO(result.stdout.decode('utf-8-sig'))))
        process=f'(SELECT upid FROM process WHERE pid={pid} ORDER BY start_ts DESC LIMIT 1)'
        logs=query('run-markers',f"SELECT l.ts,l.msg FROM android_logs l JOIN thread t USING(utid) WHERE t.upid={process} AND l.tag='IMG_BENCH' ORDER BY l.ts")
        starts=[int(x['ts']) for x in logs if x['msg'].startswith(f'RUN_START id={run_id} ')]
        alignment={'method':'android_logs RUN_START/RUN_STOP'}
        if len(starts)==1:
            start=starts[0]
            stop=min(int(x['ts']) for x in logs if int(x['ts'])>start and x['msg'].startswith('RUN_STOP '))
        else:
            # Một số ROM không ghi android_logs; hiệu chỉnh epoch bằng clock_snapshot.
            clocks=query('clock-calibration','SELECT ts,clock_value FROM clock_snapshot WHERE clock_id=1 ORDER BY ts')
            assert clocks,'Missing CLOCK_REALTIME calibration'
            epoch=int(summary['startedAtEpochMs'])*1_000_000
            nearest=min(clocks,key=lambda x:abs(int(x['clock_value'])-epoch))
            offsets=[int(x['ts'])-int(x['clock_value']) for x in clocks]
            assert max(offsets)-min(offsets)<1_000_000,'Clock drift exceeds 1ms'
            start=epoch+int(nearest['ts'])-int(nearest['clock_value'])
            stop=start+int(summary['durationMs'])*1_000_000
            lines=[x.split(maxsplit=5) for x in (folder/'logcat.txt').read_text(encoding='utf-8').splitlines()]
            lines=[x for x in lines if len(x)==6 and x[1]==str(pid)]
            begins=[int(Decimal(x[0])*1_000_000_000) for x in lines if x[5].startswith(f'RUN_START id={run_id} ')]
            ends=[int(Decimal(x[0])*1_000_000_000) for x in lines if x[5].startswith('RUN_STOP ')]
            assert len(begins)==1 and len(ends)==1,'Missing independent logcat run markers'
            begin_delta=(begins[0]-epoch)/1e6
            end_delta=(ends[0]-epoch-summary['durationMs']*1_000_000)/1e6
            assert abs(begin_delta)<50 and abs(end_delta)<50,'Epoch window does not match logcat'
            alignment=dict(method='summary epoch via CLOCK_REALTIME clock_snapshot, checked against logcat',
                clock_offset_spread_us=(max(offsets)-min(offsets))/1000,
                log_start_delta_ms=begin_delta,log_stop_delta_ms=end_delta,
                precision_note='App epoch and duration are rounded to ms; boundaries are approximate at ms resolution.')
        assert abs((stop-start)/1e6-summary['durationMs'])<300,'Run window does not match app duration'
        frames=query('app-frames',f'SELECT id,ts,dur,name,jank_type FROM actual_frame_timeline_slice WHERE upid={process} AND ts>={start} AND ts<{stop} AND dur>0 ORDER BY ts')
        slices=query('thread-slices',f'SELECT s.id,s.ts,s.dur,s.depth,s.name,t.tid,t.name AS thread FROM slice s JOIN thread_track tt ON s.track_id=tt.id JOIN thread t USING(utid) WHERE t.upid={process} AND s.dur>0 AND s.ts<{stop} AND s.ts+s.dur>{start} ORDER BY s.ts')
        states=query('thread-states',f'SELECT s.ts,s.dur,s.state,t.tid,t.name AS thread FROM thread_state s JOIN thread t USING(utid) WHERE t.upid={process} AND s.dur>0 AND s.ts<{stop} AND s.ts+s.dur>{start}')
        losses=query('trace-loss',"SELECT name,value,severity FROM stats WHERE value>0 AND (severity='data_loss' OR name GLOB '*overrun*')")
        assert frames and slices and states,'Missing frames, atrace or scheduler data'
        assert not losses,('Trace data loss',losses)
        for row in slices+states+frames:
            row['ts']=int(row['ts']);row['dur']=int(row['dur'])
        def overlap(row,begin,end):
            return max(0,min(row['ts']+row['dur'],end)-max(row['ts'],begin))/1e6
        examples=[]
        for f in sorted(frames,key=lambda x:x['dur'],reverse=True)[:5]:
            begin,end=f['ts'],f['ts']+f['dur']
            related=[s for s in slices if overlap(s,begin,end)>0]
            top=sorted(related,key=lambda s:overlap(s,begin,end),reverse=True)[:15]
            main_states=Counter()
            for s in states:
                if int(s['tid'])==pid:main_states[s['state']]+=overlap(s,begin,end)
            examples.append(dict(frame_id=f['id'],start_ms=(begin-start)/1e6,duration_ms=f['dur']/1e6,
                jank_type=f['jank_type'],main_states_ms=dict(main_states),
                gc_overlaps=[dict(name=s['name'],thread=s['thread'],overlap_ms=overlap(s,begin,end)) for s in related if 'gc' in s['name'].lower() or 'suspendall' in s['name'].lower()],
                top_overlapping_slices=[dict(name=s['name'],thread=s['thread'],overlap_ms=overlap(s,begin,end)) for s in top]))
        result=dict(config=variant,pid=pid,run_id=run_id,window_start_ts=start,window_stop_ts=stop,
            duration_ms=(stop-start)/1e6,alignment=alignment,frame_count=len(frames),jank_types=dict(Counter(f['jank_type'] for f in frames)),
            thread_slice_count=len(slices),scheduler_state_count=len(states),trace_loss=losses,slow_frame_examples=examples,
            note='All timestamps share the Perfetto clock and the app RUN_START/RUN_STOP window. Overlapping GC can be concurrent; overlap alone does not prove a UI pause. Slice wall time is not CPU time. Profiled trials are excluded from the main comparison.')
        (folder/'diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:result[k] for k in ('config','duration_ms','frame_count','jank_types','scheduler_state_count')}),flush=True)


if __name__=='__main__':
    main()
