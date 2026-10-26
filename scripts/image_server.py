"""Prepare deterministic fixtures before serving. Install: pip install -r requirements.txt."""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qs
import argparse
import json
import math
import re
import time

RATIOS = [(2, 3), (1, 1), (3, 2), (3, 4), (4, 3)]
FORMATS = ("JPEG", "PNG", "WEBP")
MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def sizes(item):
    a, b = RATIOS[(item - 1) % 5]
    w, h = (3000, 3000 * b // a) if a >= b else (3000 * a // b, 3000)
    return [(w * edge // max(w, h), h * edge // max(w, h)) for edge in (720, 1600, 3000)]


def _prepare_item(args):
    from PIL import Image, ImageDraw
    root, item, formats, version = args
    root = Path(root)
    raw = sizes(item)[-1]
    with Image.new("RGB", raw, ((item * 31) % 190 + 30, (item * 57) % 190 + 30, (item * 73) % 190 + 30)) as image:
        draw = ImageDraw.Draw(image)
        for k in range(80):
            x = (item * 71 + k * 137) % raw[0]
            y = (item * 37 + k * 173) % raw[1]
            color = ((item + k * 19 + version * 23) % 256, (k * 43) % 256, (k * 67) % 256)
            draw.ellipse((x, y, x + 150, y + 150), fill=color)
        draw.text((30, 30), f"Cyclone item={item} version={version}", fill="white", font_size=48)
        for w, h in sizes(item):
            with image.resize((w, h)) as resized:
                for selected in formats:
                    target = root / f"item{item}" / f"{w}x{h}.{selected.lower()}"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    temporary = target.with_suffix(target.suffix + ".tmp")
                    resized.save(temporary, format=selected, **({"quality": 88} if selected != "PNG" else {}))
                    temporary.replace(target)


def prepare(root, count, fmt, version):
    from PIL import Image, ImageDraw
    root = Path(root)
    if not 1 <= count <= 1000 or not 1 <= version <= 999999 or fmt not in (*FORMATS, "ALL"):
        raise ValueError("Invalid fixture count, version or format")
    formats = FORMATS if fmt == "ALL" else (fmt,)
    tasks = [(str(root), item, formats, version) for item in range(1, count + 1)]
    if count >= 100:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=4) as pool:
            list(pool.map(_prepare_item, tasks, chunksize=5))
    else:
        for task in tasks: _prepare_item(task)
    metadata = {"count": count, "format": fmt, "formats": list(formats), "version": version}
    temporary = root / "manifest.json.tmp"
    temporary.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    temporary.replace(root / "manifest.json")
    import hashlib
    entries = []
    for item in range(1, count + 1):
        for w, h in sizes(item):
            for selected in formats:
                path = root / f"item{item}" / f"{w}x{h}.{selected.lower()}"
                entries.append({"item": item, "width": w, "height": h, "format": selected, "path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (root / "files.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"Prepared {count} images x 3 sizes x {len(formats)} formats; content version={version}")


def read_manifest(root):
    metadata = json.loads((Path(root) / "manifest.json").read_text(encoding="utf-8"))
    formats = metadata.get("formats", [metadata.get("format")])
    if not formats or any(fmt not in FORMATS for fmt in formats):
        raise ValueError("Manifest contains invalid formats")
    count, version = metadata.get("count"), metadata.get("version")
    if not isinstance(count, int) or not 1 <= count <= 1000:
        raise ValueError("Manifest count must be 1..1000")
    if not isinstance(version, int) or not 1 <= version <= 999999:
        raise ValueError("Manifest version must be 1..999999")
    return {"count": count, "version": version, "formats": formats}


def query_options(query, default_format, default_delay):
    values = parse_qs(query, keep_blank_values=True, strict_parsing=True, max_num_fields=8)
    if set(values) - {"format", "v", "delay_ms", "error"} or any(len(v) != 1 for v in values.values()):
        raise ValueError("Unknown or repeated query parameter")
    def value(key, default):
        return values.get(key, [default])[0]
    fmt = value("format", default_format)
    version = value("v", "1")
    error = value("error", "0")
    if fmt not in FORMATS or not re.fullmatch(r"[0-9]{1,6}", version) or not 1 <= int(version) <= 999999:
        raise ValueError("Invalid format or v")
    if error not in ("0", "1"):
        raise ValueError("error must be 0 or 1")
    delay = default_delay
    if "delay_ms" in values:
        raw_delay = value("delay_ms", "0")
        if not re.fullmatch(r"[0-9]{1,5}", raw_delay) or not 0 <= int(raw_delay) <= 60000:
            raise ValueError("delay_ms must be 0..60000")
        delay = int(raw_delay) / 1000.0
    return fmt, int(version), delay, error == "1"


def handler(root, delay=0, fmt="JPEG"):
    root = Path(root).resolve()
    if fmt == "ALL":
        fmt = "JPEG"
    metadata = read_manifest(root)
    if fmt not in metadata["formats"] or not math.isfinite(delay) or not 0 <= delay <= 60:
        raise ValueError("Default format not prepared or delay outside 0..60 seconds")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                self.respond()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def respond(self):
            parsed = urlsplit(self.path)
            try:
                selected, version, wait, error = query_options(parsed.query, fmt, delay)
            except ValueError as exc:
                self.send_error(400, str(exc))
                return
            if parsed.path == "/error" or re.fullmatch(r"/error/item[0-9]+", parsed.path):
                self.send_error(404, "Intentional TC06 error")
                return
            match = re.fullmatch(r"/seed/item([0-9]{1,4})/([0-9]{1,4})/([0-9]{1,4})", parsed.path)
            if not match:
                self.send_error(404, "Unknown image path")
                return
            item, w, h = map(int, match.groups())
            if not 1 <= item <= metadata["count"] or (w, h) not in sizes(item):
                self.send_error(404, "Item or dimensions not prepared")
                return
            if error and item % 10 == 0:
                self.send_error(404, "Intentional TC06 error")
                return
            path = root / f"item{item}" / f"{w}x{h}.{selected.lower()}"
            if selected not in metadata["formats"] or not path.is_file():
                self.send_error(404, "Format not prepared; run --prepare --format ALL")
                return
            if wait:
                time.sleep(wait)
            try:
                data = path.read_bytes()
            except OSError:
                self.send_error(404, "Fixture unavailable")
                return
            self.send_response(200)
            self.send_header("Content-Type", MIME[selected])
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-ImageOpt-Content-Version", str(metadata["version"]))
            self.send_header("X-ImageOpt-URL-Version", str(version))
            self.end_headers()
            self.wfile.write(data)
            print(f"SENT bytes={len(data)} format={selected} contentVersion={metadata['version']} path={self.path}", flush=True)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--format", choices=[*FORMATS, "ALL"], default="JPEG")
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--dir", type=Path, default=Path("image-fixtures"))
    parser.add_argument("--delay", type=float, default=0, help="Default delay in seconds; query delay_ms overrides it")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.count <= 1000:
        parser.error("count must be 1..1000")
    if not 1 <= args.version <= 999999:
        parser.error("version must be 1..999999")
    if not math.isfinite(args.delay) or not 0 <= args.delay <= 60:
        parser.error("delay must be 0..60 seconds")
    if not 1 <= args.port <= 65535:
        parser.error("port must be 1..65535")
    if args.prepare:
        prepare(args.dir, args.count, args.format, args.version)
        return
    try:
        selected_handler = handler(args.dir, args.delay, args.format)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(f"Prepare fixtures first and check options: {exc}")
    print(f"Serving prepared fixtures at 127.0.0.1:{args.port}; delay={args.delay}s. Stop server before regenerating fixtures.", flush=True)
    try:
        with ThreadingHTTPServer(("127.0.0.1", args.port), selected_handler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
