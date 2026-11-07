import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
def alpha_of(raw):
    lum = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY).astype(np.float32); s = float(np.median(lum))
    return np.clip((s - lum) / (s - 40), 0, 1)
cuff = alpha_of(cv2.imread("tex_cuff_raw.png")[:1650, :1000])
# bend: bands curve like a ring seen around the wrist (edges rise towards the hand)
H_, W_ = cuff.shape; cx = 520.0; hw = 300.0; sag = 26.0
xs, ys = np.meshgrid(np.arange(W_, dtype=np.float32), np.arange(H_, dtype=np.float32))
mapy = ys + sag * np.clip(((xs - cx) / hw) ** 2, 0, 2.5)
cuff_b = cv2.remap(cuff, xs, mapy.astype(np.float32), cv2.INTER_LINEAR, borderValue=0)
for v in "ab":
    a = np.maximum(alpha_of(cv2.imread(f"tex_palm_{v}_raw.png")[:1650, :1000]), cuff_b)
    a = cv2.resize(a, None, fx=K, fy=K, interpolation=cv2.INTER_AREA)
    t = np.zeros((*a.shape, 4), np.uint8); t[..., 0], t[..., 1], t[..., 2] = INK; t[..., 3] = (a * 255).astype(np.uint8)
    cv2.imwrite(f"palm_{v}.png", t, [cv2.IMWRITE_PNG_COMPRESSION, 9])
bw = cv2.imread("back_warped.png", cv2.IMREAD_UNCHANGED)
cv2.imwrite("back_tex.png", cv2.resize(bw, None, fx=K, fy=K, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_PNG_COMPRESSION, 9])
# mesh: template landmarks + extra anchor points (same recipe the page uses live)
from meshdef import extra
T = np.array([gen.L[i] for i in range(21)], float)
P = np.vstack([T, extra(T)])
tri = Delaunay(P).simplices.tolist()
json.dump({"scale": K, "uv": (P * K).round(2).tolist(), "tri": tri}, open("mesh.json", "w"))
print("tri", len(tri), "points", len(P))
