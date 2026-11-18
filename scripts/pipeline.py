"""
Video Forgery (Billboard / Text Signage) Dataset Generator
============================================================
Üniversite projesi: "Video Forgery Involving Billboard and/or Text Signage
Manipulation" için orijinal / manipüle edilmiş / ground-truth maske video
üçlüsünü üretir.

Kullanım:
    python pipeline.py --video v1 --test-frame      # tek kare önizleme
    python pipeline.py --video v1                   # tüm videoyu işle
    python pipeline.py --video all                  # 5 videonun tamamı
"""
import argparse
import os
import subprocess
import sys

import cv2
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG_DIR = os.path.join(BASE, "originals")
MANIP_DIR = os.path.join(BASE, "manipulated")
MASK_DIR = os.path.join(BASE, "masks")
COMP_DIR = os.path.join(BASE, "comparisons")

import imageio_ffmpeg
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

FONT = cv2.FONT_HERSHEY_DUPLEX
FONT_BOLD = cv2.FONT_HERSHEY_TRIPLEX


def imwrite_u(path, img):
    """cv2.imwrite fails silently on Windows for non-ASCII paths; work around it."""
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise RuntimeError(f"imencode failed for {path}")
    with open(path, "wb") as f:
        f.write(buf.tobytes())


# ---------------------------------------------------------------------------
# Per-video design templates: each returns (overlay_bgr uint8 HxWx3,
# overlay_alpha float32 HxW in [0,1]) for the "yeni yazı / logo" layer drawn
# in canonical (fronto-parallel, perspective-normalized) coordinates, plus an
# "old content" mask strategy used before inpainting.
# ---------------------------------------------------------------------------

