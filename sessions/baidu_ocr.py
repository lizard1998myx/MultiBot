from .argument import ArgSession, Argument
from ..responses import ResponseMsg
from ..api_tokens import OCR_APP_ID, OCR_API_KEY, OCR_SECRET_KEY
from aip import AipOcr


client = AipOcr(OCR_APP_ID, OCR_API_KEY, OCR_SECRET_KEY)


class OcrSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 3*60
        self.session_type = 'OCR识别'
        self.extend_commands = ['ocr', '识别']
        self.description = '通过百度OCR接口进行图片文字识别'
        self.arg_list = [Argument(key='image', alias_list=['-i'],
                                  required=True, get_all=True,
                                  ask_text='等待图片传输',
                                  help_text='接收图片参数，用于文字识别'),
                         Argument(key='accurate', alias_list=['-a', '-r'],
                                  help_text='精确OCR识别')]
        self.detail_description = '发送“OCR -r”并按提示回复图片，可使用更精确的OCR识别。\n' \
                                  '在可以同时发送图文的平台（如QQ），在命令中带上“-i”即可直接读取本条消息的图片。'

    # 调用此method时必然是第一次查看
    def probability_to_call(self, request):
        probabilites = [self._called_by_command(request=request)]
        if isinstance(request.img, str):
            probabilites.append(10)
        return max(probabilites)

    def is_legal_request(self, request):
        return True

    def internal_handle(self, request):
        self.deactivate()
        img = self.arg_dict['image'].raw_req.img
        is_accurate = self.arg_dict['accurate'].called
        if isinstance(img, str):
            self.deactivate()
            return ResponseMsg('【%s】%s' % (self.session_type, whole_string(img, is_accurate)))
        else:
            return ResponseMsg(f'【{self.session_type}】未收到图片')


def bin_img_read(filename):
    with open(filename, 'rb') as f:
        return f.read()


def whole_string(filename, accurate=False):
    if accurate:
        ocr_func = client.basicAccurate
    else:
        ocr_func = client.basicGeneral
    results = ocr_func(bin_img_read(filename))['words_result']
    string = ''
    for result in results:
        string += result['words']
    return string
