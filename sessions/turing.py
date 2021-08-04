from MultiBot.responses import ResponseMsg
from MultiBot.sessions.general import Session
from MultiBot.api_tokens import TURING_API_KEY
import requests, json, re


class TuringSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 3
        self.session_type = '图灵接口'
        self.description = '来自图灵API（turingapi.com）的聊天机器人'

    # 合法Request以30成功率唤起Turing
    def probability_to_call(self, request):
        return 30

    def handle(self, request):
        reply = self.call_turing_api(msg=request.msg)
        if reply:
            if reply in ['请求次数超限制!', 'userId格式不合法!']:
                return []
            response = ResponseMsg(reply)
        else:
            response = ResponseMsg('【%s】未得到回复' % self.session_type)
        return response

    def call_turing_api(self, msg):
        # 构造请求数据，代码参考了 https://docs.nonebot.dev/guide/tuling.html，有修改
        # Turing机器人api说明见 https://www.kancloud.cn/turing/www-tuling123-com/718227
        url = 'http://openapi.tuling123.com/openapi/api/v2'
        payload = {'reqType': 0,
                   'perception': {'inputText': {'text': msg}},
                   'userInfo': {'apiKey': TURING_API_KEY,
                                'userId': self.user_id.replace('-', '').replace('.', '').replace('@', '')[:20]}}
        try:
            turing_resp = requests.post(url=url, json=payload)
            if turing_resp.status_code != 200:
                return None
            resp_payload = json.loads(turing_resp.text)
            if resp_payload['results']:
                for result in resp_payload['results']:
                    if result['resultType'] == 'text':
                        reply = result['values']['text']
                        # exclude advertisements
                        reply = reply.replace('图灵', '韩大佬').replace('机器人', '')
                        match = re.search(pattern=r'http[:/\.\w]*', string=reply)
                        if match is not None:
                            reply = reply.replace(match.group(), 'https://www.ucas.ac.cn/')
                        return reply
        except (json.JSONDecodeError, KeyError):
            return None
