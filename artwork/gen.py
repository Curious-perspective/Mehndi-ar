"""Generates the mehndi artwork (palm + back) as SVG on a canonical hand template.
The template landmark positions (MediaPipe 21-point order) are written into the SVG so the
AR page can later warp the art onto a live hand."""
import math, json, sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

INK = "#4a1c0c"      # henna line
INK2 = "#5e2611"     # fine detail
FILL = "#3a1407"     # solid fill (caps, dots)
SKIN = "#f0cfb2"
EDGE = "#c79f80"

# ---------- canonical hand template (palm view, fingers up, thumb on viewer's left) ----------
L = {
    0: (500, 1170),
    1: (408, 1090), 2: (338, 1005), 3: (282, 930), 4: (240, 862),
    5: (385, 790), 6: (362, 615), 7: (350, 505), 8: (343, 412),
    9: (500, 765), 10: (500, 572), 11: (500, 450), 12: (500, 352),
    13: (612, 778), 14: (628, 598), 15: (638, 488), 16: (644, 402),
    17: (712, 820), 18: (748, 672), 19: (768, 585), 20: (782, 515),
}
FINGERS = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16], [17, 18, 19, 20]]
FW = [94, 82, 86, 82, 72]   # finger widths (thumb..pinky)
W, H = 1000, 1650

def P(i): return L[i]
def lerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
def ang(a, b): return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
def f(x): return f"{x:.1f}"

# ---------- hand shape ----------
def palm_path():
    return ("M420,1180 C385,1150 372,1110 362,1060 C352,1000 352,940 350,880 C348,830 352,790 368,768 "
            "C400,742 450,736 500,734 C560,734 620,740 672,762 C720,782 748,810 756,860 "
            "C764,930 756,1010 736,1080 C722,1130 700,1168 650,1185 C590,1200 470,1200 420,1180 Z")

def hand_shapes(color, extra=0):
    s = [f'<path d="{palm_path()}" fill="{color}" stroke="{color}" stroke-width="{40 + extra * 2}" stroke-linejoin="round"/>']
    # forearm
    s.append(f'<path d="M400,1150 C392,1300 396,1500 404,1650 L626,1650 C632,1500 638,1300 640,1150 Z" fill="{color}" stroke="{color}" stroke-width="{2 + extra * 2}" stroke-linejoin="round"/>')
    for fi, fg in enumerate(FINGERS):
        chain = [P(k) for k in fg]
        if fi == 0: chain = [(440, 1110)] + chain[1:]
        d = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in chain)
        s.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{FW[fi] + extra * 2}" stroke-linecap="round" stroke-linejoin="round"/>')
    return "\n".join(s)

# ---------- primitives ----------
def line(a, b, w=2.2, c=INK): return f'<line x1="{f(a[0])}" y1="{f(a[1])}" x2="{f(b[0])}" y2="{f(b[1])}" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>'
def circ(c0, r, w=2, c=INK, fill="none"): return f'<circle cx="{f(c0[0])}" cy="{f(c0[1])}" r="{f(r)}" fill="{fill}" stroke="{c if fill == "none" else "none"}" stroke-width="{w}"/>'
def dot(c0, r, c=FILL): return f'<circle cx="{f(c0[0])}" cy="{f(c0[1])}" r="{f(r)}" fill="{c}"/>'
def g(content, tx=0, ty=0, rot=0, sc=1):
    return f'<g transform="translate({f(tx)},{f(ty)}) rotate({f(rot)}) scale({sc})">{content}</g>'

def spiral(r, turns=2.2, w=1.8, c=INK):
    pts = []
    n = 60
    for i in range(n + 1):
        t = i / n
        a = t * turns * 2 * math.pi
        rr = r * t
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return f'<path d="M' + " L".join(f"{f(x)},{f(y)}" for x, y in pts) + f'" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>'

def teardrop(length, width, fill=FILL, stroke=None, w=1.6):
    # points along -y, base at 0,0
    d = f"M0,0 C{f(width)},{f(-length * 0.35)} {f(width * 0.4)},{f(-length * 0.85)} 0,{f(-length)} C{f(-width * 0.4)},{f(-length * 0.85)} {f(-width)},{f(-length * 0.35)} 0,0 Z"
    st = f'stroke="{stroke}" stroke-width="{w}"' if stroke else ""
    return f'<path d="{d}" fill="{fill}" {st}/>'

def petal_ring(r0, r1, n, width_k=0.5, w=2, fill_alt=False, hatch=False, rot0=0):
    out = []
    for i in range(n):
        a = rot0 + i * 360 / n
        L_ = r1 - r0
        wd = 2 * math.pi * r0 / n * width_k + L_ * 0.12
        d = f"M0,{f(-r0)} C{f(wd)},{f(-r0 - L_ * 0.3)} {f(wd * 0.5)},{f(-r1 + L_ * 0.12)} 0,{f(-r1)} C{f(-wd * 0.5)},{f(-r1 + L_ * 0.12)} {f(-wd)},{f(-r0 - L_ * 0.3)} 0,{f(-r0)} Z"
        fill = FILL if (fill_alt and i % 2 == 0) else "none"
        p = f'<path d="{d}" fill="{fill}" stroke="{INK}" stroke-width="{w}" stroke-linejoin="round"/>'
        if hatch and fill == "none":
            # inner vein + short hatch lines
            p += line((0, -r0 - L_ * 0.12), (0, -r1 + L_ * 0.2), 1.1, INK2)
            for k in range(1, 4):
                y = -r0 - L_ * (0.2 + k * 0.17)
                ww = wd * (0.55 - k * 0.1)
                p += line((-ww * 0.15, y + 3), (-ww, y - 4), 1.0, INK2) + line((ww * 0.15, y + 3), (ww, y - 4), 1.0, INK2)
        out.append(f'<g transform="rotate({f(a)})">{p}</g>')
    return "".join(out)

