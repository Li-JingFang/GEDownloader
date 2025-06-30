import os
import cv2
import numpy as np
from osgeo import gdal
from tqdm import tqdm
from utils import tile_utils
from utils import distance_utils
from utils.url import format_url
from utils.download import download, download_tiff, download_save2tmpdir
from utils.concurrent_helper import run_with_concurrent


def get_img_center(lng, lat, datasource='google', dlng_km=0.1, dlat_km=0.1, zoom=19, nproc=8):
    center_lng = lng
    center_lat = lat
    # 地面距离转经纬度角度差
    dlng = distance_utils.lng_km2degree(dis_km=dlng_km, center_lat=lat)
    dlat = distance_utils.lat_km2degree(dis_km=dlat_km)

    # 左上角点-右下角点的瓦片标号
    tileX_tl, tileY_tl = tile_utils.lnglatToTile(center_lng - dlng, center_lat + dlat, zoom)
    tileX_br, tileY_br = tile_utils.lnglatToTile(center_lng + dlng, center_lat - dlat, zoom)
    nX = tileX_br - tileX_tl + 1
    nY = tileY_br - tileY_tl + 1

    # 最终的大图
    canvas = np.zeros((nY * 256, nX * 256, 3), dtype=np.uint8)

    with tqdm(total=nX * nY) as pbar:
        failure_count = 0
        retry_list = []
        for x in range(nX):
            task_list = []
            for y in range(nY):
                url, headers = format_url(datasource, tileX_tl, x, tileY_tl, y, zoom)
                task_list.append([url, headers, x, y, canvas, pbar])
            # 多线程并发
            status = run_with_concurrent(download, task_list, "thread", min(nproc, len(task_list)))
            for i in range(len(status)):
                if status[i] != 0:
                    retry_list.append(task_list[i])
                    failure_count += 1
            if failure_count >= (nX * nY) / 10:
                return None
    status = run_with_concurrent(download, retry_list, "thread", min(nproc, len(retry_list)))

    return canvas


def get_img_center_gdal(lng, lat, tiff_filename, datasource='google', dlng_km=0.1, dlat_km=0.1, zoom=19, nproc=8):
    center_lng = lng
    center_lat = lat
    # 地面距离转经纬度角度差
    dlng = distance_utils.lng_km2degree(dis_km=dlng_km, center_lat=lat)
    dlat = distance_utils.lat_km2degree(dis_km=dlat_km)

    # 左上角点-右下角点的瓦片标号
    tileX_tl, tileY_tl = tile_utils.lnglatToTile(center_lng - dlng, center_lat + dlat, zoom)
    tileX_br, tileY_br = tile_utils.lnglatToTile(center_lng + dlng, center_lat - dlat, zoom)
    nX = tileX_br - tileX_tl + 1
    nY = tileY_br - tileY_tl + 1

    height = nY * 256
    width = nX * 256
    channels = 3

    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(tiff_filename, width, height, channels, gdal.GDT_Byte, ['COMPRESS=LZW'])
    dataset.SetMetadataItem("BLOCKXSIZE", str(256))
    dataset.SetMetadataItem("BLOCKYSIZE", str(256))
    gdal.SetConfigOption('GDAL_CACHEMAX', '10240')  # 设置缓存大小

    with tqdm(total=nX * nY) as pbar:
        failure_count = 0
        retry_list = []
        for x in range(nX):
            task_list = []
            for y in range(nY):
                url, headers = format_url(datasource, tileX_tl, x, tileY_tl, y, zoom)
                task_list.append([url, headers, x, y, dataset, pbar])
            # 多线程并发
            status = run_with_concurrent(download_save2tmpdir, task_list, "thread", min(nproc, len(task_list)))
            for i in range(len(status)):
                if status[i] != 0:
                    retry_list.append(task_list[i])
                    failure_count += 1
            if failure_count >= (nX * nY) / 10:
                return None
    status = run_with_concurrent(download_save2tmpdir, retry_list, "thread", min(nproc, len(retry_list)))

    dataset.FlushCache()
    print("保存完成：" + tiff_filename)


def merge2tiff(tmpdir, tiff_filename, width, height):
    print('start merge images to tiff')
    print(f"width={width},height={height}")
    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(tiff_filename, width, height, 3, gdal.GDT_Byte)
    dataset.SetMetadataItem("BLOCKXSIZE", str(256))
    dataset.SetMetadataItem("BLOCKYSIZE", str(256))
    gdal.SetConfigOption('GDAL_CACHEMAX', '10240')  # 设置缓存大小

    files_list = os.listdir(tmpdir)
    for i in tqdm(range(len(files_list))):
        img_path = files_list[i]
        img = cv2.imread(os.path.join(tmpdir, img_path))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        xy = os.path.basename(img_path).split('.')[0].split('_')
        x, y = int(xy[0]), int(xy[1])
        for band in range(3):
            dataset.GetRasterBand(band + 1).WriteRaster(x * 256, y * 256, 256, 256, img[:, :, band].tobytes())
    dataset.FlushCache()
    print("保存完成：" + tiff_filename)


def get_img_center_gdal_savetmp(lng, lat, tiff_filename,
                                datasource='google', dlng_km=0.1, dlat_km=0.1, zoom=19, nproc=8):
    center_lng = lng
    center_lat = lat
    # 地面距离转经纬度角度差
    dlng = distance_utils.lng_km2degree(dis_km=dlng_km, center_lat=lat)
    dlat = distance_utils.lat_km2degree(dis_km=dlat_km)

    # 左上角点-右下角点的瓦片标号
    tileX_tl, tileY_tl = tile_utils.lnglatToTile(center_lng - dlng, center_lat + dlat, zoom)
    tileX_br, tileY_br = tile_utils.lnglatToTile(center_lng + dlng, center_lat - dlat, zoom)
    nX = tileX_br - tileX_tl + 1
    nY = tileY_br - tileY_tl + 1

    height = nY * 256
    width = nX * 256

    tmpdir = os.path.join(os.path.dirname(tiff_filename), os.path.basename(tiff_filename).split('.')[0])
    os.makedirs(tmpdir, exist_ok=True)

    with tqdm(total=nX * nY) as pbar:
        failure_count = 0
        retry_list = []
        for x in range(nX):
            task_list = []
            for y in range(nY):
                url, headers = format_url(datasource, tileX_tl, x, tileY_tl, y, zoom)
                task_list.append([url, headers, x, y, tmpdir, pbar])
            # 多线程并发
            status = run_with_concurrent(download_save2tmpdir, task_list, "thread", min(nproc, len(task_list)))
            for i in range(len(status)):
                if status[i] != 0:
                    retry_list.append(task_list[i])
                    failure_count += 1
            if failure_count >= (nX * nY) / 10:
                return None
    status = run_with_concurrent(download_save2tmpdir, retry_list, "thread", min(nproc, len(retry_list)))
    # merge2tiff(tmpdir, tiff_filename, width, height)
    print("保存完成：" + tiff_filename)
