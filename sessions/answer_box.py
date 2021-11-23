from .general import Session
from .argument import ArgSession, Argument
from ..responses import ResponseMsg, ResponseImg
from ..paths import PATHS
import os, csv, shutil, datetime, random

BOX_DIR = PATHS['box']
BOX_FILE = os.path.join(BOX_DIR, 'answer_box.csv')

try:
    os.mkdir(BOX_DIR)
except FileExistsError:
    pass

if not os.path.exists(BOX_FILE):
    with open(BOX_FILE, 'a+', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['question', 'answer_text', 'answer_img'])
        writer.writerow({'question': 'question',
                         'answer_text': 'answer_text',
                         'answer_img': 'answer_img'})


class AutoAnswerSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = '问答机'
        self.description = '从问答数据库中获取问答，并自动回复，有多条符合时会全部回复（除非设定只选一条）'
        self.answer_table = []
        self._load_table()
        self._list_commands = False

    def probability_to_call(self, request):
        return self._called_by_command(request=request, extend_p=70, strict_p=90)

    def _load_table(self):
        try:
            with open(BOX_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.answer_table.append(row)
                    command = row['question']
                    if command[0] == '/':
                        command = command[1:]
                        if len(command) == 0 or command == '+':
                            # empty question, do not search
                            continue
                    if command[-1] == '+':
                        self.extend_commands.append(command[:-1])
                    else:
                        self.strict_commands.append(command)
        except FileNotFoundError:
            return

    def handle(self, request):
        self.deactivate()
        responses = []
        responses_to_choose = []
        strict_only = False
        for item in self.answer_table:
            # read command
            command = item['question']
            command_is_extended = bool(command[-1] == '+')
            command_is_to_choose = bool(command[0] == '/')
            command_text = command.lower()
            if command_is_extended:
                command_text = command_text[:-1]
            if command_is_to_choose:
                command_text = command_text[1:]

            if command_is_extended and command_text in request.msg.lower():
                # extended command
                if strict_only:
                    continue
                else:
                    pass
            elif command_text == request.msg.lower():
                # strict command
                if strict_only:
                    pass
                else:
                    # refresh
                    responses = []
                    responses_to_choose = []
                    strict_only = True
            else:
                continue
            # add this item to the response list
            text = item['answer_text']
            img = item['answer_img']
            if text:
                if command_is_to_choose:
                    responses_to_choose.append(ResponseMsg(text))
                else:
                    responses.append(ResponseMsg(text))
            if img:
                if command_is_to_choose:
                    responses_to_choose.append(ResponseImg(img))
                else:
                    responses.append(ResponseImg(img))
        if responses_to_choose:
            responses.append(random.choice(responses_to_choose))
        return responses


class AddAnswerSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '问答库更新'
        self.description = '在问答库中添加问题与回复，末尾带加号“+”为不严格指令，' \
                           '最前面为斜杠“/”的会在符合条件的答案中选择一条回复'
        self.extend_commands = ['问答机']
        self._max_delta = 120
        self.is_first_time = True
        self.question = None
        self.answer_text = None
        self.answer_img = None
        self.arg_list = [Argument(key='question', alias_list=['-q'], required=True, get_next=True,
                                  ask_text='你要添加什么问题？'),
                         Argument(key='text', alias_list=['-t'], required=True, get_next=True,
                                  ask_text='默认的回答文本是？（回复“-”、“无”等则无文本回复）'),
                         Argument(key='image', alias_list=['-i'], required=True, get_all=True,
                                  ask_text='是否有默认的图片回答？（直接回复图片表示有，否则无）')]
        self.default_arg = self.arg_list[0]

    def is_legal_request(self, request):
        return True

    def _add_answer(self):
        with open(BOX_FILE, 'a+', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['question', 'answer_text', 'answer_img'])
            # text = self.answer_text.replace('n', ' n').replace('\n', r'\n').replace('\r', '')
            text = self.answer_text
            writer.writerow({'question': self.question,
                             'answer_text': text,
                             'answer_img': self.answer_img})

    def info(self):
        text = '问题：{}'.format(self.question)
        if self.answer_text:
            text += '\n回答：{}'.format(self.answer_text)
        if self.answer_img:
            text += '\n图片：{}'.format(self.answer_img)
        return text

    def internal_handle(self, request):
        self.deactivate()
        question = self.arg_dict['question'].value
        if not bool(question):
            return ResponseMsg(f'【{self.session_type}】空白问题，不添加')
        else:
            self.question = self.arg_dict['question'].value
        text = self.arg_dict['text'].value
        if text.lower() in ['-', '/', '无', 'none', 'null']:
            self.answer_text = ''
        else:
            self.answer_text = text
        image = self.arg_dict['image'].raw_req.img
        if image:
            self.answer_img = os.path.join(BOX_DIR,
                                           datetime.datetime.now().strftime('box_image_%Y%m%d-%H%M%S.jpg'))
            shutil.copyfile(image, self.answer_img)
        else:
            self.answer_img = ''

        if self.answer_text or self.answer_img:
            try:
                self._add_answer()
            except PermissionError:
                return ResponseMsg('【{}】写入失败，不加入回答'.format(self.session_type))
            else:
                return ResponseMsg('【{}】加入问答\n{}'.format(self.session_type, self.info()))
        else:
            return ResponseMsg('【{}】空白回复，不加入回答'.format(self.session_type))