import numpy as np
from tqdm import tqdm
from utils import tile_utils
from utils.url import format_url
from utils.download import download, download_save2tmpdir
from utils.concurrent_helper import run_with_concurrent
import os
import shutil
from utils.merge import mergeInJPG, mergeJPG2TIF


def get_img_tblr(loc_tl, loc_br, datasource='google', zoom=20, nproc=8):
    """
    根据左上角和右下角的经纬度返回图像
    :param loc_tl:[tl_lng, tl_lat] 左上角的经度，纬度
    :param loc_br:[br_lng, br_lat] 右下角的经度，纬度
    :param datasource:数据来源
    :param zoom:瓦片级别
    :param nproc:下载线程数
    :return:区域的卫星图像
    """
    tl_lng, tl_lat = loc_tl
    br_lng, br_lat = loc_br
    # 左上角点-右下角点的瓦片标号
    tileX_tl, tileY_tl = tile_utils.lnglatToTile(tl_lng, tl_lat, zoom)
    tileX_br, tileY_br = tile_utils.lnglatToTile(br_lng, br_lat, zoom)
    nX = tileX_br - tileX_tl + 1
    nY = tileY_br - tileY_tl + 1
    assert (nX > 0) & (nY > 0), "input loc error"

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


# 直接保存所有的瓦片到临时目录，先合成为更大的jpg，再合并为tiff，适合用于大图下载
def get_img_tblr_gdal_GTiff(loc_tl, loc_br, tiff_filename, datasource='google', zoom=20, nproc=8):
    tl_lng, tl_lat = loc_tl
    br_lng, br_lat = loc_br
    # 左上角点-右下角点的瓦片标号
    tileX_tl, tileY_tl = tile_utils.lnglatToTile(tl_lng, tl_lat, zoom)
    tileX_br, tileY_br = tile_utils.lnglatToTile(br_lng, br_lat, zoom)
    nX = tileX_br - tileX_tl + 1
    nY = tileY_br - tileY_tl + 1
    assert (nX > 0) & (nY > 0), "input loc error"

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
