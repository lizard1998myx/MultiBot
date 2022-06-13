from ..responses import ResponseMsg
from .argument import ArgSession
from ..paths import PATHS
from ..external.record_table import RecordTable, RecordNotFoundError
import os, datetime

# 2021-12-11: 完成代码并进行调试
# 2021-12-11: 支持多条加入，另外加入了删除机制
# 2022-06-13: 支持企业微信平台

SUBS_LIST = os.path.join(PATHS['data'], 'qq_subscription_list.xlsx')
SUBS_LISTS = {'CQ': os.path.join(PATHS['data'], 'qq_subscription_list.xlsx'),
              'WCE': os.path.join(PATHS['data'], 'wce_subscription_list.xlsx')}


# 给scheduler调用，用于查找订阅列表
def get_qq_subscriptions(request, now=None):
    return SubscriptionRecords().get_subscriptions(request=request, now=now)


# 添加新的订阅，用于AddSubscription插件和其他
def add_qq_subscription(hour, msg, user_id, minute=0, dhour=0, temp=False, no_repeat=False, get_brief=False):
    return SubscriptionRecords().append(hour=hour, msg=msg, user_id=user_id,
                                        minute=minute, dhour=dhour, temp=temp,
                                        no_repeat=no_repeat, get_brief=get_brief)


# 同样功能，但用于企业微信平台
def get_wce_subscriptions(request, now=None):
    return SubscriptionRecords(platform='WCE').get_subscriptions(request=request, now=now)


def add_wce_subscription(hour, msg, user_id, minute=0, dhour=0, temp=False, no_repeat=False, get_brief=False):
    return SubscriptionRecords(platform='WCE').append(hour=hour, msg=msg, user_id=user_id,
                                                      minute=minute, dhour=dhour, temp=temp,
                                                      no_repeat=no_repeat, get_brief=get_brief)


class AddSubscriptionSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '添加订阅条目'
        self.description = '添加订阅条目，进行定点报时或天气预报等'
        self._max_delta = 60
        self.strict_commands = ['订阅', 'subscribe']
        self.add_arg(key='hour', alias_list=['-hr'],
                     required=True, get_next=True,
                     help_text='发送消息的时间（小时，0-23之间）',
                     ask_text='定时任务的时间是（小时，可带小数，24时制）？')
        self.add_arg(key='minute', alias_list=['-min'],
                     required=False, get_next=True,
                     default_value=0,
                     help_text='发送消息的时间（分钟，0-59之间）')
        self.add_arg(key='delta-hour', alias_list=['-dhr'],
                     required=False, get_next=True,
                     default_value=0,
                     help_text='重复发送间隔（整数，默认为0，不重复）')
        self.add_arg(key='user_id', alias_list=['-uid'],
                     required=False, get_next=True,
                     default_value=user_id,
                     help_text='接收订阅的用户ID（QQ号/企业微信ID）',
                     ask_text='请输入接收订阅用户的ID（QQ号/企业微信ID）')
        self.add_arg(key='platform', alias_list=['-p'],
                     required=False, get_next=True,
                     default_value='CQ',
                     help_text='订阅平台，除企业微信平台外默认为CQ（QQ），'
                               '可变更为WCE（企业微信）')
        self.add_arg(key='temp', alias_list=['-t'],
                     required=False, get_next=False,
                     help_text='一次性订阅条目标记')
        self.add_arg(key='message', alias_list=['-msg'],
                     required=True, get_next=True,
                     help_text='订阅内容',
                     ask_text='订阅内容（即定时发送的指令）是？')

        self.default_arg = [self.arg_list[0], self.arg_list[-1]]
        self.detail_description = '例如，发送“订阅 -hr 23 -min 30 -msg 北京疫情”，' \
                                  '每天晚23时30分机器人会认为你给它发送了“北京疫情”指令，' \
                                  '他就会将疫情信息发送给你。\n' \
                                  '进阶案例：\n' \
                                  '1. 订阅 -hr 20 -msg "天气 北京市奥林匹克公园 -g -nr"\n' \
                                  '2. 订阅 -hr 8 -msg "查教室 -d 今天 -b 教一楼 -c 雁栖湖 -y"\n' \
                                  '3. 订阅 -hr 8 -dhr 6 -msg "天气 北京市 -wmap"'

    def prior_handle_test(self, request):
        if request.platform == 'WCE':
            self.arg_dict['platform'].value = 'WCE'
        elif request.platform != 'CQ':
            self.arg_dict['user_id'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        self.deactivate()

        # 读取记录
        try:
            hour = float(self.arg_dict['hour'].value)
            minute = float(self.arg_dict['minute'].value)
            dhour = int(self.arg_dict['delta-hour'].value)
        except ValueError:
            return ResponseMsg(f'【{self.session_type}】输入时间格式有误')

        msg = self.arg_dict['message'].value
        user_id = str(self.arg_dict['user_id'].value)  # 已经设置default value

        if self.arg_dict['platform'].value.upper() in ['CQ', 'QQ']:
            brief = add_qq_subscription(hour=hour, minute=minute, dhour=dhour,
                                        msg=msg, user_id=user_id,
                                        temp=self.arg_dict['temp'].called,
                                        get_brief=True)
        elif self.arg_dict['platform'].value.upper() in ['WCE']:
            brief = add_wce_subscription(hour=hour, minute=minute, dhour=dhour,
                                         msg=msg, user_id=user_id,
                                         temp=self.arg_dict['temp'].called,
                                         get_brief=True)
        else:
            return ResponseMsg(f'【{self.session_type}】平台参数仅支持CQ/WCE两种')

        return ResponseMsg(f'【{self.session_type}】订阅成功：\n{brief}\n'
                           f'（添加好友后可收取通知）')


class DelSubscriptionSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '删除订阅条目'
        self._max_delta = 60
        self.strict_commands = ['删除订阅', '取消订阅', 'unsubscribe']
        self.add_arg(key='user_id', alias_list=['-uid'],
                     required=False, get_next=True,
                     default_value=user_id,
                     help_text='对应的用户ID（QQ号/企业微信ID）')
        self.add_arg(key='platform', alias_list=['-p'],
                     required=False, get_next=True,
                     default_value='CQ',
                     help_text='订阅平台，除企业微信平台外默认为CQ（QQ），'
                               '可变更为WCE（企业微信）')
        self.default_arg = None  # 没有缺省argument
        self.detail_description = '寻找并删除订阅条目，默认使用发送人的id'
        self.this_first_time = True
        self.record_table = None

    def prior_handle_test(self, request):
        if request.platform == 'WCE':
            self.arg_dict['platform'].value = 'WCE'
        elif request.platform != 'CQ':
            self.arg_dict['user_id'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        if self.this_first_time:
            self.this_first_time = False

            try:
                self.record_table = SubscriptionRecords(platform=self.arg_dict['platform'].value.upper())
            except KeyError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】平台参数仅支持CQ/WCE两种')

            record_list = self.record_table.find_all(user_id=self.arg_dict['user_id'].value)

            if len(record_list) == 0:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】未找到条目')
            else:
                return ResponseMsg(f'【{self.session_type}】找到以下条目：\n'
                                   f'{self.record_table.list_records(record_list=record_list)}\n'
                                   f'请回复需要删除条目的序号（正整数），回复其他内容以取消')
        else:  # 删除条目
            try:
                d_del = self.record_table.pop_by_index(index=request.msg)
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
                                   f'({d_del["hour"]:02d}:{d_del["minute"]:02d}) {d_del["message"]}\n'
                                   f'请回复需继续删除的条目序号')


class ListSubscriptionSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '查看订阅条目'
        self._max_delta = 60
        self.strict_commands = ['查看订阅', '订阅列表']
        self.add_arg(key='user_id', alias_list=['-uid'],
                     required=False, get_next=True,
                     default_value=user_id,
                     help_text='对应的用户ID（QQ号/企业微信ID）')
        self.add_arg(key='platform', alias_list=['-p'],
                     required=False, get_next=True,
                     default_value='CQ',
                     help_text='订阅平台，除企业微信平台外默认为CQ（QQ），'
                               '可变更为WCE（企业微信）')
        self.default_arg = None  # 没有缺省argument
        self.detail_description = '寻找并删除订阅条目，默认使用发送人的id'
        self.record_table = None

    def prior_handle_test(self, request):
        if request.platform == 'WCE':
            self.arg_dict['platform'].value = 'WCE'
        elif request.platform != 'CQ':
            self.arg_dict['user_id'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        self.deactivate()

        try:
            self.record_table = SubscriptionRecords(platform=self.arg_dict['platform'].value.upper())
        except KeyError:
            return ResponseMsg(f'【{self.session_type}】平台参数仅支持CQ/WCE两种')

        record_list = self.record_table.find_all(user_id=self.arg_dict['user_id'].value)

        if len(record_list) == 0:
            return ResponseMsg(f'【{self.session_type}】未找到条目')
        else:
            return ResponseMsg(f'【{self.session_type}】找到以下条目：\n'
                               f'{self.record_table.list_records(record_list=record_list)}')


class SubscriptionRecords(RecordTable):
    def __init__(self, platform='CQ'):
        if platform == 'QQ':
            platform = 'CQ'
        RecordTable.__init__(self, table_file=SUBS_LISTS[platform], string_cols=['user_id'])

    @staticmethod
    def list_single_record(record) -> str:
        msg = ''
        msg += f'({record["hour"]:02d}:{record["minute"]:02d}'
        if record['temp']:
            msg += ' | temp'
        msg += f') {record["message"]}'
        return msg

    def _append_no_repeat(self, record_list):
        for i in record_list:
            if i not in self.get_dfl():  # 每次都要检查
                self.append_full(i)

    def append(self, hour, msg, user_id, minute=0, dhour=0, temp=False, no_repeat=False, get_brief=False):
        # 整理、检测合法性
        minute = float(minute) + float(hour) * 60  # 全部加到分钟上
        minute = int(minute)  # 向下取整
        hour = minute // 60
        minute %= 60
        hour %= 24
        dhour = int(dhour)
        user_id = str(user_id)

        if temp:
            temp_flag = 1
        else:
            temp_flag = 0

        new_records = []

        if dhour > 0:  # 重复，往后
            for h in range(hour, 24, dhour):
                new_records.append({'hour': h, 'minute': minute, 'user_id': user_id, 'temp': temp_flag, 'message': msg})
        elif dhour < 0:  # 重复，往回
            for h in range(hour, -1, dhour):
                new_records.append({'hour': h, 'minute': minute, 'user_id': user_id, 'temp': temp_flag, 'message': msg})
        else:  # 不重复
            new_records.append({'hour': hour, 'minute': minute, 'user_id': user_id, 'temp': temp_flag, 'message': msg})

        if no_repeat:
            self._append_no_repeat(record_list=new_records)
        else:
            for i in new_records:
                self.append_full(item=i)

        if get_brief:
            return f'{hour:02d}:{minute:02d} - {user_id}\n{msg}'

    def get_subscriptions(self, request, now=None):
        # 如果订阅列表不存在
        if not self.is_exist():
            return []

        request_list = []  # 转化成的request
        expire_list = []  # 过期的临时项目
        if now is None:
            now = datetime.datetime.now()

        for i in self.get_dfl():
            if int(i['hour']) == now.hour and int(i['minute'] == now.minute):
                new_r = request.new(msg=i['message'])
                new_r.user_id = str(i['user_id'])
                request_list.append(new_r)
                if i['temp'] == 1:  # 临时项目
                    expire_list.append(i)

        # 去除过期项目（temp项）
        for i in expire_list:
            try:
                self.delete(record=i, from_new=False)
            except RecordNotFoundError:
                pass

        return request_list
