from .web_app import WebAppPorter
from ..WCPublic.wcp_flask import WCPublicPorter, WCP_TOKEN
from ...paths import PATHS
import flask, hashlib, wechatpy, random
import os, datetime, sys

if sys.platform == 'win32':
    import win32api, win32print
    DEBUG = True
else:
    DEBUG = False  # disable debug in linux etc

LOCAL_PORT = 13090
TEMP_DIR = PATHS['temp']

app = flask.Flask(__name__)
app.static_folder = 'static'
app.debug = DEBUG
# app.send_file_max_age_default = datetime.timedelta(seconds=1)


@app.route("/")
def home():
    response = flask.make_response(flask.render_template("index.html"))
    response.set_cookie('id', '%i' % random.randint(0, 10000), max_age=3600)
    return response


@app.route('/get_cookie')
def get_cookie():
    name = flask.request.cookies.get('id')
    return name


@app.route("/get")
def get_bot_response():
    userText = flask.request.args.get('msg')
    user_id = flask.request.cookies.get('id')
    return str(WebAppPorter.interface(userText, user_id=user_id))


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


@app.route('/wechat_api2/', methods=['GET', 'POST'])  # duplicate the previous wcp
def wechat2():
    if flask.request.method == 'GET':
        data = flask.request.args
        s = sorted([data.get('timestamp', ''), data.get('nonce', ''), WCP_TOKEN])
        # 字典排序
        s = ''.join(s)
        if hashlib.sha1(s.encode('utf-8')).hexdigest() == data.get('signature', ''):
            return flask.make_response(data.get('echostr', ''))
    else:
        return WCPublicPorter.msg2reply(wechatpy.parse_message(flask.request.get_data()),
                                        appid='wx0fddfec2f4ba60c8', appsecret='')


# 添加路由
@app.route('/upload', methods=['POST', 'GET'])
def upload():
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1] in set(['doc', 'docx', 'pdf'])

    if flask.request.method == 'POST':
        return '远程打印功能关闭'

        # 通过file标签获取文件
        f = flask.request.files['file']
        if not (f and allowed_file(f.filename)):
            return "allowed file: doc, docx, pdf"
        upload_path = os.path.join(TEMP_DIR,
                                   datetime.datetime.now().strftime('WebPrinter_%Y%m%d_' + str(f.filename)))
        f.save(upload_path)
        if sys.platform == 'win32':
            win32api.ShellExecute(0, "print", upload_path,
                                  '/d:"%s"' % win32print.GetDefaultPrinter(), ".", 0)
            return "upload success!"
        else:
            return f"unable to print in {sys.platform}"
    # 重新返回上传界面
    return flask.render_template('upload.html')


def main():
    app.run(port=LOCAL_PORT)
