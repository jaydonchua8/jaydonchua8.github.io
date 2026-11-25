"""Offline renderer for the portfolio's chess pieces.

Each piece is modelled as a signed distance field (Staunton profiles turned on a
lathe, plus CSG details), ray-marched with an orthographic camera at the board's
2:1 isometric angle (30 degree elevation), and shaded. The output is a shade map
plus coverage per sprite; the page dithers it at runtime with the same 8x8 Bayer
matrix as the floor, so pieces and board share one pixel grid.
"""
import json
import math
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw

ELEV = math.radians(30.0)
SE, CE = math.sin(ELEV), math.cos(ELEV)
RIGHT = np.array([1.0, 0.0, 0.0])
UP = np.array([0.0, SE, CE])
FWD = np.array([0.0, CE, -SE])          # into the screen and down
VIEW = -FWD
SCALE = 21.5                            # art pixels per piece unit (base radius ~1)


# ---------------------------------------------------------------- 2D helpers
def catmull(points, sub=8):
    """Smooth a polyline through control points (Catmull-Rom), keep endpoints."""
    p = [np.array(points[0])] + [np.array(q) for q in points] + [np.array(points[-1])]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for k in range(sub):
            t = k / sub
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(np.array(points[-1]))
    return [tuple(map(float, q)) for q in out]


class Field2D:
    """Signed distance to a 2D polygon, sampled on a grid (negative inside)."""

    def __init__(self, poly, xmin, xmax, ymin, ymax, res=0.004):
        self.xmin, self.ymin, self.res = xmin, ymin, res
        nx = int(round((xmax - xmin) / res)) + 1
        ny = int(round((ymax - ymin) / res)) + 1
        img = Image.new('L', (nx, ny), 0)
        ImageDraw.Draw(img).polygon([((x - xmin) / res, (y - ymin) / res) for x, y in poly], fill=255)
        m = np.array(img) > 127
        din = ndimage.distance_transform_edt(m)
        dout = ndimage.distance_transform_edt(~m)
        self.sdf = ((dout - din) * res).astype(np.float32)

    def __call__(self, x, y):
        ix = (x - self.xmin) / self.res
        iy = (y - self.ymin) / self.res
        return ndimage.map_coordinates(self.sdf, [iy, ix], order=1, mode='nearest')


# ---------------------------------------------------------------- 3D primitives
def length(v):
    return np.sqrt((v * v).sum(axis=-1))


def sd_sphere(p, c, r):
    return length(p - np.asarray(c)) - r


def sd_round_box(p, c, b, r=0.0):
    q = np.abs(p - np.asarray(c)) - (np.asarray(b) - r)
    return length(np.maximum(q, 0.0)) + np.minimum(q.max(axis=-1), 0.0) - r


def sd_ellipsoid(p, c, rad):
    rad = np.asarray(rad)
    q = (p - np.asarray(c))
    k0 = length(q / rad)
    k1 = length(q / (rad * rad))
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def sd_capsule(p, a, b, r):
    a, b = np.asarray(a), np.asarray(b)
    pa, ba = p - a, b - a
    h = np.clip((pa * ba).sum(-1) / (ba * ba).sum(), 0.0, 1.0)
    return length(pa - ba * h[:, None]) - r


def rot_z(p, ang):
    c, s = math.cos(ang), math.sin(ang)
    x, y = p[:, 0], p[:, 1]
    return np.stack([c * x - s * y, s * x + c * y, p[:, 2]], axis=-1)


def rot_x(p, ang):
    c, s = math.cos(ang), math.sin(ang)
    y, z = p[:, 1], p[:, 2]
    return np.stack([p[:, 0], c * y - s * z, s * y + c * z], axis=-1)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


class Lathe:
    """Solid of revolution from an (r, z) outline running bottom-axis -> top-axis."""

    def __init__(self, ctrl, sub=8):
        pts = catmull(ctrl, sub)
        zs = [z for _, z in pts]
        poly = [(0.0, pts[0][1])] + pts + [(0.0, pts[-1][1])]
        self.field = Field2D(poly, -0.2, 3.2, min(zs) - 0.6, max(zs) + 0.6)
        self.top = max(zs)
        self.rmax = max(r for r, _ in pts)

    def __call__(self, p):
        rho = np.sqrt(p[:, 0] ** 2 + p[:, 1] ** 2)
        return self.field(rho, p[:, 2])


