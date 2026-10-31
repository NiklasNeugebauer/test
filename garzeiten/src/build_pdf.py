"""Build the 4-page 'Die wichtigsten Garzeiten' PDF from garzeiten.csv, mimicking the original layout."""
import csv, re, sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = '/usr/share/fonts/truetype/liberation/'
pdfmetrics.registerFont(TTFont('Serif', FONT_DIR + 'LiberationSerif-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Serif-Bold', FONT_DIR + 'LiberationSerif-Bold.ttf'))

PAGE_W, PAGE_H = A5
FS = 8.6            # body font size
TITLE_FS = 11.5
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

def rows_for(rows, page):
    return [r for r in rows if int(r['seite']) == page]

def lines(s):
    return s.replace('\\n', '\n').split('\n') if s else []

def draw_water(c, x, y, text):
    """Draw text containing vulgar fractions as superscript/subscript fractions like the original."""
    for ch in text:
        if ch in FRACS:
            n, d = FRACS[ch]
            small = FS * 0.62
            c.setFont('Serif', small); c.drawString(x, y + FS * 0.36, n); x += pdfmetrics.stringWidth(n, 'Serif', small) - 0.2
            c.setFont('Serif', FS * 0.9); c.drawString(x, y - 0.3, '/'); x += pdfmetrics.stringWidth('/', 'Serif', FS * 0.9) - 0.4
            c.setFont('Serif', small); c.drawString(x, y - FS * 0.08, d); x += pdfmetrics.stringWidth(d, 'Serif', small)
            c.setFont('Serif', FS)
        else:
            c.drawString(x, y, ch); x += pdfmetrics.stringWidth(ch, 'Serif', FS)

def draw_time(c, x, y, t):
    """Times like '6– 8' are set so that the dash aligns with two-digit entries."""
    if re.fullmatch(r'\d– \d', t):
        x += pdfmetrics.stringWidth('0', 'Serif', FS)
    c.drawString(x, y, t)

def draw_symbol(c, x, y, sym):
    if sym == '○':
        c.setLineWidth(0.55); c.circle(x, y + FS * 0.33, 3.0, stroke=1, fill=0)
    elif sym == '*':
        c.setFont('Serif-Bold', FS * 1.15); c.drawCentredString(x, y - 1.2, '*'); c.setFont('Serif', FS)

def rule(c, y, dashed=True, width=0.5):
    c.setLineWidth(width)
    c.setDash([2.6, 1.3] if dashed else [])
    c.line(L, y, R, y)
    c.setDash([])

def row_height(r):
    name_l = lines(r['gericht']); label_l = lines(r['label'])
    above = max(len(label_l) - 1, 0)
    return ROW + LINE * (above + len(name_l) - 1), above

def draw_page(c, rows, page):
    c.setFont('Serif-Bold', TITLE_FS)
    c.drawCentredString((L + R) / 2 + 6, TITLE_Y, 'Die wichtigsten Garzeiten')
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
            draw_symbol(c, L + 3.0, y, r['symbol']); c.drawString(L + 8.5, y, r['gericht'])
            continue
        if r['typ'] == 'spaltenkopf':
            h = ROW; yb = y - h + BASE_UP
            c.drawString(L + X_SOAK, yb, r['garzeit_eingeweicht_min'])
            c.drawString(L + X_TIME - 7, yb, r['garzeit_min'])
            y -= h; rule(c, y); indent = 14.0
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
            c.setFont('Serif-Bold', FS); c.drawString(L, hy, pending_hint['label'])
            c.setFont('Serif', FS); c.drawString(L + pdfmetrics.stringWidth(pending_hint['label'], 'Serif-Bold', FS) + 2.5, hy, pending_hint['gericht'])
            pending_hint = None
        # category label (bold), last label line on the first dish line
        c.setFont('Serif-Bold', FS)
        for k, t in enumerate(reversed(label_l)):
            c.drawString(L, first_base + LINE * k, t)
        c.setFont('Serif', FS)
        draw_symbol(c, L + X_SYM + indent, first_base, r['symbol'])
        for k, t in enumerate(name_l):
            c.drawString(L + X_NAME + indent, first_base - LINE * k, t)
        # numbers/columns sit on the last dish line
        last_base = bottom + BASE_UP
        e_l = lines(r['einsatz']); w_l = lines(r['wasser'])
        top_aligned = len(e_l) > 1 or len(w_l) > 1
        col_base = first_base if top_aligned else last_base
        if r['garzeit_eingeweicht_min']:
            c.drawString(L + X_SOAK, col_base, r['garzeit_eingeweicht_min'])
        if r['garzeit_min']:
            draw_time(c, L + X_TIME, col_base, r['garzeit_min'])
        if r['gericht'].startswith('Sauerkraut'):   # original sets the quantity in the insert column
            draw_water(c, L + X_E, col_base, r['wasser']); e_l, w_l = [], []
        for k, t in enumerate(e_l):
            c.drawString(L + X_E, col_base - LINE * k, t)
        for k, t in enumerate(w_l):
            draw_water(c, L + X_WATER, col_base - LINE * k, t)
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
    c.drawCentredString((L + R) / 2, y - 22.0, str(page))

def main(csv_path='garzeiten.csv', out='garzeiten.pdf'):
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8')))
    c = canvas.Canvas(out, pagesize=A5)
    c.setTitle('Die wichtigsten Garzeiten'); c.setAuthor('Rekonstruktion aus Handbuchseiten 12–15')
    for p in (12, 13, 14, 15):
        draw_page(c, rows_for(rows, p), p); c.showPage()
    c.save(); print('wrote', out)

if __name__ == '__main__':
    main(*sys.argv[1:])
