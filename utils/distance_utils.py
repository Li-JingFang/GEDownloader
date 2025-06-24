"""
    地理中常用的数学计算，把地球简化成了一个标准球形，如果想要推广到任意星球可以改成类的写法，然后修改半径即可
"""
import math

earth_radius = 6370.856  # 地球平均半径，单位km，最简单的模型往往把地球当做完美的球形，这个值就是常说的RE
math_2pi = math.pi * 2
pis_per_degree = math_2pi / 360  # 角度一度所对应的弧度数，360对应2*pi


def lat_degree2km(dif_degree=.0001, radius=earth_radius):
    """
    通过圆环求法，纯纬度上，度数差转距离(km)，与中间点所处的地球上的位置关系不大
    :param dif_degree: 度数差, 经验值0.0001对应11.1米的距离
    :param radius: 圆环求法的等效半径，纬度距离的等效圆环是经线环，所以默认都是earth_radius
    :return: 这个度数差dif_degree对应的距离，单位km
    """
    return radius * dif_degree * pis_per_degree


def lat_km2degree(dis_km=111, radius=earth_radius):
    """
    通过圆环求法，纯纬度上，距离值转度数(diff)，与中间点所处的地球上的位置关系不大
    :param dis_km: 输入的距离，单位km，经验值111km相差约(接近)1度
    :param radius: 圆环求法的等效半径，纬度距离的等效圆环是经线环，所以默认都是earth_radius
    :return: 这个距离dis_km对应在纯纬度上差多少度
    """
    return dis_km / radius / pis_per_degree


def lng_degree2km(dif_degree=.0001, center_lat=22):
    """
    通过圆环求法，纯经度上，度数差转距离(km)，纬度的高低会影响距离对应的经度角度差，具体表达式为：
    :param dif_degree: 度数差
    :param center_lat: 中心点的纬度，默认22为深圳附近的纬度值；为0时表示赤道，赤道的纬线环半径使得经度计算和上面的纬度计算基本一致
    :return: 这个度数差dif_degree对应的距离，单位km
    """
    # 修正后，中心点所在纬度的地表圆环半径
    real_radius = earth_radius * math.cos(center_lat * pis_per_degree)
    return lat_degree2km(dif_degree, real_radius)


def lng_km2degree(dis_km=1, center_lat=22):
    """
    纯经度上，距离值转角度差(diff)，单位度数。
    :param dis_km: 输入的距离，单位km
    :param center_lat: 中心点的纬度，默认22为深圳附近的纬度值；为0时表示赤道。
         赤道、中国深圳、中国北京、对应的修正系数分别约为： 1  0.927  0.766
    :return: 这个距离dis_km对应在纯经度上差多少度
    """
    # 修正后，中心点所在纬度的地表圆环半径
    real_radius = earth_radius * math.cos(center_lat * pis_per_degree)
    return lat_km2degree(dis_km, real_radius)


def ab_distance(a_lat, a_lng, b_lat, b_lng):
    """
    计算经纬度表示的ab两点的距离，这是种近似计算，当两点纬度差距不大时更为准确，产生近似的原因也是来主要自于center_lat
    :param a_lat: a点纬度
    :param a_lng: a点经度
    :param b_lat: b点纬度
    :param b_lng: b点纬度
    :return:
    """
    center_lat = .5 * a_lat + .5 * b_lat
    lat_dis = lat_degree2km(abs(a_lat - b_lat))
    lng_dis = lng_degree2km(abs(a_lng - b_lng), center_lat)
    return math.sqrt(lat_dis ** 2 + lng_dis ** 2)


if __name__ == "__main__":
    print(lng_km2degree(dis_km=100, center_lat=39))
