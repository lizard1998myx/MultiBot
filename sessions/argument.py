from .general import Session
from ..responses import ResponseMsg


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
        self.is_first_time = True
        self.arg_list = []
        self.arg_dict = {}
        self.default_arg = None
        self.help_args = ['help', '帮助', '-h', '--h', '--help']
        self.detail_description = ''

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
            help_str += '\n[指令]'
            for arg in self.arg_list:
                help_str += f'\n{arg.key}'
                if arg.required:
                    help_str += '(required)'
                help_str += f": {', '.join(arg.alias_list)}"
                if arg.help_text:
                    help_str += f"\n{arg.help_text}"
            if self.detail_description:
                help_str += f'\n[详细介绍]\n{self.detail_description}'
            return help_str

    def handle(self, request):
        fill_first_arg = True
        # 只在第一次分析argument
        if self.is_first_time:
            self.is_first_time = False
            fill_first_arg = False
            if request.msg is None:
                req_args = ['']
            else:
                req_args = request.msg.split()[1:]
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
                    for arg in self.arg_list:
                        # 循环arguments
                        if req_args[i] == arg.key or req_args[i] in arg.alias_list:
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
                    if use_default and self.default_arg is not None:
                        assert not self.default_arg.called
                        assert self.default_arg.get_next
                        self.default_arg.called = True
                        self.default_arg.value = req_args[i]
                        if self.default_arg.get_all:
                            self.default_arg.raw_req = request
                    # 最后+1
                    i += 1

        # 载入argument之后，进行正常操作
        for arg in self.arg_list:
            if arg.required and not arg.called:
                # 除了第一次以外，填第一个argument
                # 不是第一次填写时，fill_first_arg为True
                if fill_first_arg:
                    fill_first_arg = False
                    arg.called = True
                    if arg.get_next:
                        arg.value = request.msg
                    if arg.get_all:
                        arg.raw_req = request
                else:
                    if arg.ask_text is not None:
                        return ResponseMsg(f'【{self.session_type}】{arg.ask_text}')
                    else:
                        return ResponseMsg(f'【{self.session_type}】需要{arg.key}参数')

        # 当所有都填完才有可能到达此处
        for arg in self.arg_list:
            assert not arg.required or arg.called
            self.arg_dict[arg.key] = arg
        return self.internal_handle(request=request)

    def internal_handle(self, request):
        for arg in self.arg_list:
            assert not arg.required or arg.called
        return []