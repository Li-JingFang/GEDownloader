import os

import cv2
import pandas as pd
import numpy as np
from downloader.downloader_center import get_img_center_gdal_savetmp

if __name__ == '__main__':
    csv_path = 'save_files/locs.csv'
    save_path = 'F:/GEtempsavefile/'
    dis_km = 18.7
    zoom = 19  # 0.3 km/pixel
    datasource = 'google'
    data = pd.read_csv(csv_path, encoding='utf-8')
    name = np.array(data['name']).tolist()
    lng = np.array(data['lng']).tolist()
    lat = np.array(data['lat']).tolist()
    time = np.array(data['time']).tolist()

    for i in range(len(name)):
        print('=' * 50)
        print(f"start download point {name[i]}")
        tiff_name = os.path.join(save_path, name[i] + '.tif')
        get_img_center_gdal_savetmp(lng=lng[i], lat=lat[i], tiff_filename=tiff_name,
                                    datasource=datasource,
                                    dlng_km=dis_km, dlat_km=dis_km,
                                    zoom=zoom, nproc=8)
    print('全部区域影像下载结束')
