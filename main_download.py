import cv2
from downloader.downloader_tblr import get_img_tblr
from downloader.downloader_center import get_img_center, get_img_center_gdal, get_img_center_gdal_savetmp

if __name__ == '__main__':
    # save_file = 'save_files/whu.jpg'
    # loc_tl = [114.341316, 30.553657]
    # loc_br = [114.37745, 30.517285]
    # zoom = 20
    # image = get_img_tblr(loc_tl, loc_br, 'google', zoom, 8)
    # cv2.imwrite(save_file, image)

    # from utils.url import format_url
    # from utils.download import download
    # import numpy as np
    # from tqdm import tqdm
    #
    # tileX_tl = 857331
    # tileY_tl = 430749
    # url, headers = format_url('google', tileX_tl, 0, tileY_tl, 0, 20)
    # canvas = np.zeros((256, 256, 3), dtype=np.uint8)
    # with tqdm(total=1) as pbar:
    #     download(url, headers, 0, 0, canvas, pbar)

    save_file = 'C:/temp_files/test2.tiff'
    loc = [-116.05778333333333333333, 37.00976388888888888889]
    dis_km = 18.7
    zoom = 19  # 0.3 km/pixel
    datasource = 'google'
    # get_img_center_gdal_savetmp(lng=loc[0], lat=loc[1], tiff_filename=save_file,
    #                             datasource=datasource,
    #                             dlng_km=dis_km, dlat_km=dis_km,
    #                             zoom=zoom, nproc=8)

    import os
    from downloader.downloader_center import merge2tiff

    width = 157440
    height = 157440
    tiff_filename = save_file
    tmpdir = os.path.join(os.path.dirname(tiff_filename), os.path.basename(tiff_filename).split('.')[0])
    merge2tiff(tmpdir, tiff_filename, width, height)

    # import PIL.Image as pil
    # import numpy as np
    #
    # lenx = 921
    # leny = 1353
    # # output = pil.new('RGBA', (lenx * 256, leny * 256))
    # output = np.zeros((lenx * 256, leny * 256))
    # print('end')