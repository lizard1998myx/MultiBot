from .general import Session
from ..porters.Service.clients import MultiBotClient
from ..responses import ResponseMsg, ResponseImg
from ..paths import PATHS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import time, traceback, os, threading, requests, base64
from ..utils import image_filename


ZYK_ID = 3288849221
BOT_COM_GROUP = 280506894
webdriver_dir = PATHS['webdriver']
TEMP_DIR = PATHS['temp']


# 核心功能实现：后台driver
class AutoQuitThread(threading.Thread):
    def __init__(self, timer=60, driver_params={}):
        threading.Thread.__init__(self)
        self.timer = timer
        self.driver_params = driver_params
        self.url = None
        self.sid = None
        self.created = False
        self.quited = False
        self._quit_next_time = True

    def run(self):
        dr0 = webdriver.Chrome(**self.driver_params)
        self.url = dr0.command_executor._url
        self.sid = dr0.session_id
        self.created = True
        while True:
            time.sleep(self.timer)
            if self._quit_next_time:
                self.quited = True
                dr0.quit()
                return
            else:
                self._quit_next_time = True

    def keep_alive(self):
        assert not self.quited, 'your webdriver is dead already'
        self._quit_next_time = False


class SubNaocSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 60
        self.session_type = '国台自动填报'
        self.strict_commands = ['subnaoc', '国台填报']
        self.description = '登记自动疫情填报（国台版），半自动获取cookie并提交。'
        self.is_first_time = True
        self.is_second_time = False
        self.is_third_time = False
        self.cookie_string = ''
        self._dx_params = {}
        self.use_legacy_selenium = False
        self._requests_session = None
        self._requests_checkkey = None  # in requests method

    def probability_to_call(self, request):
        return self._called_by_command(request=request, extend_p=95, strict_p=95)

    def handle(self, request):
        if self.is_first_time:
            self.is_first_time = False
            self.is_second_time = True
            return ResponseMsg(f'【{self.session_type}】\n'
                               f'[原理]\n'
                               f'本插件用于自动获取腾讯文档的cookie并提交给zyk师兄的机器人小青（{ZYK_ID}），'
                               f'后者每天17时自动填报（信息来自前一天的填报表格），'
                               f'若当天已经填过，则不会重复填报。\n'
                               f'[警告]\n'
                               f'所需的cookie可以用于登录腾讯文档，'
                               f'请在了解可能风险并信任机器人管理员的前提下进行后续操作。\n'
                               f'[说明]\n'
                               f'30天左右登录凭据会过期，需要重新录入。\n'
                               f'[继续]\n'
                               f'请回复“准备好了”，然后稍等（由于网络原因可能需要等待稍长）。')

        # requests method, step 2 & 3, via zyk post_covid.py
        elif self.is_second_time and not self.use_legacy_selenium:  # requests方法的第二步
            self.is_second_time = False
            self.is_third_time = True
            if request.msg != '准备好了':
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】填报中止')
            else:
                self._requests_session = requests.Session()
                url = 'https://docs.qq.com/desktop/'
                r = self._requests_session.get(url)
                xsrf = r.cookies['TOK']

                url = 'https://docs.qq.com/cgi-bin/online_docs/wxqrcode/'
                data = {
                    'page': 'pages/landingpage/landingpage',
                    'ac': 'login',
                    'xsrf': xsrf,
                    'ts': int(time.time() * 1e3),
                    'checkKey': '1',
                    '__t': int(time.time() * 1e3)
                }

                r = self._requests_session.post(url, data=data)
                self._requests_checkkey = r.json()['checkKey']

                imgdata = base64.b64decode(r.json()['img'])
                img_file = os.path.abspath(os.path.join(TEMP_DIR,
                                                        image_filename(header='SubNaoc', post='.jpg')))
                with open(img_file, 'wb') as f:
                    f.write(imgdata)
                return [ResponseMsg(f'【{self.session_type}】'
                                    f'请在{self._max_delta}秒内扫码、在手机上点击确认，然后回复任意消息继续。'),
                        ResponseImg(file=img_file)]

        elif self.is_third_time and not self.use_legacy_selenium:  # requests方法的第三步
            self.is_third_time = False
            assert self._requests_session is not None, '似乎没有完成第二步'
            assert self._requests_checkkey is not None, '似乎没有完成第二步'

            url = 'https://docs.qq.com/v2/cgi-bin/online_docs/polling'
            data = {
                'CheckKey': self._requests_checkkey
            }
            r = self._requests_session.post(url, params=data)
            if r.json()['status']['login'] == 1:
                cookie_dict = requests.utils.dict_from_cookiejar(r.cookies)
                result_str = ''
                for key in cookie_dict:
                    if key in ['TOK', 'uid', 'uid_key']:
                        if key == 'TOK':
                            result_str += 'traceid' + '=' + cookie_dict[key][:10] + '; '
                        result_str += key + '=' + cookie_dict[key] + '; '
                self.cookie_string = result_str[:-2]
                return ResponseMsg(f'【{self.session_type}】登录成功，'
                                   f'回复[是/y]自动进行部署。')
            else:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】似乎没有登录成功，请重新操作。')

        # requests method, step 2 & 3, abandoned
        elif self.is_second_time and self.use_legacy_selenium:  # selenium方法的第二步
            self.is_second_time = False
            self.is_third_time = True
            if request.msg != '准备好了':
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】填报中止')
            else:
                # legacy selenium method
                # 启动实验型webdriver
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                driver_params = {'executable_path': webdriver_dir}
                # driver_params['chrome_options'] = chrome_options  # headless
                t = AutoQuitThread(timer=600, driver_params=driver_params)
                t.start()
                while True:
                    if t.created:
                        self._dx_params.update({'url': t.url, 'sid': t.sid})
                        dx = webdriver.Remote(command_executor=self._dx_params['url'],
                                              desired_capabilities={})
                        break
                    else:
                        time.sleep(0.05)
                dx.close()
                dx.session_id = self._dx_params['sid']

                # 获取登录二维码
                url = 'https://docs.qq.com/desktop/'
                dx.get(url=url)
                img_file = os.path.abspath(os.path.join(TEMP_DIR,
                                                        image_filename(header='SubNaoc', post='.png')))
                try:
                    dx.find_element_by_xpath('//div[@class="wechat inactive"]').click()
                except NoSuchElementException:
                    # wechat activated
                    pass
                max_tries = 5
                n_tries = 0
                while n_tries <= max_tries:
                    try:
                        dx.find_element_by_xpath('//img[@class="wechat-qrcode"]').screenshot(img_file)
                    except:
                        time.sleep(1)
                        n_tries += 1
                    else:
                        print(f'n_tries={n_tries}')
                        break
                # dx.start_session()  # 由于此时driver没有被关闭，因此不需要这一步
                t.keep_alive()  # refresh
                return [ResponseMsg(f'【{self.session_type}】'
                                    f'请在{self._max_delta}秒内扫码、在手机上点击确认，然后回复任意消息继续。'),
                        ResponseImg(file=img_file)]

        elif self.is_third_time and self.use_legacy_selenium:  # selenium方法的第三步
            self.is_third_time = False

            # 再次启动实验型webdriver
            dx = webdriver.Remote(command_executor=self._dx_params['url'],
                                  desired_capabilities={})
            dx.close()
            dx.session_id = self._dx_params['sid']

            url = 'https://docs.qq.com/desktop/'
            # useful = ['low_login_enable', 'has_been_login',
            #           'uid', 'utype', 'uid_key', 'fingerprint',
            #           'traceid', 'TOK', 'hashkey']
            useful = ['uid', 'uid_key', 'traceid', 'TOK']
            # useful = ['SID']  # update in 20220418, after selenium bug

            dx.refresh()

            # 获取cookie
            cookies = dx.get_cookies()
            result = ''
            for i in useful:
                found = False
                for j in cookies:
                    if j['name'].lower() == i.lower():
                        result += f'{i}={j["value"]}; '
                        found = True
                        break
                if not found:
                    print(f'{i} not found')
            self.cookie_string = result[:-2]
            success = (not dx.current_url == url)

            dx.quit()
            if success:
                return ResponseMsg(f'【{self.session_type}】登录成功，'
                                   f'回复[是/y]自动进行部署。')
            else:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】似乎没有登录成功，请重新操作。')

        else:  # third time  # 4th time
            self.deactivate()
            if request.msg == '是' or request.msg.lower()[0] == 'y':
                print(MultiBotClient.send_qq_private(user_id=ZYK_ID, msg=f'covid -a {self.cookie_string}'))
                return ResponseMsg(f'【{self.session_type}】自动发送成功，请等待17时的自动填报以确认部署成功。')
            else:
                return ResponseMsg(f'【{self.session_type}】不自动发送，可以手动给小青（{ZYK_ID}）发送以下内容部署填报：\n'
                                   f'addcovid {self.cookie_string}')
