# 一些网上的简单有趣的插件
from .argument import ArgSession, Argument
from ..responses import ResponseMsg, ResponseImg
from ..utils import image_url_to_path, format_filename
from ..permissions import get_permissions
import random, requests, os
import matplotlib.pyplot as plt
import numpy as np


# 来自https://lab.magiconch.com/nbnhhsh
# 2021-12-12: 创建
class NbnhhshSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '能不能好好说话'
        self.description = '拼音缩写翻译查询，来自https://lab.magiconch.com/nbnhhsh/，速度较慢'
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
        self.description = '随机回复答案，来自https://github.com/FYWinds/takker'
        self._max_delta = 60
        self.strip_command = True  # 将句子分离
        self.extend_commands = ['答案之书', '答案书']
        self.arg_list = [Argument(key='question', alias_list=['-q'],
                                  required=True, get_next=True,
                                  ask_text='你有什么想问的？')]
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        self.deactivate()
        answer = random.choice(ANSWERS)
        return ResponseMsg(f'【{self.session_type}】{answer}')


# 来自https://github.com/MeetWq/mybot
# https://github.com/MeetWq/mybot/blob/master/src/plugins/setu/data_source.py
# 2021-12-12: 创建
class WebImgSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '网图'
        self.description = '获取有关网络图片，来自https://github.com/MeetWq/mybot'
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
        self.description = '枝网小作文查重功能，来自https://asoulcnki.asia/'
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


