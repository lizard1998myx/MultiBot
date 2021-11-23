from ...requests import Request
from ...responses import *
from ...distributor import Distributor
from ...server_config import FLASK_PORTS
from ...api_tokens import SENDER
import smtplib, flask, threading
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

PLATFORM = 'Mail'

SERVER_ACTIVE = False

app = flask.Flask(__name__)
# app.debug = True


@app.route('/', methods=['GET', 'POST'])
def service():
    MailPorter.execute_form(flask.request.form.to_dict())
    return {}


class MailPorter:
    @staticmethod
    def execute_form(form_dict: dict):
        MailPorter.send_email(subject=form_dict.get('subject', 'Email from MultiBot'),
                              text=form_dict.get('msg'),
                              img_file=form_dict.get('img'),
                              receivers=[form_dict['address']],
                              receiver_name=form_dict.get('name', ''))

    # 用于执行Response序列
    @staticmethod
    def execute(response_list, receivers):
        for response in response_list:
            if isinstance(response, ResponseMsg):
                msg = ''
                for at_id in response.at_list:
                    msg += '@%s ' % str(at_id)
                msg += response.text
                MailPorter.send_email(subject='EmailPorter',
                                      text=msg,
                                      receivers=receivers)
            elif isinstance(response, ResponseImg):
                MailPorter.send_email(subject='EmailPorter',
                                      img_file=response.file,
                                      receivers=receivers)
            else:
                print('EmailPorter - Response类型不支持：%s' % str(response))

    @staticmethod
    def run():
        # 在任何情况下，把msg打包成Request交给分拣中心（Distributor），然后处理分拣中心发回的Response序列
        # Resqust打包
        request = Request()
        request.platform = PLATFORM
        request.user_id = '0'
        request.msg = 'hello world!'

        # 分拣中心处理
        distributor = Distributor()
        MailPorter.execute(response_list=distributor.handle(request=request),
                           receivers=[request.user_id])
        distributor.refresh_and_save()

    @staticmethod
    def send_email(subject, text='', img_file=None, receivers=['315887212@qq.com'], receiver_name='Recevier'):
        msgRoot = MIMEMultipart('related')
        msgRoot['From'] = Header(SENDER['name'], 'utf-8')
        msgRoot['To'] = Header(receiver_name, 'utf-8')
        msgRoot['Subject'] = Header(subject, 'utf-8')

        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)

        mail_msg = """
        <p>%s</p>
        <p><img src="cid:image1"></p>
        """ % text.replace('\n', '<br>')
        msgAlternative.attach(MIMEText(mail_msg, 'html', 'utf-8'))

        if img_file is not None:
            # 指定图片为当前目录
            fp = open(img_file, 'rb')
            msgImage = MIMEImage(fp.read())
            fp.close()

            # 定义图片 ID，在 HTML 文本中引用
            msgImage.add_header('Content-ID', '<image1>')
            msgRoot.attach(msgImage)

        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(SENDER['address'], SENDER['pwd'])
        server.sendmail(SENDER['address'], receivers, msgRoot.as_string())
        server.quit()


def main():
    if SERVER_ACTIVE:
        threading.Thread(target=app.run, kwargs={'port': FLASK_PORTS[PLATFORM]}, daemon=True).start()
