"""Verify prepared Cyclone files against their recorded hashes and dimensions."""
from pathlib import Path
import argparse,hashlib,json
from PIL import Image
def verify(root):
    root=Path(root);meta=json.loads((root/"manifest.json").read_text())
    entries=json.loads((root/"files.json").read_text())
    assert len(entries)==meta["count"]*3*len(meta["formats"])
    assert len({e["path"] for e in entries})==len(entries)
    for e in entries:
        p=root/e["path"]
        assert p.stat().st_size==e["bytes"],str(p)
        assert hashlib.sha256(p.read_bytes()).hexdigest()==e["sha256"],str(p)
        with Image.open(p) as image:
            assert image.size==(e["width"],e["height"]) and image.format==e["format"],str(p)
    subsets={}
    for count in (100,500,1000):
        if count<=meta["count"]:
            selected=[e for e in entries if e["item"]<=count]
            subsets[str(count)]={"item_ids":len({e["item"] for e in selected}),
                "unique_jpeg_raw_urls":len({f"/seed/item{e['item']}/{e['width']}/{e['height']}?format=JPEG&v=1&delay_ms=0" for e in selected if e["format"]=="JPEG" and max(e["width"],e["height"])==3000}),
                "unique_raw_jpeg_hashes":len({e["sha256"] for e in selected if e["format"]=="JPEG" and max(e["width"],e["height"])==3000}),
                "files":len(selected)}
    return {"passed":True,"manifest":meta,"files_verified":len(entries),"payload_bytes":sum(e["bytes"] for e in entries),"subsets":subsets,"index_sha256":hashlib.sha256((root/"files.json").read_bytes()).hexdigest()}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("root");p.add_argument("--out",default="dataset-verification.json");a=p.parse_args()
    result=verify(a.root);Path(a.out).write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps(result))