# ---------------------------------------------------------------- the pieces
BASE = [(0.0, 0.0), (0.98, 0.0), (1.00, 0.06), (0.98, 0.13), (0.93, 0.17), (0.97, 0.22), (0.96, 0.28),
        (0.86, 0.34), (0.74, 0.37), (0.78, 0.42), (0.74, 0.47), (0.62, 0.52)]


def scaled_base(s):
    return [(r * s, z) for r, z in BASE]


def make_king():
    body = Lathe(scaled_base(1.0) + [
        (0.50, 0.62), (0.44, 0.85), (0.40, 1.30), (0.37, 1.90), (0.37, 2.30), (0.41, 2.52),
        (0.60, 2.58), (0.64, 2.64), (0.60, 2.70), (0.44, 2.74), (0.58, 2.80), (0.60, 2.86), (0.44, 2.92),
        (0.40, 3.02), (0.47, 3.30), (0.60, 3.60), (0.74, 3.84), (0.80, 3.94), (0.76, 4.00),
        (0.56, 4.03), (0.30, 4.07), (0.12, 4.10), (0.0, 4.11)])

    def f(p):
        d = body(p)
        cross_v = sd_round_box(p, (0, 0, 4.46), (0.085, 0.085, 0.36), 0.03)
        cross_h = sd_round_box(p, (0, 0, 4.56), (0.27, 0.085, 0.085), 0.03)
        return np.minimum(d, np.minimum(cross_v, cross_h))
    return f, 4.90, 1.05


def make_queen():
    body = Lathe(scaled_base(0.96) + [
        (0.48, 0.62), (0.42, 0.85), (0.37, 1.30), (0.33, 1.85), (0.34, 2.20), (0.38, 2.38),
        (0.57, 2.44), (0.60, 2.50), (0.56, 2.56), (0.41, 2.60), (0.54, 2.66), (0.56, 2.72), (0.40, 2.78),
        (0.38, 2.90), (0.46, 3.20), (0.58, 3.48), (0.68, 3.68), (0.70, 3.76), (0.62, 3.80),
        (0.50, 3.76), (0.36, 3.82), (0.20, 3.90), (0.08, 3.95), (0.0, 3.96)])

    def f(p):
        d = body(p)
        for k in range(10):
            a = k * 2 * math.pi / 10 + 0.3
            d = smin(d, sd_sphere(p, (0.64 * math.cos(a), 0.64 * math.sin(a), 3.84), 0.085), 0.04)
        d = smin(d, sd_sphere(p, (0, 0, 4.08), 0.14), 0.06)
        return d
    return f, 4.30, 1.0


def make_bishop():
    body = Lathe(scaled_base(0.90) + [
        (0.44, 0.62), (0.38, 0.85), (0.32, 1.25), (0.28, 1.70), (0.29, 1.90), (0.33, 2.00),
        (0.52, 2.06), (0.55, 2.12), (0.51, 2.18), (0.36, 2.22), (0.48, 2.28), (0.50, 2.33), (0.33, 2.39),
        (0.34, 2.46), (0.46, 2.62), (0.52, 2.82), (0.50, 3.02), (0.42, 3.22), (0.29, 3.40),
        (0.15, 3.52), (0.06, 3.58), (0.0, 3.59)])
    n = np.array([math.sin(math.radians(48)), 0.0, math.cos(math.radians(48))])
    p0 = np.array([0.04, 0.0, 3.02])

    def f(p):
        d = body(p)
        slab = np.abs((p - p0) @ n) - 0.06
        side = -(p[:, 0] + 0.14)              # cut most of the way through the mitre
        cut = np.maximum(slab, side)
        d = np.maximum(d, -cut)
        d = smin(d, sd_sphere(p, (0, 0, 3.68), 0.11), 0.05)
        return d
    return f, 3.82, 0.95


def make_rook():
    body = Lathe(scaled_base(0.94) + [
        (0.54, 0.62), (0.50, 0.90), (0.47, 1.40), (0.46, 1.70), (0.50, 1.78),
        (0.62, 1.84), (0.66, 1.92), (0.62, 1.98), (0.66, 2.04), (0.68, 2.12), (0.68, 2.50),
        (0.52, 2.50), (0.50, 2.34), (0.0, 2.34)])

    def f(p):
        d = body(p)
        notch = None
        for k in range(4):
            q = rot_z(p, -(k * math.pi / 2 + math.pi / 4))
            b = sd_round_box(q, (0.62, 0.0, 2.50), (0.30, 0.11, 0.16), 0.01)
            notch = b if notch is None else np.minimum(notch, b)
        return np.maximum(d, -notch)
    return f, 2.70, 1.0


