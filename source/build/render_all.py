"""Render every sprite (upright pieces, rigid rotation frames, books, bunny) into one atlas.

Atlas format: 8-bit greyscale PNG. 0 = empty, 1..255 = covered pixel with shade (v-1)/254.
Each piece gets true 3D rotation frames about its base rim: tipping left (positive angles, used for
toppling and for rocking) and a few small right tilts (negative angles, for rocking). The page drives
them with rigid-body physics, so frames are finer where the motion is slow.
"""
import json, math, os, sys, time
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pieces as P

OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

PIECES = [
    # name, factory, material, azimuth
    ('king', P.make_king, 'white', math.radians(8)),
    ('queen', P.make_queen, 'white', 0.0),
    ('bishop', P.make_bishop, 'white', math.radians(-45)),
    ('knight', P.make_knight, 'black', math.radians(-18)),
    ('rook', P.make_rook, 'black', math.radians(10)),
    ('rook_w', P.make_rook, 'white', math.radians(-24)),
    ('pawn', P.make_pawn, 'black', 0.0),
]
SLOW = list(range(2, 21, 2))      # the slow start of a tip, and rocking
MID = list(range(24, 61, 4))
RIGHT = [-2, -4, -6, -8, -10, -12]
BUNNY = [('bunny_sit', 'sit'), ('bunny_crouch', 'crouch'), ('bunny_leap', 'leap')]
BUNNY_SCALE = 21.0


def pose_points(pts, pivot, deg):
    th = math.radians(deg)
    c, s = math.cos(th), math.sin(th)
    x = pts[:, 0] - pivot
    wx = x * c - pts[:, 2] * s + pivot
    wz = x * s + pts[:, 2] * c
    return wx, wz


only = set(sys.argv[1:])
results, frames, phys = {}, {}, {}
for name, fac, mat, az in PIECES:
    if only and name not in only:
        continue
    t0 = time.time()
    f0, h, r = fac()
    f = P.with_azimuth(f0, az)
    results[name] = P.render(f, h, r, material=mat)
    pts = P.point_cloud(f, h, r)
    base = pts[pts[:, 2] < 0.2]
    pivL, pivR = float(base[:, 0].min()), float(base[:, 0].max())
    com = pts.mean(axis=0)
    critL = math.degrees(math.atan2(com[0] - pivL, com[2]))     # balance angle tipping left
    critR = math.degrees(math.atan2(pivR - com[0], com[2]))
    rest = P.rest_angle(pts, pivL)
    big = list(np.arange(66.0, rest - 2.5, 6.0))
    angles = RIGHT + [a for a in SLOW + MID + big if a < rest - 3.5] + [round(rest - 2, 2), rest]
    seq = []
    for k, deg in enumerate(angles):
        pivot = pivL if deg > 0 else pivR
        wx, wz = pose_points(pts, pivot, deg)
        lift = max(0.0, -float(wz.min()))
        wz = wz + lift
        g = P.toppled(f, math.radians(deg), pivot, lift)
        ys = pts[:, 1]
        sy = ys * P.SE + wz * P.CE
        bounds = (float(wx.min()) - 0.2, float(wx.max()) + 0.2, float(sy.min()) - 0.2, float(sy.max()) + 0.2)
        nm = f'{name}_r{k}'
        results[nm] = P.render(g, h, r, material=mat, ss=3, bounds=bounds)
        seq.append([nm, round(float(deg), 2)])
    frames[name] = seq
    phys[name] = {'rest': round(rest, 2), 'critL': round(critL, 2), 'critR': round(critR, 2)}
    print(f'{name}: rest {rest:.1f}, balance L {critL:.1f} R {critR:.1f}, {len(seq)} frames, {time.time()-t0:.1f}s', flush=True)

if not only or 'books' in only:
    f, h, r = P.make_books()
    results['books'] = P.render(f, h, r, material='white')
for name, pose in BUNNY:
    if only and name not in only:
        continue
    f = P.make_bunny(pose)
    results[name] = P.render(f, 1.25, 0.8, scale=BUNNY_SCALE, material='white',
                             azim=math.radians(-28), albedo_fn=P.bunny_albedo(pose))

if only and os.path.exists(f'{OUT}/sprites3.npy'):      # partial render: merge into the previous one
    prev = np.load(f'{OUT}/sprites3.npy', allow_pickle=True).item()
    prev.update(results); results = prev
    meta = json.load(open(f'{OUT}/atlas.json'))
    meta['frames'].update(frames); meta['phys'].update(phys)
    frames, phys = meta['frames'], meta['phys']
np.save(f'{OUT}/sprites3.npy', results, allow_pickle=True)

# ---- pack (shelf packing, tallest first)
items = sorted(results.items(), key=lambda kv: -kv[1][0].shape[0])
ATW = 1024
x = y = rowh = 0
rects = {}
for name, (shade, alpha, ax, ay) in items:
    hh, ww = shade.shape
    if x + ww > ATW:
        x, y, rowh = 0, y + rowh + 1, 0
    rects[name] = [x, y, ww, hh, round(float(ax), 2), round(float(ay), 2)]
    x += ww + 1
    rowh = max(rowh, hh)
ATH = y + rowh
atlas = np.zeros((ATH, ATW), np.uint8)
for name, (shade, alpha, ax, ay) in results.items():
    x0, y0, ww, hh = rects[name][:4]
    v = np.where(alpha >= 0.5, 1 + np.round(np.clip(shade, 0, 1) * 254), 0).astype(np.uint8)
    atlas[y0:y0 + hh, x0:x0 + ww] = v
Image.fromarray(atlas, 'L').save(f'{OUT}/atlas.png', optimize=True)
json.dump({'rects': rects, 'frames': frames, 'phys': phys}, open(f'{OUT}/atlas.json', 'w'), separators=(',', ':'))
print('atlas', atlas.shape, os.path.getsize(f'{OUT}/atlas.png'), 'bytes')
