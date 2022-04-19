# 一些网上的简单有趣的插件
from .argument import ArgSession, Argument
from ..responses import ResponseMsg, ResponseImg
from ..utils import image_url_to_path, format_filename
from ..permissions import get_permissions
from ..external.answer_book_data import ANSWER_BOOK
from ..external.slscq import Slscq
from ..external.slscq_data import SLSCQ_DATA
import random, requests, os
import matplotlib.pyplot as plt
import numpy as np


# 来自https://lab.magiconch.com/nbnhhsh
# 2021-12-12: 创建
class NbnhhshSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '能不能好好说话'
        self.description = '拼音缩写翻译查询，来自lab.magiconch.com/nbnhhsh，速度较慢'
        self._max_delta = 60
        self.extend_commands = ['好好说话', 'nbnhhsh', '缩写']
        self.arg_list = [Argument(key='text', alias_list=['-s'],
                                  required=True, get_next=True,
                                  ask_text='要查询的缩写是？',
                                  help_text='要查询的缩写')]
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        self.deactivate()
        url = 'https://lab.magiconch.com/api/nbnhhsh/guess'
        payload = {'text': self.arg_dict['text'].value}
        r = requests.post(url=url, data=payload)
        try:
            return ResponseMsg(f'【{self.session_type}】查到释义如下：\n{r.json()[0]["trans"]}')
        except KeyError:
            return ResponseMsg(f'【{self.session_type}】未能找到缩写。')
        except requests.exceptions.ConnectionError:
            return ResponseMsg(f'【{self.session_type}】查询失败。')


# 来自https://github.com/FYWinds/takker
# 2021-12-12: 创建
class BookOfAnswersSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '答案之书'
        self.description = '随机回复答案，来自github.com/FYWinds/takker'
        self._max_delta = 60
        self.strip_command = True  # 将句子分离
        self.extend_commands = ['答案之书', '答案书']
        self.arg_list = [Argument(key='question', alias_list=['-q'],
                                  required=True, get_next=True,
                                  ask_text='你有什么想问的？')]
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        self.deactivate()
        answer = random.choice(ANSWER_BOOK)
        return ResponseMsg(f'【{self.session_type}】{answer}')


# 来自https://github.com/MeetWq/mybot
# https://github.com/MeetWq/mybot/blob/master/src/plugins/setu/data_source.py
# 2021-12-12: 创建
class WebImgSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '网图'
        self.description = '获取有关网络图片，来自github.com/MeetWq/mybot'
        self._max_delta = 60
        self.strict_commands = ['网图', 'WebImg']
        self.arg_list = [Argument(key='keyword', alias_list=['-k'],
                                  required=True, get_next=True,
                                  ask_text='关键词是？'),
                         Argument(key='r18', alias_list=['r18', '-r'],
                                  required=False, get_next=False),
                         Argument(key='url', alias_list=['-u'],
                                  required=False, get_next=False,
                                  help_text='直接获取url')
                         ]
        self.permissions = get_permissions().get('WebImgSession', {})
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        self.deactivate()
        url = 'https://api.lolicon.app/setu/v2'
        params = {
            'r18': 1 if self.arg_dict['r18'].called else 0,
            'num': 1,
            'size': ['regular'],
            'proxy': 'i.pixiv.cat',
            'keyword': self.arg_dict['keyword'].value
        }
        r = requests.get(url, params=params)
        r = r.json()
        if r['error']:
            return ResponseMsg(f'【{self.session_type}】搜图出错')
        elif r['data']:
            img_url = r['data'][0]['urls']['regular']
            if self.arg_dict['url'].called:  # 只获取url
                return ResponseMsg(img_url)
            try:
                img_file = image_url_to_path(url=img_url, filename=f'WebImg_{os.path.basename(img_url)}')
                return ResponseImg(file=img_file)
            except requests.exceptions.ConnectionError:
                return [ResponseMsg(f'【{self.session_type}】网络连接出错'), ResponseMsg(img_url)]
        else:
            return ResponseMsg(f'【{self.session_type}】未找到')


