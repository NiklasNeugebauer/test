"""Rectify the four crumpled manual pages: global deskew, then rule-based vertical dewarp
(every dashed table rule is traced as a curve and straightened), then crop + illumination flattening."""
import cv2, json, numpy as np
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d

UP = '/root/.claude/uploads/14dca6c2-e92b-506d-881e-25a5b0001bfc/'
PAGES = {12: '6e6a4e5f-image.jpg', 13: '3d77bc8b-image.jpg', 14: '385c6dba-image.jpg', 15: '70da2ac0-image.jpg'}

def flatten(gray, lo=150, hi=245):
    bg = cv2.GaussianBlur(gray, (0, 0), 41)
    norm = cv2.divide(gray, bg, scale=255).astype(np.float32)
    return np.clip((norm - lo) * (255 / (hi - lo)), 0, 255).astype(np.uint8)

def binarize(gray):
    return cv2.adaptiveThreshold(flatten(gray), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)

def horiz_mask(b):
    w = b.shape[1]
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 60, 1))
    return cv2.morphologyEx(b, cv2.MORPH_OPEN, k)

def global_angle(b):
    h = horiz_mask(b)
    hd = cv2.dilate(h, cv2.getStructuringElement(cv2.MORPH_RECT, (40, 5)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(hd)
    angs, wts = [], []
    for i in range(1, n):
        x, y, ww, hh, a = stats[i]
        if ww > 0.25 * b.shape[1]:
            ys, xs = np.where(lab == i)
            m = np.polyfit(xs, ys, 1)[0]
            angs.append(np.degrees(np.arctan(m))); wts.append(ww)
    return float(np.average(angs, weights=wts)) if angs else 0.0

def rotate(img, ang, border):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=border)

def trace_rules(b, min_frac=0.35):
    """Find each table rule as a curve y(x) over the full width (interpolated over gaps)."""
    h, w = b.shape
    hm = horiz_mask(b)
    prof = uniform_filter1d(hm.sum(axis=1).astype(float), 7)
    peaks, _ = find_peaks(prof, distance=35, height=0.12 * 255 * w)
    curves, extents = [], []
    for py in peaks:
        y0, y1 = max(0, py - 22), min(h, py + 22)
        band = hm[y0:y1]
        cols = band.sum(axis=0) > 0
        if cols.sum() < min_frac * w:
            continue
        ys = np.arange(y0, y1)[:, None]
        ymean = (band / 255.0 * ys).sum(axis=0) / np.maximum((band / 255.0).sum(axis=0), 1e-6)
        xs = np.where(cols)[0]
        curve = np.interp(np.arange(w), xs, ymean[xs])
        curve = uniform_filter1d(curve, 61, mode='nearest')
        curves.append(curve); extents.append((xs.min(), xs.max()))
    return curves, extents

def dewarp(img, curves):
    h, w = img.shape[:2]
    C = np.array(curves)                      # (n, w) source y of each rule per column
    T = C.mean(axis=1)                        # target (straight) y of each rule
    map_y = np.zeros((h, w), np.float32)
    Y = np.arange(h, dtype=np.float32)
    for x in range(w):
        src = C[:, x]
        # piecewise-linear: target y -> source y, linear extrapolation outside
        order = np.argsort(T)
        ts, ss = T[order], src[order]
        my = np.interp(Y, ts, ss)
        m0 = (ss[1] - ss[0]) / (ts[1] - ts[0]); m1 = (ss[-1] - ss[-2]) / (ts[-1] - ts[-2])
        my = np.where(Y < ts[0], ss[0] + (Y - ts[0]) * m0, my)
        my = np.where(Y > ts[-1], ss[-1] + (Y - ts[-1]) * m1, my)
        map_y[:, x] = my
    map_x = np.tile(np.arange(w, dtype=np.float32), (h, 1))
    return cv2.remap(img, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE), T

def rectify(page, fn):
    img = cv2.imread(UP + fn)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ang = global_angle(binarize(gray))
    img = rotate(img, ang, (230, 230, 230))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    curves, extents = trace_rules(binarize(gray))
    out, T = dewarp(img, curves)
    xl = int(np.percentile([e[0] for e in extents], 25)); xr = int(np.percentile([e[1] for e in extents], 75))
    y0 = int(max(0, T.min() - 190)); y1 = int(min(out.shape[0], T.max() + 330))
    x0 = max(0, xl - 70); x1 = min(out.shape[1], xr + 70)
    out = out[y0:y1, x0:x1]
    clean = flatten(cv2.cvtColor(out, cv2.COLOR_BGR2GRAY))
    print(f'page {page}: angle {ang:+.2f} deg, {len(curves)} rules, crop x{x0}-{x1} y{y0}-{y1}')
    cv2.imwrite(f'rectified/page{page}_color.png', out)
    cv2.imwrite(f'rectified/page{page}_clean.png', clean)
    json.dump({'rules': [float(t - y0) for t in sorted(T)], 'x0': x0, 'y0': y0}, open(f'rectified/page{page}_rules.json', 'w'))

if __name__ == '__main__':
    for p, fn in PAGES.items():
        rectify(p, fn)