def make_pawn():
    body = Lathe(scaled_base(0.86) + [
        (0.42, 0.62), (0.36, 0.82), (0.30, 1.12), (0.27, 1.42), (0.29, 1.52),
        (0.47, 1.58), (0.49, 1.65), (0.45, 1.70), (0.29, 1.74), (0.23, 1.80), (0.0, 1.82)])

    def f(p):
        return smin(body(p), sd_sphere(p, (0, 0, 2.14), 0.40), 0.05)
    return f, 2.62, 0.9


def make_knight():
    base = Lathe(scaled_base(0.92) + [(0.56, 0.58), (0.0, 0.58)])
    head2d = [
        (0.46, 0.52), (0.56, 0.80), (0.62, 1.15), (0.62, 1.50), (0.57, 1.85), (0.48, 2.15),
        (0.36, 2.42), (0.22, 2.64), (0.08, 2.78), (-0.06, 2.80), (-0.22, 2.70), (-0.40, 2.52),
        (-0.58, 2.28), (-0.74, 2.04), (-0.84, 1.88), (-0.84, 1.78), (-0.74, 1.72), (-0.64, 1.70),
        (-0.56, 1.64), (-0.40, 1.62), (-0.26, 1.54), (-0.20, 1.40), (-0.30, 1.16), (-0.42, 0.92),
        (-0.48, 0.70), (-0.46, 0.52)]
    head2d = [(x * 1.08, 0.52 + (z - 0.52) * 1.22) for x, z in head2d]
    head = Field2D(catmull(head2d, 6) + [head2d[0]], -1.3, 1.1, 0.2, 3.9)
    rr = 0.07

    def f(p):
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        th = 0.33 - 0.08 * np.clip(-x, 0.0, 1.0)
        d2 = head(x, z) + rr
        wy = np.abs(y) - (th - rr)
        wx = d2
        d = np.minimum(np.maximum(wx, wy), 0.0) + np.sqrt(np.maximum(wx, 0) ** 2 + np.maximum(wy, 0) ** 2) - rr
        d = smin(d, base(p), 0.10)
        for s in (-1, 1):
            d = smin(d, sd_ellipsoid(p, (0.10, 0.14 * s, 3.36), (0.09, 0.055, 0.20)), 0.04)
            d = np.maximum(d, -sd_sphere(p, (-0.44, 0.30 * s, 2.64), 0.065))
            d = np.maximum(d, -sd_sphere(p, (-0.89, 0.14 * s, 2.14), 0.05))
        # mane: a ridge of small bumps down the back of the neck
        for i in range(7):
            t = i / 6
            mx, mz = 0.30 + 0.36 * t, 3.02 - 1.55 * t
            d = smin(d, sd_ellipsoid(p, (mx, 0.0, mz), (0.10, 0.13, 0.11)), 0.05)
        return d
    return f, 3.80, 1.10


def make_toppled(factory=None, rbase=0.90, phi_deg=7.0, shift=1.6):
    f0, h0, r0 = (factory or make_bishop)()
    phi = math.radians(phi_deg)
    ca, sa = math.cos(phi), math.sin(phi)
    k = math.sqrt(0.5)
    A = np.array([ca * k, -ca * k, -sa])         # piece axis: base at upper-left -> top at lower-right on screen
    B = np.array([k, k, 0.0])
    C = np.cross(A, B)
    o = np.array([0.0, 0.0, rbase]) - shift * np.array([k, -k, 0.0])
    def f(p):
        q = p - o
        return f0(np.stack([q @ B, q @ C, q @ A], axis=-1))
    return f, 1.9, 2.4


