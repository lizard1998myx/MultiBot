import requests, hmac, hashlib, base64, time, json, shutil
from ..api_tokens import TCT_APPID, TCT_SECRET_ID, TCT_SECRET_KEY
from .argument import Argument, ArgSession
from .general import Session
from ..responses import ResponseMsg
import ffmpy3

# 核心代码来自：https://github.com/TencentCloud/tencentcloud-speech-sdk-python

ENGINE_TYPE = "16k_zh"


class ActiveAudioSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 3*60
        self.session_type = '主动语音识别'
        self.extend_commands = ['audio', '语音']
        self.description = '通过腾讯云API进行语音转文字'
        self.accurate = False
        self.arg_list = [Argument(key='audio', alias_list=['-a'],
                                  required=True, get_all=True,
                                  ask_text='等待语音传输',
                                  help_text='接收语音参数，转为文字')]

    def is_legal_request(self, request):
        return True

    def internal_handle(self, request):
        self.deactivate()
        audio_file = self.arg_dict['audio'].raw_req.aud
        if isinstance(audio_file, str):
            return ResponseMsg(f'【{self.session_type}】{convert(audio_file)}')
        else:
            return ResponseMsg(f'【{self.session_type}】未收到语音')


class PassiveAudioSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 0
        self.session_type = '被动语音识别'
        self.description = '通过腾讯云API进行语音转文字，自动将语音转化为命令'

    def probability_to_call(self, request):
        if isinstance(request.aud, str):
            return 100
        else:
            return 0

    def is_legal_request(self, request):
        return isinstance(request.aud, str)

    def handle(self, request):
        self.deactivate()
        text = convert(request.aud).replace('。', '')
        new_req = request.new()
        new_req.msg = text
        return [ResponseMsg(f'【{self.session_type}】转义为：\n{text}'), new_req]


def amr2wav(inputfile):
    output_filename = 'output.wav'
    ff = ffmpy3.FFmpeg(inputs={inputfile: None},
                       outputs={output_filename: None})
    try:
        ff.run()
    except ffmpy3.FFExecutableNotFoundError as e:
        print('refer this page to for help https://www.jianshu.com/p/2b609afb9800')
        raise e
    except ffmpy3.FFRuntimeError:
        raise ValueError('不支持.amr语音格式')
    return output_filename


def amr2silk(inputfile):
    out = inputfile.replace('.amr', '.silk')
    shutil.copyfile(inputfile, out)
    return out


def convert(filename):
    print(f'== DEBUG: Conversion on file {filename} ==')
    if filename[:4] == 'http':
        return convert_from_url(filename)

    credential_var = Credential(TCT_SECRET_ID, TCT_SECRET_KEY)
    # 新建FlashRecognizer，一个recognizer可以执行N次识别请求
    recognizer = FlashRecognizer(TCT_APPID, credential_var)

    # convert amr file
    if filename.split('.')[-1] == 'amr':
        filename = amr2silk(inputfile=filename)

    # 新建识别请求
    req = FlashRecognitionRequest(ENGINE_TYPE)
    req.set_filter_modal(0)
    req.set_filter_punc(0)
    req.set_filter_dirty(0)
    # req.set_voice_format("wav")
    req.set_voice_format(filename.split('.')[-1])  # 'amr' file
    req.set_word_info(0)
    req.set_convert_num_mode(1)

    # 音频路径
    audio = filename
    with open(audio, 'rb') as f:
        #读取音频数据
        data = f.read()
        #执行识别
        resultData = recognizer.recognize(req, data)
        resp = json.loads(resultData)
        request_id = resp["request_id"]
        code = resp["code"]
        if code != 0:
            return f"recognize faild! request_id: {request_id}, " \
                   f"code: {code}, message: {resp['message']})"
        else:
            """
            print("request_id: ", request_id)
            #一个channl_result对应一个声道的识别结果
            #大多数音频是单声道，对应一个channl_result
            for channl_result in resp["flash_result"]:
                print("channel_id: ", channl_result["channel_id"])
                print(channl_result["text"])
            """
            return resp['flash_result'][0]['text']


class Credential:
    def __init__(self, secret_id, secret_key):
        self.secret_id = secret_id
        self.secret_key = secret_key


class FlashRecognitionRequest:
    def __init__(self, engine_type):
        self.engine_type = engine_type
        self.speaker_diarization = 0
        self.filter_dirty = 0
        self.filter_modal = 0
        self.filter_punc = 0
        self.convert_num_mode = 1
        self.word_info = 0
        self.hotword_id = ""
        self.voice_format = ""
        self.first_channel_only = 1

    def set_first_channel_only(self, first_channel_only):
        self.first_channel_only = first_channel_only

    def set_speaker_diarization(self, speaker_diarization):
        self.speaker_diarization = speaker_diarization

    def set_filter_dirty(self, filter_dirty):
        self.filter_dirty = filter_dirty

    def set_filter_modal(self, filter_modal):
        self.filter_modal = filter_modal

    def set_filter_punc(self, filter_punc):
        self.filter_punc = filter_punc

    def set_convert_num_mode(self, convert_num_mode):
        self.convert_num_mode = convert_num_mode

    def set_word_info(self, word_info):
        self.word_info = word_info

    def set_hotword_id(self, hotword_id):
        self.hotword_id = hotword_id

    def set_voice_format(self, voice_format):
        self.voice_format = voice_format


