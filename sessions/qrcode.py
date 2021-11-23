from .argument import ArgSession, Argument
from ..responses import ResponseMsg, ResponseImg
from ..paths import PATHS
from pyzbar import pyzbar
from PIL import Image
import qrcode, datetime, os

TEMP_DIR = PATHS['temp']


class DeCodeSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 3*60
        self.session_type = '二维码读取'
        self.strict_commands = ['scan', '扫描']
        self.description = '读取图片中的二维码，并将其中携带的字符串返回（有Bug）'
        self.arg_list = [Argument(key='image', alias_list=['-i'],
                                  required=True, get_all=True,
                                  ask_text='等待图片传输',
                                  help_text='接收图片参数，用于扫描')]

    def is_legal_request(self, request):
        return True

    def internal_handle(self, request):
        self.deactivate()
        img = self.arg_dict['image'].raw_req.img
        if isinstance(img, str):
            string_list = decode(img)
            response_list = []
            if len(string_list) == 0:
                response_list.append(ResponseMsg('【%s】未发现二维码' % self.session_type))
            else:
                response_list.append(ResponseMsg('【%s】识别到%i个二维码' % (self.session_type, len(string_list))))
            for i, code_string in enumerate(string_list):
                response_list.append(ResponseMsg('【%s】第%i个二维码是：%s' % (self.session_type, i+1, code_string)))
            return response_list
        else:
            return ResponseMsg(f'【{self.session_type}】未收到图片')


class EnCodeSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 3*60
        self.session_type = '二维码生成'
        self.strict_commands = ['make', '生成']
        self.description = '从提供的字符串生成一个二维码图片'
        self.arg_list = [Argument(key='string', alias_list=['-t', '-s'],
                                  required=True, get_next=True,
                                  ask_text='请输入二维码携带的字符串',
                                  help_text='二维码携带的字符串')]
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        self.deactivate()
        filename = datetime.datetime.now().strftime('QR_image_%Y%m%d-%H%M%S.jpg')
        abs_dir = TEMP_DIR
        abs_path = os.path.join(abs_dir, filename)
        encode(text=self.arg_dict['string'].value, filename=abs_path)
        return [ResponseMsg('【%s】生成二维码，信息为：%s' % (self.session_type, request.msg)),
                ResponseImg(abs_path)]


def encode(text: str, filename: str):
    qrcode.make(text).save(filename)


def decode(filename: str):
    code_list = pyzbar.decode(Image.open(filename))
    string_list = []
    for code in code_list:
        string_list.append(str(code.data, encoding='utf-8'))
    return string_list
