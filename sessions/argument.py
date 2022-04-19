from .general import Session
from ..responses import ResponseMsg
import logging

# 2021-12-12: 加入strip command项，将is_first_time改名
# 2022-04-18: 加入add_arg方法，不需要再import Argument
# 2022-04-19: 增加list类default_arg的处理


class Argument:
    def __init__(self, key='arg', alias_list=[], required=False,
                 get_next=False, get_all=False, ask_text=None, help_text=None,
                 default_value=None):
        """
        ArgSession中，每个需要处理的argument
        :param key: argument名称，可用于arg
        :param alias_list: 同义词，用于输入arg
        :param required: 是否必要
        :param get_next: 是否获取下一条指令
        :param get_all: 是否获取整个request
        :param ask_text: 若缺少这个arg，如何要求输入？
        :param help_text: 帮助信息
        :param default_value: value的缺省值
        """
        self.key = key
        self.alias_list = alias_list
        self.required = required
        self.called = False  # 是否被呼叫过
        self.get_next = get_next
        self.get_all = get_all
        self.value = default_value
        self.raw_req = None
        self.ask_text = ask_text
        self.help_text = help_text
        # assert not get_next or not get_all


class ArgSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = 'argument'
        self.description = '模板，处理带argument的Session'
        self._is_first_time = True
        self.arg_list = []
        self.arg_dict = {}
        self.default_arg = None
        self.help_args = ['help', '帮助', '-h', '--h', '-help', '--help', '-?', '--?']
        self.mute_args = ['-mute', '--mute']
        self.detail_description = ''
        self._interrupted = False
        self._mute_response = False
        self.strip_command = False

    def add_arg(self, **kwargs):
        self.arg_list.append(Argument(**kwargs))

    def probability_to_call(self, request):
        try:
            msg = request.msg.split()[0]
        except AttributeError:
            return 0
        except IndexError:
            return 0
        else:
            return self._called_by_command(msg=msg)

    def help(self, detail=False):
        help_str = self._default_help()
        if not detail:
            return help_str
        else:
            # 介绍所有参数
            if len(self.arg_list) > 0:
                help_str += '\n[指令]'
                for arg in self.arg_list:
                    if arg.required:
                        help_str += f'\n<{arg.key}>'
                    else:
                        help_str += f'\n{arg.key}'
                    help_str += f": {', '.join(arg.alias_list)}"
                    if arg.help_text:
                        help_str += f"\n{arg.help_text}"
            # 介绍缺省参数信息
            if self.default_arg is not None:
                if isinstance(self.default_arg, Argument):
                    help_str += f'\n[缺省参数] {self.default_arg.key}'
                elif isinstance(self.default_arg, list):
                    help_str += f'\n[缺省参数] '
                    for arg in self.default_arg:
                        help_str += f'{arg.key}, '
                    help_str = help_str[:-2]
            # 详细说明
            if self.detail_description:
                help_str += f'\n[详细介绍]\n{self.detail_description}'
            return help_str

    # 在handle之前进行简单检查
    def prior_handle_test(self, request):
        return

    # 测试是否插入任务，每次获取参数后或第一次获取了全部参数后都进行判断，默认不管
    def test_interruption(self):
        return False

    # 符合插入任务条件时的反应，默认中止任务并返回提示
    # 结束interruption后不会自动获取下条消息作为参数
    # 举例：判断某一输入的参数不合法以后停止处理并返回报错
    def interrupted_handle(self, request):
        self.deactivate()
        return ResponseMsg(f'【{self.session_type}】任务中止。')

    def handle(self, request):
        fill_first_arg = True
        # 只在第一次分析argument
        if self._is_first_time:
            self._is_first_time = False
            fill_first_arg = False

            # 初始化arg dict
            for arg in self.arg_list:
                self.arg_dict[arg.key] = arg
            if request.msg is None:
                req_args = ['']
            else:
                # 规整req_args
                req_args = self._arg_splitter(request.msg)[1:]
            # 完成初始化后进行检查
            self.prior_handle_test(request=request)
            print('== ArgSession ==')
            print(request.msg)
            print(req_args)
            n = len(req_args)
            if n == 0:
                pass
            else:
                i = 0
                while i < n:
                    use_default = True
                    if req_args[i] in self.help_args:
                        # 如果需要帮助，直接返回帮助信息
                        self.deactivate()
                        return ResponseMsg(self.help(detail=True))
                    elif req_args[i] in self.mute_args:
                        self._mute_response = True
                        i += 1
                        continue  # pass this while loop
                    for arg in self.arg_list:
                        # 循环arguments，检查是否被输入
                        if req_args[i] == f'--{arg.key}' or req_args[i] in arg.alias_list:
                            if arg.called:
                                self.deactivate()
                                return ResponseMsg(f'【{self.session_type}】参数[{arg.key}]重复，请检查')
                            use_default = False
                            arg.called = True
                            if arg.get_all:
                                arg.raw_req = request
                            if arg.get_next:
                                if i == n-1:
                                    self.deactivate()
                                    return ResponseMsg(f'【{self.session_type}】报错，缺少"{arg.key}"的参数')
                                else:
                                    i += 1
                                    arg.value = req_args[i]
                            break
                    # 如果没有唤起任何一个argument，查看缺省值
                    # 要求argument支持get_next，且不能唤起两次
                    if use_default:
                        if self.default_arg is None:
                            logging.warning('输入参数中未指定参数类型，而此session没有缺省参数')  # 不应该出现
                        elif isinstance(self.default_arg, Argument):  # 单个argument，这部分之后可以整合掉
                            # 如果已经完成了缺省参数或缺省参数不需要value，报错
                            if self.default_arg.called:
                                self.deactivate()
                                return ResponseMsg(f'【{self.session_type}】参数[{self.default_arg.key}]重复，请检查')
                            if not self.default_arg.get_next:
                                self.deactivate()
                                return ResponseMsg(f'【{self.session_type}】默认参数设置有bug，请联系管理')
                            # 否则把这个arg作为缺省参数的值
                            self.default_arg.called = True
                            self.default_arg.value = req_args[i]
                            if self.default_arg.get_all:
                                self.default_arg.raw_req = request
                        elif isinstance(self.default_arg, list):
                            if len(self.default_arg) == 0:
                                self.deactivate()
                                return ResponseMsg(f'【{self.session_type}】输入了太多的默认参数')
                            else:
                                # 处理第一个argument
                                arg = self.default_arg.pop(0)
                                if arg.called:
                                    self.deactivate()
                                    return ResponseMsg(f'【{self.session_type}】参数[{arg.key}]重复，请检查')
                                if not arg.get_next:
                                    self.deactivate()
                                    return ResponseMsg(f'【{self.session_type}】默认参数设置有bug，请联系管理')
                                # 否则把这个arg作为缺省参数的值
                                arg.called = True
                                arg.value = req_args[i]
                                if arg.get_all:
                                    arg.raw_req = request
                    # 最后+1
                    i += 1

        # 输入初始参数后，测试是否插入任务
        if self.test_interruption():
            self._interrupted = True
            return self.interrupted_handle(request=request)
        # 如果上一次插入了任务，之后会直接获取下一参数
        elif self._interrupted:
            self._interrupted = False
            fill_first_arg = False

        # 载入argument之后，进行正常操作
        # 第二次进入时会直接到这里，且fill_fir_arg为True
        for arg in self.arg_list:
            if arg.required and not arg.called:  # 仅看未填参数
                if fill_first_arg:  # 除了第一次以外，填列表中未填的第一个argument
                    fill_first_arg = False
                    arg.called = True
                    if arg.get_next:
                        arg.value = request.msg
                    if arg.get_all:
                        arg.raw_req = request

                    # 输入一个参数后，测试是否插入任务
                    if self.test_interruption():
                        self._interrupted = True
                        return self.interrupted_handle(request=request)
                else:
                    # 若是第一次进入，已经初始化一些参数，直接进入这里，以获取其他参数
                    # 第二次进入时会在填完第一个argument后到这里，以获取其他参数
                    if arg.ask_text is not None:
                        return ResponseMsg(f'【{self.session_type}】{arg.ask_text}')
                    else:
                        return ResponseMsg(f'【{self.session_type}】需要{arg.key}参数')

        # 当所有都填完才有可能到达此处
        for arg in self.arg_list:
            assert not arg.required or arg.called
        if self._mute_response:
            # mute不会影响前面获取argument的部分，只是最后不返回response
            self.internal_handle(request=request)  # handle but return nothing
            return []
        else:  # not muted
            return self.internal_handle(request=request)

    def internal_handle(self, request):
        for arg in self.arg_list:
            assert not arg.required or arg.called
        return []

    """
    用于切割原始string为argument列表
    通过引号判断一条内容的开始与结束，规则如下：
    开头为 " 时开始新条目，若正文开头有双引号，可用 \\" 代替
    结尾为 " 或 \\\\" 时结束新条目，若正文部分末尾有双引号，可用 \\" 代替
    （这里没有考虑到正文结尾有多个转义符的情况，但可能性不大）
    另外，若只有开头引号没有结尾，会自动补充
    中文的前后引号与英文引号等价，转义符为反斜杠
    """
    def _arg_splitter(self, raw_string):
        arg_list = []
        current_item = ''
        escapes = ['\\']
        quotes = ['"', '“', '”']

        for i in raw_string.split(' '):
            if current_item == '':
                if len(i) == 0:  # 跳过空白
                    continue
                elif i[0] not in quotes:  # 不需要延长的
                    # 将 \"* 开头的转为 "*
                    if len(i) >= 2:
                        if i[0] in escapes and i[1] in quotes:
                            i = i[1:]
                    arg_list.append(i)
                else:  # 开头为 "* 的
                    i = i[1:]
                    if len(i) >= 1 and i[-1] in quotes:  # 末尾为 *" 此时可能不需要延长
                        if len(i) == 1:  # 表示前后都是quote，直接截止
                            arg_list.append('')
                            continue
                        elif i[-2] not in escapes:  # 倒数第二个不是转义符，截止
                            arg_list.append(i[:-1])  # 删除后引号
                            continue
                        else:  # 倒数第二个是转义符，判断
                            if len(i) == 2:  # 形如 \"，末尾引号不是截止
                                i = i[:-2] + i[-1:]  # 删除转义符
                            elif i[-3] not in escapes:  # 形如 *\"，末尾引号不是截止
                                i = i[:-2] + i[-1:]  # 删除转义符
                            else:  # 形如 \\"，末尾引号表示截止
                                arg_list.append(i[:-3] + i[-2:-1])  # 删除转义符和前后引号，直接结束
                                continue
                    current_item += i + ' '
            else:  # 表示已有current_item
                # 检测是否截止
                if len(i) == 0:
                    current_item += ' '
                    continue
                elif i[-1] in quotes:  # 末尾为 *" 此时可能不需要延长
                    if len(i) == 1:  # 单个引号，表示截止
                        arg_list.append(current_item)
                        current_item = ''
                        continue
                    elif i[-2] not in escapes:  # 倒数第二个不是转义符，截止
                        current_item += i[:-1]  # 删除后引号
                        arg_list.append(current_item)
                        current_item = ''
                        continue
                    else:  # 倒数第二个是转义符，判断
                        if len(i) == 2:  # 形如 \"，末尾引号不是截止
                            i = i[-1:]  # 删除转义符
                        elif i[-2] not in escapes:  # 形如 *\"，末尾引号不是截止
                            i = i[:-2] + i[-1:]  # 删除转义符
                        else:  # 形如 \\"，末尾引号表示截止
                            current_item += i[:-3] + i[-2:-1]  # 删除转义符和后引号，截止
                            arg_list.append(current_item)
                            current_item = ''
                            continue
                # 其他所有情况，表示不需要截止，把原始或修改好的i加上
                current_item += i + ' '

        # 如果到结束时仍没有产生，此时直接附上结果
        if current_item != '':
            arg_list.append(current_item[:-1])

        # 在第一条中检查command
        if self.strip_command:
            first_arg = arg_list[0]
            # 只需要检查extended commands，因为strict不可能被分开
            for command in self.extend_commands:
                if command.lower() in first_arg.lower():
                    # 去除command后的语句
                    s = first_arg.lower().replace(command.lower(), '')
                    if len(s) > 0:  # 若有空余，则新增一节
                        arg_list = [command, s] + arg_list[1:]
                    break

        return arg_list
