from ..responses import ResponseGrpMsg
from .general import Session
from .subcovid import daily_run
from .classroom_schedule import classroom_cache_update
from .covid_regions import covid_region_cache_update
from .covid_data import covid_data_cache_update_schedule
from .subscription import get_qq_subscriptions
from .reminder import check_reminders
import datetime

# 2021-12-11: 支持分钟级，并加入订阅功能


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
        if request.platform == 'CQ' and request.from_scheduler:
            return True
        return False

    def handle(self, request):
        response_list = []
        now = datetime.datetime.now()
        if now.minute == 0:  # 整点
            if 0 <= now.hour <= 2:
                check_reminders()
            if now.hour == 3:
                classroom_cache_update()
            if 4 <= now.hour <= 6:
                daily_run()
            if now.hour in [7, 10, 11, 12, 18]:
                covid_data_cache_update_schedule()
            if now.hour in [8, 14, 20]:
                covid_region_cache_update()
        return response_list + get_qq_subscriptions(request=request, now=now)


class WCScheduleSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = 'WC定时任务'
        self.description = '已停用，群报时，发送问好和天气预报'

    def probability_to_call(self, request):
        if self.is_legal_request(request=request):
            return 100
        return 0

    def is_legal_request(self, request):
        if request.platform == 'Wechat' and request.from_scheduler:
            return True
        return False

    def handle(self, request):
        response_list = []
        now = datetime.datetime.now()
        if now.minute == 0:  # 整点
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
