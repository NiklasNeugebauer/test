"""Register the rectified originals onto the rendered PDF pages (300 dpi) so that a true
difference image can be computed.
  y: detected table rules in the original  <->  known rule positions of the PDF (piecewise linear)
  x: per table row, 1-D cross-correlation of ink profiles over scale+offset, smoothed over y
  final polish: ECC affine refinement."""
import cv2, json, sys, numpy as np
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d
sys.path.insert(0, 'src')
from rectify import flatten
from reportlab.lib.pagesizes import A5

DPI = 300; PX = DPI / 72.0
PAGE_H_PT = A5[1]
PITCH = 16.0 * PX
PAGES = {12: 1, 13: 2, 14: 3, 15: 4}
LOCAL_REFINE = False
GEOM = json.load(open('garzeiten_geom.json'))

def ink_orig(gray):
    return cv2.adaptiveThreshold(flatten(gray), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 18)

def ink_pdf(gray):
    return ((gray < 170) * 255).astype(np.uint8)

def rule_ys_orig(ink):
    w = ink.shape[1]
    hm = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (w // 50, 1)))
    prof = uniform_filter1d(hm.sum(axis=1).astype(float), 5)
    peaks, props = find_peaks(prof, distance=20, height=0.10 * 255 * w)
    return peaks.astype(float), props['peak_heights']

def rule_ys_pdf(page):
    ys = sorted((PAGE_H_PT - r['y']) * PX for r in GEOM[str(page)]['rules'])
    merged = []
    for y in ys:                      # merge the closing double rule into one position
        if merged and y - merged[-1][-1] < 6 * PX:
            merged[-1].append(y)
        else:
            merged.append([y])
    return np.array([np.mean(m) for m in merged])

def match_rules(yo, yp):
    """Monotone matching of detected rules (original) to pdf rules by dynamic programming on the
    gap sequence: consecutive matched gaps must have a similar ratio (local scale may drift slowly,
    e.g. crumpled regions), spurious or missed rules cost a penalty. Returns matched (yo_k, yp_k)."""
    n, m = len(yo), len(yp)
    best_total = None
    span_ratio = (yo[-1] - yo[0]) / (yp[-1] - yp[0])
    for s0 in span_ratio * np.array([0.85, 0.92, 1.0, 1.08, 1.15]):
        INF = 1e9
        cost = np.full((n, m), INF); prev = np.full((n, m, 2), -1, int)
        for i in range(min(5, n)):
            for j in range(min(3, m)):
                cost[i, j] = 0.3 * (i + j)
        for j in range(1, m):
            for i in range(1, n):
                for jp in range(max(0, j - 3), j):
                    for ip in range(max(0, i - 4), i):
                        if cost[ip, jp] >= INF: continue
                        r = (yo[i] - yo[ip]) / ((yp[j] - yp[jp]) * s0)
                        c = cost[ip, jp] + 3.0 * abs(np.log(r)) + 0.6 * (i - ip - 1) + 0.6 * (j - jp - 1)
                        if c < cost[i, j]:
                            cost[i, j] = c; prev[i, j] = (ip, jp)
        # end anywhere in the last 3 pdf rules
        cands = [(cost[i, j] + 0.3 * (m - 1 - j), i, j) for i in range(n) for j in range(max(0, m - 3), m) if cost[i, j] < INF]
        c, i, j = min(cands)
        if best_total is None or c < best_total[0]:
            path = []
            while i >= 0 and j >= 0:
                path.append((i, j)); i, j = prev[i, j]
            best_total = (c, path[::-1])
    path = best_total[1]
    yo_m = np.array([yo[i] for i, j in path]); yp_m = np.array([yp[j] for i, j in path])
    return yo_m, yp_m, len(path)

def ymap_from_pairs(yo_m, yp_m, H):
    Y = np.arange(H, dtype=np.float64)
    src = np.interp(Y, yp_m, yo_m)
    m0 = (yo_m[1] - yo_m[0]) / (yp_m[1] - yp_m[0]); m1 = (yo_m[-1] - yo_m[-2]) / (yp_m[-1] - yp_m[-2])
    src = np.where(Y < yp_m[0], yo_m[0] + (Y - yp_m[0]) * m0, src)
    src = np.where(Y > yp_m[-1], yo_m[-1] + (Y - yp_m[-1]) * m1, src)
    return src

def xcorr_fit(po, pp, scales, max_shift):
    """Best (a, b, score) such that po(a*x + b) ~ pp(x)."""
    W = len(pp); x = np.arange(W)
    pp_n = (pp - pp.mean()); pp_n /= (np.linalg.norm(pp_n) + 1e-9)
    best = (1.0, 0.0, -1.0)
    for a in scales:
        xs = a * x
        po_a = np.interp(xs, np.arange(len(po)), po, left=0, right=0)
        po_n = po_a - po_a.mean(); po_n /= (np.linalg.norm(po_n) + 1e-9)
        # cross-correlation via FFT
        n = 1 << int(np.ceil(np.log2(2 * W)))
        cc = np.fft.irfft(np.fft.rfft(pp_n, n) * np.conj(np.fft.rfft(po_n, n)), n)
        cc = np.concatenate([cc[-max_shift:], cc[:max_shift + 1]])   # shifts -max..max
        k = int(cc.argmax()); d = k - max_shift                      # pp(x) ~ po_a(x - d)
        if cc[k] > best[2]:
            best = (a, -a * d, float(cc[k]))
    return best

def align_page(page, n, refine=True):
    P = cv2.imread(f'compare/pdf300-{n}.png', cv2.IMREAD_GRAYSCALE)
    Ocol = cv2.imread(f'rectified/page{page}_color.png')
    Og = cv2.cvtColor(Ocol, cv2.COLOR_BGR2GRAY)
    H, W = P.shape
    pink = ink_pdf(P); oink = ink_orig(Og)
    # ---- vertical
    yo, _ = rule_ys_orig(oink)
    yp = rule_ys_pdf(page)
    yo_m, yp_m, ninl = match_rules(yo, yp)
    print(f'page {page}: {len(yo)} rules in original, {len(yp)} in pdf, matched {ninl}')
    ysrc = ymap_from_pairs(yo_m, yp_m, H)
    sy = (yo_m[-1] - yo_m[0]) / (yp_m[-1] - yp_m[0])      # original px per pdf px (vertical)
    # vertical-only warp of the original ink (x scaled isotropically) for the x search
    map_y0 = np.repeat(ysrc[:, None], W, axis=1).astype(np.float32)
    map_x0 = np.tile((np.arange(W) * sy).astype(np.float32), (H, 1))
    o_v = cv2.remap(oink, map_x0, map_y0, cv2.INTER_LINEAR, borderValue=0)
    # ---- horizontal: local scale = local vertical scale (isotropic perspective approximation),
    #      offset per row band from the NAME block only (x < time column), so that the column
    #      positions of the pdf can later be measured against the names without circularity.
    Lpx = GEOM[str(page)]['rules'][0]['x0'] * PX
    xcut = int(Lpx + 195 * PX)                       # just left of the time column
    dys = np.gradient(ysrc)                           # original px per pdf px, per row
    dys_s = cv2.GaussianBlur(dys.reshape(-1, 1).astype(np.float32), (0, 0), 60).ravel() / sy  # relative to global sy
    yc, Av, Bv, Sv = [], [], [], []
    for y0, y1 in zip(yp_m[:-1], yp_m[1:]):
        a0, a1 = int(y0 + 8), int(y1 - 8)
        if a1 - a0 < 20: continue
        # scale from the whole row profile
        po_f = uniform_filter1d(o_v[a0:a1].sum(axis=0).astype(float), 5)
        pp_f = uniform_filter1d(pink[a0:a1].sum(axis=0).astype(float), 5)
        if pp_f.sum() < 255 * 300 or po_f.sum() < 255 * 300: continue
        a_row, _, sc_a = xcorr_fit(po_f, pp_f, np.linspace(0.95, 1.05, 41), max_shift=int(0.08 * W))
        Av.append(a_row)
        # offset from the name block only, using that scale
        po = uniform_filter1d(o_v[a0:a1, :xcut].sum(axis=0).astype(float), 5)
        pp = uniform_filter1d(pink[a0:a1, :xcut].sum(axis=0).astype(float), 5)
        a, b, sc = xcorr_fit(po, pp, [a_row], max_shift=int(0.08 * W))
        yc.append((a0 + a1) / 2); Bv.append(b); Sv.append(min(sc, sc_a))
    yc, Av, Bv, Sv = map(np.array, (yc, Av, Bv, Sv))
    wts = np.clip(Sv, 0, None) ** 2
    for _ in range(3):
        ca = np.polyfit(yc, Av, 1, w=wts); cb = np.polyfit(yc, Bv, 1, w=wts)
        ra = Av - np.polyval(ca, yc); rb = Bv - np.polyval(cb, yc)
        ok = (np.abs(ra) < 2.5 * (np.std(ra[wts > 0]) + 1e-6)) & (np.abs(rb) < 2.5 * (np.std(rb[wts > 0]) + 1e-6)); wts = wts * ok
    print(f'   x: scale from row profiles, offset from name block; {int(ok.sum())}/{len(ok)} bands, mean corr {Sv.mean():.2f}')
    Y = np.arange(H); aY = np.polyval(ca, Y); bY = np.polyval(cb, Y)
    print(f'   x-scale {aY.min():.4f}..{aY.max():.4f}, x-offset {bY.min():.1f}..{bY.max():.1f} px')
    # full remap: pdf pixel (x,y) -> original pixel
    map_x = (aY[:, None] * np.arange(W)[None, :] + bY[:, None]) * sy
    map_x = map_x.astype(np.float32); map_y = map_y0
    def warp(img, interp=cv2.INTER_CUBIC, border=255):
        return cv2.remap(img, map_x, map_y, interp, borderMode=cv2.BORDER_CONSTANT, borderValue=(border,) * 3)
    Acol = warp(Ocol); Ag = cv2.cvtColor(Acol, cv2.COLOR_BGR2GRAY)
    def overlap(img_gray):
        a = ink_orig(img_gray) > 0; p = pink > 0
        return (a & p).sum() / max(p.sum(), 1)
    Ag = cv2.cvtColor(Acol, cv2.COLOR_BGR2GRAY); ov0 = overlap(Ag)
    # ---- ECC affine polish on blurred ink (kept only if the ink overlap improves)
    if refine:
        src = cv2.GaussianBlur(ink_orig(Ag).astype(np.float32) / 255, (0, 0), 4)
        dst = cv2.GaussianBlur(pink.astype(np.float32) / 255, (0, 0), 4)
        M = np.eye(2, 3, dtype=np.float32)
        try:
            cc, M = cv2.findTransformECC(dst, src, M, cv2.MOTION_AFFINE,
                                         (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
            cand = cv2.warpAffine(Acol, M, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderValue=(255, 255, 255))
            ov1 = overlap(cv2.cvtColor(cand, cv2.COLOR_BGR2GRAY))
            print(f'   ECC affine: overlap {ov0:.3f} -> {ov1:.3f}', '(accepted)' if ov1 > ov0 else '(rejected)')
            if ov1 > ov0:
                Acol = cand
        except cv2.error as e:
            print('   ECC failed:', str(e).splitlines()[0])
    # ---- local refinement: shift per (row band x column segment), interpolated to a smooth field
    Ag = cv2.cvtColor(Acol, cv2.COLOR_BGR2GRAY)
    a_blur = cv2.GaussianBlur(ink_orig(Ag).astype(np.float32) / 255, (0, 0), 1.5)
    p_blur = cv2.GaussianBlur(pink.astype(np.float32) / 255, (0, 0), 1.5)
    R_ = 10                                       # search radius in px
    segs = [(0.0, 0.52), (0.52, 0.78), (0.78, 1.0)]  # name block | time+E | water column (fractions of table width)
    xl, xr = int(GEOM[str(page)]['rules'][0]['x0'] * PX), int(GEOM[str(page)]['rules'][0]['x1'] * PX)
    ys_all = np.concatenate([[yp_m[0] - PITCH * 1.2], yp_m, [yp_m[-1] + PITCH * 1.5]])
    gy, gx, gdx, gdy, gw = [], [], [], [], []
    for y0, y1 in zip(ys_all[:-1], ys_all[1:]):
        a0, a1 = int(y0 + 6), int(y1 - 6)
        if a1 - a0 < 16: continue
        for f0, f1 in segs:
            b0, b1 = int(xl + f0 * (xr - xl)), int(xl + f1 * (xr - xl))
            tmpl = p_blur[a0:a1, b0:b1]
            if tmpl.sum() < 40: continue
            ya, yb = max(0, a0 - R_), min(H, a1 + R_); xa, xb = max(0, b0 - R_), min(W, b1 + R_)
            win = a_blur[ya:yb, xa:xb]
            if win.shape[0] <= tmpl.shape[0] or win.shape[1] <= tmpl.shape[1]: continue
            res = cv2.matchTemplate(win, tmpl, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            dx = (xa + loc[0]) - b0; dy = (ya + loc[1]) - a0
            gy.append((a0 + a1) / 2); gx.append((b0 + b1) / 2); gdx.append(dx); gdy.append(dy); gw.append(max(mx, 0.05))
    gy, gx, gdx, gdy, gw = map(np.array, (gy, gx, gdx, gdy, gw))
    # weighted smoothing of the sparse shifts onto the full grid (Gaussian kernel regression)
    from scipy.interpolate import griddata
    Yg, Xg = np.mgrid[0:H:16, 0:W:16]
    def kreg(vals):
        out = np.zeros(Yg.shape)
        wsum = np.zeros(Yg.shape)
        for yy, xx, v, ww in zip(gy, gx, vals, gw):
            k = ww * np.exp(-((Yg - yy) ** 2 / (2 * (PITCH * 1.2) ** 2) + (Xg - xx) ** 2 / (2 * (0.25 * (xr - xl)) ** 2)))
            out += k * v; wsum += k
        return out / np.maximum(wsum, 1e-9)
    DX = cv2.resize(kreg(gdx).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    DY = cv2.resize(kreg(gdy).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    mx_, my_ = (np.arange(W)[None, :] + DX).astype(np.float32), (np.arange(H)[:, None] + DY).astype(np.float32)
    cand = cv2.remap(Acol, mx_, my_, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    ov2 = overlap(cv2.cvtColor(cand, cv2.COLOR_BGR2GRAY)); ov1 = overlap(Ag)
    print(f'   local refinement ({len(gy)} patches, |dx|<= {np.abs(gdx).max():.0f}, |dy|<= {np.abs(gdy).max():.0f} px): overlap {ov1:.3f} -> {ov2:.3f}', '(accepted)' if ov2 > ov1 else '(rejected)')
    if ov2 > ov1 and LOCAL_REFINE:
        Acol = cand
    Ag = cv2.cvtColor(Acol, cv2.COLOR_BGR2GRAY)
    Aclean = flatten(Ag)
    cv2.imwrite(f'aligned/page{page}_color.png', Acol)
    cv2.imwrite(f'aligned/page{page}_clean.png', Aclean)
    # ---- difference image: black = both, red = only original, blue = only pdf
    a_ink = ink_orig(Ag) > 0; p_ink = pink > 0
    k3 = np.ones((3, 3), np.uint8)
    a_d = cv2.dilate(a_ink.astype(np.uint8), k3) > 0; p_d = cv2.dilate(p_ink.astype(np.uint8), k3) > 0
    diff = np.full((H, W, 3), 255, np.uint8)
    diff[a_ink & ~p_d] = (0, 0, 220)
    diff[p_ink & ~a_d] = (220, 90, 0)
    diff[(a_ink & p_d) | (p_ink & a_d)] = (0, 0, 0)
    cv2.imwrite(f'diff/page{page}_diff.png', diff)
    side = np.hstack([cv2.cvtColor(Aclean, cv2.COLOR_GRAY2BGR), np.full((H, 12, 3), (0, 0, 255), np.uint8), diff])
    cv2.imwrite(f'diff/page{page}_side.jpg', side, [cv2.IMWRITE_JPEG_QUALITY, 85])
    both = (a_ink & p_ink).sum(); print(f'   ink overlap: {both / max(p_ink.sum(), 1):.2%} of pdf ink, {both / max(a_ink.sum(), 1):.2%} of original ink')

if __name__ == '__main__':
    pages = [int(a) for a in sys.argv[1:]] or list(PAGES)
    for p in pages:
        align_page(p, PAGES[p])
