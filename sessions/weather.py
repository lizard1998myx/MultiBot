from MultiBot.sessions.argument import ArgSession, Argument
from MultiBot.responses import ResponseMsg, ResponseImg
from MultiBot.api_tokens import CAIYUN_API_TOKEN, BAIDU_MAP_API_TOKEN
import requests, urllib, datetime, os, math, re
import matplotlib.pyplot as plt
import numpy as np


class WeatherSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 60*2
        self.session_type = '天气插件'
        self.strict_commands = ['weather', '天气']
        self.description = '根据给定的地点查找经纬度，并从彩云天气API（caiyunapp.com）获取实时天气'
        # self.is_first_time = True
        self.arg_list = [Argument(key='location', alias_list=['-l', '-loc'], required=True,
                                  get_next=True, get_all=True,
                                  ask_text='请返回要查找的地点或经纬度（逗号隔开）'),
                         Argument(key='no-realtime', alias_list=['-nr'],
                                  help_text='不获取实时天气'),
                         Argument(key='general', alias_list=['-g'],
                                  help_text='获取次日天气总览（温度、降水、空气质量、风力等）'),
                         Argument(key='wind', alias_list=['-w'],
                                  help_text='获取次日风力预报'),
                         Argument(key='precipitation', alias_list=['-p'],
                                  help_text='获取2小时降雨预报'),
                         Argument(key='today', alias_list=['-t'],
                                  help_text='修改为获取今日天气（对天气总览与风力预报有效）'),
                         ]
        self.default_arg = self.arg_list[0]
        self.detail_description = '例如，可以直接发送“天气”后回复地理位置获取实时天气，或直接发送“天气 北京”获取信息。\n'\
                                  '也可直接使用经纬度，如“天气 120.0,40.0”，注意不加空格，单命令行的空格是参数的分隔符。\n'\
                                  '进阶可发送“天气 雁栖湖 -nr -w -t”获取今日（-t）风力预报（-w），且不获取实时天气（-nr）。'

    def is_legal_request(self, request):
        if not self.is_first_time and request.loc is not None:
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
                loc_str = self.arg_dict['location'].value
                use_coord = False
                # try coordinates
                if ',' in loc_str or '，' in loc_str:
                    coord_str = re.split(pattern='[,，]', string=loc_str)
                    # coord_str = loc_str.split(',', '，')
                    try:
                        assert len(coord_str) == 2
                        longitude = float(coord_str[0])
                        latitude = float(coord_str[1])
                        assert -180.0 < longitude < 180.0
                        assert -90.0 < latitude < 90.0
                        use_coord = True
                        w_api = WeatherAPI(longitude=longitude, latitude=latitude)
                    except ValueError:
                        pass
                    except AssertionError:
                        pass
                # use city name instead
                if not use_coord:
                    w_api = WeatherAPI()
                    w_api.set_city(city_name=self.arg_dict['location'].value)
            if not self.arg_dict['no-realtime'].called:  # add general report
                responses.append(ResponseMsg(w_api.realtime_report()))

            # select target date
            if self.arg_dict['today'].called:
                delta_days = 0
            else:
                delta_days = 1

            # get detail prediction
            if self.arg_dict['general'].called:  # add general report
                filename = os.path.abspath(os.path.join('..', 'temp',
                                                        '%s_Next_day_general.jpg' % datetime.date.today().isoformat()))
                w_api.auto_plot_general(filename=filename, delta_days=delta_days)
                responses.append(ResponseImg(file=filename))
            if self.arg_dict['wind'].called:  # add wind report
                filename = os.path.abspath(os.path.join('..', 'temp',
                                                        '%s_Next_day_wind.jpg' % datetime.date.today().isoformat()))
                w_api.auto_plot_winds(filename=filename, delta_days=delta_days)
                responses.append((ResponseImg(file=filename)))
            if self.arg_dict['precipitation'].called:
                filename = os.path.abspath(os.path.join('..', 'temp',
                                                        '%s_2h_precipitation.jpg' % datetime.date.today().isoformat()))
                w_api.auto_plot_p2h(filename=filename)
                responses.append((ResponseImg(file=filename)))
            return responses
        except KeyError:
            return ResponseMsg('【%s】天气查询异常' % self.session_type)


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
        realtime_string = '温度[%.2f ℃]，相对湿度[%.0f%%]\n' % (rdict['temperature'], 100 * rdict['humidity']) + \
                          '云量[%.0f%%]，天气状况[%s]\n' % (100 * rdict['cloudrate'], rdict['skycon']) + \
                          '能见度[%.1f km]，向下短波辐射通量[%.1f W/M2]\n' % (rdict['visibility'], rdict['dswrf']) + \
                          '风速[%.2f kmph]，风向[%.1f°]\n' % (rdict['wind']['speed'], rdict['wind']['direction']) + \
                          '压强[%.1f Pa]，体感温度[%.1f ℃]\n' % (rdict['pressure'], rdict['apparent_temperature']) + \
                          '本地降水：强度[%.1f]\n' % rdict['precipitation']['local']['intensity'] + \
                          '最近降水：距离[%.1f km]，强度[%.1f]\n' % (rdict['precipitation']['nearest']['distance'],
                                                           rdict['precipitation']['nearest']['intensity']) + \
                          '空气污染物浓度(默认μg/m3)：pm2.5[%.0f]，pm10[%.0f]，臭氧[%.1f]，二氧化氮[%.1f]，二氧化硫[%.1f]，一氧化碳[%.1f mg/m3]\n' % (
                          rdict['air_quality']['pm25'], rdict['air_quality']['pm10'], rdict['air_quality']['o3'],
                          rdict['air_quality']['no2'], rdict['air_quality']['so2'], rdict['air_quality']['co']) + \
                          'AQI：中国[%.0f]，美国[%.0f]\n' % (
                          rdict['air_quality']['aqi']['chn'], rdict['air_quality']['aqi']['usa']) + \
                          '生活指数：紫外线[%.1f(%s)]，舒适度[%i(%s)]' % (
                          rdict['life_index']['ultraviolet']['index'], rdict['life_index']['ultraviolet']['desc'],
                          rdict['life_index']['comfort']['index'], rdict['life_index']['comfort']['desc'])
        return f'== 实时天气@{self.longitude:.2f},{self.latitude:.2f} ==\n{self.get_city()}\n{realtime_string}'

    @staticmethod
    def _locate_from_path(source_dict, path_list):
        result = source_dict
        for key in path_list:
            result = result[key]
        return result

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
        return {'date': target_date.isoformat(),
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
        ax.set_title('Hourly Temperature %s' % date)
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
        ax1.set_title('Weather Forecast %s' % a['date'])
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
        ax.set_title('Wind Forcast %s' % w['date'])
        fig.tight_layout()
        fig.savefig(filename)

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
        axs[0].set_ylim(10, 40)
        axs[0].set_ylabel('Temperature [℃]')
        axs[0].set_title('Weather Forecast %s' % temp['date'])
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


    def test(self):
        self.auto_plot_general('test_general.png')


def next_day_temperature(longitude=116.33, latitude=39.98):
    wapi = WeatherAPI(longitude=longitude, latitude=latitude)
    filename = os.path.abspath(os.path.join('..', 'temp',
                                            '%s_Next_day_weather.jpg' % datetime.date.today().isoformat()))
    wapi.plot_temperature(**wapi.next_day_temperature(), filename=filename)
    return ResponseImg(file=filename)


def next_day_t_a(longitude=116.33, latitude=39.98):
    wapi = WeatherAPI(longitude=longitude, latitude=latitude)
    filename = os.path.abspath(os.path.join('..', 'temp',
                                            '%s_Next_day_t_a.jpg' % datetime.date.today().isoformat()))
    wapi.auto_plot_t_a(filename=filename)
    return ResponseImg(file=filename)


def next_day_general(longitude=116.33, latitude=39.98):
    wapi = WeatherAPI(longitude=longitude, latitude=latitude)
    filename = os.path.abspath(os.path.join('..', 'temp',
                                            '%s_Next_day_general.jpg' % datetime.date.today().isoformat()))
    wapi.auto_plot_general(filename=filename)
    return ResponseImg(file=filename)


def next_day_wind(longitude=116.33, latitude=39.98):
    wapi = WeatherAPI(longitude=longitude, latitude=latitude)
    filename = os.path.abspath(os.path.join('..', 'temp',
                                            '%s_Next_day_wind.jpg' % datetime.date.today().isoformat()))
    wapi.auto_plot_winds(filename=filename)
    return ResponseImg(file=filename)


def realtime_weather(longitude=116.33, latitude=39.98):
    wapi = WeatherAPI(longitude=longitude, latitude=latitude)
    return wapi.realtime_report()