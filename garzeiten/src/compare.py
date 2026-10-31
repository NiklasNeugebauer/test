"""Side-by-side comparison: rectified original (left) vs rendered PDF page (right), scaled to equal table width."""
import cv2, json, numpy as np, sys
PAGES = {12: 1, 13: 2, 14: 3, 15: 4}
for p, n in PAGES.items():
    pdf = cv2.imread(f'compare/pdf-{n}.png')
    orig = cv2.imread(f'rectified/page{p}_clean.png')
    # scale original so that its row pitch (~57 px) matches the PDF row pitch (16pt at 150 dpi = 33.3 px)
    s = (16.0 / 72 * 150) / 57.0
    orig = cv2.resize(orig, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    h = max(pdf.shape[0], orig.shape[0])
    def pad(im):
        out = np.full((h, im.shape[1], 3), 255, np.uint8); out[:im.shape[0], :im.shape[1]] = im; return out
    side = np.hstack([pad(orig), np.full((h, 20, 3), (0, 0, 255), np.uint8), pad(pdf)])
    cv2.imwrite(f'compare/side{p}.jpg', side, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(p, side.shape)