class FlashRecognizer:
    '''
    reponse:
    字段名            类型
    request_id        string
    status            Integer
    message           String
    audio_duration    Integer
    flash_result      Result Array
    Result的结构体格式为:
    text              String
    channel_id        Integer
    sentence_list     Sentence Array
    Sentence的结构体格式为:
    text              String
    start_time        Integer
    end_time          Integer
    speaker_id        Integer
    word_list         Word Array
    Word的类型为:
    word              String
    start_time        Integer
    end_time          Integer
    stable_flag：     Integer
    '''

    def __init__(self, appid, credential):
        self.credential = credential
        self.appid = appid

    def _format_sign_string(self, param):
        signstr = "POSTasr.cloud.tencent.com/asr/flash/v1/"
        for t in param:
            if 'appid' in t:
                signstr += str(t[1])
                break
        signstr += "?"
        for x in param:
            tmp = x
            if 'appid' in x:
                continue
            for t in tmp:
                signstr += str(t)
                signstr += "="
            signstr = signstr[:-1]
            signstr += "&"
        signstr = signstr[:-1]
        return signstr

    def _build_header(self):
        header = dict()
        header["Host"] = "asr.cloud.tencent.com"
        return header

    def _sign(self, signstr, secret_key):
        hmacstr = hmac.new(secret_key.encode('utf-8'),
                           signstr.encode('utf-8'), hashlib.sha1).digest()
        s = base64.b64encode(hmacstr)
        s = s.decode('utf-8')
        return s

    def _build_req_with_signature(self, secret_key, params, header):
        query = sorted(params.items(), key=lambda d: d[0])
        signstr = self._format_sign_string(query)
        signature = self._sign(signstr, secret_key)
        header["Authorization"] = signature
        requrl = "https://"
        requrl += signstr[4::]
        return requrl

    def _create_query_arr(self, req):
        query_arr = dict()
        query_arr['appid'] = self.appid
        query_arr['secretid'] = self.credential.secret_id
        query_arr['timestamp'] = str(int(time.time()))
        query_arr['engine_type'] = req.engine_type
        query_arr['voice_format'] = req.voice_format
        query_arr['speaker_diarization'] = req.speaker_diarization
        query_arr['hotword_id'] = req.hotword_id
        query_arr['filter_dirty'] = req.filter_dirty
        query_arr['filter_modal'] = req.filter_modal
        query_arr['filter_punc'] = req.filter_punc
        query_arr['convert_num_mode'] = req.convert_num_mode
        query_arr['word_info'] = req.word_info
        query_arr['first_channel_only'] = req.first_channel_only
        return query_arr

    def recognize(self, req, data):
        header = self._build_header()
        query_arr = self._create_query_arr(req)
        req_url = self._build_req_with_signature(self.credential.secret_key, query_arr, header)
        r = requests.post(req_url, headers=header, data=data)
        return r.text


def convert_from_url(url):
    # https://console.cloud.tencent.com/api/explorer?Product=asr&Version=2019-06-14&Action=CreateRecTask&SignVersion=
    import json
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.asr.v20190614 import asr_client, models

    cred = credential.Credential(TCT_SECRET_ID, TCT_SECRET_KEY)
    httpProfile = HttpProfile()
    httpProfile.endpoint = "asr.tencentcloudapi.com"

    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = asr_client.AsrClient(cred, "", clientProfile)

    # upload
    req_up = models.CreateRecTaskRequest()
    params_up = {
        "EngineModelType": "16k_zh",
        "ChannelNum": 1,
        "ResTextFormat": 0,
        "SourceType": 0,
        "Url": url,
    }
    req_up.from_json_string(json.dumps(params_up))

    resp_up = client.CreateRecTask(req_up)

    # download
    def download():
        req_down = models.DescribeTaskStatusRequest()
        params_down = {"TaskId": resp_up.Data.TaskId}
        req_down.from_json_string(json.dumps(params_down))

        resp_down = client.DescribeTaskStatus(req_down)
        return resp_down

    start = time.time()
    resp_down = download()

    while (time.time() - start) < 20:
        if resp_down.Data.Status <= 1:
            # 0 - waiting, 1 - in progress
            time.sleep(0.3)
            resp_down = download()
            continue
        else:
            # 2 - success, 3 - failed
            break

    result = resp_down.Data.Result

    if result:
        return result
    else:
        return resp_down.to_json_string()