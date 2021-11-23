from ..responses import ResponseGrpMsg, ResponseGrpImg
from .general import Session
from .subcovid import daily_run
from .weather import next_day_general
from .classroom_schedule import classroom_cache_update
from .covid_regions import covid_region_cache_update
import datetime


class QQScheduleSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = 'QQ定时任务'
        self.description = '预设定时任务模块，包括自动填报、报时、早晚问好、天气预报'

    def probability_to_call(self, request):
        if self.is_legal_request(request=request):
            return 100
        return 0

    def is_legal_request(self, request):
        if request.platform == 'CQ':
            return True
        return False

    def handle(self, request):
        response_list = []
        now = datetime.datetime.now()
        if now.hour == 3:
            classroom_cache_update()
        if now.hour in [8, 14, 20]:
            covid_region_cache_update()
        if 4 <= now.hour <= 6:
            subcovid_result = daily_run()
            subcovid_msg = '【自动疫情填报】成功%i个，失败%i个' % (subcovid_result['success'], subcovid_result['fail'])
            response_list.append(ResponseGrpMsg(group_id=230697355, text=subcovid_msg))
        if now.hour == 6:
            response_list.append(ResponseGrpMsg(group_id=865640538, text='国台的扛把子们早上好！o(*￣▽￣*)ブ'))
        if now.hour == 22:
            f = next_day_general().file
            f2 = next_day_general(116.26, 39.92).file
            response_list.append(ResponseGrpImg(group_id=865640538, file=f))
            response_list.append(ResponseGrpImg(group_id=230697355, file=f))
            response_list.append(ResponseGrpImg(group_id=810070877, file=f2))
        response_list.append(ResponseGrpMsg(group_id=230697355, text='【报时】现在%i点了' % now.hour))
        return response_list


class WCScheduleSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = 'WC定时任务'
        self.description = '在测试，群报时，发送问好和天气预报'

    def probability_to_call(self, request):
        if self.is_legal_request(request=request):
            return 100
        return 0

    def is_legal_request(self, request):
        if request.platform == 'Wechat':
            return True
        return False

    def handle(self, request):
        response_list = []
        now = datetime.datetime.now()
        if now.hour == 22:
            response_list.append(ResponseGrpImg(group_id='20201501班级群',  # '国科大天文学院2020级学生群'
                                                file=next_day_general().file))
        if now.hour % 3 == 0:
            time_info = ResponseGrpMsg(group_id='Testing', text='【报时】现在%i点了' % now.hour)
            time_info.at_list.append('Bot.Lizard')
            response_list.append(time_info)
        if now.hour == 4:
            classroom_cache_update()
        if 5 <= now.hour <= 7:
            subcovid_result = daily_run()
            subcovid_msg = '【自动疫情填报】成功%i个，失败%i个' % (subcovid_result['success'], subcovid_result['fail'])
            response_list.append(ResponseGrpMsg(group_id='Testing', text=subcovid_msg))
        if now.hour == 9:
            covid_region_cache_update()
        return response_list