def round_petal_ring(r0, r1, n, w=2.4):
    out = []
    span = 2 * math.pi * r0 / n
    for i in range(n):
        a = i * 360 / n
        L_ = r1 - r0; hw = span * 0.62
        d = (f"M{f(-span * 0.32)},{f(-r0)} C{f(-hw)},{f(-r0 - L_ * 0.55)} {f(-hw * 0.55)},{f(-r1)} 0,{f(-r1)} "
             f"C{f(hw * 0.55)},{f(-r1)} {f(hw)},{f(-r0 - L_ * 0.55)} {f(span * 0.32)},{f(-r0)} Z")
        pid = f"rp{r0}_{i}"
        p = f'<clipPath id="{pid}"><path d="{d}"/></clipPath><g clip-path="url(#{pid})">'
        for k in range(1, 6):   # concentric inner outlines (petal-within-petal) like fine cone work
            sc = 1 - k * 0.15
            p += f'<path d="{d}" fill="none" stroke="{INK2}" stroke-width="1.1" transform="translate(0,{f(-r0 * (1 - sc))}) scale({f(sc)})"/>'
        p += "</g>"
        p += f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{w}" stroke-linejoin="round"/>'
        p += dot((0, -r0 - L_ * 0.18), 2.4)
        out.append(f'<g transform="rotate({f(a)})">{p}</g>')
    return "".join(out)

def scallop_ring(r, n, depth, w=2):
    pts = []
    d = ""
    for i in range(n):
        a0 = 2 * math.pi * i / n; a1 = 2 * math.pi * (i + 1) / n; am = (a0 + a1) / 2
        p0 = (r * math.cos(a0), r * math.sin(a0)); p1 = (r * math.cos(a1), r * math.sin(a1))
        c = ((r + depth) * math.cos(am), (r + depth) * math.sin(am))
        if i == 0: d += f"M{f(p0[0])},{f(p0[1])} "
        d += f"Q{f(c[0])},{f(c[1])} {f(p1[0])},{f(p1[1])} "
    return f'<path d="{d}Z" fill="none" stroke="{INK}" stroke-width="{w}"/>'

def dot_ring(r, n, rad, rot=0):
    return "".join(dot((r * math.cos(math.radians(rot + i * 360 / n)), r * math.sin(math.radians(rot + i * 360 / n))), rad) for i in range(n))

def mini_flower(r, n=6, filled_center=True):
    out = petal_ring(r * 0.28, r, n, width_k=0.75, w=1.5)
    out += circ((0, 0), r * 0.26, 1.5)
    out += dot((0, 0), r * 0.12)
    return out

def four_petal_star(r):
    out = ""
    for a in (0, 90, 180, 270):
        out += f'<g transform="rotate({a})">{teardrop(r, r * 0.38, fill=FILL)}</g>'
    return out + dot((0, 0), r * 0.18, "#f0cfb2")

# ---------- finger segment helpers (local frame: y along finger, towards fingertip = -y) ----------
def seg_frame(a, b):
    """returns (cx, cy, rot) so that local -y points from a to b"""
    c = lerp(a, b, 0.5)
    rot = ang(a, b) + 90
    return c, rot

def band(wd, lines=3, gap=7, w=2.2, fringe=False):
    out = ""
    for k in range(lines):
        y = (k - (lines - 1) / 2) * gap
        out += line((-wd / 2, y), (wd / 2, y), w)
    if fringe:
        y0 = -(lines - 1) / 2 * gap - 2
        n = int(wd / 6)
        for k in range(n + 1):
            x = -wd / 2 + k * wd / n
            out += line((x, y0), (x, y0 - 10), 1.4)
        out += line((-wd / 2, y0 - 12), (wd / 2, y0 - 12), 1.8)
    return out

