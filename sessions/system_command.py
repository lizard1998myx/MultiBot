from .argument import ArgSession, Argument
from ..responses import ResponseMsg
from ..permissions import get_permissions
import os


class SystemCmdSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '系统命令'
        self.description = '执行一条命令'
        self._max_delta = 120
        self.strict_commands = ['system', 'sys']
        self.arg_list = [Argument(key='command', alias_list=['-c'],
                                  required=True, get_next=True,
                                  ask_text='请输入要执行的命令',
                                  help_text='执行的命令')]
        self.default_arg = self.arg_list[0]
        self.permissions = get_permissions().get('super', {})

    def internal_handle(self, request):
        self.deactivate()
        with os.popen(str(self.arg_dict['command'].value)) as f:
            text = f.read()
        if text:
            return ResponseMsg(text)
        else:
            return ResponseMsg(f'【{self.session_type}】空白返回值')

