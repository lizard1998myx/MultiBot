from ..responses import ResponseMsg, ResponseImg
from ..version_description import DESCRIPTION, VERSION_LIST, INTRODUCTION
from ..paths import PATHS
import datetime, os, csv

DEFAULT_WAIT = 10
HISTORY_DIR = PATHS['history']
DATA_DIR = PATHS['data']


# 基本的Session类，默认功能是复读机
class Session:
    def __init__(self, user_id):
        self._active = True
        self._last_activity = datetime.datetime.now()  # 上次活动时间
        self.user_id = user_id
        self.session_id = ''
        self.session_type = 'general'
        self.description = ''
        self._max_delta = DEFAULT_WAIT  # 最大挂起时间（单位：秒），超时后会被关闭
        self.extend_commands = []  # 包含即唤起
        self.strict_commands = []  # 严格相等时才唤起
        # 权限要求，内容为 platform: id_list，空序列表示全部通过
        # 例如：{'Console': [], 'CQ': ['123456']}
        # 表示控制台的所有用户、CQ中id为123456的用户有权限，其他平台拒绝
        self.permissions = {}
        self._list_commands = True

    # 判断是否在活动，检查挂起时间是否超出时限
    def is_active(self):
        if self._active:
            delta = datetime.datetime.now() - self._last_activity
            if delta.seconds < self._max_delta:
                return True
        self._active = False
        return False

    # 停止本Session的活动，一般是执行完全部指令后在Session内主动停止
    def deactivate(self):
        self._active = False

    # 刷新最后活动时间，在分拣中心中调用
    def refresh(self):
        self._active = True
        self._last_activity = datetime.datetime.now()

    # 处理这个Request时，本Session的唤起率/优先级（最大值100，大的Session优先）
    def probability_to_call(self, request):
        return self._called_by_command(request=request)

    # 默认session在特定command下100%唤起
    # 可传入Request，也可直接传入string
    def _called_by_command(self, request=None, msg=None, extend_p=100, strict_p=100):
        if not isinstance(msg, str):
            assert request is not None
            msg = request.msg
        if isinstance(msg, str):
            for command in self.extend_commands:
                if command.lower() in msg.lower():
                    return extend_p
            for command in self.strict_commands:
                if command.lower() == msg.lower():
                    return strict_p
        return 0

    # 判断这个request是否符合Session所需
    def is_legal_request(self, request):
        return self._permission(request=request) and self._text_request_only(request=request)

    # 默认session只响应文本request，这个方法供它们调用
    def _text_request_only(self, request):
        return request.msg and not request.img

    # 在有权限要求的情况下，可能返回false
    def _permission(self, request):
        if self.permissions:
            try:
                id_list = self.permissions[request.platform]
                if not id_list:  # empty list, permission granted anyway
                    return True
                elif self.user_id in id_list:
                    return True
                else:  # id not in permission list
                    return False
            except KeyError:  # platform not in permission
                return False
        else:
            return True

    # 处理传入的request，并返回response序列
    def handle(self, request):
        return []

    # 在handle时主动获取信息，再到此处进行下一步处理，默认是直接打印返回值
    def process_output(self, output):
        # return ResponseMsg('【%s/Output】%s' % (self.session_type, str(output)))
        return []

    # Session的描述
    def help(self):
        return self._default_help()

    def _default_help(self):
        help_text = '[插件名] %s' % self.session_type
        if self.permissions:
            help_text += ' (受限)'
        if self._list_commands:
            if self.extend_commands or self.strict_commands:
                help_text += '\n[关键词] '
                for command in self.extend_commands:
                    help_text += '{}+, '.format(command)
                for command in self.strict_commands:
                    help_text += '{}, '.format(command)
                help_text = help_text[:-2]
        if self._max_delta != DEFAULT_WAIT:
            help_text += '\n[等待时间] %i 秒' % self._max_delta
        if self.description:
            help_text += '\n{}'.format(self.description)
        return help_text


class RepeatSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.extend_commands = ['复读']
        self.session_type = '复读机'
        self.header = '【%s】' % self.session_type
        self.description = '复读一次消息，或复读图片'

    def probability_to_call(self, request):
        if request.echo:
            self.header = ''
            return 200
        else:
            return max(20, self._called_by_command(request=request))

    def is_legal_request(self, request):
        return request.msg or request.img

    def handle(self, request):
        responses = []
        if isinstance(request.img, str):
            responses.append(ResponseMsg('%s复读图片' % self.header))
            responses.append(ResponseImg(request.img))
        if isinstance(request.msg, str) and request.msg != '':
            responses.append(ResponseMsg('%s%s' % (self.header, request.msg)))
        self.deactivate()
        return responses