# ---------- PALM ----------
def palm_art():
    out = []
    THUMB_LATTICE = None
    # --- fingertip caps + finger bands ---
    for fi, fg in enumerate(FINGERS):
        p1, p2, p3, p4 = [P(k) for k in fg]
        wd = FW[fi]
        # solid cap: covers distal phalanx from 45% to the tip (round end)
        a = lerp(p3, p4, 0.35)
        tipdir = ((p4[0] - p3[0]) / dist(p3, p4), (p4[1] - p3[1]) / dist(p3, p4))
        b = (p4[0] + tipdir[0] * wd * 0.05, p4[1] + tipdir[1] * wd * 0.05)
        out.append(line(a, b, wd * 0.97, FILL))
        c, rot = seg_frame(p3, p4)
        # line band just below the cap
        bc = lerp(p3, p4, 0.22)
        out.append(g(band(wd * 0.92, 2, 6, 2), bc[0], bc[1], rot))
        # middle phalanx: band + spiral row or mini flower
        c, rot = seg_frame(p2, p3)
        if fi == 0:
            THUMB_LATTICE = (c, rot)
        else:
            motif = band(wd * 0.94, 2, 6, 2, fringe=True)
            motif += g(mini_flower(wd * 0.36), 0, 30)
            motif += "".join(dot((0, y), 2.6) for y in (-30, -38))
            out.append(g(motif, c[0], c[1], rot))
        # proximal phalanx
        c, rot = seg_frame(p1, p2)
        if fi == 0:
            c, rot = THUMB_LATTICE
            # thumb lattice with tiny flowers in the cells, bounded by bands
            lw_ = wd * 0.92; lh = dist(p2, p3) * 0.8
            cell = 21
            lat = f'<clipPath id="thumbclip"><rect x="{f(-lw_ / 2)}" y="{f(-lh / 2)}" width="{f(lw_)}" height="{f(lh)}"/></clipPath><g clip-path="url(#thumbclip)">'
            k = -6
            while k <= 6:
                lat += line((k * cell - lh, -lh), (k * cell + lh, lh), 1.8)
                lat += line((k * cell + lh, -lh), (k * cell - lh, lh), 1.8)
                k += 1
            for i in range(-5, 6):
                for j in range(-6, 7):
                    x = i * cell; y = j * cell
                    if (i + j) % 2 == 0:
                        lat += g(four_petal_star(5.5), x, y + cell * 0)
            lat += "</g>"
            out.append(g(lat + g(band(lw_, 2, 6, 2.2), 0, -lh / 2 - 6) + g(band(lw_, 2, 6, 2.2), 0, lh / 2 + 6), c[0], c[1], rot))
        else:
            m = ""
            m += g(spiral(wd * 0.27, 2.6, 2) + circ((0, 0), wd * 0.31, 2.2) + dot_ring(wd * 0.4, 12, 2.2), 0, -12)
            # leafy lotus bud below the spiral
            m += g(teardrop(26, 9, fill="none", stroke=INK, w=1.6) + teardrop(16, 5), 0, 34)
            m += g(teardrop(20, 6, fill="none", stroke=INK, w=1.4), -9, 34, -35) + g(teardrop(20, 6, fill="none", stroke=INK, w=1.4), 9, 34, 35)
            m += g(band(wd * 0.94, 2, 6, 2.0), 0, -dist(p1, p2) * 0.42)
            out.append(g(m, c[0], c[1], rot))

    # --- arch of half-flowers along the knuckle line ---
    for (x, y, r) in [(418, 774, 32), (500, 764, 34), (584, 770, 32), (664, 790, 28)]:
        hf = f'<path d="M{-r},0 A{r},{r} 0 0 1 {r},0" fill="none" stroke="{INK}" stroke-width="2"/>'
        hf += petal_ring(r * 0.35, r * 0.95, 7, 0.6, 1.5).replace("<g transform", "<g style='' transform")
        hf = f'<clipPath id="hfc{x}"><rect x="{-r - 4}" y="{-r - 4}" width="{2 * r + 8}" height="{r + 4}"/></clipPath><g clip-path="url(#hfc{x})">{hf}</g>'
        hf += dot((0, 0), r * 0.18) + line((-r - 2, 2), (r + 2, 2), 2.2)
        out.append(g(hf, x, y + 4, 180 + 0))
    # --- central medallion with names ---
    cx, cy = 552, 985
    med = ""
    med += round_petal_ring(136, 182, 14, 2.6)
    for i in range(14):   # dark wedges between the petals
        med += f'<g transform="rotate({i * 360 / 14 + 180 / 14})">' + g(teardrop(34, 7), 0, -136) + "</g>"
    med += scallop_ring(126, 24, 9, 2.2)
    med += f'<circle r="117" fill="none" stroke="{FILL}" stroke-width="7"/>'
    med += dot_ring(108, 40, 2.2)
    med += circ((0, 0), 101, 1.8)
    med += dot_ring(186, 32, 2.8, rot=5.6)
    for i in range(8):
        med += f'<g transform="rotate({i * 45 + 11.25})">' + g(teardrop(22, 8), 0, -194) + "</g>"
    out.append(g(med, cx, cy, 0, 0.86))
    out.append(("NAMES", cx, cy))

    # --- vine with leaves down the pinky-side heel ---
    vine = f'<path d="M738,860 C760,930 752,1010 712,1090" fill="none" stroke="{INK}" stroke-width="2.2"/>'
    for t, side in [(0.12, 1), (0.3, -1), (0.48, 1), (0.66, -1), (0.84, 1)]:
        # cubic point
        p0, p1, p2, p3 = (738, 860), (760, 930), (752, 1010), (712, 1090)
        def bez(t):
            return tuple((1 - t) ** 3 * p0[i] + 3 * (1 - t) ** 2 * t * p1[i] + 3 * (1 - t) * t * t * p2[i] + t ** 3 * p3[i] for i in range(2))
        q = bez(t); q2 = bez(t + 0.01)
        a_ = ang(q, q2)
        vine += g(teardrop(22, 8, fill="none" if side < 0 else FILL, stroke=INK, w=1.4), q[0], q[1], a_ + 90 + side * 55)
    out.append(vine)
    # thumb-base paisley-ish swirl stack
    tv = f'<path d="M430,1120 C392,1060 372,990 372,900" fill="none" stroke="{INK}" stroke-width="2.2"/>'
    for (x, y, a_, fl) in [(424, 1100, -150, 1), (400, 1060, 30, 0), (386, 1015, -150, 1), (377, 965, 30, 0), (373, 915, -150, 1)]:
        tv += g(teardrop(22, 8, fill=FILL if fl else "none", stroke=INK, w=1.4), x, y, a_)
    tv += g(spiral(10, 1.8, 1.8), 372, 890)
    out.append(tv)
    # --- half-sun at palm base (facing up) ---
    # --- wrist cuff ---
    out.append(cuff(1172))
    # --- trailing half-sun on the forearm (facing down) ---
    out.append(g(half_sun(96), 518, 1452, 180))
    out.append(g(teardrop(22, 8), 518, 1562, 180))
    out.append(dot((518, 1596), 6))
    return out

def half_sun(r):
    s = ""
    s += f'<clipPath id="hs{r}"><rect x="{-r - 30}" y="{-r - 30}" width="{2 * r + 60}" height="{r + 30}"/></clipPath><g clip-path="url(#hs{r})">'
    s += petal_ring(r * 0.62, r * 0.96, 18, 0.5, 1.8, hatch=False, fill_alt=True)
    s += scallop_ring(r * 0.58, 16, 6, 1.6)
    s += petal_ring(r * 0.26, r * 0.52, 10, 0.6, 1.6, hatch=True)
    s += f'<circle r="{f(r * 0.6)}" fill="none" stroke="{FILL}" stroke-width="4"/>'
    s += dot_ring(r * 1.06, 26, 2.2)
    s += "</g>"
    s += f'<path d="M{-r * 0.2},0 A{r * 0.2},{r * 0.2} 0 0 1 {r * 0.2},0 Z" fill="{FILL}"/>'
    s += line((-r - 8, 2), (r + 8, 2), 3)
    return s

def cuff(y0):
    xl, xr = 398, 642
    s = ""
    y = y0
    def hl(y, w=2.2): return line((xl, y), (xr, y), w)
    s += hl(y, 3.4); y += 8
    s += hl(y, 1.6); y += 10
    for k in range(14): s += dot((xl + 10 + k * (xr - xl - 20) / 13, y), 3.4)
    y += 10; s += hl(y, 1.6); y += 6
    # leaf chain (chevron leaves) band
    s += hl(y, 2.4); y += 18
    n = 12
    for k in range(n):
        x = xl + 12 + k * (xr - xl - 24) / (n - 1)
        s += g(teardrop(15, 5.5, fill=FILL), x, y, -60) + g(teardrop(15, 5.5, fill="none", stroke=INK, w=1.3), x, y, 60)
    s += line((xl, y), (xr, y), 1.4)
    y += 16; s += hl(y, 2.4); y += 10
    # lattice band with dots
    yA = y; y += 46
    lat = f'<clipPath id="cufflat"><rect x="{xl}" y="{yA}" width="{xr - xl}" height="{y - yA}"/></clipPath><g clip-path="url(#cufflat)">'
    for k in range(-2, 16):
        x = xl + k * 23
        lat += line((x, yA), (x + 46, y), 1.6) + line((x + 46, yA), (x, y), 1.6)
    lat += "</g>"
    for k in range(12):
        lat += dot((xl + 12.5 + k * 23, (yA + y) / 2), 2.6)
    s += lat + hl(yA, 2.2) + hl(y, 2.2); y += 8
    s += hl(y, 1.6); y += 10
    # scallop teeth
    n = 13; s_ = ""
    for k in range(n):
        x0 = xl + k * (xr - xl) / n; x1 = xl + (k + 1) * (xr - xl) / n
        s_ += f'<path d="M{f(x0)},{f(y)} Q{f((x0 + x1) / 2)},{f(y + 22)} {f(x1)},{f(y)}" fill="none" stroke="{INK}" stroke-width="2"/>'
        s_ += dot(((x0 + x1) / 2, y + 9), 2.4)
    s += s_ + hl(y, 2.4)
    return s

