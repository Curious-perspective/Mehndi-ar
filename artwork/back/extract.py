import cv2, numpy as np
im = cv2.imread('ref/back_ref.jpg')                     # BGR
b, g, r = [im[..., i].astype(np.float32) for i in range(3)]
lum = 0.299 * r + 0.587 * g + 0.114 * b
# background is saturated red: R much larger than G
bg = (r - g > 90) & (g < 80)
skin = (~bg) & (lum > 150)
# hand mask = everything not background, cleaned
hand = (~bg).astype(np.uint8) * 255
hand = cv2.morphologyEx(hand, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(hand)
big = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]); hand = np.where(lab == big, 255, 0).astype(np.uint8)
hand = cv2.morphologyEx(hand, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
hand_er = cv2.erode(hand, np.ones((9, 9), np.uint8))   # avoid the dark hand edge / shadow
# local skin brightness (henna darkness is relative to the skin around it)
# black-hat: thin dark structures (ink lines, dots) relative to their surroundings; broad shadows vanish
k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (35, 35))
bh = cv2.morphologyEx(lum, cv2.MORPH_BLACKHAT, k)
dark = np.clip((bh - 28) / 70.0, 0, 1)
# also require the pixel to be henna-brown, not red-tinted shadow (shadows here pick up the red cloth)
dark[(r - g) > 95] = 0
dark[hand_er == 0] = 0
# remove skin creases / nail edges: henna is brown-dark; creases are faint — the -25 offset handles most; drop tiny specks
m = (dark > 0.15).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(m)
keep = np.zeros_like(m)
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] >= 60: keep[lab == i] = 1
dark *= cv2.dilate(keep, np.ones((3, 3), np.uint8))
# erase the photo's finger-gap / thumb shadows (the design never reaches these areas)
for x0, y0, x1, y1 in [(95, 790, 180, 1220), (245, 850, 305, 1446), (418, 885, 455, 1100), (600, 550, 665, 770), (735, 840, 800, 960)]:
    dark[y0:y1, x0:x1] = 0
alpha = (dark * 255).astype(np.uint8)
rgba = np.zeros((*alpha.shape, 4), np.uint8)
rgba[..., 0], rgba[..., 1], rgba[..., 2] = 12, 28, 74     # BGR of henna brown (#4a1c0c)
rgba[..., 3] = alpha
cv2.imwrite('ref/back_henna.png', rgba)
cv2.imwrite('ref/hand_mask.png', hand)
prev = np.full_like(im, 255); a3 = (alpha[..., None] / 255.0)
prev = (prev * (1 - a3) + np.array([12, 28, 74]) * a3).astype(np.uint8)
prev[hand == 0] = (235, 240, 245)
cv2.imwrite('ref/back_henna_preview.png', prev)
print('henna px', int((alpha > 40).sum()))
