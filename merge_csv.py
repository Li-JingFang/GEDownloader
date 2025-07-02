import os
import shutil
import pandas as pd
import numpy as np
from utils import tile_utils, distance_utils
from utils.merge import mergeInJPG, mergeJPG2TIF

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

    target_dir = 'G:\GoogleEarth'

    for i in range(len(name)):
        if name[i] == 'M1':
            continue  # 跳过M1点
        if name[i].startswith('R'):
            continue
        print('=' * 80)
        print(f"start merge point {name[i]}")
        tiff_name = os.path.join(save_path, name[i] + '.tif')
        tmpdir = os.path.join(os.path.dirname(tiff_name), os.path.basename(tiff_name).split('.')[0])

        center_lng = lng[i]
        center_lat = lat[i]
        # 地面距离转经纬度角度差
        dlng = distance_utils.lng_km2degree(dis_km=dis_km, center_lat=center_lat)
        dlat = distance_utils.lat_km2degree(dis_km=dis_km)

        # 左上角点-右下角点的瓦片标号
        tileX_tl, tileY_tl = tile_utils.lnglatToTile(center_lng - dlng, center_lat + dlat, zoom)
        tileX_br, tileY_br = tile_utils.lnglatToTile(center_lng + dlng, center_lat - dlat, zoom)
        nX = tileX_br - tileX_tl + 1
        nY = tileY_br - tileY_tl + 1

        height = nY * 256
        width = nX * 256

        # 合并为更大的jpg
        jpg_dir = os.path.join(os.path.dirname(tiff_name),
                               os.path.basename(tiff_name).split('.')[0] + '_merged_images')
        os.makedirs(jpg_dir, exist_ok=True)
        mergeInJPG(tmpdir, nX, nY, 70, 70, jpg_dir)
        # shutil.rmtree(tmpdir)  # 删除临时目录
        # 合并为tiff
        geoTransform = tile_utils.getGeoTransform(tileX_tl, tileY_tl, nX, nY, zoom)

        tiff_name = os.path.join(target_dir, name[i] + '.tif')
        mergeJPG2TIF(jpg_dir, tiff_name, width, height, geoTransform)
        print("保存完成：" + tiff_name)
