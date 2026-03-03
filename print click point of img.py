import cv2

img = cv2.imread("img-rbg_detecting.jpg")
img = cv2.resize(img, (1920, 1080))

def click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(x, y)

cv2.imshow("img", img)
cv2.setMouseCallback("img", click)

cv2.waitKey(0)
cv2.destroyAllWindows()

'''
img-ir_detecting.jpg
743 299
1181 573

img-rbg_detecting.jpg
730 302
1192 572
'''