# 原创
# 2022-01-01: 创建
class FocusCubeSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '专注方格'
        self.description = '网传锻炼专注力的小测试（只是好玩）'
        self.strip_command = True  # 将句子分离
        self.strict_commands = ['方格', '专注']
        self.arg_list = [Argument(key='nx', alias_list=['-x', '-n'],
                                  required=False, get_next=True,
                                  help_text='横轴的数字数量'),
                         Argument(key='ny', alias_list=['-y'],
                                  required=False, get_next=True,
                                  help_text='纵轴的数字数量')
                         ]
        self.default_arg = self.arg_list[0]
        self.detail_description = '称为舒尔特方格的专注力测试，实际上好像没什么用。' \
                                  '使用方法是从1数到最后一个数字，标准版为5x5，对于成年人，' \
                                  '12秒内为优秀，16秒内良好，19秒内中等，20秒内及格。'

    def internal_handle(self, request):
        self.deactivate()
        nx = 5
        ny = None
        if self.arg_dict['nx'].called:
            try:
                nx = int(self.arg_dict['nx'].value)
            except ValueError:
                pass
        if self.arg_dict['ny'].called:
            try:
                ny = int(self.arg_dict['ny'].value)
            except ValueError:
                pass
        filename = format_filename(header='FocusCube', post='.jpg')
        self.plot_focus_cube(filename=filename, nx=nx, ny=ny)
        return ResponseImg(filename)

    @staticmethod
    def plot_focus_cube(filename, nx, ny=None):
        if ny is None:
            ny = nx
        xx = np.arange(nx)
        yy = np.arange(ny)
        v = np.arange(nx * ny) + 1
        random.shuffle(v)
        fig, ax = plt.subplots(1, 1, figsize=[0.6 * nx, 0.6 * ny])
        plt_kwargs = {'horizontalalignment': 'center',
                      'verticalalignment': 'center'}

        i = 0
        for x in xx + 0.5:
            for y in yy + 0.5:
                ax.text(x, y, v[i], **plt_kwargs)
                i += 1

        ax.set(xlim=(0, nx), ylim=(0, ny),
               xticks=xx, xticklabels=[],
               yticks=yy, yticklabels=[])
        ax.grid()
        fig.tight_layout()
        fig.savefig(filename)


# 原创，使用https://github.com/ASoulCnki/.github/tree/master/api
# 2022-01-24: 创建
class AsoulCnkiSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '作文查重'
        self.description = '枝网小作文查重功能，来自asoulcnki.asia'
        self._max_delta = 60
        self.extend_commands = ['查重', '小作文']
        self.arg_list = [Argument(key='text', alias_list=['-t', '-s'],
                                  required=True, get_next=True,
                                  ask_text='请输入要查重的段落（长度在10-1000之间）')]
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        self.deactivate()
        text = self.arg_dict['text'].value
        if 10 <= len(text) <= 1000:
            url = 'https://asoulcnki.asia/v1/api/check'
            headers = {'Content-Type': 'application/json'}
            payload = {'text': text}
            resp = requests.post(url=url, headers=headers, json=payload)
            if resp.json()['code'] == 0:
                reply_msg = f'查重率{resp.json()["data"]["rate"]*100:.1f}%'
                if resp.json()['data']['related']:
                    reply_msg += '，相关段落：\n'
                    for related_reply in resp.json()['data']['related']:
                        reply_msg += f'[{related_reply["rate"]*100:.1f}%] ' \
                                     f'{related_reply["reply_url"]}\n'
                    reply_msg = reply_msg[:-1]
                return ResponseMsg(f'【{self.session_type}】{reply_msg}')
            else:
                return ResponseMsg(f'【{self.session_type}】获取失败')
        else:
            return ResponseMsg(f'【{self.session_type}】字数不符合要求（长度在10-1000之间）')


# 原创，参考多个upside down text converter
# 2022-01-24: 创建
class UpSideDownTextSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '字符翻转'
        self.description = '将句子中的英文、数字、符号翻转'
        self._max_delta = 60
        self.extend_commands = ['翻转', '反转', '颠倒']
        self.arg_list = [Argument(key='text', alias_list=['-t', '-s'],
                                  required=True, get_next=True,
                                  ask_text='请输入要翻转的段落')]
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        self.deactivate()
        text = self.arg_dict['text'].value
        text = text[::-1]  # reverse
        # source: ascii 33-126
        s_reverse = r"~{|}zʎxʍʌnʇsɹbdouɯןʞɾᴉɥƃɟǝpɔqɐ,‾v[\]" \
                    r"Z⅄XMᴧ∩⊥SᴚΌԀONW⅂ꓘſIHפℲƎᗡƆ𐐒∀@¿<=>;:" \
                    r"68ㄥ9ϛㄣƐᄅƖ0/˙-'+*(),⅋%$#„¡"
        s_reverse = s_reverse[::-1]

        text_reversed = ''
        for t in text:
            i = ord(t)
            if 33 <= i <= 126:
                text_reversed += s_reverse[i-33]
            else:
                text_reversed += t

        return ResponseMsg(f'{text_reversed}')


# 来自https://github.com/Uahh/Slscq
# 2022-04-19: 创建
class SlscqSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '申论生成器'
        self.description = '拼凑文章，来自github.com/Uahh/Slscq'
        self._max_delta = 60
        self.extend_commands = ['申论', '申论生成', '文章生成']
        self.add_arg(key='topic', alias_list=['-t'],
                     required=True, get_next=True,
                     ask_text='文章的主题是？',
                     help_text='文章的主题')
        self.add_arg(key='length', alias_list=['-l', '-n'],
                     required=False, get_next=True,
                     default_value=200,
                     help_text='文章字数（50-5000）')
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        self.deactivate()
        length = self.arg_dict['length'].value
        try:
            length = int(length)
        except ValueError:
            length = 200
        length = min(max(50, length), 5000)

        machine = Slscq(data=SLSCQ_DATA)
        res = machine.gen_text(them=self.arg_dict['topic'].value, essay_num=length)

        return ResponseMsg(f'【{self.session_type}】\n{res}')