def make_books():
    k = math.sqrt(0.5)
    A2 = np.array([k, -k])     # long axis on the ground (runs down-right on screen)
    B2 = np.array([k, k])
    books = [  # (offset along A, along B, z centre, half length, half width, half thickness, twist deg)
        (0.00, -0.58, 0.12, 1.46, 0.21, 0.12, 0.0),
        (0.10, 0.00, 0.12, 1.40, 0.21, 0.12, 1.0),
        (-0.04, 0.58, 0.12, 1.44, 0.21, 0.12, -1.0),
    ]
    def f(p):
        a = p[:, 0] * A2[0] + p[:, 1] * A2[1]
        b = p[:, 0] * B2[0] + p[:, 1] * B2[1]
        d = None
        for (oa, ob, zc, hl, hw, ht, tw) in books:
            t = math.radians(tw); ct, st = math.cos(t), math.sin(t)
            la, lb = a - oa, b - ob
            la, lb = ct * la + st * lb, -st * la + ct * lb
            q = np.stack([la, lb, p[:, 2]], axis=-1)
            cover = sd_round_box(q, (0, 0, zc), (hl, hw, ht), 0.025)
            # pages sit slightly recessed between the covers on the three open sides
            groove = sd_round_box(q, (0.06, 0, zc), (hl + 0.02, hw + 0.02, ht * 0.62), 0.0)
            inner = sd_round_box(q, (0.06, 0, zc), (hl - 0.05, hw - 0.05, ht * 0.7), 0.0)
            book = np.maximum(cover, -np.maximum(groove, -inner))
            d = book if d is None else np.minimum(d, book)
        return d
    return f, 0.62, 1.6


def make_book():
    def f(p):
        cover = sd_round_box(p, (0, 0, 0.13), (0.95, 0.66, 0.13), 0.03)
        pages = sd_round_box(p, (0.03, 0, 0.13), (0.94, 0.62, 0.105), 0.01)
        groove = np.maximum(-(sd_round_box(p, (-0.95, 0, 0.13), (0.1, 0.70, 0.11), 0.0)), 0)
        book1 = np.minimum(np.maximum(cover, -sd_round_box(p, (0.06, 0, 0.13), (0.96, 0.63, 0.10), 0.0)), pages)
        q = rot_z(p - np.array([0.08, 0.02, 0.26]), 0.22)
        top = sd_round_box(q, (0, 0, 0.11), (0.80, 0.56, 0.11), 0.03)
        topages = sd_round_box(q, (0.03, 0, 0.11), (0.79, 0.52, 0.085), 0.01)
        book2 = np.minimum(np.maximum(top, -sd_round_box(q, (0.06, 0, 0.11), (0.81, 0.53, 0.08), 0.0)), topages)
        return np.minimum(book1, book2) + 0 * groove
    return f, 0.62, 1.25


# ---------------------------------------------------------------- bunny frames
def make_bunny(pose):
    def f(p):
        if pose == 'sit':
            body = sd_ellipsoid(p, (0.05, 0, 0.30), (0.40, 0.28, 0.30))
            haunch = sd_sphere(p, (0.20, 0, 0.26), 0.25)
            head_c, ear_tip = (-0.33, 0, 0.62), (-0.10, 0.0, 1.15)
        elif pose == 'crouch':
            body = sd_ellipsoid(p, (0.05, 0, 0.24), (0.44, 0.29, 0.24))
            haunch = sd_sphere(p, (0.22, 0, 0.21), 0.22)
            head_c, ear_tip = (-0.38, 0, 0.48), (0.05, 0.0, 0.92)
        else:  # leap
            body = sd_ellipsoid(p, (0.0, 0, 0.36), (0.50, 0.26, 0.24))
            haunch = sd_sphere(p, (0.28, 0, 0.30), 0.20)
            head_c, ear_tip = (-0.46, 0, 0.56), (0.12, 0.0, 0.98)
        d = smin(body, haunch, 0.10)
        d = smin(d, sd_ellipsoid(p, head_c, (0.20, 0.17, 0.17)), 0.08)
        hx, hy, hz = head_c
        for s in (-1, 1):
            base = (hx + 0.08, 0.07 * s, hz + 0.12)
            tip = (ear_tip[0], 0.10 * s, ear_tip[2])
            d = smin(d, sd_capsule(p, base, (tip[0], 0.15 * s, tip[2] + 0.10), 0.072), 0.03)
        d = smin(d, sd_sphere(p, (0.45 if pose != 'leap' else 0.52, 0, 0.40), 0.09), 0.03)
        if pose == 'leap':
            d = smin(d, sd_capsule(p, (0.30, 0.10, 0.22), (0.62, 0.12, 0.10), 0.06), 0.04)
            d = smin(d, sd_capsule(p, (0.30, -0.10, 0.22), (0.62, -0.12, 0.10), 0.06), 0.04)
            d = smin(d, sd_capsule(p, (-0.40, 0.08, 0.30), (-0.62, 0.08, 0.16), 0.045), 0.03)
        else:
            d = smin(d, sd_ellipsoid(p, (-0.30, 0.10, 0.05), (0.10, 0.05, 0.05)), 0.03)
            d = smin(d, sd_ellipsoid(p, (-0.30, -0.10, 0.05), (0.10, 0.05, 0.05)), 0.03)
        return d
    return f


