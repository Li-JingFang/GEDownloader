import os
import cv2
import shutil
import numpy as np
from osgeo import gdal
from tqdm import tqdm
from utils import tile_utils
from utils import distance_utils
from utils.url import format_url
from utils.download import download, download_tiff, download_save2tmpdir
from utils.concurrent_helper import run_with_concurrent
from utils.merge import mergeInJPG, mergeJPG2TIF


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


# 基于中心点与目标像素尺寸自动决定边界并下载
def get_img_center_by_pixels(lng, lat,
                             desired_width_px=20000,
                             desired_height_px=None,
                             datasource='google',
                             zoom=19,
                             nproc=8):
    center_lng = lng
    center_lat = lat

    if desired_height_px is None:
        desired_height_px = desired_width_px

    # 计算需要的瓦片数量（256像素一瓦片），并尽量取奇数以更好地居中
    nX = max(1, int(round(desired_width_px / 256)))
    nY = max(1, int(round(desired_height_px / 256)))
    if nX % 2 == 0:
        nX += 1
    if nY % 2 == 0:
        nY += 1

    # 以中心点所在瓦片为基准，向四周扩展
    tileX_c, tileY_c = tile_utils.lnglatToTile(center_lng, center_lat, zoom)
    tileX_tl = tileX_c - nX // 2
    tileY_tl = tileY_c - nY // 2

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


# 下载后直接写入tif文件，适合用于小图下载
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
            status = run_with_concurrent(download_tiff, task_list, "thread", min(nproc, len(task_list)))
            for i in range(len(status)):
                if status[i] != 0:
                    retry_list.append(task_list[i])
                    failure_count += 1
            if failure_count >= (nX * nY) / 10:
                return None
    status = run_with_concurrent(download_tiff, retry_list, "thread", min(nproc, len(retry_list)))

    dataset.FlushCache()
    print("保存完成：" + tiff_filename)


# 直接保存所有的瓦片到临时目录
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
    # print("保存完成：" + tiff_filename)


# 直接保存所有的瓦片到临时目录，先合成为更大的jpg，再合并为tiff，适合用于大图下载
def get_img_center_gdal_GTiff(lng, lat, tiff_filename,
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
    # 合并为更大的jpg
    jpg_dir = os.path.join(os.path.dirname(tiff_filename),
                           os.path.basename(tiff_filename).split('.')[0] + '_merged_images')
    os.makedirs(jpg_dir, exist_ok=True)
    mergeInJPG(tmpdir, nX, nY, 60, 60, jpg_dir)
    files = os.listdir(tmpdir)
    if len(files) == nX * nY:
        print(f"JPG下载合并完成，没有瓦片缺失，删除临时目录：{tmpdir}")
        shutil.rmtree(tmpdir)  # 删除临时目录
    # 合并为tiff
    geoTransform = tile_utils.getGeoTransform(tileX_tl, tileY_tl, nX, nY, zoom)
    mergeJPG2TIF(jpg_dir, tiff_filename, width, height, geoTransform)
    print("保存完成：" + tiff_filename)
