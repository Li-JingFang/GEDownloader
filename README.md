# 谷歌地球卫星图下载

# 使用说明

## 环境准备

```bash
conda create -n Downloader python=3.9
conda activate Downloader
cd /path/to/this/project
pip install -r requirements.txt
conda install gdal
```

## 运行

main.py内修改需要下载区域的经纬度等参数，直接运行

### 其他

核心代码来源: https://github.com/whughw/TileDownloader  
谷歌地球影像Zoom等级和分辨率关系表： https://wiki.openstreetmap.org/wiki/Zoom_levels