from ..responses import ResponseMsg
from .argument import ArgSession, Argument
from ..paths import PATHS
import pandas as pd
import os, datetime

# 2021-12-11: 完成代码并进行调试
# 2021-12-11: 支持多条加入，另外加入了删除机制

SUBS_LIST = os.path.join(PATHS['data'], 'qq_subscription_list.xlsx')


# 给scheduler调用，用于查找订阅列表
def get_qq_subscriptions(request, now=None):
    # 如果订阅列表不存在
    if not os.path.exists(SUBS_LIST):
        return []

    df = pd.read_excel(SUBS_LIST)
    request_list = []
    expire_list = []
    if now is None:
        now = datetime.datetime.now()

    for i in df.to_dict('records'):
        if int(i['hour']) == now.hour and int(i['minute'] == now.minute):
            new_r = request.new(msg=i['message'])
            new_r.user_id = str(i['user_id'])
            request_list.append(new_r)
            if i['temp'] == 1:  # 临时项目
                expire_list.append(i)

    # 去除过期项目（temp项）
    if len(expire_list) > 0:
        dfl = df.to_dict('records')
        new_dfl = []
        for i in dfl:
            if i not in expire_list:
                new_dfl.append(i)
        pd.DataFrame(new_dfl).to_excel(SUBS_LIST, index=False)

    return request_list


# 添加新的订阅，用于AddSubscription插件和其他
# 如果用类封装会更好
def add_qq_subscription(hour, msg, user_id, minute=0, dhour=0, temp=False, no_repeat=False, get_brief=False):
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

    # 读取原数据
    if os.path.exists(SUBS_LIST):
        df = pd.read_excel(SUBS_LIST)
        df['user_id'] = df['user_id'].astype(str)
        dfl = df.to_dict('records')
    else:
        # 新建表格
        dfl = []

    def append_record(d, dfl=dfl, no_repeat=no_repeat):
        if no_repeat:
            if d not in dfl:
                dfl.append(d)
        else:
            dfl.append(d)

    if dhour > 0:  # 重复，往后
        for h in range(hour, 24, dhour):
            append_record({'hour': h, 'minute': minute, 'user_id': user_id, 'temp': temp_flag, 'message': msg})
    elif dhour < 0:  # 重复，往回
        for h in range(hour, -1, dhour):
            append_record({'hour': h, 'minute': minute, 'user_id': user_id, 'temp': temp_flag, 'message': msg})
    else:  # 不重复
        append_record({'hour': hour, 'minute': minute, 'user_id': user_id, 'temp': temp_flag, 'message': msg})

    # 保存数据
    pd.DataFrame(dfl).to_excel(SUBS_LIST, index=False)

    if get_brief:
        return f'{hour:02d}:{minute:02d} - {user_id}\n{msg}'


class AddQQSubscriptionSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '添加QQ订阅条目'
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
                     help_text='接收订阅的用户ID（QQ号）',
                     ask_text='请输入接收订阅用户的ID（QQ号）')
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
        if request.platform != 'CQ':
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

        brief = add_qq_subscription(hour=hour, minute=minute, dhour=dhour,
                                    msg=msg, user_id=user_id,
                                    temp=self.arg_dict['temp'].called,
                                    get_brief=True)

        return ResponseMsg(f'【{self.session_type}】订阅成功：\n{brief}\n'
                           f'（添加好友后可收取通知）')


class DelQQSubscriptionSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '删除QQ订阅条目'
        self._max_delta = 60
        self.strict_commands = ['删除订阅', '取消订阅', 'unsubscribe']
        self.arg_list = [Argument(key='user_id', alias_list=['-uid'],
                                  required=False, get_next=True,
                                  default_value=user_id,
                                  help_text='对应的用户ID（QQ号）'),
                         Argument(key='list', alias_list=['-l'],
                                  required=False, get_next=False,
                                  help_text='仅查看订阅列表，不删除')]
        self.default_arg = None  # 没有缺省argument
        self.detail_description = '寻找并删除订阅条目，默认使用发送人的id'
        self.this_first_time = True
        self._indexes = []
        self._records = []

    def prior_handle_test(self, request):
        if request.platform != 'CQ':
            self.arg_dict['user_id'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        if self.this_first_time:
            self.this_first_time = False
            if not os.path.exists(SUBS_LIST):
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】没有订阅记录')
            else:
                dfl = pd.read_excel(SUBS_LIST).to_dict('records')
                msg = ''
                n = 0
                uid = self.arg_dict['user_id'].value  # 已经设置default
                for i, d in enumerate(dfl):
                    if str(d['user_id']) == uid:
                        n += 1
                        self._indexes.append(i)
                        self._records.append(d)
                        msg += f'{n}. ({d["hour"]:02d}:{d["minute"]:02d}'
                        if d['temp']:
                            msg += '|temp'
                        msg += f') {d["message"]}\n'
                if len(self._indexes) == 0:
                    self.deactivate()
                    return ResponseMsg(f'【{self.session_type}】未找到有关条目')
                elif self.arg_dict['list'].called:
                    self.deactivate()
                    return ResponseMsg(f'【{self.session_type} - 仅查看】找到以下条目：\n{msg}')
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
            dfl = pd.read_excel(SUBS_LIST).to_dict('records')
            i_start = min(len(dfl)-1, self._indexes[i_del])  # 从右边向左找
            for i in range(i_start, -1, -1):  # 回溯
                d = dfl[i]
                if d == self._records[i_del]:  # record matched
                    dfl = dfl[:i] + dfl[i+1:]
                    pd.DataFrame(dfl).to_excel(SUBS_LIST, index=False)
                    return ResponseMsg(f'【{self.session_type}】已删除条目{i_del + 1}:\n'
                                       f'({d["hour"]:02d}:{d["minute"]:02d}) {d["message"]}\n'
                                       f'请回复需继续删除的条目序号')
            self.deactivate()
            return ResponseMsg(f'【{self.session_type}】未找到符合条件的订阅条目，退出')
