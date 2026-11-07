import numpy as np
def extra(lm):
    """anchor points beyond the 21 landmarks: forearm grid, palm sides, past the fingertips. Must match extraPts() in index.html."""
    lm = np.asarray(lm, float)
    w, m9, i5, p17 = lm[0], lm[9], lm[5], lm[17]
    u = m9 - w; sc = np.linalg.norm(u); u = u / sc; n = np.array([-u[1], u[0]]); pw = np.linalg.norm(i5 - p17)
    pts = []
    for k in (0.0, 0.45, 0.9, 1.35, 1.8):
        c = w - u * sc * k
        for j in (-1.3, -0.75, -0.35, 0.0, 0.35, 0.75, 1.3): pts.append(c + n * pw * j)
    for t in (0.3, 0.65, 1.0):
        c = w + u * sc * t; pts += [c + n * pw * 1.15, c - n * pw * 1.15]
    for i, j in ((4, 3), (8, 7), (12, 11), (16, 15), (20, 19)):
        d = lm[i] - lm[j]; pts.append(lm[i] + d * 0.6)
    return np.array(pts)