# ---------- BACK ----------
def back_art():
    out = []
    # finger bands à la reference 2: fringe band on the middle phalanx, 3 dots towards the knuckle, leaves hanging to the tip
    for fi, fg in enumerate(FINGERS):
        p1, p2, p3, p4 = [P(k) for k in fg]
        wd = FW[fi]
        c = lerp(p2, p3, 0.55); rot = ang(p2, p3) + 90
        m = ""
        # local frame: −y = towards the fingertip. Band, fringe on the knuckle side, dots towards the knuckle, leaves to the tip
        m += line((-wd * 0.47, 0), (wd * 0.47, 0), 3.4) + line((-wd * 0.47, -8), (wd * 0.47, -8), 2.2)
        n = 8
        for k in range(n + 1):
            x = -wd * 0.43 + k * wd * 0.86 / n
            m += line((x, 3), (x, 15), 1.6)
        m += f'<path d="M{f(-wd * 0.45)},16 Q0,27 {f(wd * 0.45)},16" fill="none" stroke="{INK}" stroke-width="2.2"/>'
        m += dot((0, 36), 7.5) + dot((0, 54), 4.2) + dot((0, 67), 2.8)
        for x_, a_, sz in [(-wd * 0.26, -14, 0.9), (0, 0, 1.05), (wd * 0.26, 14, 0.9)]:
            m += g(teardrop(wd * 0.7 * sz, wd * 0.12 * sz), x_, -11, a_)
        # this frame: −y along finger towards tip; we drew the dots at −y (towards tip) — flip so dots go knuckle-wards
        out.append(g(m, c[0], c[1], rot))
    # diagonal floral trail on the back of the hand (reference 3)
    out.append(g(shaded_flower(96, 5), 588, 1140, 12))
    out.append(g(paisley(140), 505, 1010, -28))
    out.append(g(shaded_flower(88, 4), 590, 868, -12))
    out.append(swirl_vine([(612, 800), (624, 745), (630, 690), (634, 630), (638, 575)]))
    out.append(dot_chain([(520, 1150), (430, 1085), (405, 985), (430, 890), (500, 838)], 11, r=4.4))
    out.append(dot_chain([(705, 1075), (728, 985), (712, 900), (678, 845)], 10, r=4))
    # delicate bracelet
    out.append(dot_chain([(404, 1262), (460, 1280), (520, 1286), (580, 1280), (636, 1262)], 8, r=3.4))
    out.append(g(teardrop(22, 8), 520, 1294, 180) + dot((520, 1326), 5))
    return out

def shaded_flower(r, n):
    s = ""
    for i in range(n):
        a = i * 360 / n
        # heart-shaped petal pointing -y
        d = (f"M0,{f(-r * 0.18)} C{f(r * 0.55)},{f(-r * 0.25)} {f(r * 0.72)},{f(-r * 0.95)} {f(r * 0.22)},{f(-r * 0.98)} "
             f"C{f(r * 0.08)},{f(-r * 0.98)} 0,{f(-r * 0.88)} 0,{f(-r * 0.82)} "
             f"C0,{f(-r * 0.88)} {f(-r * 0.08)},{f(-r * 0.98)} {f(-r * 0.22)},{f(-r * 0.98)} "
             f"C{f(-r * 0.72)},{f(-r * 0.95)} {f(-r * 0.55)},{f(-r * 0.25)} 0,{f(-r * 0.18)} Z")
        pid = f"pf{r}_{i}"
        petal = f'<clipPath id="{pid}"><path d="{d}"/></clipPath>'
        # shading: fine lines fanning out from the centre, denser/darker near the base
        sh = ""
        for k in range(-9, 10):
            t = k / 9
            sh += line((t * r * 0.08, -r * 0.2), (t * r * 0.62, -r * (0.55 + 0.12 * (1 - abs(t)))), 1.1, INK2)
        petal += f'<g clip-path="url(#{pid})">{sh}<path d="{d}" fill="{FILL}" opacity="0.18"/></g>'
        petal += f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="3.2" stroke-linejoin="round"/>'
        s += f'<g transform="rotate({f(a)})">{petal}</g>'
    s += circ((0, 0), r * 0.17, 3) + dot((0, 0), r * 0.08)
    return s

def paisley(sz):
    d = (f"M0,{f(sz * 0.5)} C{f(-sz * 0.62)},{f(sz * 0.45)} {f(-sz * 0.6)},{f(-sz * 0.35)} 0,{f(-sz * 0.38)} "
         f"C{f(sz * 0.42)},{f(-sz * 0.4)} {f(sz * 0.5)},{f(-sz * 0.05)} {f(sz * 0.3)},{f(-sz * 0.62)} "
         f"C{f(sz * 0.62)},{f(-sz * 0.2)} {f(sz * 0.55)},{f(sz * 0.5)} 0,{f(sz * 0.5)} Z")
    s = f'<clipPath id="pz{sz}"><path d="{d}"/></clipPath><g clip-path="url(#pz{sz})">'
    for k in range(-14, 15):
        y = k * sz * 0.045
        s += line((-sz, y + sz * 0.15), (sz, y - sz * 0.35), 1.1, INK2)
    s += f'<path d="{d}" fill="#f0cfb2" transform="scale(0.62) translate(-4,6)"/></g>'
    s += f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="3.2"/>'
    s += f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="2" transform="scale(0.62) translate(-4,6)"/>'
    s += g(spiral(sz * 0.16, 2, 2), -sz * 0.05, sz * 0.1)
    return s

def swirl_vine(pts):
    d = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in pts)
    s = f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>'
    for i, (x, y) in enumerate(pts[1:-1]):
        side = 1 if i % 2 else -1
        s += g(spiral(12, 1.6, 2), x + side * 18, y - 4)
        s += line((x, y), (x + side * 10, y - 4), 2)
        s += g(teardrop(16, 5, fill="none", stroke=INK, w=1.5), x, y, -side * 50)
    s += dot(pts[-1], 4)
    return s

