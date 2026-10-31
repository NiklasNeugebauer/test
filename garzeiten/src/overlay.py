"""For every water-column fraction cell: show the registered original (grey) with each candidate
reading rendered in red and locally shifted to the best fit, so a human can judge the reading.
Output: diff/bruch_overlays.pdf and diff/bruch_overlays_N.png"""
import csv, sys, cv2, numpy as np
sys.path.insert(0, 'src')
from align import ink_orig, PX, PAGE_H_PT, GEOM, PAGES
from cases import bbox, render_variants, FRAC_ALTS, FONT, FONT_S
import build_pdf as B
from PIL import Image, ImageDraw

rows = list(csv.DictReader(open('garzeiten.csv', encoding='utf-8')))
notes = {(r['seite'], r['gruppe'] + ' · ' + r['gericht']): r['anmerkung'] for r in rows if r['anmerkung']}
SCALE = 5
PAD = 8

def best_shift(o, m, core_w, R=26):
    """shift (dx, dy) of candidate mask m that maximises blurred correlation with original o inside the core width."""
    ob = cv2.GaussianBlur(o[:, :core_w].astype(np.float32), (0, 0), 2.0); ob -= ob.mean()
    mbf = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2.0)
    def score(dx, dy):
        mb = np.roll(np.roll(mbf, dy, 0), dx, 1)[:, :core_w]; mb = mb - mb.mean()
        return float((ob * mb).sum() / ((np.linalg.norm(ob) + 1e-6) * (np.linalg.norm(mb) + 1e-6)))
    best = (-2, 0, 0)
    for dy in range(-10, 11, 2):
        for dx in range(-R, R + 1, 2):
            r = score(dx, dy)
            if r > best[0]: best = (r, dx, dy)
    _, bx, by = best
    for dy in range(by - 2, by + 3):
        for dx in range(bx - 2, bx + 3):
            r = score(dx, dy)
            if r > best[0]: best = (r, dx, dy)
    return best

def anchor_l(mask, strict=False):
    """(x_center, y_bottom) of the unit 'l': the tallest connected component in the right part of the cell."""
    n, lab, st, cen = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    W = mask.shape[1]; best = None
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if strict and i != n - 1 and False: pass
        if x + w / 2 < 0.35 * W: continue          # fractions live on the left
        if h < (0.55 if strict else 0.42) * mask.shape[0] or w > 0.35 * h + 6: continue
        if best is None or h > best[0]:
            best = (h, x + w / 2.0, y + h)
    return None if best is None else (int(round(best[1])), int(round(best[2])))