# ---------------------------------------------------------------- renderer
def render(sdf, height, radius, *, scale=SCALE, ss=4, azim=0.0, material='white',
           albedo_fn=None, light=(0.35, -0.30, 0.89), steps=160, bounds=None):
    """Ray-march `sdf` and return (shade, alpha, anchor_x, anchor_y) at art resolution."""
    L = np.array(light, float); L /= np.linalg.norm(L)
    H = L + VIEW; H /= np.linalg.norm(H)
    R = radius * 1.15
    if bounds is None:
        sx0, sx1 = -R, R
        sy0, sy1 = -R * SE, R * SE + height * CE
    else:
        sx0, sx1, sy0, sy1 = bounds
    px = 1.0 / (scale * ss)
    pad = 2
    W = int(math.ceil((sx1 - sx0) * scale)) + 2 * pad
    Hh = int(math.ceil((sy1 - sy0) * scale)) + 2 * pad
    # anchor (ground origin) in art pixel coordinates
    ax = pad - sx0 * scale
    ay = pad + sy1 * scale
    jj, ii = np.mgrid[0:Hh * ss, 0:W * ss]
    sx = (ii + 0.5) * px - ax / scale
    sy = ay / scale - (jj + 0.5) * px
    sx, sy = sx.ravel(), sy.ravel()
    origin = sx[:, None] * RIGHT + sy[:, None] * UP - 8.0 * FWD
    ca, sa = math.cos(azim), math.sin(azim)

    def world_sdf(p):
        # rotate the piece by azim around z: evaluate the sdf in the piece frame
        q = np.stack([ca * p[:, 0] + sa * p[:, 1], -sa * p[:, 0] + ca * p[:, 1], p[:, 2]], axis=-1)
        return sdf(q)

    n = origin.shape[0]
    t = np.zeros(n)
    hit = np.zeros(n, bool)
    alive = np.arange(n)
    tmax = 16.0
    for _ in range(steps):
        if alive.size == 0:
            break
        p = origin[alive] + t[alive, None] * FWD
        d = world_sdf(p)
        t[alive] += np.maximum(d * 0.8, 0.0015)
        done_hit = d < 0.002
        hit[alive[done_hit]] = True
        keep = (~done_hit) & (t[alive] < tmax)
        alive = alive[keep]
    idx = np.flatnonzero(hit)
    p = origin[idx] + t[idx, None] * FWD
    e = 0.004
    nrm = np.zeros_like(p)
    for k in range(3):
        dv = np.zeros(3); dv[k] = e
        nrm[:, k] = world_sdf(p + dv) - world_sdf(p - dv)
    nrm /= np.maximum(length(nrm)[:, None], 1e-9)
    # ambient occlusion
    ao = np.ones(len(idx))
    for i in range(1, 6):
        h = 0.035 * i
        ao -= (h - world_sdf(p + nrm * h)) * (0.9 / i) * 1.6
    ao = np.clip(ao, 0.25, 1.0)
    diff = np.clip(nrm @ L, 0.0, 1.0)
    top = np.clip(nrm[:, 2], 0.0, 1.0)
    spec = np.clip(nrm @ H, 0.0, 1.0)
    if material == 'white':
        s = 0.16 + 0.74 * diff * ao + 0.42 * top * ao + 0.25 * spec ** 24
    else:
        rim = np.clip(1.0 - np.abs(nrm @ VIEW), 0.0, 1.0)
        s = 0.03 + 0.34 * diff * ao + 0.12 * top * ao + 0.34 * rim ** 2.0 + 0.75 * spec ** 22
    if albedo_fn is not None:
        to_local = getattr(sdf, 'to_local', None)
        s = s * albedo_fn(to_local(p) if to_local else p)
    shade_ss = np.zeros(n); shade_ss[idx] = np.clip(s, 0.0, 1.0)
    cov_ss = np.zeros(n); cov_ss[idx] = 1.0
    shade_ss = shade_ss.reshape(Hh, ss, W, ss)
    cov_ss = cov_ss.reshape(Hh, ss, W, ss)
    alpha = cov_ss.mean(axis=(1, 3))
    tot = shade_ss.sum(axis=(1, 3))
    shade = np.where(alpha > 0, tot / np.maximum(cov_ss.sum(axis=(1, 3)), 1e-9), 0.0)
    # trim empty borders
    ys, xs = np.nonzero(alpha > 0.02)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return shade[y0:y1, x0:x1], alpha[y0:y1, x0:x1], ax - x0, ay - y0


