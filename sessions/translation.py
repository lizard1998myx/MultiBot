from .argument import ArgSession, Argument
from ..responses import ResponseMsg
from ..api_tokens import CAIYUN_TRANS_TOKEN, TCT_SECRET_ID, TCT_SECRET_KEY
import requests, json


class TranslationSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 60*2
        self.session_type = '翻译插件'
        self.strict_commands = ['translation', '翻译']
        self.description = '基于腾讯云或彩云小译API（caiyunapp.com）翻译语句'
        self.arg_list = [Argument(key='script', alias_list=['-s', '-str'], required=True,
                                  get_next=True,
                                  ask_text='请返回需要翻译的句子（默认翻译中文）'),
                         Argument(key='to', alias_list=['-t', '-to'],
                                  get_next=True,
                                  help_text='目标语言（默认zh）'),
                         Argument(key='from', alias_list=['-f', '-from'],
                                  get_next=True,
                                  help_text='源语言（默认auto）'),
                         Argument(key='caiyun', alias_list=['-cy'],
                                  help_text='使用彩云小译api（目标语言只有中英日）'),
                         ]
        self.default_arg = self.arg_list[0]
        self.detail_description = '语言列表：zh（简体中文）、en（英语）、ja（日语）、ko（韩语）、fr（法语）、' \
                                  'es（西班牙语）、it（意大利语）、de（德语）、tr（土耳其语）、ru（俄语）、' \
                                  'pt（葡萄牙语）、vi（越南语）、id（印尼语）、th（泰语）、ms（马来语）'

    def internal_handle(self, request):
        self.deactivate()
        script = self.arg_dict["script"].value

        # source & target language
        if self.arg_dict['from'].called:
            source_lang = self.arg_dict['from'].value
        else:
            source_lang = 'auto'
        if self.arg_dict['to'].called:
            target_lang = self.arg_dict['to'].value
        else:
            target_lang = 'zh'
        direction = f'{source_lang}2{target_lang}'

        if self.arg_dict['caiyun'].called:
            api = 'Caiyun'
            translator = TranslationAPI(direction=direction)
        else:
            api = 'Tencent'
            translator = TranslationAPIbyTCT(direction=direction)

        hint = f'【{self.session_type}】{direction} by{api}\nScript: {script}'

        return [ResponseMsg(hint), ResponseMsg(translator.translate(script=script))]


class TranslationAPI:
    def __init__(self, direction='auto2zh'):
        self.direction = direction

    def translate(self, script: str):
        url = "http://api.interpreter.caiyunai.com/v1/translator"
        payload = {
            "source": [script],
            "trans_type": self.direction,
            "request_id": "demo",
            "detect": True,
        }
        headers = {
            'content-type': "application/json",
            'x-authorization': f"token {CAIYUN_TRANS_TOKEN}",
        }
        try:
            return requests.post(url=url, data=json.dumps(payload), headers=headers).json()['target'][0]
        except KeyError:
            return 'Translation API no respond'
        # return requests.post(url=url, data=json.dumps(payload), headers=headers).json()
        # {'confidence': 0.8, 'target': ['嗨'], 'rc': 0}


class TranslationAPIbyTCT(TranslationAPI):
    def __init__(self, direction):
        TranslationAPI.__init__(self, direction=direction)
        self.target = self.direction.split('2')[-1]
        self.source = self.direction.split('2')[0]

    def translate(self, script: str):
        import json
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
        from tencentcloud.tmt.v20180321 import tmt_client, models

        cred = credential.Credential(TCT_SECRET_ID, TCT_SECRET_KEY)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "tmt.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = tmt_client.TmtClient(cred, "ap-beijing", clientProfile)

        req = models.TextTranslateRequest()
        params = {
            "SourceText": script,
            "Source": "auto",
            "Target": self.target,
            "ProjectId": 0
        }
        req.from_json_string(json.dumps(params))

        resp = client.TextTranslate(req)
        return resp.TargetText