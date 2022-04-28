from ..responses import ResponseMsg
from .argument import ArgSession
from ..permissions import PERM_FILE, PERM_KEYS, get_permissions
from ..external.record_table import RecordTable, RecordNotFoundError
import pandas as pd
import os


class AddPermissionSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '添加权限用户'
        self._max_delta = 60
        self.strict_commands = ['添加权限', '新权限']
        self.add_arg(key='type', alias_list=['-t'],
                     required=True, get_next=True,
                     help_text='权限项目名称',
                     ask_text='要添加的权限项目名称是？')
        self.add_arg(key='key', alias_list=['-k'],
                     required=True, get_next=True,
                     help_text='权限项目密码',
                     ask_text='添加权限项目密码是？')
        self.add_arg(key='platform', alias_list=['-plt', '-p'],
                     required=False, get_next=True,
                     help_text='平台')
        self.add_arg(key='user_id', alias_list=['-uid', '-u'],
                     required=False, get_next=True,
                     help_text='用户ID')
        self.default_arg = self.arg_list[0]

    def prior_handle_test(self, request):
        # 设置默认值为request
        self.arg_dict['user_id'].value = request.user_id
        self.arg_dict['platform'].value = request.platform

    def internal_handle(self, request):
        self.deactivate()

        # 读取记录
        perm_type = str(self.arg_dict['type'].value)
        perm_key = str(self.arg_dict['key'].value)
        user_id = str(self.arg_dict['user_id'].value)
        platform = str(self.arg_dict['platform'].value)

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
        self.add_arg(key='n_items', alias_list=['-n'],
                     required=False, get_next=True,
                     default_value=10,
                     help_text='查阅的条目数')
        self.default_arg = None  # 没有缺省argument
        self.detail_description = '寻找并删除权限条目，只有属于最高权限的用户可以执行'
        self.this_first_time = True
        self.record_table = None

    def internal_handle(self, request):
        if self.this_first_time:
            self.this_first_time = False

            # 检查输入n_items
            try:
                n_items = int(self.arg_dict['n_items'].value)
                if n_items <= 0:
                    raise ValueError
            except ValueError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】数值输入有误')

            self.record_table = PermissionTable()
            record_list = self.record_table.find_all()[-n_items:]  # 只看一部分

            if len(record_list) == 0:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】未找到条目')
            else:
                return ResponseMsg(f'【{self.session_type} - 删除】找到以下条目：\n'
                                   f'{self.record_table.list_records(record_list=record_list)}\n'
                                   f'请回复需要删除条目的序号（正整数），回复其他内容以取消')

        else:  # 删除条目
            try:
                d_del = self.record_table.pop_by_index(index=request.msg, from_new=True)
            except ValueError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】退出')
            except RecordNotFoundError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】未找到相符记录，退出')
            except IndexError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】序号超出范围，退出')
            else:
                return ResponseMsg(f'【{self.session_type}】已删除条目:\n'
                                   f'{d_del}\n'
                                   f'请回复需继续删除的条目序号')


class PermissionTable(RecordTable):
    def __init__(self):
        RecordTable.__init__(self, table_file=PERM_FILE, string_cols=['user_id'])

    @staticmethod
    def list_single_record(record) -> str:
        return f'[{record["type"]}] {record["platform"]} - {record["user_id"]}'
