from ..responses import ResponseMsg, ResponseCQFunc
from .general import Session
import random


class CQGroupSuicideSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 10
        self.session_type = 'QQ群正义执行'
        self.description = '对机器人测试群中的水友提供实时的一键（被）禁言和一键退群服务'
        self.key_to_ban = ['ban', '禁言']
        self.key_to_exit = ['退群']
        self.extend_commands = self.key_to_ban + self.key_to_exit
        self.ban_duration = 60
        self.available_groups = ['230697355']
        self.report = ''

    def is_legal_request(self, request):
        if isinstance(request.msg, str) and request.platform == 'CQ':
            if request.group_id is not None and request.group_id in self.available_groups:
                return True
        return False

    def handle(self, request):
        self.deactivate()
        for key in self.key_to_ban:
            if key in request.msg:
                self.report = '【一键禁言】已对%s禁言%i秒' % (request.user_id, self.ban_duration)
                return ResponseCQFunc(func_name='set_group_ban',
                                      kwargs={'group_id': int(request.group_id),
                                              'user_id': int(request.user_id),
                                              'duration': self.ban_duration})
        for key in self.key_to_exit:
            if key in request.msg:
                self.report = '【一键退群】已对%s执行' % request.user_id
                return ResponseCQFunc(func_name='set_group_kick',
                                      kwargs={'group_id': int(request.group_id),
                                              'user_id': int(request.user_id)})

    def process_output(self, output):
        return ResponseMsg(self.report)


class CQGroupRandomSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 10
        self.session_type = 'QQ群抽签'
        self.extend_commands = ['roll', 'random', '随机', '抽奖']
        self.description = '在群中随机抽取一位幸运水友'
        self.self_id = '1976787406'

    def is_legal_request(self, request):
        return isinstance(request.msg, str) and request.platform == 'CQ' and request.group_id is not None

    def handle(self, request):
        self.deactivate()
        return ResponseCQFunc(func_name='get_group_member_list',
                              kwargs={'group_id': int(request.group_id)})

    def process_output(self, output: list):
        group_member_list = output
        while True:
            member_id = random.choice(group_member_list)['user_id']
            if member_id != self.self_id:
                break
        response = ResponseMsg('【%s】' % self.session_type)
        response.at_list.append(member_id)
        return response
