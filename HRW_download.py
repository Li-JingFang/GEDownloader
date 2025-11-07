import os
import csv
import cv2
from argparse import ArgumentParser
from downloader.downloader_center import get_img_center_by_pixels

# 配置参数
DESIRED_WIDTH_PX = 20000
DESIRED_HEIGHT_PX = 20000
ZOOM = 19
BASE_SAVE_PATH = 'E:/dataset/Downloader'

# 数据集配置映射
DATASET_CONFIG = {
    'port': {
        'csv_file': 'save_files/port.csv',
        'save_dir': 'port',
        'prefix': 'port'
    },
    'airport': {
        'csv_file': 'save_files/airport_new.csv',
        'save_dir': 'airport',
        'prefix': 'airport'
    },
    'test': {
        'csv_file': 'save_files/airport_new.csv',
        'save_dir': 'test',
        'prefix': 'airport_new_bing'
    }
}

'''
# 下载 port 数据集（默认）
python HRW_download.py --dataset port --source bing --start 0 --end 500 --nproc 8

# 下载 airport 数据集
python HRW_download.py --dataset airport --source bing --start 0 --end 500 --nproc 8
'''


def _to_uint8(img):
    if img.dtype == 'uint8':
        return img
    img = img.clip(0, 255)
    return img.astype('uint8')


def _gamma_correction(img, gamma=1.05):
    # gamma>1 稍微压暗，降低“发白”观感
    import numpy as _np
    t = (_np.arange(256) / 255.0) ** gamma
    table = (t * 255.0).clip(0, 255).astype('uint8')
    return cv2.LUT(img, table)


def _unsharp_mask(img, sigma=0.8, amount=0.12):
    blur = cv2.GaussianBlur(img, (0, 0), sigmaX=sigma, sigmaY=sigma)
    sharp = cv2.addWeighted(img, 1.0 + amount, blur, -amount, 0)
    return sharp


def _clahe_on_L(img_bgr, clip=1.1, tile=(8, 8)):
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=tile)
    l2 = clahe.apply(l)
    lab2 = cv2.merge([l2, a, b])
    return cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)


def _gray_world_wb(img_bgr):
    import numpy as _np
    b, g, r = cv2.split(img_bgr.astype('float32'))
    mean_b = b.mean() + 1e-6
    mean_g = g.mean() + 1e-6
    mean_r = r.mean() + 1e-6
    gray = (mean_b + mean_g + mean_r) / 3.0
    kb, kg, kr = gray / mean_b, gray / mean_g, gray / mean_r
    b *= kb
    g *= kg
    r *= kr
    out = cv2.merge([b, g, r])
    return _to_uint8(out)


def _adjust_hsv(img_bgr, sat=1.03, val=0.98):
    import numpy as _np
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    s = _np.clip(s.astype('float32') * sat, 0, 255).astype('uint8')
    v = _np.clip(v.astype('float32') * val, 0, 255).astype('uint8')
    out = cv2.merge([h, s, v])
    return cv2.cvtColor(out, cv2.COLOR_HSV2BGR)


def enhance_image(img_bgr, mode='gentle'):
    """避免增白的增强：
    - gentle: 轻量对比度+锐化，略降亮度，微增饱和
    - bing: 先灰度世界白平衡，再轻量对比度+锐化，略降亮度
    """
    if mode == 'gentle':
        img = _clahe_on_L(img_bgr, clip=1.1, tile=(8, 8))
        img = _unsharp_mask(img, sigma=0.8, amount=0.12)
        img = _adjust_hsv(img, sat=1.03, val=0.98)
        img = _gamma_correction(img, gamma=1.05)
        return img
    if mode == 'bing':
        img = _gray_world_wb(img_bgr)
        img = _clahe_on_L(img, clip=1.05, tile=(8, 8))
        img = _unsharp_mask(img, sigma=0.7, amount=0.10)
        img = _adjust_hsv(img, sat=1.02, val=0.97)
        img = _gamma_correction(img, gamma=1.06)
        return img
    return img_bgr


