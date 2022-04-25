from .argument import ArgSession
from ..responses import ResponseMsg, ResponseImg
from ..api_tokens import CAIYUN_API_TOKEN, BAIDU_MAP_API_TOKEN
from ..utils import image_filename
import requests, urllib, datetime, math, re, threading, time, traceback, random
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from io import BytesIO


class WeatherSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 60*2
        self.session_type = '天气插件'
        self.strict_commands = ['weather', '天气']
        self.description = '根据给定的地点查找经纬度，并从彩云天气API（caiyunapp.com）获取实时天气'
        self.add_arg(key='location', alias_list=['-l', '-loc'], required=True,
                     get_next=True, get_all=True,
                     ask_text='请返回要查找的地点或经纬度（逗号隔开）')
        self.add_arg(key='no-realtime', alias_list=['-nr'],
                     help_text='不返回实时天气')
        self.add_arg(key='general', alias_list=['-g'],
                     help_text='获取天气总览（温度、降水、空气质量、风力等）')
        self.add_arg(key='wind', alias_list=['-w'],
                     help_text='获取风力预报')
        self.add_arg(key='uv', alias_list=['-u', '-uv'],
                     help_text='获取紫外线流量预报')
        self.add_arg(key='air-pressure', alias_list=['-ap'],
                     help_text='获取大气压预报')
        self.add_arg(key='precipitation', alias_list=['-p', '-p2h'],
                     help_text='获取2小时降雨预报')
        self.add_arg(key='day', alias_list=['-d'],
                     get_next=True,
                     default_value=1,
                     help_text='获取天气预报的日期（0-今天，1-明天，2-后天）')
        self.add_arg(key='today', alias_list=['-t'],
                     help_text='等价于"--day 0"，优先级更高')
        self.add_arg(key='day2', alias_list=['-d2'],
                     help_text='等价于"--day 2"，优先级第二')
        self.default_arg = self.arg_list[0]
        self.detail_description = '例如，可以直接发送“天气”后回复地理位置获取实时天气，或直接发送“天气 北京”获取信息。'\
                                  '也可直接使用经纬度，如“天气 "120.0,40.0" ”。\n'\
                                  '还能发送参数命令“天气 雁栖湖 -nr -w -t”查看今日（-t）风力（-w），且不获取实时天气（-nr）。'

    def is_legal_request(self, request):
        if not self._is_first_time and request.loc is not None:
            return True
        else:
            return self._text_request_only(request)

    def internal_handle(self, request):
        self.deactivate()
        try:
            responses = []
            if self.arg_dict['location'].raw_req.loc is not None:
                w_api = WeatherAPI(**request.loc)
            else:
                w_api = WeatherAPI()
                w_api.set_location_from_string(location_string=self.arg_dict['location'].value)

            # add general report (realtime)
            if not self.arg_dict['no-realtime'].called:
                responses.append(ResponseMsg(w_api.realtime_report()))

            # select target date
            if self.arg_dict['today'].called:
                delta_days = 0
            elif self.arg_dict['day2'].called:
                delta_days = 2
            else:  # 最后，从day参数获取时间
                try:
                    delta_days = int(self.arg_dict['day'].value)
                    assert 0 <= delta_days <= 2
                except ValueError:
                    return ResponseMsg(f'【{self.session_type}】日期格式输入有误。')
                except AssertionError:
                    return ResponseMsg(f'【{self.session_type}】时间超出，仅支持近48h天气预报。')

            # get detail prediction
            if self.arg_dict['general'].called:  # add general report
                filename = image_filename(header='WeatherGeneral', abs_path=True)
                w_api.auto_plot_general(filename=filename, delta_days=delta_days)
                responses.append(ResponseImg(file=filename))

            if self.arg_dict['wind'].called:  # add wind report
                filename = image_filename(header='WeatherWind', abs_path=True)
                w_api.auto_plot_winds(filename=filename, delta_days=delta_days)
                responses.append((ResponseImg(file=filename)))

            if self.arg_dict['uv'].called:  # add uv flux report
                filename = image_filename(header='WeatherUV', abs_path=True)
                w_api.auto_plot_uv(filename=filename, delta_days=delta_days)
                responses.append((ResponseImg(file=filename)))

            if self.arg_dict['air-pressure'].called:  # add air-pressure report
                filename = image_filename(header='WeatherPressure', abs_path=True)
                w_api.auto_plot_pressure(filename=filename, delta_days=delta_days)
                responses.append((ResponseImg(file=filename)))

            if self.arg_dict['precipitation'].called:  # rain
                filename = image_filename(header='WeatherRain', abs_path=True)
                w_api.auto_plot_p2h(filename=filename)
                responses.append((ResponseImg(file=filename)))

            return responses
        except KeyError:
            return ResponseMsg(f'【{self.session_type}】天气查询异常')


class WindMapSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 60*2
        self.session_type = '风向图'
        self.strict_commands = ['wind', 'wmap', '风向', '风力']
        self.description = '从彩云天气API（caiyunapp.com）获取给定地点风向图'
        self.add_arg(key='location', alias_list=['-l', '-loc'], required=True,
                     get_next=True, get_all=True,
                     ask_text='请返回要查找的地点或经纬度（逗号隔开）')
        self.add_arg(key='day', alias_list=['-d'],
                     get_next=True, default_value=0,
                     help_text='风力图的日期（距离0-2天，默认0）')
        self.add_arg(key='hour', alias_list=['-hr'],
                     get_next=True, default_value=0,
                     help_text='风力图的时间（0-23时，默认0）')
        self.add_arg(key='length', alias_list=['-len'],
                     get_next=True, default_value=10,
                     help_text='风力图的边长（km，默认10）')
        self.add_arg(key='deltalength', alias_list=['-dl'],
                     get_next=True, default_value=1,
                     help_text='风力图的点间隔（km，默认1）')
        self.add_arg(key='figsize', alias_list=['-fs'],
                     get_next=True, default_value=8,
                     help_text='风力图的画布尺寸（matplotlib参数，默认8.0，建议不大于25）')
        self.default_arg = self.arg_list[0]  # location
        self.detail_description = '获取高可自定义性的风力分布图（默认为实时）；' \
                                  '风矢中长划线表示10节（5.14m/s），短划线表示5节（2.57m/s），' \
                                  '点数过多时会随机舍弃部分数据点。\n' \
                                  '例如，“风向 北京市 -d 1 -hr 6 -len 60 -dl 5 -fs 20”。'

    def internal_handle(self, request):
        self.deactivate()
        try:
            if self.arg_dict['location'].raw_req.loc is not None:
                w_api = WeatherAPI(**request.loc)
            else:
                w_api = WeatherAPI()
                w_api.set_location_from_string(location_string=self.arg_dict['location'].value)

            # get prediction
            filename = image_filename(header='WindMap', abs_path=True)
            w_api.auto_plot_wind_map(length_km=float(self.arg_dict['length'].value),
                                     delta_km=float(self.arg_dict['deltalength'].value),
                                     filename=filename,
                                     delta_days=int(self.arg_dict['day'].value),
                                     hour=int(self.arg_dict['hour'].value),
                                     figsize=float(self.arg_dict['figsize'].value))
            return ResponseImg(file=filename)
        except KeyError:
            return ResponseMsg(f'【{self.session_type}】天气查询异常')


