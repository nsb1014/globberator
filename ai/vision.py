"""Image side of the fitter: reference segmentation and render-vs-reference scores."""
from collections import deque
import math

import numpy as np
from PIL import Image

NORM = 128


def load_rgba(path):
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32) / 255.0


def segment(path, max_side=384):
    """Foreground mask of a reference image.

    Uses alpha when the image has transparency; otherwise treats the colour of
    the image border as background, keeps the largest connected blob and fills
    its holes. Works for renders, drawings and product-style photos on a plain
    background. Returns a boolean mask.
    """
    img = Image.open(path).convert("RGBA")
    s = max_side / max(img.size)
    if s < 1:
        img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)
    a = np.asarray(img, dtype=np.float32) / 255.0
    rgb, alpha = a[..., :3], a[..., 3]
    if alpha.min() < 0.5:
        fg = alpha > 0.5
    else:
        border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        bg = np.median(border, axis=0)
        spread = np.percentile(np.linalg.norm(border - bg, axis=1), 90)
        dist = np.linalg.norm(rgb - bg, axis=2)
        fg = dist > max(0.12, spread * 2.0)
    fg = largest_component(fg)
    fg = fill_holes(fg)
    return fg


def _neighbors(h, w, y, x):
    if y > 0:
        yield y - 1, x
    if y < h - 1:
        yield y + 1, x
    if x > 0:
        yield y, x - 1
    if x < w - 1:
        yield y, x + 1


def largest_component(mask):
    h, w = mask.shape
    label = np.zeros((h, w), np.int32)
    best, best_n, cur = 0, 0, 0
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if label[y0, x0]:
            continue
        cur += 1
        label[y0, x0] = cur
        q = deque([(y0, x0)])
        n = 0
        while q:
            y, x = q.popleft()
            n += 1
            for ny, nx in _neighbors(h, w, y, x):
                if mask[ny, nx] and not label[ny, nx]:
                    label[ny, nx] = cur
                    q.append((ny, nx))
        if n > best_n:
            best, best_n = cur, n
    return label == best if best else mask


def fill_holes(mask):
    h, w = mask.shape
    outside = np.zeros((h, w), bool)
    q = deque()
    for y in range(h):
        for x in (0, w - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                q.append((y, x))
    for x in range(w):
        for y in (0, h - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for ny, nx in _neighbors(h, w, y, x):
            if not mask[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                q.append((ny, nx))
    return ~outside


def load_mask(path):
    """Mask from a transparent render (alpha) or a black/white mask image."""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA"):
        a = np.asarray(im.convert("RGBA"))[..., 3]
        if a.min() < 128:
            return a > 127
    return np.asarray(im.convert("L")) > 127


def normalized(mask, size=NORM):
    """Crop to the bounding box and fit into a size x size square (aspect kept)."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return np.zeros((size, size), bool), 1.0
    crop = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = crop.shape
    s = (size - 4) / max(h, w)
    im = Image.fromarray((crop * 255).astype(np.uint8)).resize((max(1, round(w * s)), max(1, round(h * s))), Image.BILINEAR)
    out = np.zeros((size, size), np.uint8)
    oy, ox = (size - im.height) // 2, (size - im.width) // 2
    out[oy:oy + im.height, ox:ox + im.width] = np.asarray(im)
    return out > 127, w / h


def iou(a, b):
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter / union) if union else 0.0


def silhouette_score(ref_mask, render_mask):
    """IoU of bounding-box-normalized silhouettes and an aspect-ratio score."""
    a, ar_a = normalized(ref_mask)
    b, ar_b = normalized(render_mask)
    prop = math.exp(-abs(math.log(max(ar_a, 1e-3) / max(ar_b, 1e-3))) * 2.0)
    return iou(a, b), prop


def contact_sheet(paths, labels, out, cell=128, cols=8):
    from PIL import ImageDraw
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 14)), (30, 33, 38))
    draw = ImageDraw.Draw(sheet)
    for i, (p, lab) in enumerate(zip(paths, labels)):
        x, y = (i % cols) * cell, (i // cols) * (cell + 14)
        try:
            sheet.paste(Image.open(p).convert("RGB").resize((cell, cell)), (x, y))
        except OSError:
            pass
        draw.text((x + 3, y + cell + 1), lab[:20], fill=(230, 230, 230))
    sheet.save(out)
    return out