def main():
    cells = []
    for page, n in PAGES.items():
        A = cv2.imread(f'aligned/page{page}_color.png')
        Ag = cv2.cvtColor(A, cv2.COLOR_BGR2GRAY)
        oink = (ink_orig(Ag) > 0).astype(np.uint8)
        for t in GEOM[str(page)]['texts']:
            if t['kind'] != 'water' or not any(ch in t['text'] for ch in B.FRACS): continue
            cells.append(dict(page=page, t=t, A=A, Ag=Ag, oink=oink, note=notes.get((str(page), t.get('row') or ''))))
    cells.sort(key=lambda c: (c['page'], -c['t']['y']))
    import re
    for c in cells:
        txt = c['t']['text']
        m = re.match(r'^(.*?)([⅛¼½](?:–[⅛¼½])?) l$', txt)
        prefix = m.group(1) if m else ''
        frac = m.group(2) if m else ''
        c['prefix'] = prefix
        if '–' in frac:
            c['alts'] = [prefix + f + ' l' for f in ('⅛–¼', '¼–½', '⅛–½')]
        else:
            c['alts'] = [prefix + f + ' l' for f in ('⅛', '¼', '½')]
    items = [(c['page'], c['t']['x'], c['t']['y'], a) for c in cells for a in c['alts']]
    masks = render_variants(items)
    k = 0
    tiles_rows = []
    for c in cells:
        t = c['t']; wmax = max(B.water_width(a) for a in c['alts'])
        x0, y0, x1, y1 = bbox(t, wmax)
        x0 += int(B.water_width(c['prefix']) * PX)        # crop only the fraction part
        x0 -= PAD; x1 += PAD + 14; y0 -= PAD; y1 += PAD
        o = c['oink'][y0:y1, x0:x1]
        g = c['Ag'][y0:y1, x0:x1].astype(np.float32)
        lo, hi = np.percentile(g, 2), np.percentile(g, 98)
        g = np.clip((g - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
        g_big = cv2.resize(g, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)
        tiles = []
        # header tile
        head = np.full((g_big.shape[0] + 40, 300, 3), 255, np.uint8)
        pil = Image.fromarray(head); d = ImageDraw.Draw(pil)
        name = (t.get('row') or '').split(' · ')
        d.text((6, 4), f"S. {c['page']}  {name[-1][:26]}", fill=(0, 0, 0), font=FONT)
        d.text((6, 30), name[0][:30] if len(name) > 1 else '', fill=(90, 90, 90), font=FONT_S)
        d.text((6, 56), f"gelesen: {t['text']}", fill=(0, 100, 0), font=FONT)
        if c['note']: d.text((6, 84), 'unsicher', fill=(180, 0, 0), font=FONT)
        tiles.append(np.array(pil))
        # original tile
        def captioned(img, cap, color=(0, 0, 0)):
            canvas_ = np.full((img.shape[0] + 40, img.shape[1] + 12, 3), 255, np.uint8)
            canvas_[6:6 + img.shape[0], 6:6 + img.shape[1]] = img
            pil = Image.fromarray(canvas_); d = ImageDraw.Draw(pil)
            tw = d.textlength(cap, font=FONT_S); d.text(((canvas_.shape[1] - tw) / 2, img.shape[0] + 12), cap, fill=color, font=FONT_S)
            return np.array(pil)
        tiles.append(captioned(cv2.cvtColor(g_big, cv2.COLOR_GRAY2RGB), 'Original'))
        ref = anchor_l(o)
        for a in c['alts']:
            m = masks[k][y0:y1, x0:x1]; k += 1
            cand = anchor_l(m, strict=True)
            if ref is not None and cand is not None:
                dx, dy = ref[0] - cand[0], ref[1] - cand[1]
                r = best_shift(o, np.roll(np.roll(m, dy, 0), dx, 1), m.shape[1], R=2)[0]
            else:
                r, dx, dy = best_shift(o, m, m.shape[1])
            ms = np.roll(np.roll(m, dy, 0), dx, 1)
            ms_big = cv2.resize(ms, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_NEAREST) > 0
            over = cv2.cvtColor(g_big, cv2.COLOR_GRAY2RGB).astype(np.float32)
            red = np.array([230, 30, 30], np.float32)
            over[ms_big] = 0.45 * over[ms_big] + 0.55 * red
            over = over.astype(np.uint8)
            cur = (a == t['text'])
            img = captioned(over, f"{a}   r={r:.2f}", (0, 110, 0) if cur else (0, 0, 0))
            if cur:
                cv2.rectangle(img, (0, 0), (img.shape[1] - 1, img.shape[0] - 1), (0, 140, 0), 3)
            tiles.append(img)
        h = max(x.shape[0] for x in tiles)
        tiles = [np.vstack([x, np.full((h - x.shape[0], x.shape[1], 3), 255, np.uint8)]) if x.shape[0] < h else x for x in tiles]
        tiles_rows.append(np.hstack(tiles))
    W = max(r.shape[1] for r in tiles_rows)
    sep = np.full((3, W, 3), 190, np.uint8)
    title = np.full((56, W, 3), 255, np.uint8); pil = Image.fromarray(title)
    ImageDraw.Draw(pil).text((10, 14), 'Wassermengen-Brüche: registriertes Original (grau), darüber jede Lesart am Liter-l verankert (rot). Grün = aktuelle Lesung in der CSV, \"unsicher\" = in der CSV als abgerieben markiert.', fill=(0, 0, 0), font=FONT)
    title = np.array(pil)
    per_page = 12; pages = []
    for i in range(0, len(tiles_rows), per_page):
        parts = [title]
        for r in tiles_rows[i:i + per_page]:
            r = np.hstack([r, np.full((r.shape[0], W - r.shape[1], 3), 255, np.uint8)]) if r.shape[1] < W else r
            parts += [r, sep]
        pages.append(np.vstack(parts))
    pil_pages = []
    for i, im in enumerate(pages):
        cv2.imwrite(f'diff/bruch_overlays_{i + 1}.png', cv2.cvtColor(im, cv2.COLOR_RGB2BGR))
        pil_pages.append(Image.fromarray(im))
    pil_pages[0].save('diff/bruch_overlays.pdf', save_all=True, append_images=pil_pages[1:], resolution=150)
    print(len(cells), 'cells on', len(pages), 'pages')

if __name__ == '__main__':
    main()