class WeatherAPI:
    def __init__(self, longitude=0.0, latitude=0.0):
        self.longitude = longitude  # 经度
        self.latitude = latitude  # 纬度
        self.resp_dict = None

    def general_url(self):
        return f'https://api.caiyunapp.com/v2.5/{CAIYUN_API_TOKEN}/' \
               f'{self.longitude:.4f},{self.latitude:.4f}/weather.json'

    def get_resp(self, url=None):
        if self.resp_dict is None:
            if url is None:
                url = self.general_url()
            resp = requests.get(url=url)
            self.resp_dict = resp.json()
        return self.resp_dict

    def set_location_from_string(self, location_string):
        # try coordinates
        if ',' in location_string or '，' in location_string:
            coord_str = re.split(pattern='[,，]', string=location_string)
            # coord_str = loc_str.split(',', '，')
            try:
                assert len(coord_str) == 2
                longitude = float(coord_str[0])
                latitude = float(coord_str[1])
                assert -180.0 < longitude < 180.0
                assert -90.0 < latitude < 90.0
                self.longitude = longitude
                self.latitude = latitude
                return
            except ValueError:
                pass
            except AssertionError:
                pass
        # not coordinates
        self.set_city(city_name=location_string)

    def set_city(self, city_name):
        resp = requests.get('http://api.map.baidu.com/geocoding/v3/?address=%s&output=json&ak=%s'
                            % (urllib.request.quote(city_name), BAIDU_MAP_API_TOKEN))
        loc = resp.json()['result']['location']
        self.longitude, self.latitude = loc['lng'], loc['lat']
        self.resp_dict = None

    def get_city(self):
        resp = requests.get(f'http://api.map.baidu.com/reverse_geocoding/v3/?ak={BAIDU_MAP_API_TOKEN}'
                            f'&output=json&coordtype=wgs84ll&location={self.latitude},{self.longitude}')
        # loc = resp.json()['result']['addressComponent']
        # return f"{loc['country']}{loc['province']}{loc['city']}{loc['district']}{loc['town']}[{loc['adcode']}]"
        # return f"{loc['city']}{loc['district']}{loc['town']}({loc['adcode']})"
        return f"{resp.json()['result']['formatted_address']}" \
               f"[{resp.json()['result']['addressComponent']['adcode']}]"

    def realtime_report(self):
        results = self.get_resp(url=self.general_url())
        rdict = results['result']['realtime']

        realtime_string = f"温度[{rdict['temperature']:.2f} ℃]，相对湿度[{100 * rdict['humidity']:.0f}%]\n" \
                          f"云量[{100 * rdict['cloudrate']:.0f}%]，天气状况[{rdict['skycon']}]\n" \
                          f"能见度[{rdict['visibility']:.1f} km]，向下短波辐射通量[{rdict['dswrf']:.1f} W/M2]\n" \
                          f"风速[{rdict['wind']['speed']:.2f} kmph]，风向[{rdict['wind']['direction']:.1f}°]\n" \
                          f"压强[{rdict['pressure']:.1f} Pa]，体感温度[{rdict['apparent_temperature']:.1f} ℃]\n" \
                          f"本地降水：强度[{rdict['precipitation']['local']['intensity']:.1f}]\n" \
                          f"最近降水：距离[{rdict['precipitation']['nearest']['distance']:.1f} km]，" \
                          f"强度[{rdict['precipitation']['nearest']['intensity']:.1f}]\n" \
                          f"空气污染物浓度(默认μg/m3)：pm2.5[{rdict['air_quality']['pm25']:.0f}]，" \
                          f"pm10[{rdict['air_quality']['pm10']:.0f}]，臭氧[{rdict['air_quality']['o3']:.1f}]，" \
                          f"二氧化氮[{rdict['air_quality']['no2']:.1f}]，二氧化硫[{rdict['air_quality']['so2']:.1f}]，" \
                          f"一氧化碳[{rdict['air_quality']['co']:.1f} mg/m3]\n" \
                          f"AQI：中国[{rdict['air_quality']['aqi']['chn']:.0f}]，" \
                          f"美国[{rdict['air_quality']['aqi']['usa']:.0f}]\n" \
                          f"生活指数：紫外线[{rdict['life_index']['ultraviolet']['index']:.1f}" \
                          f"({rdict['life_index']['ultraviolet']['desc']})]，" \
                          f"舒适度[{rdict['life_index']['comfort']['index']}" \
                          f"({rdict['life_index']['comfort']['desc']})]"

        return f'== 实时天气@{self.longitude:.2f},{self.latitude:.2f} ==\n{self.get_city()}\n{realtime_string}'

    @staticmethod
    def _locate_from_path(source_dict, path_list):
        result = source_dict
        for key in path_list:
            result = result[key]
        return result

    @staticmethod
    def _date_brief(date: datetime.date):
        # 输出时间标记，形如 04-25 Mon
        week_briefs = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        return f'{date.strftime("%m-%d")} {week_briefs[date.weekday()]}'

    def next_day_data(self, path_to_data=['result', 'hourly', 'temperature'],
                      path_to_datetime=['datetime'], path_to_value=['value']):
        return self.delta_day_data(path_to_data=path_to_data, path_to_datetime=path_to_datetime,
                                   path_to_value=path_to_value, delta_days=1)

    def delta_day_data(self, path_to_data=['result', 'hourly', 'temperature'],
                       path_to_datetime=['datetime'], path_to_value=['value'],
                       delta_days=1):
        results = self._locate_from_path(source_dict=self.get_resp(url=self.general_url()),
                                         path_list=path_to_data)
        target_date = datetime.date.today() + datetime.timedelta(days=delta_days)
        hour_list = []
        value_list = []
        for tag in results:
            tag_time = datetime.datetime.fromisoformat(self._locate_from_path(tag, path_to_datetime))
            if tag_time.day == target_date.day:
                hour_list.append(tag_time.hour)
                value_list.append(self._locate_from_path(tag, path_to_value))
        return {'date': self._date_brief(target_date),
                'hour': hour_list, 'value': value_list}

    def next_day_wind(self):
        return self.delta_day_wind(delta_days=1)

    def delta_day_wind(self, delta_days=1):
        speed_data = self.delta_day_data(path_to_data=['result', 'hourly', 'wind'],
                                         path_to_datetime=['datetime'], path_to_value=['speed'],
                                         delta_days=delta_days)
        direction_data = self.delta_day_data(path_to_data=['result', 'hourly', 'wind'],
                                             path_to_datetime=['datetime'], path_to_value=['direction'],
                                             delta_days=delta_days)
        return {'date': speed_data['date'], 'hour': speed_data['hour'],
                'speed': speed_data['value'], 'direction': direction_data['value']}

    @staticmethod
    def plot_temperature(hour_list, temp_list, date, filename):
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot(hour_list, temp_list)
        ax.set_xlabel('Hour')
        ax.set_ylabel('Temperature[℃]')
        ax.set_title('Hourly Temperature [%s]' % date)
        ax.grid()
        fig.tight_layout()
        fig.savefig(filename)

    @staticmethod
    def _next_day_plotter(ax: plt.Axes, data_dict, label: str, plot_kwargs={}):
        ln = ax.plot(data_dict['hour'], data_dict['value'], label=label, **plot_kwargs)
        ax.set_xlim(min(data_dict['hour']), max(data_dict['hour']))
        return ln

    @staticmethod
    def _wind_plotter(ax: plt.Axes, data_dict):
        t = np.array(data_dict['hour'])
        s = np.array(data_dict['speed'])
        d = np.array(data_dict['direction']) * math.pi / 180
        u = -s * np.sin(d) / 1.852
        v = -s * np.cos(d) / 1.852
        ax.plot(t, s / 3.6)
        ax.barbs(t, s / 3.6, u, v, pivot='middle')

    def auto_plot_t_a(self, filename):
        t = self.next_day_data(path_to_data=['result', 'hourly', 'temperature'], path_to_value=['value'])
        a = self.next_day_data(path_to_data=['result', 'hourly', 'air_quality', 'aqi'], path_to_value=['value', 'chn'])
        fig, ax1 = plt.subplots(figsize=(4, 3))
        ln1 = self._next_day_plotter(ax1, t, label='Temperature')
        ax1.set_ylim(-5, 30)
        ax1.set_xlabel('Time [H]')
        ax1.set_ylabel('Temperature [℃]')
        ax1.set_title('Weather [%s]' % a['date'])
        ax1.grid()
        ax2 = ax1.twinx()
        ln2 = self._next_day_plotter(ax2, a, label='AQI', plot_kwargs={'color': 'orange'})
        ax2.set_ylim(0, 500)
        ax2.set_ylabel('Air Quality Index')
        lns = ln1 + ln2
        labs = [l.get_label() for l in lns]
        ax1.legend(lns, labs)
        fig.tight_layout()
        fig.savefig(filename)

    def auto_plot_winds(self, filename, delta_days=1):
        w = self.delta_day_wind(delta_days=delta_days)
        fig, ax = plt.subplots(figsize=(4, 3))
        self._wind_plotter(ax, w)
        ax.set_xlabel('Time [h]')
        ax.set_ylabel('Wind Speed [m/s]')
        ax.set_title('Wind Forcast [%s]' % w['date'])
        fig.tight_layout()
        fig.savefig(filename)

    def auto_plot_hourly(self, filename, delta_days, path_to_data,
                         ylabel, title):
        data = self.delta_day_data(path_to_data=path_to_data, delta_days=delta_days)
        fig, ax = plt.subplots(figsize=(4, 3))
        self._next_day_plotter(ax=ax, data_dict=data, label='')
        ax.set_xlabel('Hour')
        ax.set_ylabel(ylabel)
        ax.set_title(f'{title} [{data["date"]}]')
        ax.grid()
        fig.tight_layout()
        fig.savefig(filename)

    def auto_plot_uv(self, filename, delta_days=1):
        self.auto_plot_hourly(filename=filename, delta_days=delta_days,
                              path_to_data=['result', 'hourly', 'dswrf'],
                              ylabel=r'Flux [$ \rm W/m^2 $]',
                              title='Downwards UV Flux')

    def auto_plot_pressure(self, filename, delta_days=1):
        self.auto_plot_hourly(filename=filename, delta_days=delta_days,
                              path_to_data=['result', 'hourly', 'pressure'],
                              ylabel=r'Pressure [Pa]',
                              title='Hourly Air Pressure')

    def auto_plot_general(self, filename, delta_days=1):
        temp = self.delta_day_data(path_to_data=['result', 'hourly', 'temperature'], delta_days=delta_days)
        aqi = self.delta_day_data(path_to_data=['result', 'hourly', 'air_quality', 'aqi'],
                                  path_to_value=['value', 'chn'], delta_days=delta_days)
        pm25 = self.delta_day_data(path_to_data=['result', 'hourly', 'air_quality', 'pm25'], delta_days=delta_days)
        dswrf = self.delta_day_data(path_to_data=['result', 'hourly', 'dswrf'], delta_days=delta_days)
        visibility = self.delta_day_data(path_to_data=['result', 'hourly', 'visibility'], delta_days=delta_days)
        cloudrate = self.delta_day_data(path_to_data=['result', 'hourly', 'cloudrate'], delta_days=delta_days)
        pressure = self.delta_day_data(path_to_data=['result', 'hourly', 'pressure'], delta_days=delta_days)
        skycon = self.delta_day_data(path_to_data=['result', 'hourly', 'skycon'], delta_days=delta_days)
        humidity = self.delta_day_data(path_to_data=['result', 'hourly', 'humidity'], delta_days=delta_days)
        precipitation = self.delta_day_data(path_to_data=['result', 'hourly', 'precipitation'], delta_days=delta_days)

        fig, axs = plt.subplots(nrows=4, ncols=1, figsize=(4, 8), sharex=True)

        # First axis Temperature & Precipitation
        ln0a = self._next_day_plotter(axs[0], temp, label='Temperature', plot_kwargs={'color': 'orangered'})

        # preset temperature limits
        ymin_set = -10
        ymax_set = 20
        # move up
        while np.max(temp['value']) > ymax_set:
            ymax_set += 10
            ymin_set += 10
        # move down
        while np.min(temp['value']) < ymin_set:
            ymin_set -= 10
            ymax_set -= 10
        # adjust delta
        while np.max(temp['value']) > ymax_set:
            ymax_set += 10

        axs[0].set_ylim(ymin_set, ymax_set)
        axs[0].set_ylabel('Temperature [℃]')
        axs[0].set_title('Weather [%s]' % temp['date'])
        axs[0].grid()
        ax0b = axs[0].twinx()
        ln0b = self._next_day_plotter(ax0b, precipitation, label='Precipitation', plot_kwargs={'color': 'royalblue'})
        ax0b.set_ylabel('Precipitation [mm/h]')
        ax0b.set_ylim(0.1, 100)
        ax0b.set_yscale('log')
        ln0s = ln0a + ln0b
        lab0s = [l.get_label() for l in ln0s]
        axs[0].legend(ln0s, lab0s)

        # Second axis AQI, pm25 & visibility
        ln1a0 = self._next_day_plotter(axs[1], aqi, label='AQI', plot_kwargs={'color': 'darkgreen'})
        ln1a1 = self._next_day_plotter(axs[1], pm25, label='PM2.5', plot_kwargs={'color': 'olive'})
        axs[1].set_ylim(1, 1000)
        axs[1].set_ylabel('Air Quality')
        axs[1].set_yscale('log')
        axs[1].grid()
        ax1b = axs[1].twinx()
        ln1b = self._next_day_plotter(ax1b, visibility, label='Visibility', plot_kwargs={'color': 'purple'})
        ax1b.set_ylabel('Visibility [km]')
        ax1b.set_ylim(0, 30)
        ln1s = ln1a0 + ln1a1 + ln1b
        lab1s = [l.get_label() for l in ln1s]
        axs[1].legend(ln1s, lab1s)

        # Third axis cloudrate & humidity
        ln2a = self._next_day_plotter(axs[2], cloudrate, label='Cloudrate', plot_kwargs={'color': 'deepskyblue'})
        axs[2].set_ylim(0, 1.05)
        axs[2].set_ylabel('Cloudrate [%]')
        axs[2].grid()
        ax2b = axs[2].twinx()
        ln2b = self._next_day_plotter(ax2b, humidity, label='Humidity', plot_kwargs={'color': 'springgreen'})
        ax2b.set_ylabel('Humidity [%]')
        ax2b.set_ylim(0, 1.05)
        ln2s = ln2a + ln2b
        lab2s = [l.get_label() for l in ln2s]
        axs[2].legend(ln2s, lab2s)

        # Forth axis Wind
        wind = self.delta_day_wind(delta_days=delta_days)
        self._wind_plotter(axs[3], wind)
        axs[3].set_ylabel('Wind Speed [m/s]')
        axs[3].set_xlabel('Time [H]')
        axs[3].set_ylim(0, 13)

        fig.tight_layout()
        fig.savefig(filename)

    def auto_plot_p2h(self, filename):
        # get 2h precipitation list of 120 elements
        p = self._locate_from_path(source_dict=self.get_resp(url=self.general_url()),
                                   path_list=['result', 'minutely', 'precipitation_2h'])
        # plot figure
        fig, ax = plt.subplots(figsize=(4, 3))
        t = np.arange(120) + 1
        ax.plot(t, p, color='royalblue')
        ax.set_xlabel('Time [min]')
        ax.set_ylabel('Precipitation [mm/h]')
        ax.set_ylim(0.1, 100)
        ax.set_yscale('log')
        ax.set_title('Precipitation forcast in 2 hours')
        ax.set_xlim(1, 120)
        fig.tight_layout()
        fig.savefig(filename)

    def auto_plot_wind_map(self, length_km, delta_km, filename, delta_days=1, hour=12, figsize=8., max_points=100):
        # overlay wind map on BaiduMap
        # optimized with threading

        earth_radius = 6378  # constant, km
        center_x = self.longitude
        center_y = self.latitude
        length_deg = length_km / (math.pi / 180 * earth_radius)
        delta_deg = delta_km / (math.pi / 180 * earth_radius)

        xx = np.arange(center_x - length_deg / 2, center_x + length_deg / 2 + delta_deg, delta_deg)
        yy = np.arange(center_y - length_deg / 2, center_y + length_deg / 2 + delta_deg, delta_deg)

        # initial conditions
        zoom = 2  # 3 or higher
        length_pixels = 0
        # adjust zooming and lengths
        while length_pixels < 500:
            zoom += 1
            length_pixels = (length_km + delta_km) / (6.13e-3 * 2 ** (15 - zoom))
            if zoom >= 18:
                break

        map_img_url = f"https://api.map.baidu.com/staticimage/v2?ak={BAIDU_MAP_API_TOKEN}" \
                      f"&center={center_x},{center_y}&width={length_pixels}&height={length_pixels}" \
                      f"&zoom={zoom}"
        print(map_img_url)

        nx = xx.shape[0]
        ny = yy.shape[0]

        # 当总点数超出最高点数后，以一定概率抛弃该点，防止过度访问
        probability = max_points/(nx*ny)

        # intialize array of WeatherApi objects
        wapi_array = []
        for x in xx:
            wapi_list = []
            for y in yy:
                wapi_list.append(WeatherAPI(x, y))
            wapi_array.append(wapi_list)

        # initialize threads
        thread_array = []
        for i in range(nx):
            thread_list = []
            for j in range(ny):
                thread_list.append(WapiThread(wapi=wapi_array[i][j], delta_days=delta_days))
                if random.random() > probability:
                    # 以一定概率（1-p）抛弃此数据点
                    thread_list[-1].fail_reason = 'abandoned'
                else:
                    thread_list[-1].start()
            thread_array.append(thread_list)

        # wait until completion
        while True:
            time.sleep(0.1)
            still_alive = False
            for i in range(nx):
                for j in range(ny):
                    if thread_array[i][j].is_alive():
                        still_alive = True
                        break
            if still_alive:
                # pipeline not finished
                continue
            else:
                break

        # fill wind arrays
        wind_array = []
        for i in range(nx):
            wind_list = []
            for j in range(ny):
                wind_list.append(thread_array[i][j].wind)
            wind_array.append(wind_list)

        n_unexpected_errors = 0

        # check errors
        for i in range(nx):
            for j in range(ny):
                if wind_array[i][j] is None:
                    if thread_array[i][j].unexpected_error:
                        n_unexpected_errors += 1
                        print(f'error in {i},{j}')
                        print(thread_array[i][j].fail_reason)

        img = Image.open(BytesIO(requests.get(map_img_url).content))

        h_index = None

        xlist = []  # longitude
        ylist = []  # latitude
        slist = []  # speed
        dlist = []  # direction

        for i in range(nx):
            for j in range(ny):
                if wind_array[i][j] is None:
                    # exception handling
                    # when data not properly acquired
                    continue
                else:
                    # when data acquired successfully
                    if h_index is None:
                        # when hour is not set
                        data_hour_list = wind_array[i][j]['hour']
                        if hour < data_hour_list[0]:
                            hour = data_hour_list[0]
                            h_index = 0
                        elif hour > data_hour_list[-1]:
                            hour = data_hour_list[-1]
                            h_index = -1
                        else:
                            h_index = hour - data_hour_list[0]
                    # loading data into plot variables
                    xlist.append(xx[i])
                    ylist.append(yy[j])
                    slist.append(wind_array[i][j]['speed'][h_index])
                    dlist.append(wind_array[i][j]['direction'][h_index])

        fig, ax = plt.subplots(figsize=(figsize, figsize))
        s = np.array(slist)
        d = np.array(dlist) * math.pi / 180
        u = -s * np.sin(d) / 1.852
        v = -s * np.cos(d) / 1.852

        ax.barbs(xlist, ylist, u, v, pivot='middle')
        ax.imshow(img, extent=(xx[0] - delta_deg / 2, xx[-1] + delta_deg / 2,
                               yy[0] - delta_deg / 2, yy[-1] + delta_deg / 2))
        ax.set_xlabel('Longitude [deg]')
        ax.set_ylabel('Latitude [deg]')

        # set title
        title = f'Wind Map {hour:02d}:00'
        if len(xlist) != (nx*ny):
            title += f' ({len(xlist)}/{nx*ny} points'
            if n_unexpected_errors > 0:
                title += f' with {n_unexpected_errors} errors'
            title += ')'

        ax.set_title(title)
        fig.tight_layout()
        fig.savefig(filename)

    def test(self):
        self.auto_plot_general('test_general.png')


# optimize with threadings
class WapiThread(threading.Thread):
    def __init__(self, wapi, delta_days):
        threading.Thread.__init__(self)
        self.wapi = wapi
        self.delta_days = delta_days
        self.wind = None
        self.success = False
        self.unexpected_error = False
        self.fail_reason = ''

    def run(self):
        try:
            max_connection_retries = 3
            retries = 0
            while not self.success:
                try:
                    wind = self.wapi.delta_day_wind(delta_days=self.delta_days)
                    self.wind = wind
                    self.success = True
                except requests.exceptions.ConnectionError as e:
                    # if failed by connection error, wait and restart
                    retries += 1
                    if retries <= max_connection_retries:
                        time.sleep(0.1)
                        # goes back to the while loop
                    else:
                        raise e
                        # raise the error to previous try (next line)
        except Exception:
            # if unexpected error happened or max retries reached
            self.unexpected_error = True
            self.fail_reason = traceback.format_exc()