def design_v1(W, H):
    """Büfe tabelası: 'CAN BÜFE' yazısı + içecek logosu (coca-cola yerine)."""
    overlay = np.zeros((H, W, 3), np.uint8)
    alpha = np.zeros((H, W), np.float32)

    txt_layer = np.zeros((H, W, 3), np.uint8)
    cv2.putText(txt_layer, "CAN BUFE", (int(W*0.03), int(H*0.64)), FONT_BOLD,
                H/65.0, (235, 242, 248), max(2, int(H/24)), cv2.LINE_AA)
    txt_mask = (txt_layer.sum(axis=2) > 0).astype(np.float32)
    overlay[txt_mask > 0] = (255, 255, 255)
    alpha = np.maximum(alpha, txt_mask)

    cx, cy, r = int(W*0.75), int(H*0.49), int(H*0.43)
    logo = np.zeros((H, W, 3), np.uint8)
    logo_a = np.zeros((H, W), np.float32)
    cv2.circle(logo, (cx, cy), r, (32, 35, 190), -1, cv2.LINE_AA)
    cv2.circle(logo_a, (cx, cy), r, 1.0, -1, cv2.LINE_AA)
    cv2.circle(logo, (cx, cy), r, (255, 255, 255), max(2, r//18), cv2.LINE_AA)
    cv2.putText(logo, "Fizz", (cx - int(r*0.72), cy + int(r*0.25)), cv2.FONT_HERSHEY_SCRIPT_COMPLEX,
                r/43.0, (250, 248, 238), max(2, r//16), cv2.LINE_AA)
    cv2.putText(logo, "FIZZ", (cx - int(r*0.38), cy + int(r*0.58)), FONT_BOLD,
                r/160.0, (240, 220, 180), max(1, r//38), cv2.LINE_AA)
    logo_a = np.maximum(logo_a, (logo.sum(axis=2) > 0).astype(np.float32))

    out_overlay = overlay.copy()
    out_alpha = alpha.copy()
    sel = logo_a > 0
    out_overlay[sel] = logo[sel]
    out_alpha = np.maximum(out_alpha, logo_a)
    return out_overlay, out_alpha


def design_v2(W, H):
    """LIDL mavi kare üzerindeki sarı oval logo -> farklı marka 'NOVA'."""
    overlay = np.zeros((H, W, 3), np.uint8)
    alpha = np.zeros((H, W), np.float32)
    cx, cy = int(W*0.5), int(H*0.50)
    rx, ry = int(W*0.48), int(H*0.48)
    cv2.ellipse(overlay, (cx, cy), (rx, ry), 0, 0, 360, (0, 128, 255), -1, cv2.LINE_AA)
    cv2.ellipse(alpha_mask := np.zeros((H, W), np.float32), (cx, cy), (rx, ry), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    alpha = np.maximum(alpha, alpha_mask)
    cv2.ellipse(overlay, (cx, cy), (rx, ry), 0, 0, 360, (255, 255, 255), max(3, W//40), cv2.LINE_AA)
    cv2.putText(overlay, "NOVA", (int(W*0.10), int(H*0.62)), FONT_BOLD,
                W/145.0, (20, 20, 170), max(2, W//18), cv2.LINE_AA)
    return overlay, alpha


def design_v3(W, H):
    """Üst sarı bant 'NHAT LINH' -> 'THANH TAM'; alt kırmızı bant 'BIA HA NOI' -> 'BIA SAO MAI'."""
    overlay = np.zeros((H, W, 3), np.uint8)
    # Rebuild the cropped two-tone fascia, including the old crest and the
    # full NHAT LINH word, so no source lettering can peek through.
    split = int(W*0.19)
    for y in range(H):
        shade = int(5 * (1.0 - y/max(H-1, 1)))
        overlay[y, :split] = (52+shade, 68+shade, 82+shade)
        overlay[y, split:] = (26+shade, 54+shade, 92+shade)
    alpha = np.ones((H, W), np.float32)
    t1 = np.zeros((H, W, 3), np.uint8)
    cv2.putText(t1, "THANH TAM", (int(W*0.43), int(H*0.70)), FONT_BOLD,
                H/65.0, (24, 24, 112), max(2, int(H/25)), cv2.LINE_AA)
    m1 = (t1.sum(axis=2) > 0)
    overlay[m1] = (20, 20, 150)
    alpha[m1] = 1.0

    t2 = np.zeros((H, W, 3), np.uint8)
    cv2.putText(t2, "BIA SAO MAI", (int(W*0.015), int(H*0.82)), FONT,
                H/106.0, (22, 27, 46), max(1, int(H/36)), cv2.LINE_AA)
    m2 = (t2.sum(axis=2) > 0)
    overlay[m2] = (255, 255, 230)
    alpha[m2] = 1.0
    return overlay, alpha


def design_v4(W, H):
    """Rebuild the FOSTERS sign face as a teal panel with a neon PARKERS tube."""
    overlay = np.zeros((H, W, 3), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    shade = (7.0 * (1.0 - yy/max(H-1, 1)) - 3.0 * xx/max(W-1, 1))
    overlay[:, :, 0] = np.clip(100 + shade, 0, 255)
    overlay[:, :, 1] = np.clip(135 + shade, 0, 255)
    overlay[:, :, 2] = np.clip(75 + shade, 0, 255)
    alpha = np.ones((H, W), np.float32)
    glow = np.zeros((H, W, 3), np.uint8)
    text = "PARKERS"
    unit_w = cv2.getTextSize(text, FONT, 1.0, 2)[0][0]
    scale = min(H/38.0, (W*0.86)/unit_w)
    baseline = int(H*0.68)
    core_thickness = max(1, int(scale*0.32))
    cv2.putText(glow, text, (int(W*0.07), baseline), FONT,
                scale, (22, 25, 230), max(3, int(scale*1.25)), cv2.LINE_AA)
    glow = cv2.GaussianBlur(glow, (0, 0), H/22.0)
    gv = glow.max(axis=2)
    gm = gv > 2
    ga = np.clip(gv.astype(np.float32) / 235.0, 0, 0.50)
    overlay = (overlay.astype(np.float32)*(1-ga[..., None]) + glow.astype(np.float32)*ga[..., None]).astype(np.uint8)
    core = np.zeros((H, W, 3), np.uint8)
    cv2.putText(core, text, (int(W*0.07), baseline), FONT,
                scale, (105, 115, 255), core_thickness, cv2.LINE_AA)
    cm = core.sum(axis=2) > 0
    overlay[cm] = core[cm]
    return overlay, alpha


def design_v5(W, H):
    """Piccadilly LED pano: tam opak yeni reklam ('VIVA / Live Without Limits')."""
    overlay = np.zeros((H, W, 3), np.uint8)
    overlay[:] = (112, 56, 18)
    cv2.putText(overlay, "VIVA", (int(W*0.08), int(H*0.42)), FONT_BOLD,
                W/160.0, (255, 255, 255), max(3, int(H/22)), cv2.LINE_AA)
    cv2.putText(overlay, "Live Without Limits", (int(W*0.08), int(H*0.62)), FONT,
                W/420.0, (255, 255, 255), max(2, int(H/60)), cv2.LINE_AA)
    cv2.putText(overlay, "Cholo", (int(W*0.55), int(H*0.92)), cv2.FONT_HERSHEY_SCRIPT_COMPLEX,
                W/260.0, (255, 255, 255), max(2, int(H/55)), cv2.LINE_AA)
    alpha = np.ones((H, W), np.float32)
    return overlay, alpha


def fosters_text_mask(front_bgr, thresh=6):
    """Red/orange neon letters occupy most of this canonical rect, so a
    majority-background assumption (global median) fails. Instead select by
    hue: red/orange text (and its diffuse glow halo, which is dimmer but
    still R > G) has R notably higher than G, while the teal panel has
    G >= R. The halo fades out gradually rather than having a hard edge, so
    we use a low threshold plus heavy dilation to fully swallow it -- any
    over-masked background is harmless since inpainting reconstructs it
    cleanly from the surrounding teal anyway."""
    hsv = cv2.cvtColor(front_bgr, cv2.COLOR_BGR2HSV)
    b, g, r = cv2.split(front_bgr.astype(np.int16))
    # Capture saturated red/orange tubes and their low-saturation glow; use
    # local contrast against the teal sign face to catch dim tube segments.
    sat = hsv[:, :, 1]
    hue = hsv[:, :, 0]
    red_hue = ((hue <= 18) | (hue >= 165)) & (sat > 22)
    mask = (((r - g) > thresh) | red_hue).astype(np.uint8) * 255
    k = np.ones((7, 7), np.uint8)
    mask = cv2.dilate(mask, k, iterations=7)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=4)
    return mask


def lidl_manual_mask(W, H):
    m = np.zeros((H, W), np.float32)
    cv2.ellipse(m, (int(W*0.5), int(H*0.48)), (int(W*0.47), int(H*0.46)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    return m


# ---------------------------------------------------------------------------
# Configuration per video
# ---------------------------------------------------------------------------

VIDEOS = {
    "v1": dict(
        file="13644866_3840_2160_25fps.mp4",
        quad=[(1550, 450), (2510, 450), (2510, 685), (1550, 685)],
        track=True, mode="inpaint", design=design_v1, canon=(960, 235),
        label="buffe_kiosk",
    ),
    "v2": dict(
        file="17195622_3840_2160_60fps.mp4",
        quad=[(1365, 935), (1700, 935), (1700, 1290), (1365, 1290)],
        track=False, mode="inpaint_manual", design=design_v2, canon=(335, 355),
        label="lidl_store",
        manual_mask=lidl_manual_mask,
    ),
    "v3": dict(
        file="3783548-hd_1920_1080_25fps.mp4",
        quad=[(260, -30), (1510, -30), (1510, 116), (260, 116)],
        track=False, mode="direct", design=design_v3, canon=(1250, 146),
        label="nhatlinh_storefront",
        # Camera tilts up during frames ~250-300 revealing the sign; the quad
        # above was measured on the stable framing that holds from frame 320
        # to the end (~7.8s, > the 5s minimum). Outside this range the sign
        # is only partially in view, so those frames are left pristine.
        active=(320, 515),
        preview_frame=463,  # unoccluded by passing traffic, unlike the window midpoint
    ),
    "v4": dict(
        file="4606777-uhd_3840_2160_24fps.mp4",
        # Broad face rectangle extends over every FOSTERS glyph and its glow.
        # Corners measured on frame 0 (the tracker reference), not on a later
        # zoomed frame. The front face is the plane containing all neon tubes.
        quad=[(1865, 420), (2495, 320), (2435, 615), (1860, 650)],
        track=True, mode="direct", design=design_v4, canon=(630, 245),
        label="fosters_neon",
    ),
    "v5": dict(
        file="5086597-uhd_3840_2160_30fps.mp4",
        quad=[(2060, 488), (2636, 408), (2632, 948), (2057, 966)],
        track=False, mode="direct", design=design_v5, canon=(570, 435),
        label="piccadilly_led",
    ),
}


# ---------------------------------------------------------------------------
# Core geometry / compositing helpers
# ---------------------------------------------------------------------------

def quad_to_dst(W, H):
    return np.float32([[0, 0], [W, 0], [W, H], [0, H]])


def _global_median_mask(front_bgr, thresh):
    pixels = front_bgr.reshape(-1, 3).astype(np.float32)
    bg = np.median(pixels, axis=0)
    diff = np.abs(front_bgr.astype(np.float32) - bg)
    d = diff.max(axis=2)
    mask = (d > thresh).astype(np.uint8) * 255
    k = np.ones((3, 3), np.uint8)
    mask = cv2.dilate(mask, k, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    return mask


def make_text_mask_adaptive(front_bgr, thresh=45, bands=None):
    """Global-median background-distance mask. `bands` is an optional list of
    (y0, y1) row ranges, each treated with its own local background color
    estimate (needed when a sign has multiple differently-colored zones)."""
    if not bands:
        return _global_median_mask(front_bgr, thresh)
    H, W = front_bgr.shape[:2]
    mask = np.zeros((H, W), np.uint8)
    for y0, y1 in bands:
        mask[y0:y1] = _global_median_mask(front_bgr[y0:y1], thresh)
    return mask


def composite_frame(frame, quad_pts, cfg, design_layer):
    """Returns (manipulated_frame, quad_mask_uint8[0/255]) for one frame."""
    h, w = frame.shape[:2]
    W, H = cfg["canon"]
    src = np.float32(quad_pts)
    dst = quad_to_dst(W, H)
    M = cv2.getPerspectiveTransform(src, dst)
    Minv = cv2.getPerspectiveTransform(dst, src)

    overlay_bgr, overlay_alpha = design_layer

    if cfg["mode"] == "direct":
        new_front = overlay_bgr
    else:
        # Warp only the sign's source bounding box, avoiding full-frame
        # perspective resampling at 4K for every frame.
        pad = 3
        x0 = max(0, int(np.floor(src[:, 0].min())) - pad)
        y0 = max(0, int(np.floor(src[:, 1].min())) - pad)
        x1 = min(w, int(np.ceil(src[:, 0].max())) + pad)
        y1 = min(h, int(np.ceil(src[:, 1].max())) + pad)
        local_src = src - np.float32([x0, y0])
        M = cv2.getPerspectiveTransform(local_src, dst)
        front = cv2.warpPerspective(frame[y0:y1, x0:x1], M, (W, H), flags=cv2.INTER_LINEAR)
        if cfg["mode"] == "inpaint_manual":
            old_mask = (cfg["manual_mask"](W, H) * 255).astype(np.uint8)
        elif cfg.get("mask_fn"):
            old_mask = cfg["mask_fn"](front)
        else:
            old_mask = make_text_mask_adaptive(front, bands=cfg.get("bands"))
        inpainted = cv2.inpaint(front, old_mask, 5, cv2.INPAINT_TELEA)
        a = overlay_alpha[..., None]
        new_front = (inpainted.astype(np.float32) * (1 - a) + overlay_bgr.astype(np.float32) * a).astype(np.uint8)

    # Composite within the same local bounds; retain a 4 px feather margin.
    if cfg["mode"] == "direct":
        x0, y0 = max(0, int(src[:, 0].min()) - 4), max(0, int(src[:, 1].min()) - 4)
        x1, y1 = min(w, int(src[:, 0].max()) + 5), min(h, int(src[:, 1].max()) + 5)
        local_src = src - np.float32([x0, y0])
        Minv_local = cv2.getPerspectiveTransform(dst, local_src)
    else:
        Minv_local = cv2.getPerspectiveTransform(dst, local_src)
    warped_back = cv2.warpPerspective(new_front, Minv_local, (x1-x0, y1-y0), flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    local_poly = np.int32(src - np.float32([x0, y0]))
    local_mask = np.zeros((y1-y0, x1-x0), np.uint8)
    cv2.fillPoly(local_mask, [local_poly], 255)
    soft = cv2.GaussianBlur(local_mask, (0, 0), 1.2).astype(np.float32) / 255.0
    roi = frame[y0:y1, x0:x1]
    changed = np.max(np.abs(warped_back.astype(np.int16) - roi.astype(np.int16)), axis=2) > 1
    mask = ((soft > 0.005) & changed).astype(np.uint8) * 255
    out_roi = (roi.astype(np.float32) * (1 - soft[..., None]) + warped_back.astype(np.float32) * soft[..., None]).astype(np.uint8)
    # Return the rendered ROI and its location. The writer can splice it into
    # the original full frame and encode only the localized binary mask.
    return out_roi, mask, (x0, y0, x1, y1)


# ---------------------------------------------------------------------------
# Feature-based homography tracking of the quad across frames (forward from
# frame 0), used for videos with camera motion (v1, v4).
# ---------------------------------------------------------------------------

def _roi_mask_from_quad(shape, quad, pad):
    """Polygon mask following the quad's own rotated shape (scaled outward
    from its centroid), NOT its axis-aligned bounding box -- a bbox would
    include corner regions of the (possibly non-planar) background, whose
    motion can differ from the quad's own plane under camera translation
    (parallax) and would corrupt the homography estimate."""
    c = quad.mean(axis=0)
    poly = c + (quad - c) * (1.0 + pad)
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.int32(poly)], 255)
    return m


class QuadTracker:
    """Registers the quad in every frame directly against the reference
    (frame-0) ORB descriptors -- not a frame-to-frame chain -- so small
    per-step errors cannot accumulate into long-range drift. A rigid
    object (the sign itself, not the surrounding wall) is tracked by
    restricting feature search to a tight region around the quad, which
    also avoids motion-parallax mismatch between the sign plane and the
    background wall during camera translation."""

    def __init__(self, ref_gray, quad0, search_pad=0.18):
        self.quad0 = np.float32(quad0)
        self.search_pad = search_pad
        self.orb = cv2.ORB_create(nfeatures=3000, scaleFactor=1.15, nlevels=12)
        ref_mask = _roi_mask_from_quad(ref_gray.shape, self.quad0, pad=0.15)
        self.kp0, self.des0 = self.orb.detectAndCompute(ref_gray, ref_mask)
        self.pts0 = np.float32([kp.pt for kp in self.kp0])
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.cur_quad = self.quad0.copy()

    def update(self, gray, debug=False):
        mask = _roi_mask_from_quad(gray.shape, self.cur_quad, pad=self.search_pad)
        kp, des = self.orb.detectAndCompute(gray, mask)
        n_kp = 0 if des is None else len(des)
        n_good = 0
        n_inl = 0
        if des is not None and len(des) >= 8 and self.des0 is not None:
            matches = self.matcher.knnMatch(self.des0, des, k=2)
            good = [m for m, n in matches if m.distance < 0.80 * n.distance]
            n_good = len(good)
            if len(good) >= 8:
                src = np.float32([self.pts0[m.queryIdx] for m in good])
                dst = np.float32([kp[m.trainIdx].pt for m in good])
                Hm, inl = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
                if inl is not None:
                    n_inl = int(inl.sum())
                if Hm is not None and inl is not None and inl.sum() >= 8:
                    q = cv2.perspectiveTransform(self.quad0.reshape(1, -1, 2), Hm).reshape(-1, 2)
                    self.cur_quad = q
        if debug:
            print(f"    kp_in_roi={n_kp} good_matches={n_good} inliers={n_inl}")
        return self.cur_quad


# ---------------------------------------------------------------------------
# ffmpeg pipe writer
# ---------------------------------------------------------------------------

def open_ffmpeg_writer(path, w, h, fps, lossless=False, gray_input=False):
    pix_fmt_in = "gray" if gray_input else "bgr24"
    if lossless:
        codec_args = ["-c:v", "ffv1", "-pix_fmt", "gray" if gray_input else "yuv420p"]
    else:
        codec_args = ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p"]
    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{w}x{h}", "-pix_fmt", pix_fmt_in, "-r", str(fps),
        "-i", "-",
        *codec_args,
        "-r", str(fps),
        path,
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


# ---------------------------------------------------------------------------
# Main per-video processing
# ---------------------------------------------------------------------------

def process_video(key, test_frame=False):
    cfg = VIDEOS[key]
    src_path = os.path.join(ORIG_DIR, cfg["file"])
    cap = cv2.VideoCapture(src_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    active_start, active_end = cfg.get("active", (0, nframes))
    print(f"[{key}] {cfg['file']}  {w}x{h} @ {fps:.3f}fps  {nframes} frames  ({nframes/fps:.2f}s)"
          f"  active=[{active_start},{active_end}) ({(active_end-active_start)/fps:.2f}s manip)")

    W, H = cfg["canon"]
    design_layer = cfg["design"](W, H)

    ok, frame0 = cap.read()
    assert ok, "could not read first frame"

    tracker = None
    if cfg["track"]:
        gray0 = cv2.cvtColor(frame0, cv2.COLOR_BGR2GRAY)
        tracker = QuadTracker(gray0, cfg["quad"])

    if test_frame:
        preview_idx = (active_start + active_end) // 2
        frame = frame0
        gray_prev = gray0 if cfg["track"] else None
        for i in range(1, preview_idx + 1):
            ok, frame = cap.read()
            if not ok:
                break
            if cfg["track"]:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                tracker.update(gray)
        quad_cur = cfg["quad"] if not cfg["track"] else tracker.cur_quad
        roi_out, roi_mask, (x0, y0, x1, y1) = composite_frame(frame, quad_cur, cfg, design_layer)
        manip = frame.copy(); manip[y0:y1, x0:x1] = roi_out
        mask = np.zeros((h, w), np.uint8); mask[y0:y1, x0:x1] = roi_mask
        os.makedirs(COMP_DIR, exist_ok=True)
        imwrite_u(os.path.join(COMP_DIR, f"{key}_test_original.png"), frame)
        imwrite_u(os.path.join(COMP_DIR, f"{key}_test_manip.png"), manip)
        imwrite_u(os.path.join(COMP_DIR, f"{key}_test_mask.png"), mask)
        print(f"[{key}] wrote test frame outputs (frame {preview_idx}) to", COMP_DIR)
        cap.release()
        return

    stem = os.path.splitext(cfg["file"])[0]
    manip_path = os.path.join(MANIP_DIR, f"{stem}_manip.mp4")
    mask_path = os.path.join(MASK_DIR, f"{stem}_mask.mkv")

    manip_writer = open_ffmpeg_writer(manip_path, w, h, fps, lossless=False, gray_input=False)
    mask_writer = open_ffmpeg_writer(mask_path, w, h, fps, lossless=True, gray_input=True)

    frame_idx = 0
    frame = frame0
    while True:
        if frame_idx == 0:
            quad_cur = cfg["quad"] if not cfg["track"] else tracker.cur_quad
        else:
            ok, frame = cap.read()
            if not ok:
                break
            if cfg["track"]:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                quad_cur = tracker.update(gray)
            else:
                quad_cur = cfg["quad"]

        if active_start <= frame_idx < active_end:
            roi_out, roi_mask, (x0, y0, x1, y1) = composite_frame(frame, quad_cur, cfg, design_layer)
            manip = frame.copy(); manip[y0:y1, x0:x1] = roi_out
            mask = np.zeros((h, w), np.uint8); mask[y0:y1, x0:x1] = roi_mask
        else:
            manip = frame
            mask = np.zeros((h, w), np.uint8)

        manip_writer.stdin.write(manip.tobytes())
        mask_writer.stdin.write(mask.tobytes())

        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"  [{key}] frame {frame_idx}/{nframes}")
        if frame_idx >= nframes:
            break

    manip_writer.stdin.close(); manip_writer.wait()
    mask_writer.stdin.close(); mask_writer.wait()
    cap.release()
    print(f"[{key}] done -> {manip_path} ; {mask_path}  ({frame_idx} frames written)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, help="v1..v5 or 'all'")
    ap.add_argument("--test-frame", action="store_true")
    args = ap.parse_args()

    keys = list(VIDEOS.keys()) if args.video == "all" else [args.video]
    for k in keys:
        process_video(k, test_frame=args.test_frame)
