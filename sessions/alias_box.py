from .general import Session
from .argument import ArgSession, Argument
from ..responses import ResponseMsg
from ..paths import PATHS
import os, csv

BOX_DIR = PATHS['box']
BOX_FILE = os.path.join(BOX_DIR, 'alias_box.csv')

try:
    os.mkdir(BOX_DIR)
except FileExistsError:
    pass

if not os.path.exists(BOX_FILE):
    with open(BOX_FILE, 'a+', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['key', 'value'])
        writer.writerow({'key': 'key',
                         'value': 'value'})


class AutoAliasSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = '同义词机'
        self.description = '从同义词数据库中获取关键词，并等价为一个指令，多个符合时会返回多个'
        self.answer_table = []
        self._load_table()
        self._list_commands = False

    def probability_to_call(self, request):
        return self._called_by_command(request=request, extend_p=65, strict_p=85)

    def _load_table(self):
        try:
            with open(BOX_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.answer_table.append(row)
                    command = row['key']
                    if command[-1] == '+':
                        self.extend_commands.append(command[:-1])
                    else:
                        self.strict_commands.append(command)
        except FileNotFoundError:
            return

    def handle(self, request):
        self.deactivate()

        # get alias commands and check
        values = []
        results = []
        for item in self.answer_table:
            command = item['key']
            if command[-1] == '+' and command[:-1].lower() in request.msg.lower():
                # extended command
                pass
            elif command.lower() == request.msg.lower():
                # strict command
                pass
            else:
                continue
            value = item['value']
            new_req = request.new()
            new_req.msg = value
            # check no iterate
            if self.probability_to_call(request=new_req) <= 0:
                if AddAliasSession(user_id=self.user_id).probability_to_call(request=new_req) <= 0:
                    results.append(new_req)
                    values.append(value)

        # alias report
        report = f'【{self.session_type}】关键词“{request.msg}”转义为：'
        if len(values) == 0:
            return []
        elif len(values) == 1:
            report += values[0]
        else:
            for i, value in enumerate(values):
                report += f'\n{i+1}. {value}'
        return [ResponseMsg(report)] + results


class AddAliasSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '同义词库更新'
        self.description = '在同义词库中添加关键词与等效指令，末尾带“+”为不严格指令'
        self.strict_commands = ['同义词', 'alias']
        self._max_delta = 120
        self.is_first_time = True
        self.add_key = None
        self.add_value = None
        self.arg_list = [Argument(key='key', alias_list=['-k'], required=True, get_next=True,
                                  ask_text='同义词来源关键词是？（末尾带加号为不严格指令）'),
                         Argument(key='value', alias_list=['-v'], required=True, get_next=True,
                                  ask_text='等效的指令是？（回复“-”、“无”等则取消）')]
        self.default_arg = self.arg_list[0]
        self.detail_description = '例如，发送“同义词 -k 我的关键词 -v 帮助”添加词条，' \
                                  '之后发送“我的关键词”即相当于发送“帮助”，机器人会返回帮助信息。\n' \
                                  '另外，同义词机不会等效输出会调用自己的同义指令，' \
                                  '部分指令（需要返回值的）可能会有问题。\n' \
                                  '同义词机的优先级低于其他明确指令和问答机。'

    def is_legal_request(self, request):
        return True

    def _add_alias(self):
        with open(BOX_FILE, 'a+', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['key', 'value'])
            writer.writerow({'key': self.add_key, 'value': self.add_value})

    def info(self):
        text = '关键词：{}'.format(self.add_key)
        if self.add_value:
            text += '\n同义指令：{}'.format(self.add_value)
        return text

    def internal_handle(self, request):
        self.deactivate()
        self.add_key = self.arg_dict['key'].value
        value = self.arg_dict['value'].value
        if value.lower() in ['-', '/', '无', 'none', 'null']:
            self.add_value = ''
        else:
            self.add_value = value

        if self.add_value:
            try:
                self._add_alias()
            except PermissionError:
                return ResponseMsg('【{}】写入失败，不加入同义词'.format(self.session_type))
            else:
                return ResponseMsg('【{}】加入同义词\n{}'.format(self.session_type, self.info()))
        else:
            return ResponseMsg('【{}】空白指令，不加入同义词库'.format(self.session_type))