from MultiBot.responses import ResponseGrpMsg, ResponseGrpImg
from MultiBot.sessions.general import Session
from MultiBot.sessions.subcovid import daily_run
from MultiBot.sessions.weather import next_day_general, realtime_weather
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
        if 4 <= now.hour <= 6:
            subcovid_result = daily_run()
            subcovid_msg = '【自动疫情填报】成功%i个，失败%i个' % (subcovid_result['success'], subcovid_result['fail'])
            # subcovid_msg += '\n' + str(subcovid_result['reasons'])
            response_list.append(ResponseGrpMsg(group_id='230697355', text=subcovid_msg))
        if now.hour == 6:
            response_list.append(ResponseGrpMsg(group_id='865640538', text='国台的扛把子们早上好！o(*￣▽￣*)ブ'))
        if now.hour == 23:
            response_list.append(ResponseGrpMsg(group_id='865640538', text='夜深了。辛苦了一天，大家晚安！:)'))
            f = next_day_general().file
            response_list.append(ResponseGrpImg(group_id='865640538', file=f))
            response_list.append(ResponseGrpImg(group_id='230697355', file=f))
        response_list.append(ResponseGrpMsg(group_id='230697355', text='【报时】现在%i点了' % now.hour))
        # response_list.append(ResponseGrpMsg(group_id='230697355', text=realtime_weather(116.69, 40.41)))
        return response_list