BAYER8 = np.array([
    [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]])


def dither_preview(shade, alpha, gain=1.0):
    h, w = shade.shape
    th = (BAYER8[np.arange(h)[:, None] % 8, np.arange(w)[None, :] % 8] + 0.5) / 64
    on = (shade * gain > th) & (alpha >= 0.5)
    img = np.full((h, w, 3), (12, 12, 14), np.uint8)
    img[on] = (211, 253, 233)
    return img


def bunny_albedo(pose):
    eye = {'sit': (-0.40, 0.0, 0.66), 'crouch': (-0.45, 0.0, 0.52), 'leap': (-0.53, 0.0, 0.60)}[pose]
    def f(pt):
        # dark eye on both sides of the head
        q = pt - np.array(eye)
        d = np.sqrt(q[:, 0] ** 2 + (np.abs(q[:, 1]) - 0.13) ** 2 + q[:, 2] ** 2)
        return np.where(d < 0.06, 0.0, 1.0)
    return f


# ---------------------------------------------------------------- toppling
def _local(sdf):
    return getattr(sdf, 'to_local', lambda p: p)


# ---------------------------------------------------------------- surface texture
def _hash3(ix, iy, iz):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def value_noise(p, freq):
    q = p * freq
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3.0 - 2.0 * f)
    out = 0.0
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                w = ((f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1])
                     * (f[:, 2] if dz else 1 - f[:, 2]))
                out = out + w * _hash3(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz)
    return out


def piece_texture(p):
    """Surface mottling for the pieces: layered value noise in the piece's own frame, plus a fine grain."""
    n = (0.55 * value_noise(p, 7.0) + 0.30 * value_noise(p, 17.0) + 0.15 * value_noise(p, 41.0))
    grain = value_noise(p, 95.0)
    k = 0.72 + 0.9 * (n - 0.5) + 0.22 * (grain - 0.5)
    return np.clip(k, 0.25, 1.25)


def with_azimuth(sdf, azim):
    ca, sa = math.cos(azim), math.sin(azim)
    def f(p):
        q = np.stack([ca * p[:, 0] + sa * p[:, 1], -sa * p[:, 0] + ca * p[:, 1], p[:, 2]], axis=-1)
        return sdf(q)
    def to_local(p):
        q = np.stack([ca * p[:, 0] + sa * p[:, 1], -sa * p[:, 0] + ca * p[:, 1], p[:, 2]], axis=-1)
        return _local(sdf)(q)
    f.to_local = to_local
    return f


def point_cloud(sdf, height, radius, res=0.03):
    """Interior sample points of a piece in its local frame (used to find ground contact)."""
    R = radius * 1.25
    xs = np.arange(-R, R, res); ys = np.arange(-R, R, res); zs = np.arange(-0.05, height + 0.3, res)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=-1)
    keep = []
    for i in range(0, len(P), 400000):
        chunk = P[i:i + 400000]
        keep.append(chunk[sdf(chunk) < 0])
    return np.concatenate(keep)


def topple_pose(pts, pivot_x, theta):
    """World z of each local point after tipping by theta (rad) toward -x about the base edge."""
    c, s = math.cos(theta), math.sin(theta)
    x = pts[:, 0] - pivot_x
    return x * s + pts[:, 2] * c


def rest_angle(pts, pivot_x):
    """First angle where something other than the base edge reaches the ground."""
    far = np.hypot(pts[:, 0] - pivot_x, pts[:, 2]) > 0.45
    q = pts[far]
    for deg in np.arange(40.0, 120.0, 0.25):
        if topple_pose(q, pivot_x, math.radians(deg)).min() <= 0.0:
            return float(deg)
    return 90.0


def toppled(sdf, theta, pivot_x, lift):
    c, s = math.cos(theta), math.sin(theta)
    def f(p):
        x = p[:, 0] - pivot_x
        z = p[:, 2] - lift
        lx = x * c + z * s
        lz = -x * s + z * c
        return sdf(np.stack([lx + pivot_x, p[:, 1], lz], axis=-1))
    def to_local(p):
        x = p[:, 0] - pivot_x
        z = p[:, 2] - lift
        lx = x * c + z * s
        lz = -x * s + z * c
        return _local(sdf)(np.stack([lx + pivot_x, p[:, 1], lz], axis=-1))
    f.to_local = to_local
    return f
