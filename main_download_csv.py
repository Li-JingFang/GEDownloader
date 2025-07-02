import os
import cv2
import pandas as pd
import numpy as np
from downloader.downloader_center import get_img_center_gdal_savetmp, get_img_center, get_img_center_gdal_GTiff

if __name__ == '__main__':
    csv_path = 'save_files/locs.csv'
    # save_path = 'F:/GEtempsavefile_new/'
    save_path = 'G:/GoogleEarth'
    dis_km = 18.7 / 2
    zoom = 19  # 0.3 km/pixel
    datasource = 'google'
    data = pd.read_csv(csv_path, encoding='utf-8')
    name = np.array(data['name']).tolist()
    lng = np.array(data['lng']).tolist()
    lat = np.array(data['lat']).tolist()
    time = np.array(data['time']).tolist()

    os.makedirs(save_path, exist_ok=True)

    for i in range(len(name)):
        # if name[i].startswith('R1'):
        #     continue
        if name[i].startswith('R'):
            continue
        print('=' * 80)
        print(f"start download point {name[i]}")
        tiff_name = os.path.join(save_path, name[i] + '.tif')
        print(f"tiff_name: {tiff_name}, lng: {lng[i]}, lat: {lat[i]}, dis_km: {dis_km}, zoom: {zoom}")
        get_img_center_gdal_GTiff(lng=lng[i], lat=lat[i], tiff_filename=tiff_name,
                                  datasource=datasource,
                                  dlng_km=dis_km, dlat_km=dis_km,
                                  zoom=zoom, nproc=8)
        # get_img_center_gdal_savetmp(lng=lng[i], lat=lat[i], tiff_filename=tiff_name,
        #                             datasource=datasource,
        #                             dlng_km=dis_km, dlat_km=dis_km,
        #                             zoom=zoom, nproc=8)

        # save_path_test = os.path.join(save_path, 'test')
        # zoom_test = 14
        # save_name = os.path.join(save_path_test, name[i] + '_z14.jpg')
        # canvas = get_img_center(lng=lng[i], lat=lat[i],
        #                         datasource=datasource,
        #                         dlng_km=dis_km, dlat_km=dis_km,
        #                         zoom=zoom_test, nproc=8)
        # cv2.imwrite(save_name, canvas)
    print('全部区域影像下载结束')
