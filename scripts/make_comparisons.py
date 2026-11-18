"""Builds labeled before/after/mask comparison images for each video."""
import os
import sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import pipeline as P


def label(img, text):
    """Adds a label strip above the image (does not overlay/occlude content)."""
    bar = np.zeros((50, img.shape[1], 3), np.uint8)
    cv2.putText(bar, text, (14, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    return np.vstack([bar, img])


def read_frame_exact(path, idx):
    """cv2's CAP_PROP_POS_FRAMES seek is not frame-exact on compressed
    video (keyframe-dependent), so decode sequentially from 0 instead."""
    cap = cv2.VideoCapture(path)
    frame = None
    for i in range(idx + 1):
        ok, frame = cap.read()
        if not ok:
            break
    cap.release()
    return frame


def read_frames_sequential(path, indices):
    wanted = set(indices)
    found = {}
    cap = cv2.VideoCapture(path)
    i = 0
    while i <= max(indices):
        ok, frame = cap.read()
        if not ok:
            break
        if i in wanted:
            found[i] = frame
        i += 1
    cap.release()
    return found


def main():
    for key, cfg in P.VIDEOS.items():
        stem = os.path.splitext(cfg["file"])[0]
        orig_path = os.path.join(P.ORIG_DIR, cfg["file"])
        manip_path = os.path.join(P.MANIP_DIR, f"{stem}_manip.mp4")
        mask_path = os.path.join(P.MASK_DIR, f"{stem}_mask.mkv")

        cap_o = cv2.VideoCapture(orig_path)
        n = int(cap_o.get(cv2.CAP_PROP_FRAME_COUNT))
        cap_o.release()
        mask_cap = cv2.VideoCapture(mask_path)
        active = []
        idx = 0
        while True:
            ok, f = mask_cap.read()
            if not ok:
                break
            if cv2.countNonZero(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)):
                active.append(idx)
            idx += 1
        mask_cap.release()
        if not active:
            raise RuntimeError(f"{key}: output mask is empty")
        picks = [active[0], active[len(active)//2], active[-1]]
        originals = read_frames_sequential(orig_path, picks)
        manipulated = read_frames_sequential(manip_path, picks)
        masks = read_frames_sequential(mask_path, picks)
        rows = []
        for pos, preview_idx in enumerate(picks, 1):
            fo = originals[preview_idx]
            fm = manipulated[preview_idx]
            fk = masks[preview_idx]
            h, w = fo.shape[:2]
            scale = 640 / w
            tw, th = int(w * scale), int(h * scale)
            fo_s = cv2.resize(fo, (tw, th))
            fm_s = cv2.resize(fm, (tw, th))
            fk_s = cv2.resize(fk, (tw, th))
            overlay = fo_s.copy()
            red = np.zeros_like(fo_s)
            red[:, :, 2] = 255
            m01 = (cv2.cvtColor(fk_s, cv2.COLOR_BGR2GRAY) > 127).astype(np.float32)[..., None]
            overlay = (overlay.astype(np.float32) * (1 - 0.4 * m01) + red.astype(np.float32) * (0.4 * m01)).astype(np.uint8)
            row1 = np.hstack([label(fo_s, f"ORIGINAL · {pos}/3 frame {preview_idx}"), label(fm_s, "MANIPULATED")])
            row2 = np.hstack([label(fk_s, "GROUND TRUTH MASK"), label(overlay, "CHANGED REGION OVERLAY")])
            rows.append(np.vstack([row1, row2]))
            outpath = os.path.join(P.COMP_DIR, f"{key}_{cfg['label']}_frame_{preview_idx:05d}.jpg")
            P.imwrite_u(outpath, rows[-1])
        P.imwrite_u(os.path.join(P.COMP_DIR, f"{key}_{cfg['label']}_comparison.jpg"), rows[len(rows)//2])
        print(f"[{key}] comparisons from mask frames {picks}: {P.COMP_DIR}")


if __name__ == "__main__":
    main()