def dot_chain(pts, step, r=3.2):
    # Catmull-Rom through pts, dots every `step` px
    def cr(p0, p1, p2, p3, t):
        return tuple(0.5 * ((2 * p1[i]) + (-p0[i] + p2[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t * t + (-p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]) * t ** 3) for i in range(2))
    ext = [pts[0]] + pts + [pts[-1]]
    samples = []
    for i in range(len(pts) - 1):
        for k in range(40):
            samples.append(cr(ext[i], ext[i + 1], ext[i + 2], ext[i + 3], k / 40))
    samples.append(pts[-1])
    s = ""; acc = 0; last = samples[0]; s += dot(last, r)
    for q in samples[1:]:
        acc += dist(q, last); last = q
        if acc >= step * 1.0: s += dot(q, r); acc = 0
    return s

# ---------- names (script lettering as filled paths with henna flourishes) ----------
def text_path(font, txt, size):
    gs = font.getGlyphSet(); cmap = font.getBestCmap(); upm = font["head"].unitsPerEm
    sc = size / upm; x = 0; parts = []
    for ch in txt:
        gn = cmap.get(ord(ch));
        if not gn: continue
        pen = SVGPathPen(gs)
        tp = TransformPen(pen, (sc, 0, 0, -sc, x, 0))
        gs[gn].draw(tp)
        parts.append(pen.getCommands())
        x += font["hmtx"][gn][0] * sc
    return " ".join(parts), x

def names_svg(fontfile, cx, cy):
    font = TTFont(fontfile)
    big = 56 if "Sacramento" in fontfile else 48
    s = ""
    for txt, size, dy in [("Akshay", big, -22), ("weds", big * 0.6, 12), ("Shreya", big, 50)]:
        d, wdt = text_path(font, txt, size)
        stroke = 1.8 if "Sacramento" in fontfile else 0.6
        s += f'<path d="{d}" transform="translate({f(cx - wdt / 2)},{f(cy + dy)})" fill="{FILL}" stroke="{FILL}" stroke-width="{stroke}" stroke-linejoin="round"/>'
    # flourishes: small heart between the lines and dot trails
    s += g(f'<path d="M0,6 C-12,-4 -6,-14 0,-6 C6,-14 12,-4 0,6 Z" fill="{FILL}"/>', cx + 46, cy + 4, 0, 0.9)
    s += "".join(dot((cx - 46 - k * 8, cy + 6), 2.6 - k * 0.6) for k in range(3))
    return s

# ---------- assemble ----------
def build(side, fontfile, outname):
    art = palm_art() if side == "palm" else back_art()
    body = []
    for a in art:
        if isinstance(a, tuple) and a[0] == "NAMES":
            body.append(names_hand(a[1], a[2], fontfile))
        else:
            body.append(a)
    lm_json = json.dumps({str(k): v for k, v in L.items()})
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" data-landmarks='{lm_json}' data-side="{side}">
<defs><mask id="hand"><rect width="{W}" height="{H}" fill="black"/>{hand_shapes("white")}</mask></defs>
<rect width="{W}" height="{H}" fill="#fbf6ef"/>
<g id="skin">{hand_shapes(EDGE, 2)}{hand_shapes(SKIN)}</g>
<g id="art" mask="url(#hand)">{"".join(body)}</g>
</svg>'''
    open(outname, "w").write(svg)

# ---------- hand-written lettering (no typeface): own pen strokes, smoothed ----------
# units: x-height = 1, baseline y = 0, up = negative. Each letter: list of strokes (point lists).
CURSIVE = {
    "A": [[(0.0, 0.0), (0.42, -1.3), (0.68, -2.2), (0.8, -1.2), (0.95, 0.0)], [(0.15, -0.85), (0.6, -0.95), (1.2, -0.85), (1.35, -0.4), (1.2, -0.1)]],
    "k": [[(0, -0.1), (0.25, -1.3), (0.35, -2.1), (0.18, -2.2), (0.1, -1.6), (0.12, 0.0)], [(0.12, -0.45), (0.5, -0.95), (0.62, -0.75), (0.35, -0.5), (0.2, -0.45), (0.5, -0.35), (0.62, 0.0), (0.85, -0.15)]],
    "s": [[(0, -0.1), (0.35, -1.0), (0.42, -0.6), (0.55, -0.25), (0.4, 0.0), (0.15, -0.05), (0.3, -0.06), (0.7, -0.15)]],
    "h": [[(0, -0.1), (0.25, -1.3), (0.35, -2.1), (0.18, -2.2), (0.1, -1.6), (0.1, 0.0), (0.2, -0.7), (0.45, -1.0), (0.6, -0.7), (0.6, -0.15), (0.72, 0.0), (0.9, -0.15)]],
    "a": [[(0.75, -0.8), (0.45, -1.0), (0.12, -0.75), (0.08, -0.2), (0.35, 0.02), (0.68, -0.4), (0.76, -1.0), (0.74, -0.35), (0.85, 0.0), (1.05, -0.15)]],
    "y": [[(0, -0.9), (0.1, -0.35), (0.3, -0.02), (0.55, -0.4), (0.62, -0.95), (0.6, 0.3), (0.45, 0.9), (0.2, 0.95), (0.25, 0.55), (0.75, 0.05), (0.95, -0.2)]],
    "w": [[(0, -0.9), (0.05, -0.3), (0.25, 0.0), (0.42, -0.45), (0.45, -0.75), (0.5, -0.3), (0.7, 0.0), (0.88, -0.5), (0.9, -0.95), (0.85, -0.8), (1.1, -0.85)]],
    "e": [[(0, -0.15), (0.4, -0.5), (0.5, -0.85), (0.35, -1.0), (0.15, -0.7), (0.15, -0.2), (0.4, 0.0), (0.7, -0.2)]],
    "d": [[(0.75, -0.8), (0.45, -1.0), (0.12, -0.75), (0.08, -0.2), (0.35, 0.02), (0.68, -0.4), (0.8, -1.4), (0.85, -2.15), (0.78, -1.0), (0.78, -0.3), (0.9, 0.0), (1.08, -0.15)]],
    "r": [[(0, -0.1), (0.2, -0.85), (0.3, -1.0), (0.38, -0.85), (0.45, -0.9), (0.6, -0.95), (0.55, -0.4), (0.62, 0.0), (0.82, -0.15)]],
    "S": [[(1.0, -1.9), (0.62, -2.2), (0.25, -1.98), (0.3, -1.45), (0.75, -0.95), (0.82, -0.35), (0.48, 0.02), (0.08, -0.15), (0.0, -0.4)], [(0.75, -0.08), (1.0, -0.15)]],
}
CAPS = {  # simple hand-printed capitals, 4 x 6 grid → scaled to cap height 2
    "A": [[(0, 6), (2, 0), (4, 6)], [(0.9, 3.8), (3.1, 3.8)]],
    "K": [[(0, 0), (0, 6)], [(3.8, 0), (0, 3.4)], [(1.3, 2.5), (4, 6)]],
    "S": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 2.2), (1, 3), (3, 3), (4, 3.8), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "Y": [[(0, 0), (2, 3)], [(4, 0), (2, 3), (2, 6)]],
    "R": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)], [(1.6, 3), (4, 6)]],
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    "W": [[(0, 0), (0.8, 6), (2, 2.2), (3.2, 6), (4, 0)]],
    "D": [[(0, 0), (0, 6), (2, 6), (3.4, 5), (4, 3), (3.4, 1), (2, 0), (0, 0)]],
}

def smooth(pts, n=10):
    if len(pts) < 3: return pts
    ext = [pts[0]] + pts + [pts[-1]]; out = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    out.append(pts[-1]); return out

def write_word(word, x0, y0, u, style, w):
    """returns (svg, width). style 'cursive' or 'caps'. u = x-height in px"""
    s = ""; x = x0
    for ch in word:
        if style == "cursive":
            strokes = CURSIVE[ch]; sc = u; adv = max(p[0] for st in strokes for p in st)
            tr = lambda p: (x + p[0] * sc, y0 + p[1] * sc)
            sm = True
        else:
            strokes = CAPS[ch.upper()]; sc = u * 2 / 6; adv = 4 * sc / u + 0.35
            tr = lambda p: (x + p[0] * sc, y0 - 2 * u + p[1] * sc)
            sm = False
        for st in strokes:
            pts = [tr(p) for p in (smooth(st) if sm else st)]
            d = "M" + " L".join(f"{f(a)},{f(b)}" for a, b in pts)
            s += f'<path d="{d}" fill="none" stroke="{FILL}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
            # cone blob where the artist lifts the cone
            s += dot(pts[-1], w * 0.62) + dot(pts[0], w * 0.55)
        x += adv * (u if style == "cursive" else u) + (0.08 * u if style == "cursive" else 0)
    return s, x - x0

def names_hand(cx, cy, style):
    s = ""
    if style == "cursive":
        u = 19
        for word, dy, uu in [("Akshay", -18, u), ("weds", 12, u * 0.62), ("Shreya", 58, u)]:
            _, wd = write_word(word, 0, 0, uu, style, 1)
            sv, _ = write_word(word, cx - wd / 2, cy + dy, uu, style, 3.0 if uu == u else 2.2)
            s += sv
    else:
        u = 12.5
        for word, dy, uu, w in [("AKSHAY", -14, u, 3.4), ("WEDS", 16, u * 0.6, 2.4), ("SHREYA", 58, u, 3.4)]:
            _, wd = write_word(word, 0, 0, uu, style, 1)
            sv, _ = write_word(word, cx - wd / 2 + uu * 0.17, cy + dy, uu, style, w)
            s += sv
    s += g(f'<path d="M0,6 C-12,-4 -6,-14 0,-6 C6,-14 12,-4 0,6 Z" fill="{FILL}"/>', cx + 50, cy + 6, 0, 0.8)
    s += "".join(dot((cx - 48 - k * 8, cy + 8), 2.6 - k * 0.6) for k in range(3))
    return s

# ---------- PALM v3: one connected composition; regions divided by thick outlines and filled with simple patterns ----------
THICK = 5.0
_cid = [0]
def cid(p="c"):
    _cid[0] += 1; return f"{p}{_cid[0]}"

def clip_to(shape_d, content, transform=""):
    i = cid()
    return f'<clipPath id="{i}"><path d="{shape_d}" {transform}/></clipPath><g clip-path="url(#{i})">{content}</g>'

def rect_d(x, y, w, h): return f"M{f(x)},{f(y)} h{f(w)} v{f(h)} h{f(-w)} Z"

# simple fills over a box (x0,y0,x1,y1)
def pat_crosshatch(x0, y0, x1, y1, step=11, w=1.1):
    s = ""; n = int((x1 - x0 + y1 - y0) / step) + 2
    for k in range(-n, n):
        a = x0 + k * step
        s += line((a, y0), (a + (y1 - y0), y1), w, INK2) + line((a + (y1 - y0), y0), (a, y1), w, INK2)
    return s
def pat_hatch(x0, y0, x1, y1, step=8, w=1.1):
    s = ""; n = int((x1 - x0 + y1 - y0) / step) + 2
    for k in range(-n, n):
        a = x0 + k * step
        s += line((a, y0), (a + (y1 - y0), y1), w, INK2)
    return s
def pat_dots(x0, y0, x1, y1, step=11, r=1.7):
    s = ""; y = y0; row = 0
    while y <= y1:
        x = x0 + (step / 2 if row % 2 else 0)
        while x <= x1: s += dot((x, y), r, INK2); x += step
        y += step * 0.87; row += 1
    return s
def pat_scales(x0, y0, x1, y1, r=13, w=1.4):
    s = ""; y = y0; row = 0
    while y <= y1 + r:
        x = x0 + (r if row % 2 else 0)
        while x <= x1 + r:
            s += f'<path d="M{f(x - r)},{f(y)} A{f(r)},{f(r)} 0 0 0 {f(x + r)},{f(y)}" fill="none" stroke="{INK2}" stroke-width="{w}"/>'
            s += dot((x, y + r * 0.45), 1.6, INK2)
            x += 2 * r
        y += r * 0.9; row += 1
    return s
def pat_lattice_flowers(x0, y0, x1, y1, cell=26):
    s = pat_crosshatch(x0, y0, x1, y1, cell / 2 ** 0.5 * 1.0, 1.5)
    y = y0; row = 0
    while y <= y1:
        x = x0 + (cell / 2 if row % 2 else 0)
        while x <= x1: s += g(four_petal_star(5), x, y); x += cell
        y += cell / 2; row += 1
    return s

def knock(c0, r):  # clean skin under a main motif so it stands out from the fills
    return f'<circle cx="{f(c0[0])}" cy="{f(c0[1])}" r="{f(r)}" fill="{SKIN}"/>'

def finger_column(fi):
    """whole finger covered: cap | band | pattern block with motif | band | motif block | base band"""
    p1, p2, p3, p4 = [P(k) for k in FINGERS[fi]]
    wd = FW[fi]; s = ""
    def seg(a, b, body_fn):
        c = lerp(a, b, 0.5); rot = ang(a, b) + 90; Ls = dist(a, b)
        x0, y0 = -wd, -Ls / 2
        body = body_fn(wd, Ls)
        return g(clip_to(rect_d(x0, y0, 2 * wd, Ls), body), c[0], c[1], rot)
    def thick_across(pt, a, b, w=THICK):
        rot = ang(a, b) + 90
        return g(line((-wd, 0), (wd, 0), w) + line((-wd, 7), (wd, 7), 1.6), pt[0], pt[1], rot)
    # distal: solid cap (tip end) over a thin band
    a = lerp(p3, p4, 0.38)
    tipdir = ((p4[0] - p3[0]) / dist(p3, p4), (p4[1] - p3[1]) / dist(p3, p4))
    s += line(a, (p4[0] + tipdir[0] * wd * 0.1, p4[1] + tipdir[1] * wd * 0.1), wd * 1.02, FILL)
    s += seg(p3, lerp(p3, p4, 0.38), lambda w_, L_: pat_dots(-w_, -L_ / 2, w_, L_ / 2, 8, 1.5))
    s += thick_across(lerp(p3, p4, 0.36), p4, p3, 3.4)
    if fi == 0:
        # thumb: lattice with tiny flowers on the proximal phalanx
        s += seg(p2, p3, lambda w_, L_: pat_lattice_flowers(-w_, -L_ / 2, w_, L_ / 2, 24))
        s += thick_across(p3, p4, p2) + thick_across(p2, p3, p1)
        return s
    # middle phalanx: cross-hatch fill, mini flower on clean skin in the middle
    def mid(w_, L_):
        b = pat_crosshatch(-w_, -L_ / 2, w_, L_ / 2, 10, 1.0)
        b += knock((0, 0), wd * 0.36) + circ((0, 0), wd * 0.36, 2.4) + mini_flower(wd * 0.3)
        return b
    s += seg(p2, p3, mid)
    s += thick_across(p3, p4, p2)
    # proximal phalanx: scales fill, spiral medallion on clean skin
    def prox(w_, L_):
        b = pat_scales(-w_, -L_ / 2, w_, L_ / 2, 9, 1.2)
        b += knock((0, -L_ * 0.05), wd * 0.38) + circ((0, -L_ * 0.05), wd * 0.38, 2.4)
        b += g(spiral(wd * 0.26, 2.6, 2) + dot_ring(wd * 0.31, 12, 1.8), 0, -L_ * 0.05)
        return b
    s += seg(p1, p2, prox)
    s += thick_across(p2, p3, p1)
    return s

def palm_art():
    out = []
    pd = palm_path()
    cx, cy = 552, 985; R = 172                     # medallion outer radius (thick ring)
    BIG = 900
    def wedge(a0, a1):
        pts = [(cx, cy)] + [(cx + BIG * math.cos(math.radians(a0 + (a1 - a0) * k / 12)), cy + BIG * math.sin(math.radians(a0 + (a1 - a0) * k / 12))) for k in range(13)]
        return "M" + " L".join(f"{f(x)},{f(y)}" for x, y in pts) + " Z"
    box = (330, 700, 790, 1220)
    # regions around the medallion: angle ranges (SVG: 0 = right, -90 = up)
    regions = [
        (-150, -32, pat_scales(*box, 14, 1.4)),                 # under the knuckles
        (-32, 72, pat_dots(*box, 10, 2.3)),                     # pinky-side edge
        (72, 112, pat_hatch(*box, 7, 1.2)),                     # heel → wrist (rays region)
        (112, 210, pat_lattice_flowers(*box, 28)),              # thumb mound
    ]
    fills = ""
    for a0, a1, pat in regions:
        fills += clip_to(wedge(a0, a1), pat)
    out.append(clip_to(pd, fills))
    # thick dividers: palm-edge outline is implied by the hand; spokes from the medallion ring to the edge
    spokes = ""
    for a in (-150, -32, 72, 112):
        r0 = R; r1 = 420
        spokes += line((cx + r0 * math.cos(math.radians(a)), cy + r0 * math.sin(math.radians(a))), (cx + r1 * math.cos(math.radians(a)), cy + r1 * math.sin(math.radians(a))), THICK)
    # knuckle line: thick curve across the finger bases, with half flowers hanging from it on clean skin
    knuckle = "M352,800 C420,772 470,766 500,766 C560,766 640,774 760,826"
    spokes += f'<path d="{knuckle}" fill="none" stroke="{INK}" stroke-width="{THICK}"/>'
    out.append(clip_to(pd, spokes))
    # clean skin above the knuckle line (between the line and finger bases) with a dot row
    out.append(clip_to(pd, f'<path d="M330,700 L790,700 L790,826 C640,774 560,766 500,766 C470,766 420,772 330,808 Z" fill="{SKIN}"/>'))
    for x, y in [(418, 768), (500, 760), (584, 764), (664, 782)]:
        out.append(dot((x, y - 6), 4.2))
    for (x, y, r) in [(420, 792, 32), (502, 786, 34), (586, 792, 32), (664, 814, 28)]:
        hf = clip_to(rect_d(-r - 6, 0, 2 * r + 12, r + 8), knock((0, 0), r + 5))
        hf += f'<path d="M{-r},0 A{r},{r} 0 0 0 {r},0" fill="none" stroke="{INK}" stroke-width="2.6"/>'
        hf += petal_ring(r * 0.32, r * 0.92, 7, 0.6, 1.5)
        hf = clip_to(rect_d(-r - 4, 0, 2 * r + 8, r + 6), hf)
        hf += dot((0, 2), r * 0.18)
        out.append(g(hf, x, y))
    # pinky-side leaf vine sits on the dotted region (on its own clean stripe)
    vine_d = "M752,880 C762,960 752,1040 716,1120"
    vine = f'<path d="{vine_d}" fill="none" stroke="{SKIN}" stroke-width="30" stroke-linecap="round"/>'
    vine += f'<path d="{vine_d}" fill="none" stroke="{INK}" stroke-width="3.4"/>'
    def bez(t, p=((752, 880), (762, 960), (752, 1040), (716, 1120))):
        return tuple((1 - t) ** 3 * p[0][i] + 3 * (1 - t) ** 2 * t * p[1][i] + 3 * (1 - t) * t * t * p[2][i] + t ** 3 * p[3][i] for i in range(2))
    for k, t in enumerate([0.1, 0.26, 0.42, 0.58, 0.74, 0.9]):
        q = bez(t); q2 = bez(t + 0.01); a_ = ang(q, q2); side = 1 if k % 2 else -1
        vine += g(teardrop(20, 7, fill=FILL if k % 2 else "none", stroke=INK, w=1.5), q[0], q[1], a_ + 90 + side * 50)
    out.append(clip_to(pd, vine))
    # medallion: clean skin disc with a thick outer ring
    med = knock((0, 0), R)
    med += round_petal_ring(118, 160, 14, 2.6)
    for i in range(14):
        med += f'<g transform="rotate({i * 360 / 14 + 180 / 14})">' + g(teardrop(30, 7), 0, -120) + "</g>"
    med += scallop_ring(110, 24, 8, 2.2)
    med += f'<circle r="102" fill="none" stroke="{FILL}" stroke-width="6"/>'
    med += dot_ring(94, 40, 2.0)
    med += circ((0, 0), 88, 1.8)
    med += dot_ring(166, 36, 2.4, rot=5)
    med += f'<circle r="{R}" fill="none" stroke="{INK}" stroke-width="{THICK}"/>'
    out.append(g(med, cx, cy))
    out.append(("NAMES", cx, cy - 2))
    # heel rays: a half-sun hugging the bottom of the medallion, joining it to the cuff
    out.append(clip_to(pd, g(f'<path d="M-60,0 A60,60 0 0 1 60,0 Z" fill="{SKIN}"/>' + petal_ring(22, 56, 9, 0.6, 1.6, fill_alt=True) + f'<path d="M-60,0 A60,60 0 0 1 60,0" fill="none" stroke="{INK}" stroke-width="3"/>', 552, 1196, 0)))
    # fingers, fully covered
    for fi in range(5):
        out.append(finger_column(fi))
    # cuff + forearm
    out.append(cuff3(1196))
    return out

def cuff3(y0):
    xl, xr = 380, 660
    s = ""; y = y0
    def hl(y, w=THICK): return line((xl, y), (xr, y), w)
    def bandfill(ya, yb, pat):
        return clip_to(rect_d(xl, ya, xr - xl, yb - ya), pat)
    # band 1: dots row on hatch
    yb = y + 26
    s += bandfill(y, yb, pat_hatch(xl, y, xr, yb, 7, 1.1)) + f'<rect x="{xl}" y="{y + 6}" width="{xr - xl}" height="14" fill="{SKIN}"/>'
    for k in range(15): s += dot((xl + 10 + k * (xr - xl - 20) / 14, y + 13), 4)
    s += hl(y); y = yb; s += hl(y)
    # band 2: leaf chain on clean skin
    yb = y + 34
    n = 13
    for k in range(n):
        x = xl + 12 + k * (xr - xl - 24) / (n - 1)
        s += g(teardrop(16, 6, fill=FILL), x, y + 17, -60) + g(teardrop(16, 6, fill="none", stroke=INK, w=1.4), x, y + 17, 60)
    s += line((xl, y + 17), (xr, y + 17), 1.4)
    y = yb; s += hl(y)
    # band 3: lattice with flowers
    yb = y + 56
    s += bandfill(y, yb, pat_lattice_flowers(xl, y, xr, yb, 28)); y = yb; s += hl(y)
    # band 4: scallops on dots
    yb = y + 30
    s += bandfill(y, yb, pat_dots(xl, y, xr, yb, 9, 1.5))
    n = 12
    for k in range(n):
        x0 = xl + k * (xr - xl) / n; x1 = xl + (k + 1) * (xr - xl) / n
        s += f'<path d="M{f(x0)},{f(y)} Q{f((x0 + x1) / 2)},{f(y + 46)} {f(x1)},{f(y)} Z" fill="{SKIN}" stroke="{INK}" stroke-width="2.2"/>'
        s += dot(((x0 + x1) / 2, y + 11), 3)
    y = yb; s += hl(y)
    # band 5: diamond-petal band
    yb = y + 48
    s += bandfill(y, yb, pat_crosshatch(xl, y, xr, yb, 9, 1.0))
    for k in range(7):
        x = xl + 20 + k * (xr - xl - 40) / 6
        s += knock((x, (y + yb) / 2), 19) + g(four_petal_star(17), x, (y + yb) / 2)
    y = yb; s += hl(y)
    # forearm half-sun hanging from the last band (connected)
    s += g(half_sun3(104), 520, y, 180)
    s += g(teardrop(24, 9), 520, y + 128, 180) + dot((520, y + 164), 6)
    return s

def half_sun3(r):
    i = cid()
    s = f'<clipPath id="{i}"><rect x="{-r - 40}" y="{-r - 40}" width="{2 * r + 80}" height="{r + 40}"/></clipPath><g clip-path="url(#{i})">'
    s += f'<circle r="{r}" fill="{SKIN}"/>'
    s += clip_to(f"M{-r},0 A{r},{r} 0 0 1 {r},0 L{r * 0.62},0 A{r * 0.62},{r * 0.62} 0 0 0 {-r * 0.62},0 Z", pat_hatch(-r, -r, r, 0, 6, 1.1))
    s += round_petal_ring(r * 0.62, r * 0.98, 16, 2.2)
    s += f'<circle r="{f(r * 0.6)}" fill="{SKIN}" stroke="{FILL}" stroke-width="5"/>'
    s += petal_ring(r * 0.2, r * 0.56, 10, 0.6, 1.6, hatch=True)
    s += dot_ring(r * 1.07, 30, 2.4)
    s += f'<circle r="{r}" fill="none" stroke="{INK}" stroke-width="{THICK}"/>'
    s += "</g>"
    s += f'<path d="M{-r * 0.18},0 A{r * 0.18},{r * 0.18} 0 0 1 {r * 0.18},0 Z" fill="{FILL}"/>'
    return s

if __name__ == "__main__":
    style = sys.argv[1] if len(sys.argv) > 1 else "cursive"
    build("palm", style, f"palm_{style}.svg")
    build("back", style, "back.svg")
    print("ok")

