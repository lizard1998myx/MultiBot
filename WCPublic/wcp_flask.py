import hashlib, flask, wechatpy, requests, logging, os, traceback
from MultiBot.requests import Request
from MultiBot.responses import *
from MultiBot.distributor import Distributor
from MultiBot.utils import image_url_to_path
from MultiBot.api_tokens import WCP_APP_ID, WCP_APP_SECRET, WCP_TOKEN

PLATFORM = 'WCP'
LOCAL_PORT = 13090

logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')
app = flask.Flask(__name__)
app.debug = True


class WCPublicPorter:
    @staticmethod
    def make_request(wechat_msg):
        request = Request()
        request.platform = PLATFORM
        request.user_id = wechat_msg.source
        if wechat_msg.type == 'text':
            request.msg = wechat_msg.content
        elif wechat_msg.type == 'image':
            request.img = image_url_to_path(wechat_msg.image, header='WCPFlask')
        elif wechat_msg.type == 'location':
            request.loc = {'longitude': float(wechat_msg.location_y),
                           'latitude': float(wechat_msg.location_x)}
        else:
            request.echo = True
            request.msg = '[MultiBotWCP] 消息类型不支持：%s' % str(wechat_msg)
        return request

    @staticmethod
    def get_response(request):
        # 初始化分拣中心
        distributor = Distributor()
        try:
            response_list = distributor.handle(request=request)
        except:
            traceback.print_exc()
            response_list = [ResponseMsg(traceback.format_exc())]
        distributor.refresh_and_save()
        return response_list

    @staticmethod
    def make_reply(response_list, source_msg):
        total_reply_str = ''
        for i, response in enumerate(response_list):
            if i > 0:
                total_reply_str += '\n\n'
            if len(response_list) > 1:
                total_reply_str += '[%i.]\n' % (i+1)
            if isinstance(response, ResponseMsg):
                for at_id in response.at_list:
                    total_reply_str += '@%s ' % str(at_id)
                total_reply_str += response.text
            elif isinstance(response, ResponseImg):
                media_id = WCPublicPorter.upload_image(file=response.file,
                                                       access_token=WCPublicPorter.get_access_token())
                return wechatpy.replies.ImageReply(media_id=media_id, message=source_msg)
            elif isinstance(response, ResponseMusic):
                total_reply_str += response.info()
            else:
                total_reply_str += '[MultiBotWCP] Response类型不支持：%s' % str(response)
        if len(total_reply_str) > 600:
            total_reply_str = total_reply_str[:596] + '\n...'
        return wechatpy.replies.TextReply(content=total_reply_str, message=source_msg)

    @staticmethod
    def get_access_token():
        resp = requests.get(url='https://api.weixin.qq.com/cgi-bin/token',
                            params={"grant_type": "client_credential",
                                    "appid": WCP_APP_ID, "secret": WCP_APP_SECRET})
        return resp.json()['access_token']

    @staticmethod
    def upload_image(file, access_token):
        resp = requests.post(url='https://api.weixin.qq.com/cgi-bin/media/upload',
                             params={"access_token": access_token, 'type': 'image'},
                             files={'media': open(file, 'rb')})
        return resp.json()['media_id']

    @staticmethod
    def msg2reply(msg):
        return WCPublicPorter.make_reply(WCPublicPorter.get_response(WCPublicPorter.make_request(msg)),
                                         source_msg=msg).render()


@app.route("/")
def hello():
    return "Hello World! - from flask at %s" % os.environ['COMPUTERNAME']


@app.route('/wechat_api/', methods=['GET', 'POST'])  # 定义路由地址请与URL后的保持一致
def wechat():
    if flask.request.method == 'GET':
        data = flask.request.args
        s = sorted([data.get('timestamp', ''), data.get('nonce', ''), WCP_TOKEN])
        # 字典排序
        s = ''.join(s)
        if hashlib.sha1(s.encode('utf-8')).hexdigest() == data.get('signature', ''):
            return flask.make_response(data.get('echostr', ''))
    else:
        return WCPublicPorter.msg2reply(wechatpy.parse_message(flask.request.get_data()))


if __name__ == '__main__':
    app.run(port=LOCAL_PORT)
