"""Summarize real exported trials. No simulated or placeholder performance values."""
import argparse,csv,json,re,statistics
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
def read_csv(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def write_csv(p,rows):
    if not rows:return
    with Path(p).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def number(x):return float(x) if x not in (None,"","None") else None
def med(rows,key):
    values=[number(r.get(key)) for r in rows];values=[v for v in values if v is not None]
    return statistics.median(values) if values else None
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--evidence",required=True);p.add_argument("--dataset",required=True);p.add_argument("--out",required=True);p.add_argument("--updated-dataset");a=p.parse_args()
    ev=Path(a.evidence);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    index=json.loads((Path(a.dataset)/"files.json").read_text())
    by_file={(e["item"],e["width"],e["height"],e["format"]):e["bytes"] for e in index}
    updated_root=Path(a.updated_dataset) if a.updated_dataset else Path(a.dataset).parent/"updated-v2"
    updated_index=json.loads((updated_root/"files.json").read_text()) if (updated_root/"files.json").exists() else []
    by_updated={(e["item"],e["width"],e["height"],e["format"]):e["bytes"] for e in updated_index}
    all_rows=[];groups={}
    for group in ("final-suite","regressions","reload","formats"):
        for row in read_csv(ev/group/"all_trials.csv"):
            trial=ev/group/row["name"]
            requests=read_csv(trial/"requests.csv");payload=0
            for request in requests:
                if request["outcome"]!="OK" or request["source"]!="NETWORK":continue
                uri=urlsplit(request["url"]);match=re.fullmatch(r"/seed/item(\d+)/(\d+)/(\d+)",uri.path)
                if match:
                    lookup=by_updated if group=="regressions" and row["name"]=="TC11_new_URL_v2" else by_file
                    key=(*map(int,match.groups()),parse_qs(uri.query).get("format",["JPEG"])[0])
                    if key not in lookup: raise ValueError("Missing dataset index for payload: "+str(key))
                    payload+=lookup[key]
            row["response_file_payload_bytes"]=payload
            row["evidence_group"]=group
            row["evidence"]=group+"/"+row["evidence"]
            all_rows.append(row)
            match=re.fullmatch(r"TC08_(100|500|1000)_(load|scroll)_r[1-3]_(A|D)",row["name"])
            if match:groups.setdefault((match[2],int(match[1]),match[3]),[]).append(row)
            match=re.fullmatch(r"TC08_reload_r[1-3]_(A|D)",row["name"])
            if match:groups.setdefault(("reload",100,match[1]),[]).append(row)
    assert len(all_rows)==81,len(all_rows)
    assert all(r["passed"]=="True" for r in all_rows)
    write_csv(out/"all_trials.csv",all_rows)
    summary=[]
    for (scenario,count,config),rows in sorted(groups.items()):
        assert len(rows)==3,(scenario,count,config,len(rows))
        late=[number(r["frames_missing_deadline"])/number(r["frames_with_deadline"])*100 for r in rows if number(r["frames_with_deadline"])]
        summary.append(dict(scenario=scenario,count=count,config=config,n=len(rows),
            viewport_ms=med(rows,"viewport_predraw_ms"),median_request_ms=med(rows,"median_request_ms"),
            median_decode_ms=med(rows,"median_decode_ms"),sampled_peak_pss_mib=med(rows,"sampled_pss_peak_kib")/1024,
            process_cpu_ms=med(rows,"process_cpu_ms"),frame_p90_ms=med(rows,"frame_p90_ns")/1e6,
            median_deadline_miss_pct=statistics.median(late) if late else None,
            median_response_file_payload_bytes=med(rows,"response_file_payload_bytes")))
    write_csv(out/"comparison.csv",summary)
    formats=[]
    for fmt in ("JPEG","PNG","WEBP"):
        rows=[r for r in all_rows if r["evidence_group"]=="formats" and r["name"].endswith("_"+fmt)]
        assert len(rows)==3
        formats.append(dict(format=fmt,n=3,median_request_ms=med(rows,"median_request_ms"),median_decode_ms=med(rows,"median_decode_ms"),
            sampled_peak_pss_mib=med(rows,"sampled_pss_peak_kib")/1024,process_cpu_ms=med(rows,"process_cpu_ms"),
            median_response_file_payload_bytes=med(rows,"response_file_payload_bytes")))
    write_csv(out/"formats.csv",formats)
    def display(v):return "—" if v is None else f"{v:.2f}" if isinstance(v,float) else str(v)
    def table(rows):
        keys=list(rows[0])
        return "| "+" | ".join(keys)+" |\n|"+"---|"*len(keys)+"\n"+"\n".join("| "+" | ".join(display(r[k]) for k in keys)+" |" for r in rows)
    text="# Tổng hợp kỹ thuật từ dữ liệu thật\n\nKhông phải chương báo cáo tiểu luận. Mỗi ô là median của 3 giá trị từng lượt tương ứng; PSS là median các max lấy mẫu, không phải max liên tục. Frame p90 là median của p90 từng lượt. Mẫu riêng ở all_trials.csv và ZIP gốc.\n\n"+table(summary)+"\n\n## Định dạng — D/100/cold\n\n"+table(formats)+"\n\nPayload là tổng dung lượng tệp tương ứng với request NETWORK thành công, tra files.json; không phải byte TCP/TLS/HTTP thực trên dây. Nhiệt/pin có lưu từng lượt; không khóa xungCPU. Không suy cải thiện riêng từng kỹ thuật từ A/D. Mốc viewport gồm ảnh lỗi nên đọc viewport_errors; các lượt chính này không có lỗi. Trace, stress cancel và prime không trộn vào bảng A/D chính.\n\nKhông gộp số đo Sony v3 vào ma trận máy ảo v3.1. Các lượt thử công cụ trước bản APK cuối được giữ riêng và không dùng để so sánh hiệu năng.\n"
    (out/"KET_QUA_KY_THUAT.md").write_text(text,encoding="utf-8")
    try:
        import matplotlib
    except ImportError:
        print("CSV/Markdown saved. Optional chart: install scripts/requirements-analysis.txt.")
        return
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(2,2,figsize=(10,7),layout="constrained")
    panels=[("load","viewport_predraw_ms",1,"Initial viewport terminal pre-draw (ms)"),
            ("scroll","sampled_pss_peak_kib",1/1024,"Sampled process PSS peak (MiB)"),
            ("scroll","process_cpu_ms",1,"Process CPU time in scroll (ms)"),
            ("scroll",None,1,"Frames missing system deadline (%)")]
    for ax,(scenario,key,scale,title) in zip(axes.flat,panels):
        for offset,config,color in [(-.18,"A","#666666"),(.18,"D","#c70039")]:
            values=[]
            for i,count in enumerate((100,500,1000)):
                rows=groups[(scenario,count,config)]
                v=[number(r[key])*scale if key else number(r["frames_missing_deadline"])/number(r["frames_with_deadline"])*100 for r in rows]
                values.append(statistics.median(v))
                ax.scatter([i+offset]*len(v),v,color=color,s=15,zorder=4,edgecolor="white",linewidth=.4)
            ax.bar(np.arange(3)+offset,values,width=.34,color=color,alpha=.65,label=config)
        ax.set_title(title,fontsize=10);ax.set_xticks(range(3),["100","500","1000"]);ax.set_xlabel("Dataset item count");ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True)
    axes.flat[0].legend(title="Config")
    model=json.loads((ev/"final-suite/conditions.json").read_text(encoding="utf-8"))["model"]
    fig.suptitle(f"Cyclone / {model} / benchmark / local JPEG / n=3\nBars: median, dots: individual trials; load and scroll are separate",fontsize=11)
    fig.savefig(out/"comparison.png",dpi=170);plt.close(fig)
    print(json.dumps({"trial_rows":len(all_rows),"comparison_groups":len(summary),"format_groups":len(formats),"all_assertions_passed":True}))
if __name__=="__main__":main()
