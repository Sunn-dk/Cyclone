"""Summarize isolated pairs from real, individually retained trials."""
import argparse,csv,json,re,statistics
from pathlib import Path
from summarize_results import read_csv,write_csv,number,med
p=argparse.ArgumentParser(description=__doc__);p.add_argument("--evidence",required=True);p.add_argument("--out",required=True)
a=p.parse_args();ev=Path(a.evidence);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
rows=read_csv(ev/"all_trials.csv");assert len(rows)==24 and all(r["passed"]=="True" for r in rows)
groups={}
for row in rows:
    match=re.fullmatch(r"(cache_prime|cache_warm|decode_cold|thumbnail_cold)_r[1-3]_([ABCD])",row["name"])
    assert match,row["name"]
    groups.setdefault((match[1],match[2]),[]).append(row)
summary=[]
for (scenario,config),samples in sorted(groups.items()):
    assert len(samples)==3
    late=[number(s["frames_missing_deadline"])/number(s["frames_with_deadline"])*100 for s in samples if number(s["frames_with_deadline"])]
    summary.append(dict(scenario=scenario,config=config,n=3,viewport_ms=med(samples,"viewport_predraw_ms"),
        request_ms=med(samples,"median_request_ms"),decode_ms=med(samples,"median_decode_ms"),
        pss_mib=med(samples,"sampled_pss_peak_kib")/1024,cpu_ms=med(samples,"process_cpu_ms"),
        frame_p90_ms=med(samples,"frame_p90_ns")/1e6,deadline_miss_pct=statistics.median(late) if late else None,
        network_n=med(samples,"network_n"),disk_n=med(samples,"disk_n"),memory_n=med(samples,"memory_n")))
write_csv(out/"ablation.csv",summary);write_csv(out/"ablation_trials.csv",rows)
text="# Đo tách kỹ thuật trên máy ảo\n\nĐây là hồ sơ kỹ thuật, không phải chương báo cáo. n=3 là lựa chọn thực nghiệm. Không suy rộng ra Sony hoặc mạng Internet.\n\n"
text+="| Kịch bản | Cấu hình | n | Viewport ms | Request ms | Decode ms | PSS mẫu MiB | CPU ms | NETWORK/DISK/RAM |\n|---|---|---|---|---|---|---|---|---|\n"
def f(v):return "—" if v is None else f"{v:.2f}"
for s in summary:
    text+=f"| {s['scenario']} | {s['config']} | 3 | {f(s['viewport_ms'])} | {f(s['request_ms'])} | {f(s['decode_ms'])} | {f(s['pss_mib'])} | {f(s['cpu_ms'])} | {s['network_n']}/{s['disk_n']}/{s['memory_n']} |\n"
text+="\n- Cache: A/B đều tải ảnh gốc, giải mã gốc; khác policy cache. So warm sau prime lạnh riêng. B có thể đọc đĩa khi ảnh gốc vượt RAM cache; không mặc định mọi warm là RAM.\n- Downsampling: B/C cùng URL raw3000, cache lạnh, cùng chức năng; C giải mã theo ô.\n- Thumbnail: C/D cùng cache lạnh và giải mã theo ô; D dùng tài nguyên720 thay raw3000.\n- E thêm crossfade/preview/URL chi tiết1600: mới kiểm tra chức năng, chưa đo tách ảnh hưởng UX này.\n- Không trộn load với scroll, không lấy các cặp load này để kết luận số frame giật trong cuộn. Mỗi số là median từng lượt; xem CSV để thấy biến động.\n"
(out/"TACH_KY_THUAT.md").write_text(text,encoding="utf-8")
