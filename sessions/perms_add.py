from ..responses import ResponseMsg
from .argument import ArgSession, Argument
from ..permissions import PERM_FILE, PERM_KEYS, get_permissions
import pandas as pd
import os, datetime


class AddPermissionSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '添加权限用户'
        self._max_delta = 60
        self.strict_commands = ['添加权限', '新权限']
        self.arg_list = [Argument(key='type', alias_list=['-t'],
                                  required=True, get_next=True,
                                  help_text='权限项目名称',
                                  ask_text='要添加的权限项目名称是？'),
                         Argument(key='key', alias_list=['-k'],
                                  required=True, get_next=True,
                                  help_text='权限项目密码',
                                  ask_text='添加权限项目密码是？'),
                         Argument(key='platform', alias_list=['-plt', '-p'],
                                  required=False, get_next=True,
                                  help_text='平台'),
                         Argument(key='user_id', alias_list=['-uid', '-u'],
                                  required=False, get_next=True,
                                  help_text='用户ID')
                         ]
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        self.deactivate()

        # 读取记录
        perm_type = str(self.arg_dict['type'].value)
        perm_key = str(self.arg_dict['key'].value)

        if self.arg_dict['user_id'].called:
            user_id = str(self.arg_dict['user_id'].value)
        else:
            user_id = request.user_id

        if self.arg_dict['platform'].called:
            platform = str(self.arg_dict['platform'].value)
        else:
            platform = request.platform

        if perm_type not in PERM_KEYS.keys():
            return ResponseMsg(f'【{self.session_type}】权限项目不存在')

        if PERM_KEYS[perm_type] and PERM_KEYS[perm_type] != perm_key:  # 有密码的情况下，密码错误
            return ResponseMsg(f'【{self.session_type}】权限密码不正确')

        new_item = {'type': perm_type, 'platform': platform, 'user_id': user_id}

        if os.path.exists(PERM_FILE):
            dfl = pd.read_excel(PERM_FILE).to_dict('records')
        else:
            # 新建表格
            dfl = []

        dfl.append(new_item)
        pd.DataFrame(dfl).to_excel(PERM_FILE, index=False)

        return ResponseMsg(f'【{self.session_type}】权限添加成功：\n{new_item}')


class DelPermissionSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '删除权限条目'
        self._max_delta = 60
        self.strict_commands = ['删除权限']
        self.permissions = get_permissions().get('super', {})
        self.arg_list = [Argument(key='n_items', alias_list=['-n'],
                                  required=False, get_next=True,
                                  default_value = 10,
                                  help_text='查阅的条目数')]
        self.default_arg = None  # 没有缺省argument
        self.detail_description = '寻找并删除权限条目，只有属于最高权限的用户可以执行'
        self.this_first_time = True
        self.table_filename = PERM_FILE
        self._indexes = []
        self._records = []

    def internal_handle(self, request):
        if self.this_first_time:
            self.this_first_time = False
            if not os.path.exists(self.table_filename):
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】没有权限记录')
            else:
                try:
                    n_items = int(self.arg_dict['n_items'].value)
                    if n_items <= 0:
                        raise ValueError
                except ValueError:
                    self.deactivate()
                    return ResponseMsg(f'【{self.session_type}】数值输入有误')

                dfl = pd.read_excel(self.table_filename).to_dict('records')[-n_items:]
                msg = ''
                n = 0
                for i, d in enumerate(dfl):
                    n += 1
                    self._indexes.append(i)
                    self._records.append(d)
                    msg += f'{n}. [{d["type"]}] {d["platform"]} - {d["user_id"]}\n'
                if len(self._indexes) == 0:
                    self.deactivate()
                    return ResponseMsg(f'【{self.session_type}】未找到有关条目')
                else:
                    return ResponseMsg(f'【{self.session_type}】找到以下条目：\n{msg}'
                                       f'请回复需要删除条目的序号（正整数），回复其他内容以取消')
        else:  # 删除条目
            try:
                i_del = int(request.msg) - 1
            except ValueError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】未找到序号，退出')
            if i_del < 0 or i_del >= len(self._indexes):
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】序号超出范围，退出')
            # 读取数据
            dfl = pd.read_excel(self.table_filename).to_dict('records')
            i_start = min(len(dfl)-1, self._indexes[i_del])  # 从右边向左找
            for i in range(i_start, -1, -1):  # 回溯
                d = dfl[i]
                if d == self._records[i_del]:  # record matched
                    dfl = dfl[:i] + dfl[i+1:]
                    pd.DataFrame(dfl).to_excel(self.table_filename, index=False)
                    return ResponseMsg(f'【{self.session_type}】已删除条目{i_del + 1}:\n'
                                       f'{d}\n'
                                       f'请回复需继续删除的条目序号')
            self.deactivate()
            return ResponseMsg(f'【{self.session_type}】未找到符合条件的条目，退出')
