from ...requests import Request
from ...responses import *
from ...distributor import Distributor
from ...server_config import FLASK_PORTS
from PIL import Image
import flask, threading, traceback

PLATFORM = 'Console'
SERVER_ACTIVE = False
app = flask.Flask(__name__)
# app.debug = True


@app.route('/', methods=['GET', 'POST'])
def service():
    ConsolePorter.execute_form(flask.request.form.to_dict())
    return {}


class ConsolePorter:
    @staticmethod
    def execute_form(form_dict: dict):
        responses = []
        msg = form_dict.get('msg')
        img = form_dict.get('img')
        if msg is not None:
            responses.append(ResponseMsg(msg))
        if img is not None:
            responses.append(ResponseImg(img))
        ConsolePorter.execute(responses)

    # 用于执行Response序列
    @staticmethod
    def execute(response_list):
        for response in response_list:
            if isinstance(response, ResponseMsg):
                msg = ''
                for at_id in response.at_list:
                    msg += '@%s ' % str(at_id)
                msg += response.text
                print(msg)
            elif isinstance(response, ResponseImg):
                im = Image.open(response.file)
                im.show()
            else:
                print('ConsolePorter - Response类型不支持：%s' % str(response))

    @staticmethod
    def interface(msg_input: str):
        # 在任何情况下，把msg打包成Request交给分拣中心（Distributor），然后处理分拣中心发回的Response序列
        # Resqust打包
        request = Request()
        request.platform = PLATFORM
        request.user_id = '0'
        request.msg = msg_input

        # 初始化分拣中心
        distributor = Distributor()

        # 把Resquest交给分拣中心，执行返回的Response序列
        try:
            ConsolePorter.execute(response_list=distributor.handle(request=request))
        except:
            traceback.print_exc()
            print('====')

        # 刷新并保存最新的session信息
        distributor.refresh_and_save()


def main():
    if SERVER_ACTIVE:
        threading.Thread(target=app.run, kwargs={'port': FLASK_PORTS[PLATFORM]}, daemon=True).start()
    while True:
        ConsolePorter.interface(input('ConsolePorter - 请发送消息：'))