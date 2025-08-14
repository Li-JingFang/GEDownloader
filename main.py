import cv2
from downloader.downloader_tblr import get_img_tblr, get_img_tblr_gdal_GTiff
from utils.distance_utils import calArea


def Demo_download_jpg():
    save_file = 'save_files/whu.jpg'
    loc_tl = [114.341316, 30.553657]
    loc_br = [114.37745, 30.517285]
    zoom = 19  # 0.3 m/pixel
    area = calArea(loc_tl=loc_tl, loc_br=loc_br)
    print(f"区域面积：{area:.2f} 平方公里")
    image = get_img_tblr(loc_tl, loc_br, 'google', zoom, 8)
    cv2.imwrite(save_file, image)


def Demo_download_tiff():
    tiff_name = 'save_files/whu.tif'
    loc_tl = [114.341316, 30.553657]
    loc_br = [114.37745, 30.517285]
    zoom = 19  # 0.3 m/pixel
    area = calArea(loc_tl=loc_tl, loc_br=loc_br)
    print(f"区域面积：{area:.2f} 平方公里")
    print(f"开始下载区域影像，左上角：{loc_tl}, 右下角：{loc_br}, 缩放级别：{zoom}, 保存路径：{tiff_name}...")
    get_img_tblr_gdal_GTiff(loc_tl, loc_br, tiff_name, 'google', zoom, 8)
    print(f"区域影像下载完成，保存路径：{tiff_name}")


if __name__ == '__main__':
    # Demo_download_jpg()
    Demo_download_tiff()