class IdentitySession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = 'ID检查'
        self.strict_commands = ['ID']
        self.description = '测试用，显示消息平台和用户ID'

    def handle(self, request):
        self.deactivate()
        return ResponseMsg('【%s】\nplatform=%s\nuser_id=%s' % (self.session_type,
                                                              request.platform, request.user_id))


class IntroSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = '简介'
        self.strict_commands = ['你好', 'hello', 'hi']

    def handle(self, request):
        self.deactivate()
        return ResponseMsg(INTRODUCTION.get(request.platform, INTRODUCTION['Default']))


class DescriptionSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = '详细信息'
        self.strict_commands = ['more', 'des', 'description', '描述', '更多']
        # self.description = '显示机器人概述、版本目标、反馈途径等'

    def handle(self, request):
        self.deactivate()
        return ResponseMsg(DESCRIPTION)


class VersionSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = '版本信息'
        self.strict_commands = ['ver', 'version', '版本']
        # self.description = '显示机器人版本更新信息'

    def handle(self, request):
        self.deactivate()
        version_string = "[%s]\n" % self.session_type
        for version in VERSION_LIST:
            version_string += 'V%s (%s): %s\n' % (version['version'], version['date'], version['info'])
        return ResponseMsg(version_string[:-1])


class HelpSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = '使用说明'
        self.strict_commands = ['help', '帮助', '说明']
        # self.description = '显示机器人插件使用说明'

    def handle(self, request):
        self.deactivate()
        help_text = f'[{self.session_type}]\n' \
                    f'机器人消息处理由插件控制，以下为插件使用帮助，' \
                    f'包括：插件名称，唤起关键词（不区分大小写，带+表示不严格指令，即消息中带有该关键字即唤起），' \
                    f'等待时间（需要输入多条消息时，等待下一条消息的时长，默认为{DEFAULT_WAIT}秒）和其他说明。' \
                    f'标明“受限”的插件仅限部分平台或部分用户使用，其他情况下会被忽略。' \
                    f'不同插件有优先级，符合多条插件关键词的消息会有限唤起高优先级的插件。' \
                    f'部分插件可以通过“插件关键词 帮助”的形式查看更详细的使用说明。\n\n'
        with open(os.path.join(DATA_DIR, 'help_description.txt'), 'r') as f:
            help_text += f.read()
        # bug：在cqhttp中可能无法发送
        return ResponseMsg(help_text)


class ErrorSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = '测试报错'
        self.strict_commands = ['error', '报错']

    def handle(self, request):
        self.deactivate()
        raise Exception('[{}]人工抛出错误，用于异常处理测试'.format(self.session_type))


class HistorySession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = '插件使用历史'
        self.strict_commands = ['history', '历史']
        self._history_table_file = os.path.join(HISTORY_DIR, 'history.csv')

    # V3.3.2 优化文件性能
    def _merge_history_file(self):
        keys = ['platform', 'user_id', 'session', 'time']
        new_history_records = []
        files_to_remove = []
        if not os.path.exists(self._history_table_file):
            new_row = {}
            for k in keys:
                new_row[k] = k
            new_history_records.append(new_row)
        for file in os.listdir(HISTORY_DIR):
            if file[-4:] == '.txt':
                files_to_remove.append(file)
                history_record = {}
                with open(os.path.join(HISTORY_DIR, file), 'r') as f:
                    lines = f.readlines()
                for i, k in enumerate(keys):
                    history_record[k] = lines[i].strip().replace(f'{k}=', '')
                if history_record['session'] in ['QQ定时任务', '插件使用历史']:  # ignore list
                    pass
                else:
                    new_history_records.append(history_record)

        with open(self._history_table_file, 'a+', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            for row in new_history_records:
                writer.writerow(row)

        for file in files_to_remove:
            try:
                os.remove(os.path.join(HISTORY_DIR, file))
            except FileNotFoundError:
                pass

    def handle(self, request):
        self.deactivate()

        # merge
        self._merge_history_file()

        # read
        session_list = []
        try:
            with open(self._history_table_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    session_list.append(row['session'])
        except FileNotFoundError:
            pass

        # count & print
        history_dict = {}
        for session in session_list[::-1]:  # new ones come first
            if session in history_dict.keys():
                history_dict[session] += 1
            else:
                history_dict[session] = 1
        history_text = f'[{self.session_type}]\n'
        for s, i in history_dict.items():
            history_text += f'{s}[{i}], '
        if history_text[-2:] == ', ':
            history_text = history_text[:-2]
        return ResponseMsg(history_text)