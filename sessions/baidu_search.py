from .general import Session
from ..responses import ResponseMsg
import urllib


class AutoBaiduSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 60
        self.session_type = '百度一下'
        self.extend_commands = ['百度', 'baidu']
        self.strict_commands = ['?', '？']
        self.description = '返回一个搜索链接'
        self.is_first_time = True

    def handle(self, request):
        if self.is_first_time:
            self.is_first_time = False
            return ResponseMsg('你想知道什么？')
        else:
            self.deactivate()
            text = '你想知道的“{}”在这里：'.format(request.msg)
            text += 'http://buhuibaidu.me/?s={}'.format(urllib.parse.quote(request.msg))
            return ResponseMsg(text)


