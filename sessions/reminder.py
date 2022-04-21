from .argument import ArgSession
from .subscription import add_qq_subscription
from ..responses import ResponseMsg
from ..paths import PATHS
import pandas as pd
import datetime, os

REMINDER_TABLE_FILE = os.path.join(PATHS['data'], 'reminder_tables.xlsx')


# 给schedule调用，建议凌晨启用，否则会有延迟
def check_reminders():
    record_expired = ReminderTable().get_expired(user_id=None)
    for d in record_expired:
        add_qq_subscription(hour=d['inform_h'], temp_flag=0, no_repeat=True,
                            user_id=d['user_id'], msg=f'echo {d["inform_msg"]}')


class AddReminderSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '添加提醒'
        self.description = '任务提醒模块的添加功能'
        self._max_delta = 60
        self.strict_commands = ['提醒', 'AddRem']
        self.add_arg(key='user_id', alias_list=['-uid'],
                     required=False, get_next=True,
                     default_value=user_id,
                     help_text='接收提醒的用户ID（QQ号）',
                     ask_text='请输入接收提醒用户的ID（QQ号）')
        self.add_arg(key='event', alias_list=['-e'],
                     required=True, get_next=True,
                     help_text='提醒事件名称',
                     ask_text='需要提醒的事件是？')
        self.add_arg(key='days', alias_list=['-d'],
                     required=True, get_next=True,
                     help_text='事件超时周期（天）',
                     ask_text='多少天提醒一次？')
        self.add_arg(key='hour', alias_list=['-hr', '-h'],
                     required=False, get_next=True,
                     default_value=12,
                     help_text='发送提醒的时间（小时，0-23之间，可带小数，默认12点）',
                     ask_text='超时时，发送提醒的时间是（小时，可带小数，24时制）？')
        self.add_arg(key='msg', alias_list=['-m'],
                     required=False, get_next=True,
                     default_value='',
                     help_text='自定义提醒内容')
        self.default_arg = self.arg_list[1]  # event
        self.detail_description = '例如，发送“提醒 -e 浇水 -d 7 -hr 8.5 -m 该浇水啦”，' \
                                  '设置每七天提醒一次浇水。'

    def prior_handle_test(self, request):
        if request.platform != 'CQ':
            self.arg_dict['user_id'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        self.deactivate()

        try:
            inform_h = float(self.arg_dict['hour'].value)
            delta_days = max(1, int(self.arg_dict['days'].value))
        except ValueError:
            print(f'【{self.session_type}】输入时间格式有误')

        inform_h %= 24  # 余数
        inform_msg = self.arg_dict['msg'].value
        event = self.arg_dict['event'].value
        if not inform_msg:
            inform_msg = None

        ReminderTable().append(user_id=self.arg_dict['user_id'].value,
                               event=event,
                               inform_msg=inform_msg,
                               inform_h=inform_h,
                               max_delta=delta_days)

        return ResponseMsg(f'【{self.session_type}】成功：\n'
                           f'将每[{delta_days}]天提醒一次[{event}]事件')


class DelReminderSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '删除提醒'
        self.description = '任务提醒模块的删除和检查功能'
        self._max_delta = 60
        self.strict_commands = ['删除提醒', 'DelRem']
        self.add_arg(key='user_id', alias_list=['-uid'],
                     required=False, get_next=True,
                     default_value=user_id,
                     help_text='接收提醒的用户ID（QQ号）',
                     ask_text='请输入接收提醒用户的ID（QQ号）')
        self.add_arg(key='list', alias_list=['-l'],
                     required=False, get_next=False,
                     help_text='仅查看提醒列表，不删除')
        self.this_first_time = True
        self.reminders = None

    def prior_handle_test(self, request):
        if request.platform != 'CQ':
            self.arg_dict['user_id'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        if self.this_first_time:
            self.this_first_time = False
            self.reminders = ReminderTable().get_all(user_id=self.arg_dict['user_id'].value)

            msg = f''
            for i, d in enumerate(self.reminders):
                msg += f'{i+1}. {d["event"]} \n' \
                       f'    每{d["max_delta"]}天{int(d["inform_h"]):02d}时提醒\n' \
                       f'    上次执行于 {d["date"]}\n'
            msg = msg[:-1]

            if len(self.reminders) == 0:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】未找到条目')
            elif self.arg_dict['list'].called:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type} - 仅查看】找到以下条目：\n{msg}')
            else:
                return ResponseMsg(f'【{self.session_type} - 删除】找到以下条目：\n{msg}'
                                   f'请回复需要删除条目的序号（正整数），回复其他内容以取消')
        else:
            try:
                i_del = int(request.msg) - 1
            except ValueError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】未找到序号，退出')
            if i_del < 0 or i_del >= len(self.reminders):
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】序号超出范围，退出')
            d_del = self.reminders[i_del]
            try:
                ReminderTable().delete_record(d_delete=d_del)
            except ValueError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】未找到，退出')
            else:
                return ResponseMsg(f'【{self.session_type}】已删除：\n'
                                   f'每{d_del["max_delta"]}天提醒的事件{d_del["event"]}\n'
                                   f'请回复需继续删除的条目序号')


class UpdateReminderSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '更新提醒'
        self.description = '任务提醒模块的日期更新功能'
        self._max_delta = 60
        self.strict_commands = ['更新提醒', 'UpRem']
        self.add_arg(key='user_id', alias_list=['-uid'],
                     required=False, get_next=True,
                     default_value=user_id,
                     help_text='接收提醒的用户ID（QQ号）',
                     ask_text='请输入接收提醒用户的ID（QQ号）')
        self.add_arg(key='event', alias_list=['-e'],
                     required=True, get_next=True,
                     help_text='提醒事件名称',
                     ask_text='要更新哪个提醒时间？')
        self.add_arg(key='delta', alias_list=['-d'],
                     required=False, get_next=True,
                     default_value=0,
                     help_text='将最后执行时间更新到距离今天n天的时间')
        self.default_arg = self.arg_list[1]  # event
        self.detail_description = '例如，完成了任务后，发送“更新提醒 浇水”，' \
                                  '将最近浇水时间更新到当天。'

    def prior_handle_test(self, request):
        if request.platform != 'CQ':
            self.arg_dict['user_id'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        self.deactivate()
        try:
            delta_days = int(self.arg_dict['delta'].value)
        except ValueError:
            return ResponseMsg(f'【{self.session_type}】输入时间格式有误')

        d_found = ReminderTable().find_event(user_id=self.arg_dict['user_id'].value,
                                             event=self.arg_dict['event'].value)
        if d_found is None:
            return ResponseMsg(f'【{self.session_type}】未找到')
        else:
            date_original = d_found['date']
            d_new = ReminderTable().update_record(d_update=d_found, days_delta=delta_days)
            date_updated = d_new['date']
            return ResponseMsg(f'【{self.session_type}】完成[{d_found["event"]}]时间更新：\n'
                               f'{date_original} -> {date_updated}')


class ReminderTable:
    def __init__(self):
        self.table_file = REMINDER_TABLE_FILE

    def append(self, user_id,
               event='event', inform_msg=None,
               inform_h=12, max_delta=1):
        append_date = datetime.date.today().isoformat()

        assert isinstance(max_delta, int)

        if inform_msg is None:
            inform_msg = f'inform of event [{event}]'

        # 读取原数据
        if os.path.exists(self.table_file):
            dfl = pd.read_excel(self.table_file).to_dict('records')
        else:
            # 新建表格
            dfl = []

        dfl.append({'date': append_date, 'user_id': user_id,
                    'event': event,
                    'inform_msg': inform_msg,
                    'inform_h': inform_h,
                    'max_delta': max_delta})

        # 保存数据
        pd.DataFrame(dfl).to_excel(self.table_file, index=False)

    def find_event(self, user_id, event):
        records_all = self.get_all(user_id=user_id)
        for d in records_all:
            if str(d['event']) == str(event):
                return d
        return None

    def get_all(self, user_id=None) -> list:
        records = []
        if os.path.exists(self.table_file):
            dfl = pd.read_excel(self.table_file).to_dict('records')
            if user_id is None:
                return dfl  # 未指定用户时，返回全部
            for d in dfl:
                if str(d['user_id']) == str(user_id):
                    records.append(d)
        return records

    def get_expired(self, user_id=None) -> list:
        records_all = self.get_all(user_id=user_id)
        records_expired = []
        for d in records_all:
            delta_days = datetime.date.today() - datetime.date.fromisoformat(d['date'])
            if delta_days >= d['max_delta']:  # 过期
                records_expired.append(d)
            elif delta_days == d['max_delta'] + 1:  # 差一天过期，但超过提醒时间了
                now = datetime.datetime.now()
                now_h = now.hour + now.minute/60
                if now_h > float(d['inform_h']):
                    records_expired.append(d)
        return records_expired

    # 删除一条记录
    def delete_record(self, d_delete):
        if os.path.exists(self.table_file):
            dfl = pd.read_excel(self.table_file).to_dict('records')
            for i, d in enumerate(dfl):
                if d == d_delete:
                    dfl = dfl[:i] + dfl[i+1:]
                    pd.DataFrame(dfl).to_excel(self.table_file, index=False)
                    return
            raise ValueError('未找到条目')
        raise FileNotFoundError('未找到表格')

    # 更新记录的日期（默认为今天，可向前或向后改）
    def update_record(self, d_update, days_delta=0):
        if os.path.exists(self.table_file):
            dfl = pd.read_excel(self.table_file).to_dict('records')
            for i, d in enumerate(dfl):
                if d == d_update:
                    today = datetime.date.today()
                    delta = datetime.timedelta(days=days_delta)
                    d['date'] = (today + delta).isoformat()
                    dfl = dfl[:i] + [d] + dfl[i+1:]
                    pd.DataFrame(dfl).to_excel(self.table_file, index=False)
                    return d
            raise ValueError('未找到条目')
        raise FileNotFoundError('未找到表格')

