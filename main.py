import cv2
from downloader.downloader_tblr import get_img_tblr

if __name__ == '__main__':
    save_file = 'save_files/whu.jpg'
    loc_tl = [114.341316, 30.553657]
    loc_br = [114.37745, 30.517285]
    zoom = 20
    image = get_img_tblr(loc_tl, loc_br, 'google', zoom, 8)
    cv2.imwrite(save_file, image)
