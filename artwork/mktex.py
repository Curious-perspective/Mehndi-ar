import cv2, numpy as np, json, importlib.util
from scipy.spatial import Delaunay
spec = importlib.util.spec_from_file_location("gen", "gen.py"); gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)
K = 0.6                       # texture scale (template 1000x1650 → 600x990)
INK = (12, 28, 74)            # BGR henna
def to_tex(raw_bgr, out):
    lum = cv2.cvtColor(raw_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    skin_l = float(np.median(lum))
    a = np.clip((skin_l - lum) / (skin_l - 40), 0, 1)
    a = cv2.resize(a, None, fx=K, fy=K, interpolation=cv2.INTER_AREA)
    t = np.zeros((*a.shape, 4), np.uint8); t[..., 0], t[..., 1], t[..., 2] = INK; t[..., 3] = (a * 255).astype(np.uint8)
    cv2.imwrite(out, t, [cv2.IMWRITE_PNG_COMPRESSION, 9])
for v in "ab":
    to_tex(cv2.imread(f"tex_palm_{v}_raw.png")[:1650, :1000], f"palm_{v}.png")
bw = cv2.imread("back_warped.png", cv2.IMREAD_UNCHANGED)
cv2.imwrite("back_tex.png", cv2.resize(bw, None, fx=K, fy=K, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_PNG_COMPRESSION, 9])
# mesh: template landmarks + extra anchor points (same recipe the page uses live)
def extra(lm):
    w, m9, i5, p17 = lm[0], lm[9], lm[5], lm[17]
    u = m9 - w; sc = np.linalg.norm(u); u = u / sc; n = np.array([-u[1], u[0]]); pw = np.linalg.norm(i5 - p17)
    pts = []
    for k in (0.0, 0.45, 0.9, 1.35):
        c = w - u * sc * k
        for j in (-0.75, -0.35, 0.0, 0.35, 0.75): pts.append(c + n * pw * j)
    for t in (0.3, 0.65):
        c = w + u * sc * t; pts += [c + n * pw * 0.75, c - n * pw * 0.75]
    # beyond the fingertips so tip caps are inside triangles
    for i, j in ((4, 3), (8, 7), (12, 11), (16, 15), (20, 19)):
        d = lm[i] - lm[j]; pts.append(lm[i] + d * 0.6)
    return np.array(pts)
T = np.array([gen.L[i] for i in range(21)], float)
P = np.vstack([T, extra(T)])
tri = Delaunay(P).simplices.tolist()
json.dump({"scale": K, "uv": (P * K).round(2).tolist(), "tri": tri}, open("mesh.json", "w"))
print("tri", len(tri), "points", len(P))
