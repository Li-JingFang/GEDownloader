import random
from utils import tile_utils


def format_url(datasource, tileX, dx, tileY, dy, zoom):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
        'Referer': 'https://www.tianditu.gov.cn/',
        'Connection': 'keep-alive',
        'Accept-Language': 'zh-CN,zh;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
    }
    supported_source = ['tianditu', 'google', 'bing', 'arcgis']
    if datasource not in supported_source:
        raise NotImplementedError("Unknown source {}. Supported source list: {}".format(datasource,
                                                                                        ".".join(supported_source)))
    url = None
    if datasource == 'tianditu':
        # max zoom 18
        assert zoom <= 18, "max_zoom=18 for tianditu"
        url = "http://t%d.tianditu.gov.cn/DataServer?T=img_w&x=%d&y=%d&l=%d&tk=9a02b3cdd29cd346de4df04229797710" % \
              (random.randint(1, 4), tileX + dx, tileY + dy, zoom)
    if datasource == 'google':
        # max zoom 20
        assert zoom <= 20, "max_zoom=20 for google"
        url = "http://mt%d.google.com/vt/lyrs=s&x=%d&y=%d&z=%d" % \
              (random.randint(0, 3), tileX + dx, tileY + dy, zoom)
        # url = "https://khms%d.google.com/kh/v=%s&src=app&x=%d&y=%d&z=%d" % \
        #       (random.randint(0, 3), "908", tileX + dx, tileY + dy, zoom)
    if datasource == 'bing':
        # max zoom 19
        assert zoom <= 19, "max_zoom=19 for bing"
        url = "http://ecn.t%d.tiles.virtualearth.net/tiles/a%s.jpeg?g=0" % \
              (random.randint(0, 3), tile_utils.TileXYToQuadKey(tileX + dx, tileY + dy, zoom))
    if datasource == 'arcgis':
        # max zoom 19
        assert zoom <= 19, "max_zoom=19 for arcgis"
        url = "http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/%d/%d/%d" % \
              (zoom, tileY + dy, tileX + dx)
    return url, headers
