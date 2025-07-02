import requests
import cv2
import numpy as np
import os

retry_limit = 3
timeout = 2


def download(url, headers, x, y, canvas, pbar):
    pbar.update(1)
    response = None
    retry = 0
    while response is None or response.status_code != 200:
        if retry == retry_limit:
            print("Failed to get {} with retry={}.".format(url, retry))
            return -1
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except Exception as e:
            pass
        retry += 1
    try:
        input_image_data = response.content
        np_arr = np.asarray(bytearray(input_image_data), np.uint8).reshape(1, -1)
        tile = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)
        canvas[y * 256:(y + 1) * 256, x * 256:(x + 1) * 256, :] = tile
    except Exception as e:
        print(str(e))
        return -1
    return 0


def download_save2tmpdir(url, headers, x, y, tmpdir, pbar):
    pbar.update(1)
    response = None
    retry = 0
    img_savepath = os.path.join(tmpdir, f"{x}_{y}.jpg")
    if os.path.exists(img_savepath):
        return 0
    while response is None or response.status_code != 200:
        if retry == retry_limit:
            print("Failed to get {} with retry={}.".format(url, retry))
            return -1
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except Exception as e:
            pass
        retry += 1
    try:
        input_image_data = response.content
        np_arr = np.asarray(bytearray(input_image_data), np.uint8).reshape(1, -1)
        tile = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)
        cv2.imwrite(img_savepath, tile)
    except Exception as e:
        print(str(e))
        return -1
    return 0


def download_tiff(url, headers, x, y, dataset, pbar):
    pbar.update(1)
    response = None
    retry = 0
    while response is None or response.status_code != 200:
        if retry == retry_limit:
            print("Failed to get {} with retry={}.".format(url, retry))
            return -1
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except Exception as e:
            pass
        retry += 1
    try:
        input_image_data = response.content
        np_arr = np.asarray(bytearray(input_image_data), np.uint8).reshape(1, -1)
        tile = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)
        # tile = tile.transpose((1,0,2))
        # canvas[y * 256:(y + 1) * 256, x * 256:(x + 1) * 256, :] = tile
        tile = cv2.cvtColor(tile, cv2.COLOR_BGR2RGB)
        for band in range(3):
            dataset.GetRasterBand(band + 1).WriteRaster(x * 256, y * 256, 256, 256, tile[:, :, band].tobytes())
    except Exception as e:
        print(str(e))
        return -1
    return 0