ANSWERS = [
    "请教你的妈妈",
    "相信你的直觉",
    "重新考虑",
    "时间会证明一切",
    "不要忽视自己的力量",
    "等待更好的",
    "尽在掌握之中",
    "花更多的时间来决定",
    "有好运",
    "抛弃首选方案",
    "不要等了",
    "你说了算",
    "换个角度想想",
    "妥协",
    "不要做得太过分",
    "尽早完成",
    "寻找更多的选择",
    "谨慎小心",
    "拭目以待",
    "你需要主动",
    "顺其自然",
    "抗拒",
    "不会失望的",
    "这是你最后的机会",
    "还有另一种情况",
    "寻找一个指路人",
    "不要过火",
    "不值得斗争",
    "省点力气吧",
    "不",
    "仔细想想再说",
    "保持现状",
    "问自己什么是最重要的",
    "要有耐心",
    "见好就收",
    " 放手",
    "这是一定的",
    "不宜在这个时候",
    "为什么不呢",
    "相信你最初的想法",
    "这取决于你的行动",
    "继续前进",
    "障碍重重",
    "寻找机会就行",
    "找个人给你意见",
    "这是一个机会",
    "不妥协",
    "别傻等了",
    "不明智",
    "别瞎折腾了",
    "你需要一点帮助",
    "为什么不呢？",
    "你心里已经有答案了",
    "现在比以往任何时候的情况都要好",
    "无论你做何种选择，结果都是对的",
    "不要被情绪左右",
    "谁都不能保证",
    "是",
    "休息一下就好了",
    "有意料之外的事会发生，不妨等待",
    "这辈子都不可能",
    "没有",
    "保持你的好奇心，去挖掘真相",
    "休息，休息一会",
    "意义非凡",
    "去行动",
    "去问你爸爸",
    "遵守规则",
    "以后再说",
    "遇上方知有",
    "地点不合适",
    "想想有没有机会",
    "谁说得准呢，先观望着",
    "别不自量力",
    "令人期待的事情马上要发生",
    "我确定",
    "删除记忆",
    "这件事会很麻烦",
    "毋庸置疑",
    "想得美",
    "对的",
    "能让你快乐的那个决定",
    "观察形势",
    "会很顺利",
    "一笑而过",
    "你必须现在就行动",
    "想法太多，选择太少",
    "没什么好结果",
    "一定会有好结果的",
    "荒谬",
    "去做其他的事情",
    "答案在镜子里",
    "绝对不",
    "会感到庆幸",
    "很麻烦",
    "有可能",
    "众所周知",
    "再多考虑",
    "它会带来好运",
    "不值得",
    "先做点别的",
    "有比这更重要的东西",
    "保存你的实力",
    "为什么不",
    "会很不顺利",
    "一个强有力的承诺会换回更好的结果",
    "万一错过，就没这个机会了",
    "情况很快就会发生变化",
    "不会作就不会死",
    "不可预测",
    "你需要考虑其他方面",
    "醒醒吧，别做梦了",
    "列出原因",
    "问天问大地，不如问自己",
    "这不可取",
    "一笑了之",
    "值得奋斗",
    "关注你的家庭生活",
    "你做什么都没用",
    "与你无关",
    "当然咯",
    "认清现实吧",
    "一年后就不那么重要了",
    "不要忧虑",
    "主动一点，人生会大不相同",
    "决定了就去做",
    "重新想想",
    "默数十秒再问我",
    "HOLD不住",
    "结果会让你惊喜",
    "扫除障碍",
    "说出来吧",
    "问问自己，为什么要这么干",
    "最后一次机会",
    "着眼未来",
    "培养一项新的爱好",
    "至关重要",
    "不赌",
    "无法预测",
    "保持头脑清醒",
    "要主动",
    "毫无疑问",
    "保持乐观",
    "随波逐流未必是好事",
    "奇迹即将降临",
    "采取行动",
    "毫无道理",
    "不作死就不会死",
    "木已成舟",
    "没法保证",
    "会付出代价",
    "你会失望的",
    "你在开玩笑吗？",
    "需要冒险",
    "现在还说不清",
    "随TA去",
    "走容易走的路",
    "另择吉日",
    "转移你的注意力",
    "事情开始变得有趣了",
    "照你想的那样去做",
    "先让自己休息",
    "改变不了世界，改变自己",
    "要 变通",
    "等待机会",
    "你开心就好",
    "注意身后",
    "千万不能失败",
    "听听专家的意见",
    "倾听你内心的声音",
    "最佳方案不一定可行",
    "结果可能让人惊讶",
    "你也许会失望",
    "眼光长远一点",
    "显而易见",
    "试试卖萌",
    "这不切实际",
    "再考虑一下",
    "告诉别人这对你意味着什么",
    "你就是答案",
    "去倾诉",
    "把心揣怀里",
    "等待",
    "注意细节",
    "等等",
    "不要忘记",
    "坚持",
    "看看会发生什么",
    "学会释然",
    "你需要掌握更多的信息",
    "再过几年",
    "别要求太多",
    "还有别的选择",
    "相信自己的直觉",
    "借助他人的经验",
    "转移注意力",
    "错的",
    "会特别顺利",
    "并非永恒",
    "大方一点",
    "去解决",
    "去争取机会",
    "观望",
    "这是在浪费金钱",
    "会失去自我",
    "不确定的因素有点多",
    "当然",
    "这会影响你的形象",
    "肯定的",
    "你必须解决一些相关的问题",
    "要知足",
    "为了确保最好的结果，保持冷静",
    "并不明智",
    "好运将会降临",
    "不要害怕",
    "机会稍纵即逝",
    "掌握更多信息",
    "三思而后行",
    "从来没有",
    "去尝试",
    "尚待时日",
    "不雅忽略身边的人",
    "制订了一个新计划",
    "没有更好的选择",
    "不会后悔的",
    "别让它影响到你",
    "管它呢",
    "不需要",
    "上帝为你关一扇门，必定会为你打开一扇窗",
    "克服困难",
    "只有一次机会",
    "信任",
    "这难以置信",
    "告诉自己什么是最重要的",
    "情况很快就会发生改变",
    "会后悔的",
    "是的",
    "做最坏的打算",
    "再等等看",
    "千万别信",
    "需要花费点时间",
    "时机未到",
    "不值得冒险",
    "用尽一切办法去努力",
    "负责",
    "千万别傻",
    "你需要知道真相",
    "去做",
    "这件事你说了不算",
    "不要迫于压力而改变初衷",
    "结果不错",
    "这事儿不靠谱",
    "这不是你想 要的",
    "需找更多的选择",
    "有",
    "玩得开心就好",
    "去改变",
    "勿忘初心，放得始终",
    "重要",
    "很快就能解决",
    "不要陷得太深",
    "你会后悔的",
    "把重心放在工作/学习上",
    "也许有更好的解决方案",
    "量力而行",
    "你可能不得不放弃其他东西",
    "算了吧",
    "不要犹豫",
    "如你所愿",
    "要抓住问题的关键",
    "天上要掉馅饼了",
    "发挥你的想象力",
    "抓住机会",
    "你不会失望的",
    "肯定",
    "这时候非常顺利",
    "你需要适应",
    "这种事情不要告诉别人",
    "不放赌一把",
    "你将取得成功",
    "得真正地努力一下",
    "时机不对",
    "学会妥协",
    "不要纠结了",
    "忽略了一件显而易见的事",
    "对他人慷慨",
    "但行好事，莫问前程",
    "这没什么意义",
    "协作",
    "实际一点",
    "表示怀疑",
    "听听别人怎么说",
    "制定计划",
    "形势不明",
    "问问你的亲人",
    "这不值得努力",
    "放轻松点，慢慢来",
    "改变自己",
    "GO",
    "列个清单",
    "放弃第一个方案",
    "记录下来",
    "你必须弥补这个缺点",
    "没错",
    "当局者迷",
    "你猜",
    "需要合作",
    "时机尚不成熟",
    "不要自作多情",
    "阻止",
    "取决于你的选择"
]