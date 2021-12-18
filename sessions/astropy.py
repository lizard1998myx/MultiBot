import numpy as np
from astropy import units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_sun, get_moon
from astropy.coordinates.name_resolve import NameResolveError
import matplotlib.pyplot as plt
import datetime
import os
from ..utils import image_filename
from .argument import ArgSession, Argument
from ..responses import ResponseMsg, ResponseImg
from ..paths import PATHS


class AstroPlotSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '天体高度计算'
        self.description = '计算天体高度的工具，基于astropy'
        self._max_delta = 60
        self.extend_commands = ['天体高度', '观测', 'astroplot']
        self.strip_command = True
        self.arg_list = [Argument(key='star', alias_list=['-s'],
                                  required=True, get_next=True,
                                  ask_text='天体名称是？',
                                  help_text='要查看的天体名称'),
                         Argument(key='polar', alias_list=['-p'],
                                  help_text='画天球图'),
                         Argument(key='days_delta', alias_list=['-d'],
                                  get_next=True, default_value=0,
                                  help_text='时间（到今天）'),
                         ]
        self.default_arg = self.arg_list[0]
        self.detail_description = '观测坐标位于河北兴隆'

    def internal_handle(self, request):
        self.deactivate()
        responses = []
        altitude_filename = os.path.join(PATHS['temp'], image_filename(header='AstroAltitude'))
        responses.append(ResponseImg(file=altitude_filename))
        if self.arg_dict['polar'].called:
            polar_filename = os.path.join(PATHS['temp'], image_filename(header='AstroPolar'))
            responses.append(ResponseImg(file=polar_filename))
        else:
            polar_filename = None

        try:
            days_delta = int(self.arg_dict['days_delta'].value)
        except ValueError:
            return ResponseMsg(f'【{self.session_type}】日期格式有误')

        try:
            get_altitude(star_name=self.arg_dict['star'].value,
                         altitude_filename=altitude_filename,
                         polar_filename=polar_filename,
                         days_delta=days_delta)
        except NameResolveError:
            return ResponseMsg(f'【{self.session_type}】目标[{self.arg_dict["star"].value}]未找到')

        return responses


def get_altitude(star_name, altitude_filename=None, polar_filename=None,
                 days_delta=0):
    midnight_time = (datetime.datetime.today() + datetime.timedelta(days=days_delta+1)).strftime('%Y-%m-%d 00:00:00')
    try:
        source = SkyCoord.from_name(star_name)
    except ValueError:
        return {'observable': False}
    site_loc = EarthLocation(lon=(117+34/60+28.35/3600)*u.deg,
                             lat=(40+23/60+45.36/3600)*u.deg,
                             height=900*u.m)
    utcoffset = 8*u.hour
    # utctime = Time('2021-5-22 23:00:00') - utcoffset
    # source.transform_to(AltAz(obstime=utctime, location=site_loc))
    midnight = Time(midnight_time) - utcoffset
    n_times = 500
    delta_midnight = np.linspace(-12, 12, n_times)*u.hour
    times = midnight + delta_midnight  # utctime
    frame = AltAz(obstime=times, location=site_loc)
    source_altazs = source.transform_to(frame)
    sun_altazs = get_sun(times).transform_to(frame)
    moon_altazs = get_moon(times).transform_to(frame)

    if altitude_filename is not None:
        plt.plot(delta_midnight, sun_altazs.alt, color='r', label='Sun')
        plt.plot(delta_midnight, moon_altazs.alt, color=[0.75]*3, ls='--', label='Moon')
        plt.scatter(delta_midnight, source_altazs.alt,
                    c=source_altazs.az, label=star_name, lw=0, s=8,
                    cmap='viridis')
        plt.fill_between(delta_midnight, 0*u.deg, 90*u.deg,
                         sun_altazs.alt < -0*u.deg, color='0.5', zorder=0)
        plt.fill_between(delta_midnight, 0*u.deg, 90*u.deg,
                         sun_altazs.alt < -18*u.deg, color='k', zorder=0)
        plt.colorbar().set_label('Azimuth [deg]')
        plt.legend(loc='upper left')
        # plt.xlim(-12*u.hour, 12*u.hour)
        plt.xlim(-12, 12)
        # plt.xticks((np.arange(13)*2-12)*u.hour)
        plt.xticks(np.arange(13)*2-12)
        # plt.ylim(0*u.deg, 90*u.deg)
        plt.ylim(0, 90)
        plt.xlabel('Hours from EDT Midnight')
        plt.ylabel('Altitude [deg]')
        plt.savefig(altitude_filename)
        plt.close()

    if polar_filename is not None:
        at_night = sun_altazs.alt < 0*u.deg
        ax = plt.subplot(111, projection='polar')
        # projection = 'polar' 指定为极坐标
        ax.set_rlim(0, 90)
        ax.plot()

        ax.plot(source_altazs.az.rad[at_night], 90 - source_altazs.alt.deg[at_night], label=star_name)
        ax.plot(moon_altazs.az.rad[at_night], 90 - moon_altazs.alt.deg[at_night],
                color=[0.75]*3, ls='--', label='Moon')

        ax.grid(True)  # 是否有网格
        ax.legend()
        plt.savefig(polar_filename)
        plt.close()



