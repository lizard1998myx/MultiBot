from MultiBot.sessions.general import Session
from MultiBot.responses import ResponseMsg


class StandbySession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.is_first_time = True
        self.session_type = '待命'
        self._max_delta = 60
        self.description = f'消息等待，在群聊中常用，用于被呼叫后{self._max_delta}秒内随时应答消息'

    def probability_to_call(self, request):
        return 10

    def is_legal_request(self, request):
        return True

    def handle(self, request):
        if self.is_first_time:
            self.is_first_time = False
            return [ResponseMsg('在')]
        else:
            self.deactivate()
            return request


