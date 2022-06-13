import traceback, flask, os, logging
from wechatpy.work.crypto import WeChatCrypto
from wechatpy.work import WeChatClient, parse_message
from wechatpy.work.events import EnterAgentEvent, LocationEvent, SubscribeEvent
from apscheduler.schedulers.blocking import BlockingScheduler
from ...requests import Request
from ...responses import *
from ...distributor import Distributor, DistributorCron
from ...utils import image_url_to_path, format_filename
from ...api_tokens import WCE_CO_ID, WCE_AES_KEY, WCE_TOKEN, WCE_APP_ID, WCE_APP_SECRET
from ...server_config import FLASK_PORTS


PLATFORM = 'WCE'


class WCEnterprisePorter:
    def __init__(self):
        # for crypto
        self.co_id = WCE_CO_ID
        self.aes_key = WCE_AES_KEY
        self.token = WCE_TOKEN
        # for sending message
        self.app_id = WCE_APP_ID
        self.app_secret = WCE_APP_SECRET

        self.client = WeChatClient(corp_id=self.co_id,
                                   secret=self.app_secret)

    def _get_crypto(self):
        return WeChatCrypto(self.token, self.aes_key, self.co_id)

    def echo(self, flask_request):
        crypto = self._get_crypto()
        signature = flask_request.args.get("msg_signature", "")
        timestamp = flask_request.args.get("timestamp", "")
        nonce = flask_request.args.get("nonce", "")
        echo_str = flask_request.args.get("echostr", "")
        echo_str = crypto.check_signature(signature, timestamp, nonce, echo_str)
        return echo_str

    def msg_pipeline(self, flask_request):
        req = self.make_request(self.decrypt_msg(flask_request=flask_request))
        if req is None:
            return
        else:
            res = self.get_response(request=req)
            self.send_responses(response_list=res)

    def cron_task(self):
        # request打包
        request = Request()
        request.platform = PLATFORM
        request.user_id = ''
        request.from_scheduler = True

        res = self.get_response(request=request, cron_task=True)
        self.send_responses(response_list=res)

    def decrypt_msg(self, flask_request):
        crypto = self._get_crypto()
        signature = flask_request.args.get("msg_signature", "")
        timestamp = flask_request.args.get("timestamp", "")
        nonce = flask_request.args.get("nonce", "")
        msg = crypto.decrypt_message(flask_request.data, signature, timestamp, nonce)
        return parse_message(msg)

    def make_request(self, wechat_msg):
        request = Request()
        request.platform = PLATFORM
        request.user_id = wechat_msg.source
        if wechat_msg.type == 'text':
            request.msg = wechat_msg.content
        elif wechat_msg.type == 'image':
            request.img = image_url_to_path(wechat_msg.image, header='WCEFlask')
        elif wechat_msg.type == 'voice':
            request.aud = format_filename(header='WCE', type='aud', post=f'.{wechat_msg.format}')
            self._download_media(media_id=wechat_msg.media_id, filename=request.aud)
        elif wechat_msg.type == 'location':
            request.loc = {'longitude': float(wechat_msg.location_y),
                           'latitude': float(wechat_msg.location_x)}
        elif isinstance(wechat_msg, SubscribeEvent):
            request.msg = 'hello'
        elif isinstance(wechat_msg, EnterAgentEvent) or isinstance(wechat_msg, LocationEvent):
            return
        else:
            request.echo = True
            request.msg = f'[MultiBotWCE] 消息类型不支持：{wechat_msg}'
        return request

    @staticmethod
    def get_response(request, cron_task=False):
        if request is None:
            return
        # 初始化分拣中心
        if not cron_task:
            distributor = Distributor()
        else:
            distributor = DistributorCron()
        try:
            response_list = distributor.handle(request=request)
        except:
            traceback.print_exc()
            response_list = [ResponseMsg(traceback.format_exc())]
        distributor.refresh_and_save()
        return response_list

    def _download_media(self, media_id, filename):
        assert not os.path.exists(filename)
        logging.debug(f'WCE - downloading -> {media_id}')
        with open(filename, 'wb') as f:
            f.write(self.client.media.download(media_id=media_id).content)

    def _upload_media(self, media_type, filename):
        # upload & get temp media_id, supports image, voice, video, file
        # https://developer.work.weixin.qq.com/document/path/90253
        with open(filename, 'rb') as f:
            r = self.client.media.upload(media_type=media_type, media_file=f)
        media_id = r['media_id']
        logging.debug(f'WCE - uploaded -> [{media_type}]{media_id}')
        return media_id

    def _upload_image(self, filename):
        return self._upload_media(media_type='image', filename=filename)

    def send_responses(self, response_list):
        for response in response_list:
            logging.debug(f'WCE - response @{response.user_id}')
            if isinstance(response, ResponseMsg):
                # make reply string
                reply_str = ''
                for at_id in response.at_list:
                    reply_str += '@%s ' % str(at_id)
                reply_str += response.text
                logging.debug(f'WCE - text: {reply_str}')

                # split & send
                max_length = 600
                while len(reply_str) > 0:
                    reply_left = reply_str[max_length:]  # msg超出maxL的部分
                    reply_str = reply_str[:max_length]  # msg只保留maxL内的部分
                    self.client.message.send_text(agent_id=self.app_id,
                                                  user_ids=response.user_id,
                                                  content=reply_str)
                    if reply_left != '':  # 这轮超出部分为0时
                        reply_str = reply_left
                    else:
                        reply_str = ''

            elif isinstance(response, ResponseImg):
                logging.debug(f'WCE - img: {response.file}')

                media_id = self._upload_image(filename=response.file)
                try:
                    self.client.message.send_image(agent_id=self.app_id,
                                                   user_ids=response.user_id,
                                                   media_id=media_id)
                except KeyError:
                    traceback.print_exc()
                    self.client.message.send_text(agent_id=self.app_id,
                                                  user_ids=response.user_id,
                                                  content='[MultiBotWCE] 企业微信后台图片接口故障，需联系管理员修复')
            elif isinstance(response, ResponseMusic):
                self.client.message.send_text(agent_id=self.app_id,
                                              user_ids=response.user_id,
                                              content=response.info())
            else:
                self.client.message.send_text(agent_id=self.app_id,
                                              user_ids=response.user_id,
                                              content=f'[MultiBotWCE] Response类型不支持：{response}')


# 基本消息处理任务
def main():
    app = flask.Flask(__name__)

    @app.route("/")
    def hello():
        return "Hello World! - from WeChatEnterprise flask at %s" % os.environ['COMPUTERNAME']

    @app.route("/wce_api", methods=["GET", "POST"])
    def wce():
        porter = WCEnterprisePorter()
        if flask.request.method == "GET":
            return porter.echo(flask_request=flask.request)
        else:
            porter.msg_pipeline(flask_request=flask.request)
            return {}

    app.run(port=FLASK_PORTS[PLATFORM])


# 定时任务
def cron_main():
    def _cron_task():
        WCEnterprisePorter().cron_task()
    scheduler = BlockingScheduler()
    scheduler.add_job(_cron_task, 'cron', hour='*', minute='*')
    scheduler.start()


