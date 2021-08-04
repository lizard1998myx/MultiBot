from MultiBot.responses import ResponseMsg
from MultiBot.sessions.general import Session


# 计数器
class CounterSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 10
        self.session_type = '计数菌'
        self.extend_commands = ['计数', 'count']
        self.description = '唤起此插件后会记录消息条数，%i秒未回复则关闭' % self._max_delta
        self.dialog_history = []

    def handle(self, request):
        if len(self.dialog_history) > 0:
            last = ResponseMsg('【%s】上次收到消息是：\n%s' % (self.session_type, self.dialog_history[-1]))
        else:
            last = ResponseMsg('【%s】这是计数器第一次收到消息' % self.session_type)
        self.dialog_history.append(request.msg)
        return [ResponseMsg(f'【{self.session_type}】目前已收到消息{len(self.dialog_history)}条'),
                ResponseMsg(f'【{self.session_type}】这次收到的消息是：\n{request.msg}'),
                last]