"""Measure, per page and column kind, the horizontal offset of the original text relative to the PDF text
(using the registered originals). Output in pt; feeds the per-page column adjustments in build_pdf.py."""
import cv2, json, re, sys, numpy as np
sys.path.insert(0, 'src')
from align import ink_orig, PX, PAGE_H_PT, GEOM, PAGES
from scipy.ndimage import uniform_filter1d
import csv
rows = list(csv.DictReader(open('garzeiten.csv', encoding='utf-8')))
indent_rows = {r['gericht'] for r in rows if r['seite'] == '15' and r['typ'] == 'eintrag'
               and r['gruppe'] in ('Hülsenfrüchte, Reis, Teigwaren', 'Obst (Kompott)', 'Süßspeisen')}

def kind_of(t):
    k = t['kind']
    if k == 'name' and (t.get('row') or '').split(' · ')[-1] in indent_rows: return 'name_indent'
    if k == 'time' and re.fullmatch(r'\d– \d', t['text']): return 'time1'
    return k

out = {}
for page, n in PAGES.items():
    A = cv2.imread(f'aligned/page{page}_color.png', cv2.IMREAD_GRAYSCALE); oink = ink_orig(A)
    P = cv2.imread(f'compare/pdf300-{n}.png', cv2.IMREAD_GRAYSCALE); pink = (P < 170).astype(np.uint8) * 255
    res = {}
    for t in GEOM[str(page)]['texts']:
        x0 = int(t['x'] * PX); w = max(int(t['w'] * PX), 12); yb = (PAGE_H_PT - t['y']) * PX
        y0, y1 = int(yb - 0.75 * t['size'] * PX), int(yb + 0.25 * t['size'] * PX)
        S = 34
        pp = uniform_filter1d(pink[y0:y1, x0:x0 + w].sum(axis=0).astype(float), 3)
        po = uniform_filter1d(oink[y0 - 3:y1 + 3, x0 - S:x0 + w + S].sum(axis=0).astype(float), 3)
        if pp.sum() < 255 * 30 or po.sum() < 255 * 30: continue
        best = None
        for d in range(-S, S + 1):
            q = po[S + d:S + d + w]
            c = np.dot(q - q.mean(), pp - pp.mean()) / ((np.linalg.norm(q - q.mean()) + 1e-6) * (np.linalg.norm(pp - pp.mean()) + 1e-6))
            if best is None or c > best[0]: best = (c, d)
        if best[0] < 0.35: continue
        res.setdefault(kind_of(t), []).append(best[1] / PX)
    out[page] = {k: (round(float(np.median(v)), 1), len(v)) for k, v in res.items()}
    print(page, {k: f'{v[0]:+.1f}pt (n={v[1]})' for k, v in sorted(out[page].items())})
json.dump(out, open('compare/column_offsets.json', 'w'), indent=1)
