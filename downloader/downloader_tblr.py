import numpy as np
from tqdm import tqdm
from utils import tile_utils
from utils.url import format_url
from utils.download import download
from utils.concurrent_helper import run_with_concurrent


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
