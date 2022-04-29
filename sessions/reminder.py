from .argument import ArgSession
from .subscription import add_qq_subscription
from ..responses import ResponseMsg
from ..paths import PATHS
from ..external.record_table import RecordTable, RecordNotFoundError
import pandas as pd
import datetime, os

REMINDER_TABLE_FILE = os.path.join(PATHS['data'], 'reminder_tables.xlsx')


# 给schedule调用，建议凌晨启用，否则会有延迟
def check_reminders():
    record_expired = ReminderTable().find_expired(user_id=None)
    for d in record_expired:
        add_qq_subscription(hour=d['inform_h'], temp=True, no_repeat=True,
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
        self._max_delta = 60
        self.strict_commands = ['删除提醒', 'DelRem']
        self.add_arg(key='user_id', alias_list=['-uid'],
                     required=False, get_next=True,
                     default_value=user_id,
                     help_text='接收提醒的用户ID（QQ号）',
                     ask_text='请输入接收提醒用户的ID（QQ号）')
        self.this_first_time = True
        self.reminder_table = None

    def prior_handle_test(self, request):
        if request.platform != 'CQ':
            self.arg_dict['user_id'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        if self.this_first_time:
            self.this_first_time = False
            self.reminder_table = ReminderTable()
            record_list = self.reminder_table.find_all(user_id=self.arg_dict['user_id'].value)

            if len(record_list) == 0:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】未找到条目')
            else:
                return ResponseMsg(f'【{self.session_type}】找到以下条目：\n'
                                   f'{self.reminder_table.list_records(record_list=record_list)}\n'
                                   f'请回复需要删除条目的序号（正整数），回复其他内容以取消')
        else:
            try:
                d_del = self.reminder_table.pop_by_index(index=request.msg)
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
                return ResponseMsg(f'【{self.session_type}】已删除：\n'
                                   f'每{d_del["max_delta"]}天提醒的事件[{d_del["event"]}]\n'
                                   f'请回复需继续删除的条目序号')


class ListReminderSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '查看提醒'
        self._max_delta = 60
        self.strict_commands = ['查看提醒', 'LsRem', 'ViewRem']
        self.add_arg(key='user_id', alias_list=['-uid'],
                     required=False, get_next=True,
                     default_value=user_id,
                     help_text='接收提醒的用户ID（QQ号）',
                     ask_text='请输入接收提醒用户的ID（QQ号）')
        self.reminder_table = None

    def prior_handle_test(self, request):
        if request.platform != 'CQ':
            self.arg_dict['user_id'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        self.deactivate()
        self.reminder_table = ReminderTable()
        record_list = self.reminder_table.find_all(user_id=self.arg_dict['user_id'].value)

        if len(record_list) == 0:
            return ResponseMsg(f'【{self.session_type}】未找到条目')
        else:
            return ResponseMsg(f'【{self.session_type}】找到以下条目：\n'
                               f'{self.reminder_table.list_records(record_list=record_list)}')


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
                     ask_text='要更新哪个提醒事件？')
        self.add_arg(key='delta', alias_list=['-d'],
                     required=False, get_next=True,
                     default_value=0,
                     help_text='将最后执行时间更新到距离今天n天的时间（未来为正）')
        self.default_arg = [self.arg_list[1], self.arg_list[2]]  # event, delta
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


class CheckReminderSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '检查提醒'
        self.description = '任务提醒模块的检查功能，上报给订阅器'
        self._max_delta = 60
        self.strict_commands = ['检查提醒', 'ChkRem']

    def internal_handle(self, request):
        self.deactivate()
        check_reminders()
        return ResponseMsg(f'【{self.session_type}】done')


class ReminderTable(RecordTable):
    def __init__(self):
        RecordTable.__init__(self, table_file=REMINDER_TABLE_FILE,
                             string_cols=['user_id'])

    def append(self, user_id,
               event='event', inform_msg=None,
               inform_h=12, max_delta=1):
        assert isinstance(max_delta, int)

        if inform_msg is None:
            inform_msg = f'inform of event [{event}]'

        item = {'date': datetime.date.today().isoformat(),
                'user_id': user_id,
                'event': event,
                'inform_msg': inform_msg,
                'inform_h': inform_h,
                'max_delta': max_delta}

        self.append_full(item=item)

    def find_event(self, user_id, event):
        records_all = self.find_all(user_id=user_id)
        for d in records_all:
            if str(d['event']) == str(event):
                return d
        return None

    def find_expired(self, user_id=None) -> list:
        records_all = self.find_all(user_id=user_id)
        records_expired = []
        for d in records_all:
            delta_days = datetime.date.today() - datetime.date.fromisoformat(d['date'])
            delta_days = delta_days.days
            if delta_days >= d['max_delta']:  # 过期
                records_expired.append(d)
            elif delta_days == d['max_delta'] + 1:  # 差一天过期，但超过提醒时间了
                now = datetime.datetime.now()
                now_h = now.hour + now.minute/60
                if now_h > float(d['inform_h']):
                    records_expired.append(d)
        return records_expired

    # 更新记录的日期（默认为今天，可向前或向后改）
    def update_record(self, d_update: dict, days_delta=0):
        record_old = d_update
        record_new = d_update.copy()
        today = datetime.date.today()
        delta = datetime.timedelta(days=days_delta)
        record_new['date'] = (today + delta).isoformat()

        self.replace(record_old=record_old, record_new=record_new)
        return record_new

    @staticmethod
    def list_single_record(record) -> str:
        days_passed = datetime.date.today() - datetime.date.fromisoformat(record['date'])
        days_left = max(record["max_delta"] - days_passed.days, 0)

        return f'{record["event"]} \n' \
               f'    每{record["max_delta"]}天{int(record["inform_h"]):02d}时提醒\n' \
               f'    上次执行于 {record["date"]}，距下次{days_left}天'


