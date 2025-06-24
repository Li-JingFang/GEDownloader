import numpy as np
from tqdm import tqdm
from utils import tile_utils
from utils import distance_utils
from utils.url import format_url
from utils.download import download
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
