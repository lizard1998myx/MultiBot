from MultiBot.responses import ResponseGrpMsg, ResponseGrpImg
from MultiBot.sessions.general import Session
from MultiBot.sessions.weather import next_day_general
import datetime, os


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
        """
        if now.hour == 6:
            inform = '233'
            response_list.append(ResponseGrpMsg(group_id='20201501班级群', text=inform))
            inform_img = os.path.join(os.path.abspath('..'), 'data', 'covid_inform.jpg')
            if os.path.exists(inform_img):
                response_list.append(ResponseGrpImg(group_id='20201501班级群', file=inform_img))
        """
        if now.hour == 23:
            response_list.append(ResponseGrpImg(group_id='20201501班级群',  # '国科大天文学院2020级学生群'
                                                file=next_day_general().file))
        if now.hour % 3 == 0:
            time_info = ResponseGrpMsg(group_id='Testing', text='【报时】现在%i点了' % now.hour)
            time_info.at_list.append('Bot.Lizard')
            response_list.append(time_info)
        return response_list
