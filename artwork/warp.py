import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2, numpy as np, json, math
from scipy.spatial import Delaunay
import importlib.util
spec = importlib.util.spec_from_file_location("gen", "gen.py"); gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)

src_lm = np.array(json.load(open('/tmp/lm_rot.json'))[0], np.float32)       # photo, rotated upright
dst_lm = np.array([gen.L[i] for i in range(21)], np.float32)                 # hand template
henna = cv2.rotate(cv2.imread('ref/back_henna.png', cv2.IMREAD_UNCHANGED), cv2.ROTATE_180)

from meshdef import extra
S = np.vstack([src_lm, extra(src_lm)]).astype(np.float32); D = np.vstack([dst_lm, extra(dst_lm)]).astype(np.float32)
tri = Delaunay(D)
H, W = 1650, 1000
out = np.zeros((H, W, 4), np.float32)
for simp in tri.simplices:
    s3 = S[simp]; d3 = D[simp]
    M = cv2.getAffineTransform(s3, d3)
    warped = cv2.warpAffine(henna, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    mask = np.zeros((H, W), np.uint8); cv2.fillConvexPoly(mask, d3.astype(np.int32), 1)
    out[mask == 1] = warped[mask == 1]
out = out.astype(np.uint8)
# drop small specks (photo nail edges etc.)
m = (out[..., 3] > 30).astype(np.uint8)
n_, lab, st, _ = cv2.connectedComponentsWithStats(m)
for i in range(1, n_):
    if st[i, cv2.CC_STAT_AREA] < 140: out[lab == i] = 0
cv2.imwrite('back_warped.png', out)
# composite on the template skin for the art sheet
skin = cv2.imread('back4.png'); skin = skin[:H, :W]
tmpl = cv2.imread('palm3.png')
# plain template: render skin only from the svg would be cleaner; reuse back4 render minus its art by drawing hand shapes
base = np.full((H, W, 3), (239, 246, 251), np.uint8)
hand = np.zeros((H, W), np.uint8)
for shape in ['skin']:
    pass
cv2.imwrite('/tmp/tri.png', base)
json.dump({"src": S.tolist(), "dst": D.tolist(), "tri": tri.simplices.tolist()}, open('back_warp_mesh.json', 'w'))
print("triangles", len(tri.simplices))
