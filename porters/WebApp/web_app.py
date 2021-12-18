from ...requests import Request
from ...responses import *
from ...distributor import Distributor
from ...paths import PATHS
import flask, html, random, traceback, shutil, os, time


PLATFORM = 'WebApp'
app = flask.Flask(__name__)
app.static_folder = 'static'


class WebTemp:
    def __init__(self):
        self.temp_dir = PATHS['webtemp']
        self.max_time = 60*5

    @staticmethod
    def get_post(filename: str):
        return filename.split('.')[-1]

    @staticmethod
    def get_time(filename: str):
        time_string = filename.rstrip(f'.{WebTemp.get_post(filename)}')
        return float(time_string)

    def get_absdir(self, filename):
        return os.path.join(self.temp_dir, filename)

    def refresh(self):
        if not os.path.exists(self.temp_dir):
            os.mkdir(self.temp_dir)
            return
        for file in os.listdir(self.temp_dir):
            try:
                create_time = self.get_time(filename=file)
                if (time.time() - create_time) > self.max_time:
                    os.remove(self.get_absdir(filename=file))
            except ValueError:
                pass

    def touch(self, filename: str):
        self.refresh()
        # 加入一个随机数防止bug
        out = f'{time.time()+random.random()}.{self.get_post(filename=filename)}'
        shutil.copy(filename, self.get_absdir(out))
        return f'/static/temp/{out}'


class WebAppPorter:
    # 用于执行Response序列
    @staticmethod
    def execute(response_list):
        final_msg = ''
        for response in response_list:
            if isinstance(response, ResponseMsg):
                msg = ''
                for at_id in response.at_list:
                    msg += '@%s ' % str(at_id)
                msg += f'{response.text}\n\n'
                msg = html.escape(msg).replace('\n', '<br>')
                final_msg += msg
            elif isinstance(response, ResponseImg):
                img_src = WebTemp().touch(filename=response.file)
                final_msg += f' <br><img src="{img_src}" height="auto" width="250"/><br><br>'
                # final_msg += f'<a href="{img_src}">{out}</a>'
            elif isinstance(response, ResponseMusic):
                final_msg += f' <br><a href="{response.link}">{response.name}</a><br><br>'
            else:
                final_msg += f'WebAppPorter - Response类型不支持：{response}<br><br>'
        if final_msg:
            return final_msg.strip('<br>')
        else:
            return 'WebAppPorter - No Response'

    @staticmethod
    def interface(msg_input: str, user_id: str):
        # 在任何情况下，把msg打包成Request交给分拣中心（Distributor），然后处理分拣中心发回的Response序列
        # Resqust打包
        request = Request()
        request.platform = PLATFORM
        request.user_id = user_id
        request.msg = msg_input

        # 初始化分拣中心
        distributor = Distributor()

        # 把Resquest交给分拣中心，执行返回的Response序列
        try:
            final_msg = WebAppPorter.execute(response_list=distributor.handle(request=request))
        except:
            traceback.print_exc()
            msg = traceback.format_exc()
            final_msg = html.escape(msg).replace('\n', '<br>')

        # 刷新并保存最新的session信息
        distributor.refresh_and_save()
        return final_msg


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


def main():
    app.run()


# ————————————————
# 版权声明：本文为CSDN博主「安替-AnTi」的原创文章，遵循CC 4.0 BY-SA版权协议，转载请附上原文出处链接及本声明。
# 原文链接：https://blog.csdn.net/weixin_35770067/article/details/108272583