"""Dataset requirement verification for the billboard/signage forgery set."""
import os
import sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import pipeline as P

ROWS = []


def probe(path):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        cap.release()
        return dict(fps=0.0, w=0, h=0, n=0, dur=0.0)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return dict(fps=fps, w=w, h=h, n=n, dur=n / fps if fps else 0)


def scan_mask(path):
    cap = cv2.VideoCapture(path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    bad = 0
    nonzero_any = False
    active = []
    idx = 0
    area_sum = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        vals = np.unique(f)
        if not set(vals.tolist()).issubset({0, 255}):
            bad += 1
        area = int(np.count_nonzero(f))
        area_sum += area
        if area:
            nonzero_any = True
            active.append(idx)
        idx += 1
    cap.release()
    return bad == 0 and idx == n, nonzero_any, active, area_sum, idx


def main():
    all_ok = True
    for key, cfg in P.VIDEOS.items():
        stem = os.path.splitext(cfg["file"])[0]
        orig_path = os.path.join(P.ORIG_DIR, cfg["file"])
        manip_path = os.path.join(P.MANIP_DIR, f"{stem}_manip.mp4")
        mask_path = os.path.join(P.MASK_DIR, f"{stem}_mask.mkv")

        o = probe(orig_path)
        m = probe(manip_path)
        k = probe(mask_path)

        bin_ok, has_nonzero, active_frames, area_sum, decoded_n = scan_mask(mask_path)
        mask_start = active_frames[0] if active_frames else 0
        mask_end = active_frames[-1] + 1 if active_frames else 0
        manip_dur = len(active_frames) / o["fps"] if o["fps"] else 0

        checks = []
        checks.append(("resolution >= 512x512", min(o["w"], o["h"]) >= 512))
        checks.append(("duration >= 15s", o["dur"] >= 15.0))
        checks.append(("manip duration >= 5s", manip_dur >= 5.0))
        checks.append(("manip matches orig resolution", (m["w"], m["h"]) == (o["w"], o["h"])))
        checks.append(("mask matches orig resolution", (k["w"], k["h"]) == (o["w"], o["h"])))
        checks.append(("manip frame count == orig", m["n"] == o["n"]))
        checks.append(("mask frame count == orig", k["n"] == o["n"] and decoded_n == o["n"]))
        checks.append(("manip fps == orig", abs(m["fps"] - o["fps"]) < 0.01))
        checks.append(("mask fps == orig", abs(k["fps"] - o["fps"]) < 0.01))

        mask_n = decoded_n
        checks.append(("mask is binary (0/255 only)", bin_ok))
        checks.append(("mask has nonzero (manipulated) region", has_nonzero))

        print(f"\n=== {key}: {cfg['file']} ===")
        print(f"  orig:  {o['w']}x{o['h']} @ {o['fps']:.3f}fps, {o['n']}f, {o['dur']:.2f}s")
        print(f"  manip: {m['w']}x{m['h']} @ {m['fps']:.3f}fps, {m['n']}f, {m['dur']:.2f}s")
        print(f"  mask:  {k['w']}x{k['h']} @ {k['fps']:.3f}fps, {k['n']}f, {k['dur']:.2f}s")
        print(f"  mask active window: frames [{mask_start},{mask_end}), {len(active_frames)} frames = {manip_dur:.2f}s; mean changed pixels/frame={area_sum/max(mask_n,1):.0f}")
        for name, ok in checks:
            print(f"  [{'OK' if ok else 'FAIL'}] {name}")
            if not ok:
                all_ok = False
        ROWS.append((key, cfg["file"], o, m, k, manip_dur, all(c[1] for c in checks)))

    print("\n" + "=" * 50)
    print("ALL CHECKS PASSED" if all_ok else "SOME CHECKS FAILED")
    return all_ok


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
