"""Build the 4-page 'Die wichtigsten Garzeiten' PDF from garzeiten.csv, mimicking the original layout."""
import csv, json, re, sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = '/usr/share/fonts/truetype/liberation/'
pdfmetrics.registerFont(TTFont('Serif', FONT_DIR + 'LiberationSerif-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Serif-Bold', FONT_DIR + 'LiberationSerif-Bold.ttf'))

PAGE_W, PAGE_H = A5
FS = 9.4            # body font size (measured against the original: digits ~1.2x, words ~1.12x of 8.6pt Liberation)
HS = 103            # horizontal scaling in percent (original face runs wider than Liberation Serif)
TITLE_FS = 12.0
ROW = 16.0          # single row pitch (pt)
LINE = 11.0         # extra line pitch inside a row
BASE_UP = 4.6       # baseline of the last text line above the bottom rule
L = 10 * mm         # table left
R = 138 * mm        # table right
TITLE_Y = PAGE_H - 13 * mm
TOP_RULE_GAP = 10.5     # title baseline -> top rule
PAGE_NUM_Y = 20 * mm
# column x offsets relative to L (measured on the rectified page 12)
X_SYM, X_NAME, X_TIME, X_SOAK, X_E, X_WATER = 57.6, 66.0, 202.7, 150.0, 249.0, 291.5
FRACS = {'⅛': ('1', '8'), '¼': ('1', '4'), '½': ('1', '2')}
# per-page column corrections in pt, measured from the registered originals (src/measure_layout.py)
COL_ADJ = {12: {'time': 4.1}, 13: {'einsatz': -4.4, 'time': -1.7, 'water': -5.1}, 14: {'time': 4.0}, 15: {'time': 3.4, 'einsatz': -1.2}}
def adj(kind):
    return COL_ADJ.get(_cur['page'], {}).get(kind, 0.0)
GEOM = {}          # page -> {'rules': [...], 'texts': [...]}

def sw(text, font, size):
    return pdfmetrics.stringWidth(text, font, size) * HS / 100.0

def txt(c, x, y, s):
    t = c.beginText(x, y); t.setFont(c._fontname, c._fontsize); t.setHorizScale(HS); t.textOut(s); c.drawText(t)
_cur = {'page': None}

def rec_text(kind, x, y, text, w, size=None, row=None):
    GEOM[_cur['page']]['texts'].append(dict(kind=kind, x=x, y=y, text=text, w=w, size=size or FS, row=row))

def water_width(text):
    w = 0.0
    for ch in text:
        if ch in FRACS:
            n, d = FRACS[ch]; small = FS * 0.62
            w += sw(n, 'Serif', small) - 0.2 + sw('/', 'Serif', FS * 0.9) - 0.4 + sw(d, 'Serif', small)
        else:
            w += sw(ch, 'Serif', FS)
    return w

def rows_for(rows, page):
    return [r for r in rows if int(r['seite']) == page]

def lines(s):
    return s.replace('\\n', '\n').split('\n') if s else []

def draw_water(c, x, y, text, row=None):
    """Draw text containing vulgar fractions as superscript/subscript fractions like the original."""
    rec_text('water', x, y, text, water_width(text), row=row)
    for ch in text:
        if ch in FRACS:
            n, d = FRACS[ch]
            small = FS * 0.62
            c.setFont('Serif', small); txt(c, x, y + FS * 0.36, n); x += sw(n, 'Serif', small) - 0.2
            c.setFont('Serif', FS * 0.9); txt(c, x, y - 0.3, '/'); x += sw('/', 'Serif', FS * 0.9) - 0.4
            c.setFont('Serif', small); txt(c, x, y - FS * 0.08, d); x += sw(d, 'Serif', small)
            c.setFont('Serif', FS)
        else:
            txt(c, x, y, ch); x += sw(ch, 'Serif', FS)

def draw_time(c, x, y, t, row=None):
    """Times like '6– 8' are set so that the dash aligns with two-digit entries."""
    if re.fullmatch(r'\d– \d', t):
        x += sw('0', 'Serif', FS)
    txt(c, x, y, t); rec_text('time', x, y, t, sw(t, 'Serif', FS), row=row)

def draw_symbol(c, x, y, sym):
    if sym == '○':
        c.setLineWidth(0.55); c.circle(x, y + FS * 0.33, 3.0, stroke=1, fill=0)
    elif sym == '*':
        c.setFont('Serif-Bold', FS * 1.15); txt(c, x - sw('*', 'Serif-Bold', FS * 1.15) / 2, y - 1.2, '*'); c.setFont('Serif', FS)

def rule(c, y, dashed=True, width=0.5):
    GEOM[_cur['page']]['rules'].append(dict(y=y, dashed=dashed, x0=L, x1=R))
    c.setLineWidth(width)
    c.setDash([2.6, 1.3] if dashed else [])
    c.line(L, y, R, y)
    c.setDash([])

def row_height(r):
    name_l = lines(r['gericht']); label_l = lines(r['label'])
    above = max(len(label_l) - 1, 0)
    return ROW + LINE * (above + len(name_l) - 1), above