def parse_csv(csv_path):
    """解析 CSV 文件，返回位置列表"""
    loc_list = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                try:
                    # CSV 格式: lat, lng (可能有多余的列)
                    lat = float(row[0])
                    lng = float(row[1])
                    loc_list.append([lat, lng])
                except (ValueError, IndexError):
                    continue
    return loc_list


def main():
    # 解析命令行参数
    parser = ArgumentParser(description='下载指定区域的高分辨率卫星图像')
    parser.add_argument(
        '--dataset', type=str, default='port',
        choices=['port', 'airport', 'test'],
        help='选择要下载的数据集: port 或 airport (默认: port)'
    )
    parser.add_argument(
        '--source', type=str, default='google',
        choices=['google', 'bing', 'tianditu', 'arcgis'],
        help='数据源: google, bing, tianditu, arcgis (默认: google)'
    )
    parser.add_argument(
        '--start', type=int, default=0,
        help='起始索引 (默认: 0)'
    )
    parser.add_argument(
        '--end', type=int, default=None,
        help='结束索引 (默认: 全部)'
    )
    parser.add_argument(
        '--nproc', type=int, default=8,
        help='并发进程数 (默认: 8)'
    )
    parser.add_argument(
        '--enhance', type=str, default='none',
        choices=['none', 'gentle', 'bing'],
        help='图像增强模式: none(默认)/gentle/bing，增强会尽量避免增白'
    )
    args = parser.parse_args()

    # 获取数据集配置
    config = DATASET_CONFIG[args.dataset]
    csv_path = config['csv_file']
    save_dir = config['save_dir']
    prefix = config['prefix']
    
    # 设置保存路径
    save_path = os.path.join(BASE_SAVE_PATH, save_dir)
    os.makedirs(save_path, exist_ok=True)
    
    # 解析 CSV 文件
    print(f"正在加载数据集: {args.dataset}")
    print(f"CSV 文件路径: {csv_path}")
    loc_list = parse_csv(csv_path)
    print(f"共找到 {len(loc_list)} 个位置点")
    
    # 设置默认结束索引
    if args.end is None:
        args.end = len(loc_list)
    
    start_idx = args.start
    end_idx = min(args.end, len(loc_list))
    
    print(f"开始下载: 索引 {start_idx} 到 {end_idx-1}")
    print(f"保存路径: {save_path}")
    print(f"数据源: {args.source}, 缩放级别: {ZOOM}, 并发数: {args.nproc}, 增强: {args.enhance}")
    print("=" * 80)

    # 下载图像
    success_count = 0
    fail_count = 0
    
    for idx in range(start_idx, end_idx):
        try:
            loc = loc_list[idx]
            print(f"[{idx+1}/{end_idx-start_idx}] 处理索引 {idx} / {end_idx-1}", end=' ... ')
            
            # 注意: CSV 中格式为 [lat, lng]，使用时需要转换为 [lng, lat]
            lat, lng = loc[0], loc[1]
            
            image = get_img_center_by_pixels(
                lng, lat,
                DESIRED_WIDTH_PX, DESIRED_HEIGHT_PX,
                args.source, ZOOM, nproc=args.nproc
            )

            # 可选增强（默认关闭）。
            if args.enhance != 'none':
                image = enhance_image(image, args.enhance)
            
            if image is None:
                print("跳过 (下载失败过多)")
                fail_count += 1
                continue
            
            # 保存图像
            filename = f"{prefix}_{idx}_{args.source}.jpg"
            filepath = os.path.join(save_path, filename)
            cv2.imencode('.jpg', image)[1].tofile(filepath)
            print("完成")
            success_count += 1
            
        except Exception as e:
            print(f"错误: {str(e)}")
            fail_count += 1
            continue
    
    # 打印统计信息
    print("=" * 80)
    print(f"下载完成!")
    print(f"成功: {success_count}, 失败: {fail_count}, 总计: {success_count + fail_count}")


if __name__ == '__main__':
    main()