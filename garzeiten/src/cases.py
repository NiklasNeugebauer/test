"""Find the hardest cells: compare original vs PDF per text cell, rank mismatches, and for the
faint water-column fractions render alternative readings and score them against the original.
Output: diff/schwierige_faelle_*.png and diff/schwierige_faelle.pdf"""
import csv, json, os, subprocess, sys, cv2, numpy as np
sys.path.insert(0, 'src')
from align import ink_orig, PX, PAGE_H_PT, GEOM, PAGES
import build_pdf as B
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from PIL import Image, ImageDraw, ImageFont

rows = list(csv.DictReader(open('garzeiten.csv', encoding='utf-8')))
notes = {(r['seite'], r['gruppe'] + ' · ' + r['gericht']): r['anmerkung'] for r in rows if r['anmerkung']}
FRAC_ALTS = ['⅛ l', '¼ l', '½ l', '⅛–¼ l', '¼–½ l']
SPECIAL_ALTS = {'Rebhühner': ['3–6 Eßlöffel', '4–6 Eßlöffel', '2–6 Eßlöffel', '5–6 Eßlöffel']}
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
FONT_S = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)

def bbox(t, w_override=None):
    x0 = t['x'] * PX; w = (w_override if w_override else t['w']) * PX; yb = (PAGE_H_PT - t['y']) * PX
    return int(x0 - 6), int(yb - 0.85 * t['size'] * PX), int(x0 + w + 6), int(yb + 0.3 * t['size'] * PX)

def ncc(o, p, shifts=5):
    """normalised cross-correlation of blurred ink images, best over small shifts."""
    ob = cv2.GaussianBlur(o.astype(np.float32), (0, 0), 2.5); pb = cv2.GaussianBlur(p.astype(np.float32), (0, 0), 2.5)
    pb = pb - pb.mean(); pn = np.linalg.norm(pb) + 1e-6
    best = -1.0
    for dy in range(-shifts, shifts + 1):
        for dx in range(-shifts, shifts + 1):
            os_ = np.roll(np.roll(ob, dy, 0), dx, 1); os_ = os_ - os_.mean()
            best = max(best, float((os_ * pb).sum() / ((np.linalg.norm(os_) + 1e-6) * pn)))
    return best

def coverage(o, p, shifts=4):
    """symmetric ink coverage (0..1, higher = better match), best over small shifts of o."""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    pd = cv2.dilate(p, k)
    best = 0.0
    for dy in range(-shifts, shifts + 1):
        for dx in range(-shifts, shifts + 1):
            os_ = np.roll(np.roll(o, dy, 0), dx, 1)
            od = cv2.dilate(os_, k)
            co = (os_ & pd).sum() / max(os_.sum(), 1); cp = (p & od).sum() / max(p.sum(), 1)
            best = max(best, 0.5 * (co + cp))
    return best

def render_variants(items):
    """items: list of (page, x, y, text). Returns list of ink masks (full page, 300 dpi)."""
    pdf = 'compare/_variants.pdf'
    c = canvas.Canvas(pdf, pagesize=A5)
    for page, x, y, text in items:
        B._cur['page'] = page; B.GEOM[page] = {'rules': [], 'texts': []}
        c.setFont('Serif', B.FS); B.draw_water(c, x, y, text); c.showPage()
    c.save()
    for f in os.listdir('compare'):
        if f.startswith('_var-'): os.remove('compare/' + f)
    subprocess.run(['pdftoppm', '-r', '300', '-png', pdf, 'compare/_var'], check=True)
    out = []
    for i in range(len(items)):
        g = cv2.imread(f'compare/_var-{i + 1:0{len(str(len(items)))}d}.png', cv2.IMREAD_GRAYSCALE)
        out.append((g < 170).astype(np.uint8))
    return out