def draw_page(c, rows, page):
    _cur['page'] = page; GEOM[page] = {'rules': [], 'texts': []}
    c.setFont('Serif-Bold', TITLE_FS)
    tw = sw('Die wichtigsten Garzeiten', 'Serif-Bold', TITLE_FS); txt(c, (L + R) / 2 + 6 - tw / 2, TITLE_Y, 'Die wichtigsten Garzeiten')
    y = TITLE_Y - TOP_RULE_GAP
    rule(c, y, dashed=False, width=0.7)
    c.setFont('Serif', FS)
    indent = 0.0
    pending_hint = None
    footnotes_started = False
    i = 0
    while i < len(rows):
        r = rows[i]; i += 1
        if r['typ'] == 'hinweis':
            pending_hint = r; continue
        if r['typ'] == 'fussnote':
            y -= 12.5 if not footnotes_started else 14.0
            footnotes_started = True
            draw_symbol(c, L + 3.0, y, r['symbol']); txt(c, L + 8.5, y, r['gericht'])
            continue
        if r['typ'] == 'spaltenkopf':
            h = ROW; yb = y - h + BASE_UP
            txt(c, L + X_SOAK, yb, r['garzeit_eingeweicht_min'])
            txt(c, L + X_TIME - 7, yb, r['garzeit_min'])
            y -= h; rule(c, y); indent = 16.0
            continue
        h, above = row_height(r)
        if pending_hint:
            h += LINE; above += 1
        name_l = lines(r['gericht']); label_l = lines(r['label'])
        first_base = y - ROW + BASE_UP - LINE * above + LINE * (len(name_l) - 1) * 0 - 0
        # baseline of the first dish line: bottom rule + BASE_UP + LINE*(name_lines-1)
        bottom = y - h
        first_base = bottom + BASE_UP + LINE * (len(name_l) - 1)
        if pending_hint:
            hy = first_base + LINE
            c.setFont('Serif-Bold', FS); txt(c, L, hy, pending_hint['label'])
            c.setFont('Serif', FS); txt(c, L + sw(pending_hint['label'], 'Serif-Bold', FS) + 2.5, hy, pending_hint['gericht'])
            pending_hint = None
        # category label (bold), last label line on the first dish line
        c.setFont('Serif-Bold', FS)
        for k, t in enumerate(reversed(label_l)):
            txt(c, L, first_base + LINE * k, t)
            rec_text('label', L, first_base + LINE * k, t, sw(t, 'Serif-Bold', FS), row=r['gruppe'] + ' · ' + r['gericht'])
        c.setFont('Serif', FS)
        draw_symbol(c, L + X_SYM + indent + adj('name'), first_base, r['symbol'])
        for k, t in enumerate(name_l):
            txt(c, L + X_NAME + indent + adj('name'), first_base - LINE * k, t)
            rec_text('name', L + X_NAME + indent + adj('name'), first_base - LINE * k, t, sw(t, 'Serif', FS), row=r['gruppe'] + ' · ' + r['gericht'])
        # numbers/columns sit on the last dish line
        last_base = bottom + BASE_UP
        e_l = lines(r['einsatz']); w_l = lines(r['wasser'])
        top_aligned = len(e_l) > 1 or len(w_l) > 1
        col_base = first_base if top_aligned else last_base
        if r['garzeit_eingeweicht_min']:
            txt(c, L + X_SOAK + adj('soak'), col_base, r['garzeit_eingeweicht_min'])
            rec_text('soak', L + X_SOAK + adj('soak'), col_base, r['garzeit_eingeweicht_min'], sw(r['garzeit_eingeweicht_min'], 'Serif', FS), row=r['gruppe'] + ' · ' + r['gericht'])
        if r['garzeit_min']:
            draw_time(c, L + X_TIME + adj('time'), col_base, r['garzeit_min'], row=r['gruppe'] + ' · ' + r['gericht'])
        if r['gericht'].startswith('Sauerkraut'):   # original sets the quantity in the insert column
            draw_water(c, L + X_E, col_base, r['wasser'], row=r['gruppe'] + ' · ' + r['gericht']); e_l, w_l = [], []
        for k, t in enumerate(e_l):
            txt(c, L + X_E + adj('einsatz'), col_base - LINE * k, t)
            rec_text('einsatz', L + X_E + adj('einsatz'), col_base - LINE * k, t, sw(t, 'Serif', FS), row=r['gruppe'] + ' · ' + r['gericht'])
        for k, t in enumerate(w_l):
            draw_water(c, L + X_WATER + adj('water'), col_base - LINE * k, t, row=r['gruppe'] + ' · ' + r['gericht'])
        y = bottom
        is_last = (i == len(rows)) or rows[i]['typ'] == 'fussnote'
        if is_last and page != 15:
            rule(c, y, dashed=False, width=0.7); rule(c, y - 3.2, dashed=False, width=0.7)
        else:
            rule(c, y, dashed=not is_last, width=0.7 if is_last else 0.5)
    if page == 15:
        y -= 14.0
        rule(c, y, dashed=False, width=0.7)
    c.setFont('Serif', FS * 1.05)
    txt(c, (L + R) / 2 - sw(str(page), 'Serif', FS * 1.05) / 2, y - 22.0, str(page))

def main(csv_path='garzeiten.csv', out='garzeiten.pdf'):
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8')))
    c = canvas.Canvas(out, pagesize=A5)
    c.setTitle('Die wichtigsten Garzeiten'); c.setAuthor('Rekonstruktion aus Handbuchseiten 12–15')
    for p in (12, 13, 14, 15):
        draw_page(c, rows_for(rows, p), p); c.showPage()
    c.save(); print('wrote', out)
    json.dump(GEOM, open(out.replace('.pdf', '_geom.json'), 'w'), ensure_ascii=False, indent=0)

def render_variant(page_no, x, y, text, out):
    """Render just one water-column cell (an alternative reading) on an otherwise empty page."""
    _cur['page'] = page_no; GEOM[page_no] = {'rules': [], 'texts': []}
    c = canvas.Canvas(out, pagesize=A5); c.setFont('Serif', FS)
    draw_water(c, x, y, text); c.showPage(); c.save()

if __name__ == '__main__':
    main(*sys.argv[1:])
