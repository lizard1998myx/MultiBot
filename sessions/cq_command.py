from ..responses import ResponseMsg, ResponseCQFunc
from ..permissions import get_permissions
from .general import Session


class CQCommandSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 30
        self.session_type = 'CQ控制台'
        self.strict_commands = ['command', 'cmd', 'console', '控制台', '命令']
        self.description = '使用onebot标准（github.com/botuniverse/onebot）的API控制机器人'
        self.permissions = get_permissions().get('super', {})
        self.is_first_time = True
        self.func_name = ''
        self.kwargs = {}

    def handle(self, request):
        if self.is_first_time:
            self.is_first_time = False
            return ResponseMsg('【%s】请输入函数名' % self.session_type)
        elif self.func_name == '':
            self.func_name = request.msg
            return ResponseMsg('【%s】请输入参数（字典形式）' % self.session_type)
        elif self.kwargs == {}:
            self.kwargs = eval(request.msg)
            self.deactivate()
            return ResponseCQFunc(func_name=self.func_name, kwargs=self.kwargs)

    def process_output(self, output):
        return ResponseMsg('【%s/Output】%s' % (self.session_type, str(output)))


class CQRebootSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 3
        self.session_type = 'CQ重启程序'
        self.strict_commands = ['restart', 'reboot', '重启']
        self.permissions = get_permissions().get('super', {})

    def handle(self, request):
        self.deactivate()
        return ResponseCQFunc(func_name='set_restart', kwargs={})

    def process_output(self, output):
        return ResponseMsg('【%s/Output】%s' % (self.session_type, str(output)))