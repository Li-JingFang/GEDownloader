from osgeo import gdal, osr
import os
import cv2
from tqdm import tqdm
import numpy as np
from utils.concurrent_helper import run_with_concurrent


def mergeInJPG(tmpdir, nX, nY, stepX, stepY, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    nX = int(nX)
    nY = int(nY)
    stepX = int(stepX)
    stepY = int(stepY)
    # 计算分块数量
    num_steps_x = int((nX + stepX - 1) // stepX)
    num_steps_y = int((nY + stepY - 1) // stepY)

    print('start merge images to jpg')
    print(f"nX={nX}, nY={nY}, stepX={stepX}, stepY={stepY}")
    with tqdm(total=num_steps_x * num_steps_y) as pbar:
        for step_x in range(num_steps_x):
            for step_y in range(num_steps_y):
                # 当前块的范围
                start_x = step_x * stepX
                start_y = step_y * stepY
                end_x = min(start_x + stepX, nX)
                end_y = min(start_y + stepY, nY)

                block_filename = f"block_{start_x}_{start_y}_{end_x}_{end_y}.jpg"
                block_path = os.path.join(output_dir, block_filename)
                if os.path.exists(block_path):
                    pbar.update(1)
                    continue

                # 创建当前块的图像
                block_image = np.zeros(((end_y - start_y) * 256, (end_x - start_x) * 256, 3), dtype=np.uint8)

                for x in range(start_x, end_x):
                    for y in range(start_y, end_y):
                        file_name = f"{x}_{y}.jpg"
                        img_path = os.path.join(tmpdir, file_name)
                        if os.path.exists(img_path):
                            img = cv2.imread(img_path)
                            block_image[(y - start_y) * 256:(y - start_y + 1) * 256,
                            (x - start_x) * 256:(x - start_x + 1) * 256, :] = img

                # 保存当前块图像
                cv2.imwrite(block_path, block_image)
                pbar.update(1)
                # print(f"保存完成：{block_path}")


def mergeJPG2TIF_single(jpg_path, tif_dataset, pbar):
    try:
        img = cv2.imread(jpg_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        sub_width = img.shape[1]
        sub_height = img.shape[0]
        xsysxeye = os.path.basename(jpg_path).split('.')[0].split('_')[-4:]
        xs, ys = int(xsysxeye[0]), int(xsysxeye[1])
        for band in range(3):
            tif_dataset.GetRasterBand(band + 1).WriteRaster(xs * 256, ys * 256, sub_width, sub_height,
                                                            img[:, :, band].tobytes())
        pbar.update(1)
    except:
        print(f"Error processing {jpg_path}, will retry later.")
        return -1
    return 0


## 多线程合并jpg为tiff, 好像不太好使，待改进
def mergeJPG2TIF_thread(jpg_dir, tiff_filename, width, height, gt, nproc=8):
    print('start merge images to tiff')
    print(f"width={width},height={height}")
    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(tiff_filename, width, height, 3, gdal.GDT_Byte)
    dataset.SetGeoTransform(gt)
    try:
        proj = osr.SpatialReference()
        proj.ImportFromEPSG(4326)
        dataset.SetSpatialRef(proj)
    except:
        print("Error: Coordinate system setting failed")

    files_list = os.listdir(jpg_dir)
    with tqdm(total=len(files_list)) as pbar:
        task_list = []
        retry_list = []
        for img_path in files_list:
            img_full_path = os.path.join(jpg_dir, img_path)
            task_list.append([img_full_path, dataset, pbar])
        # 多线程并发
        status = run_with_concurrent(mergeJPG2TIF_single, task_list, "thread", min(nproc, len(task_list)))
        for i in range(len(status)):
            if status[i] != 0:
                retry_list.append(task_list[i])
        while len(retry_list) > 0:
            print(f"Retrying {len(retry_list)} failed images...")
            status = run_with_concurrent(mergeJPG2TIF_single, retry_list, "thread", min(nproc, len(retry_list)))
            retry_list = [retry_list[i] for i in range(len(status)) if status[i] != 0]

    dataset.FlushCache()
    dataset = None
    print("保存完成：" + tiff_filename)


def mergeJPG2TIF(jpg_dir, tiff_filename, width, height, gt):
    print('start merge images to tiff')
    print(f"width={width},height={height}")
    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(tiff_filename, width, height, 3, gdal.GDT_Byte)
    dataset.SetGeoTransform(gt)
    try:
        proj = osr.SpatialReference()
        proj.ImportFromEPSG(4326)
        dataset.SetSpatialRef(proj)
    except:
        print("Error: Coordinate system setting failed")
    # dataset.SetMetadataItem("BLOCKXSIZE", str(256))
    # dataset.SetMetadataItem("BLOCKYSIZE", str(256))
    files_list = os.listdir(jpg_dir)
    for i in tqdm(range(len(files_list))):
        img_path = files_list[i]
        img = cv2.imread(os.path.join(jpg_dir, img_path))
        sub_width = img.shape[1]
        sub_height = img.shape[0]
        xsysxeye = os.path.basename(img_path).split('.')[0].split('_')[-4:]
        xs, ys = int(xsysxeye[0]), int(xsysxeye[1])
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        for band in range(3):
            dataset.GetRasterBand(band + 1).WriteRaster(xs * 256, ys * 256, sub_width, sub_height,
                                                        img[:, :, band].tobytes())
    dataset.FlushCache()
    dataset = None
    print("保存完成：" + tiff_filename)


def merge2tiff(tmpdir, tiff_filename, width, height):
    print('start merge images to tiff')
    print(f"width={width},height={height}")
    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(tiff_filename, width, height, 3, gdal.GDT_Byte)
    dataset.SetMetadataItem("BLOCKXSIZE", str(256))
    dataset.SetMetadataItem("BLOCKYSIZE", str(256))
    # gdal.SetConfigOption('GDAL_CACHEMAX', '10240')  # 设置缓存大小

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