def tile(img, w, h, caption=None, cap_color=(0, 0, 0)):
    """fit img into a w x h tile (upscale 3x max), caption below."""
    ih, iw = img.shape[:2]
    s = min(3.0, (w - 8) / iw, (h - 34) / ih)
    r = cv2.resize(img, (max(1, int(iw * s)), max(1, int(ih * s))), interpolation=cv2.INTER_CUBIC if s > 1 else cv2.INTER_AREA)
    canvas_ = np.full((h, w, 3), 255, np.uint8)
    y0 = (h - 34 - r.shape[0]) // 2; x0 = (w - r.shape[1]) // 2
    canvas_[y0:y0 + r.shape[0], x0:x0 + r.shape[1]] = r if r.ndim == 3 else cv2.cvtColor(r, cv2.COLOR_GRAY2BGR)
    if caption:
        pil = Image.fromarray(cv2.cvtColor(canvas_, cv2.COLOR_BGR2RGB)); d = ImageDraw.Draw(pil)
        tw = d.textlength(caption, font=FONT_S); d.text(((w - tw) / 2, h - 30), caption, fill=cap_color, font=FONT_S)
        canvas_ = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    return canvas_

def main():
    cases = []           # dicts with page, text, kind, score, bbox, alts
    imgs = {}
    for page, n in PAGES.items():
        A = cv2.imread(f'aligned/page{page}_color.png'); Ag = cv2.cvtColor(A, cv2.COLOR_BGR2GRAY)
        P = cv2.imread(f'compare/pdf300-{n}.png', cv2.IMREAD_GRAYSCALE)
        oink = (ink_orig(Ag) > 0).astype(np.uint8); pink = (P < 170).astype(np.uint8)
        D = cv2.imread(f'diff/page{page}_diff.png')
        imgs[page] = (A, oink, pink, D)
        for t in GEOM[str(page)]['texts']:
            x0, y0, x1, y1 = bbox(t)
            o = oink[y0:y1, x0:x1]; p = pink[y0:y1, x0:x1]
            if p.sum() == 0: continue
            sc = coverage(o, p)
            has_frac = any(ch in t['text'] for ch in B.FRACS)
            alts = None
            if t['kind'] == 'water' and has_frac: alts = FRAC_ALTS
            if (t.get('row') or '').split(' · ')[-1] in SPECIAL_ALTS and t['kind'] == 'water': alts = SPECIAL_ALTS[t['row'].split(' · ')[-1]]
            cases.append(dict(page=page, t=t, score=sc, alts=alts, note=notes.get((str(page), t.get('row') or ''))))
    # ---- alternatives for all fraction / special cells
    alt_cases = [c for c in cases if c['alts']]
    items = [(c['page'], c['t']['x'], c['t']['y'], a) for c in alt_cases for a in c['alts']]
    masks = render_variants(items)
    k = 0
    store = {}
    for c in alt_cases:
        A, oink, pink, D = imgs[c['page']]
        wmax = max(B.water_width(a) for a in c['alts'])
        x0, y0, x1, y1 = bbox(c['t'], wmax)
        o = oink[y0:y1, x0:x1]
        c['alt_scores'] = []
        for a in c['alts']:
            m = masks[k]; k += 1; store[(id(c), a)] = m
            # score only the part that differs between the alternatives (fraction glyphs, not the unit ' l')
            core = a[:-2] if a.endswith(' l') else a
            xw = int(c['t']['x'] * PX + B.water_width(core) * PX + 6)
            c['alt_scores'].append((a, ncc(o[:, :xw - x0], m[y0:y1, x0:xw])))
        c['bbox_w'] = wmax
    # ---- selection: all fraction/special cells sorted by how ambiguous they are (small margin between best alternatives or low score)
    def ambiguity(c):
        s = sorted((v for _, v in c['alt_scores']), reverse=True)
        return (s[0] - s[1]) * 2 if len(s) > 1 else 1.0
    alt_cases.sort(key=lambda c: (ambiguity(c) + 0.5 * c['score']))
    show = alt_cases[:16]
    for c in alt_cases[16:]:
        if c['note'] and c not in show: show.append(c)
    other = sorted([c for c in cases if not c['alts'] and len(c['t']['text']) >= 2], key=lambda c: c['score'])[:12]
    # ---- montage
    TW, TH = 330, 150
    def row_for(c, with_alts):
        A, oink, pink, D = imgs[c['page']]
        t = c['t']; x0, y0, x1, y1 = bbox(t, c.get('bbox_w'))
        pad = 10; y0 -= pad; y1 += pad; x0 -= pad; x1 += pad
        head = np.full((TH, 420, 3), 255, np.uint8)
        pil = Image.fromarray(head); d = ImageDraw.Draw(pil)
        rowname = (t.get('row') or t['text']).replace(chr(92) + 'n', ' / ')
        d.text((8, 6), f"S. {c['page']}  {rowname.split(' · ')[-1]}"[:34], fill=(0, 0, 0), font=FONT)
        d.text((8, 32), rowname.split(' · ')[0][:40] if ' · ' in rowname else '', fill=(90, 90, 90), font=FONT_S)
        d.text((8, 56), f"gelesen: {t['text']}", fill=(0, 0, 0), font=FONT)
        d.text((8, 86), f"Übereinstimmung {c['score']:.0%}", fill=(90, 90, 90), font=FONT_S)
        if c['note']: d.text((8, 110), 'CSV: ' + c['note'][:40], fill=(160, 0, 0), font=FONT_S)
        head = np.array(pil)
        tiles = [head, tile(A[y0:y1, x0:x1], TW, TH, 'Original (registriert)'), tile(D[y0:y1, x0:x1], TW, TH, 'Differenz  rot=Original  blau=PDF')]
        if with_alts:
            best = max(v for _, v in c['alt_scores'])
            for a, v in c['alt_scores']:
                m = masks_by_text(c, a); img = 255 - m[y0:y1, x0:x1] * 255
                col = (0, 120, 0) if v == best else (0, 0, 0)
                tiles.append(tile(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR), 230, TH, f'{a}: r={v:.2f}', col))
        return np.hstack(tiles)
    def masks_by_text(c, a): return store[(id(c), a)]
    rows_img = [row_for(c, True) for c in show]
    W = max(r.shape[1] for r in rows_img)
    def padw(r): return np.hstack([r, np.full((r.shape[0], W - r.shape[1], 3), 255, np.uint8)]) if r.shape[1] < W else r
    sep = np.full((2, W, 3), 200, np.uint8)
    title = np.full((60, W, 3), 255, np.uint8); pil = Image.fromarray(title); ImageDraw.Draw(pil).text((10, 14), 'Schwierige Zellen (Wassermengen-Brüche): Original, Differenz und bewertete Lesarten – grün = beste Übereinstimmung', fill=(0, 0, 0), font=FONT); title = np.array(pil)
    pages_out = []
    chunk = 8
    for i in range(0, len(rows_img), chunk):
        parts = [title] if i == 0 else []
        for r in rows_img[i:i + chunk]: parts += [padw(r), sep]
        pages_out.append(np.vstack(parts))
    rows2 = [row_for(c, False) for c in other]
    W2 = max(r.shape[1] for r in rows2)
    title2 = np.full((60, W, 3), 255, np.uint8); pil = Image.fromarray(title2); ImageDraw.Draw(pil).text((10, 14), 'Weitere Zellen mit der geringsten Übereinstimmung (zur Kontrolle, keine Alternativen)', fill=(0, 0, 0), font=FONT); title2 = np.array(pil)
    parts = [title2]
    for r in rows2: parts += [np.hstack([r, np.full((r.shape[0], W - r.shape[1], 3), 255, np.uint8)]), sep]
    pages_out.append(np.vstack(parts))
    pil_pages = []
    for i, im in enumerate(pages_out):
        cv2.imwrite(f'diff/schwierige_faelle_{i + 1}.png', im)
        pil_pages.append(Image.fromarray(cv2.cvtColor(im, cv2.COLOR_BGR2RGB)))
    pil_pages[0].save('diff/schwierige_faelle.pdf', save_all=True, append_images=pil_pages[1:], resolution=150)
    # text summary
    print(f'{"Seite":5s} {"Zelle":32s} {"gelesen":10s} best -> alternatives')
    for c in show:
        ranked = sorted(c['alt_scores'], key=lambda x: -x[1])
        print(f"{c['page']:<5d} {(c['t'].get('row') or '').split(' · ')[-1][:32]:32s} {c['t']['text']:10s} " + '  '.join(f'{a}:{v:.2f}' for a, v in ranked))
    print('\nother low-match cells:')
    for c in other: print(f"  S.{c['page']} {c['t'].get('row') or ''!s:30.30} [{c['t']['kind']}] '{c['t']['text']}' {c['score']:.0%}")

if __name__ == '__main__':
    main()
