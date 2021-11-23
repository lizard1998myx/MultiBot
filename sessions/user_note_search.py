from .argument import ArgSession, Argument
from ..responses import ResponseMsg
from ..paths import PATHS
import pandas as pd
import os

TOTAL_TABLE = os.path.join(PATHS['data'], 'naoc_user_note.xlsx')


class UserNoteSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 60*2
        self.session_type = '联谊活动留言查询'
        self.extend_commands = ['note', '留言', '联谊']
        self.description = '根据用户UID、密码查询留言'
        self.arg_list = [Argument(key='UID', alias_list=['-u', '-id'], required=True,
                                  get_next=True,
                                  ask_text='请输入您的编号ID'),
                         Argument(key='password', alias_list=['-p', '-pwd'], required=True,
                                  get_next=True,
                                  ask_text='请输入密码')]
        self.default_arg = self.arg_list[0]
        self.detail_description = '用于国科大联谊活动留言查询，如有疑问请在群里咨询'

    def internal_handle(self, request):
        self.deactivate()
        username = str(self.arg_dict['UID'].value)
        password = str(self.arg_dict['password'].value)

        df = pd.read_excel(TOTAL_TABLE, dtype=str)
        notes = df[(df['username'] == username)&(df['password'] == password)]['note'].values

        if len(notes) == 0:
            return ResponseMsg(f'【{self.session_type}】未找到符合的条目，请检查输入信息。如有疑问请在群里咨询')
        else:
            msg = f'【{self.session_type}】为您找到{len(notes)}条留言：'
            for note in notes:
                msg += f'\n{note}'
            return ResponseMsg(msg)
