"""Check 3.2 detail sizing, saved gallery position and a long traversal on the named test device."""
import argparse, csv, json, re, time
from pathlib import Path
from urllib.parse import urlsplit
from run_suite import Runner, PKG
from run_regressions import ui, tap, bounds, save


def visible_names(nodes):
    recycler = next(n for n in nodes if n.get("resource-id") == PKG + ":id/recycler")
    box = bounds(recycler)
    return [(n["text"], n["bounds"]) for n in nodes
            if n.get("resource-id") == PKG + ":id/name" and box[1] <= bounds(n)[1] < box[3]]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("fixtures", "out", "serial", "adb"):
        p.add_argument("--" + name, required=True)
    a = p.parse_args()
    a.repeats = 1
    r = Runner(a)
    checks = {}
    try:
        r.run("saved_position_400", count=1000, position=400, cache="cold", restart=True, expected="network")
        before = visible_names(ui(r))
        assert before, "No visible names at position 400"
        pid_before = r.adbcall("shell", "pidof", PKG).strip()
        r.adbcall("shell", "input", "keyevent", 3)
        time.sleep(1)
        r.adbcall("shell", "am", "kill", PKG)
        time.sleep(1)
        checks["background_process_killed"] = not r.adbcall("shell", "pidof", PKG, check=False).strip()
        r.adbcall("shell", "am", "start", "-W", "-n", PKG + "/.MainActivity")
        time.sleep(2)
        after = visible_names(ui(r))
        checks["process_changed"] = r.adbcall("shell", "pidof", PKG).strip() != pid_before
        checks["process_death_restores_position"] = before == after
        save(r.out / "process-restoration.json", dict(before=before, after=after))

        # Rotation only on the dedicated emulator; restore its original policy.
        if a.serial.startswith("emulator-"):
            rotation = r.adbcall("shell", "wm", "user-rotation").strip()
            try:
                r.adbcall("shell", "wm", "user-rotation", "lock", "1")
                time.sleep(2)
                landscape = ui(r)
                checks["landscape_has_images"] = bool(visible_names(landscape))
                save(r.out / "landscape-ui.json", landscape)
                r.adbcall("shell", "wm", "user-rotation", "lock", "0")
                time.sleep(2)
                restored = visible_names(ui(r))
                # A different viewport can move a few cells; keep the original region.
                old_ids = {int(re.search(r"#(\d+)", n[0])[1]) for n in before}
                new_ids = {int(re.search(r"#(\d+)", n[0])[1]) for n in restored}
                checks["rotation_keeps_region"] = bool(old_ids & new_ids)
                save(r.out / "rotation-restoration.json", dict(before=before, after=restored, original_policy=rotation))
            finally:
                parts = rotation.split()
                r.adbcall("shell", "wm", "user-rotation", *parts)

        tap(r, "btnExperiment")
        tap(r, "btnMeasureStart", scroll=True)
        time.sleep(2)
        nodes = ui(r)
        selected = visible_names(nodes)[0][0]
        tap(r, selected)
        time.sleep(2)
        detail = ui(r)
        checks["detail_correct_name"] = any(n.get("text") == selected and n.get("resource-id") == PKG + ":id/name" for n in detail)
        save(r.out / "D-detail-ui.json", detail)
        r.adbcall("shell", "screencap", "-p", "/data/local/tmp/cyclone-v32-detail.png")
        r.adbcall("pull", "/data/local/tmp/cyclone-v32-detail.png", r.out / "D-detail.png")
        tap(r, "btnBack")
        tap(r, "btnExperiment")
        tap(r, "btnExport", scroll=True)
        files = r.adbcall("shell", "ls", "-t", f"/sdcard/Android/data/{PKG}/files/requests_*.csv").splitlines()
        target = r.out / "D-detail-requests.csv"
        r.adbcall("pull", files[0], target)
        with target.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        detail_rows = [x for x in rows if x["outcome"] == "OK" and max(map(int, urlsplit(x["url"]).path.split("/")[-2:])) == 1600]
        checks["D_detail_1600_success"] = bool(detail_rows)
        checks["D_does_not_fetch_raw3000"] = all(max(map(int, urlsplit(x["url"]).path.split("/")[-2:])) <= 1600 for x in rows)
        save(r.out / "lifecycle-assertions.json", checks)
        assert all(checks.values()), checks

        r.run("D_traverse_1000", count=1000, mode="traverse", cache="cold", restart=True,
              max_ms=90000, capture=True, expected="network")
        summary = json.loads((r.out / "D_traverse_1000/summary.json").read_text())
        with (r.out / "D_traverse_1000/requests.csv").open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        unique = {urlsplit(x["url"]).path.split("/")[2] for x in rows if "/seed/" in x["url"]}
        checks["traversal_more_than_100_ids"] = len(unique) > 100
        checks["traversal_reaches_last_item"] = int(summary["automation"]["traversalFurthestPosition"]) == 999
        checks["new_measurement_fields"] = summary["schemaVersion"] == 5 and bool(summary["artRuntimeDelta"]) and summary["layoutMeasureP90Ns"] >= 0
        checks["runtime_counters_nonnegative"] = all(v >= 0 for v in summary["artRuntimeDelta"].values())
        save(r.out / "traversal-coverage.json", dict(unique_requested_ids=len(unique), **summary["automation"]))
        save(r.out / "assertions.json", dict(**checks, all_passed=all(checks.values())))
        assert all(checks.values()), checks
        print(json.dumps(checks), flush=True)
    finally:
        r.close()


if __name__ == "__main__":
    main()
