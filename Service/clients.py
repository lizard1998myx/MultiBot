import requests
from MultiBot.server_config import FLASK_PORTS

URL = 'http://localhost:%s/' % FLASK_PORTS['Integral']


class MultiBotClient:
    @staticmethod
    def show_console(msg, img=None):
        return requests.post(URL, {'platform': 'Console', 'msg': msg, 'img': img})

    @staticmethod
    def send_email(address, name, subject, msg, img=None):
        return requests.post(URL,
                             {'platform': 'Mail', 'address': address, 'name': name,
                              'subject': subject, 'msg': msg, 'img': img})

    @staticmethod
    def send_qq_private(user_id, msg, img=None):
        return requests.post(URL, {'platform': 'CQ', 'user_id': user_id, 'msg': msg, 'img': img})

    @staticmethod
    def send_qq_group(group_id, msg, img=None):
        return requests.post(URL, {'platform': 'CQ', 'group_id': group_id, 'msg': msg, 'img': img})

    @staticmethod
    def send_qq_dev(msg, img=None):
        return MultiBotClient.send_qq_private('315887212', msg=msg, img=img)

    @staticmethod
    def send_qq_dev_group(msg, img=None):
        return MultiBotClient.send_qq_group('230697355', msg=msg, img=img)

    @staticmethod
    def test(img='test_img.jpg'):
        message = {'msg': 'hello - MultiBot test'}
        try:
            with open(img, 'r') as f:
                pass
        except FileNotFoundError:
            pass
        else:
            message['img'] = img
        MultiBotClient.show_console(**message)
        MultiBotClient.send_email(address='315887212@qq.com', name='dev',
                                  subject='a test mail', **message)
        MultiBotClient.send_qq_dev(**message)
        MultiBotClient.send_qq_dev_group(**message)