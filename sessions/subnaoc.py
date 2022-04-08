from .general import Session
from ..porters.Service.clients import MultiBotClient
from ..responses import ResponseMsg
from ..paths import PATHS
from ..utils import image_filename
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import time, traceback, os


ZYK_ID = 3288849221
BOT_COM_GROUP = 280506894
webdriver_dir = PATHS['webdriver']
TEMP_DIR = PATHS['temp']


class SubNaocSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 60*3
        self.session_type = '国台自动填报'
        self.strict_commands = ['subnaoc', '国台填报']
        self.description = '登记自动疫情填报（国台版），半自动获取cookie并提交，目前仅支持QQ平台'
        self.permissions = {'CQ': []}  # on QQ only
        self.is_first_time = True
        self.is_second_time = False
        self.cookie_string = ''

    def handle(self, request):
        if self.is_first_time:
            self.is_first_time = False
            self.is_second_time = True
            return ResponseMsg(f'【{self.session_type}】\n'
                               f'[原理]\n'
                               f'本插件用于自动获取腾讯文档的cookie并提交给zyk师兄的机器人小青（{ZYK_ID}），'
                               f'后者将cookie加入数据库中，在每天17时从用户的腾讯文档列表寻找最新的填报表格，然后进行填报，'
                               f'填报信息来自前一天的填报表格，若当天已经填过，则不会重复填报。\n'
                               f'[警告]\n'
                               f'所需的cookie可以用于登录腾讯文档，'
                               f'请在了解可能风险并信任机器人管理员的前提下进行后续操作。\n'
                               f'[说明]\n'
                               f'1. 进行后续操作前请准备好使用微信扫码，'
                               f'机器人返回图片后有[30秒]的时间扫码，超时会导致录入失败；\n'
                               f'2. 录入成功后无需手动填报，但如果在群里看到马老师发文档链接，请顺手点开一下，'
                               f'因为进行自动填报需要所有用户中有一人手动点开过链接；\n'
                               f'3. cookie的有效期大约30天，在30天之后需要重新录入。\n'
                               f'[继续]\n'
                               f'请仔细阅读上述条款，若无异议且已经准备好微信扫码，请回复“准备好了”，然后稍等。')
        elif self.is_second_time:
            self.is_second_time = False
            if request.msg != '准备好了':
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】填报中止')
            else:
                hint = f'【{self.session_type}】正在获取小程序码，请稍后...\n' \
                       f'扫码后点击确认，Bot将在图片发出后30秒读取登录信息'
                if request.group_id is None:  # private message
                    print(MultiBotClient.send_qq_private(user_id=request.user_id, msg=hint))
                else:  # group message
                    print(MultiBotClient.send_qq_group(group_id=request.group_id, msg=hint))
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                try:
                    driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=webdriver_dir)
                    url = 'https://docs.qq.com/desktop/'
                    driver.get(url=url)
                    img_file = os.path.abspath(os.path.join(TEMP_DIR,
                                                            image_filename(header='SubNaoc', post='.png')))
                    try:
                        driver.find_element_by_xpath('//div[@class="wechat inactive"]').click()
                    except NoSuchElementException:
                        # wechat activated
                        pass
                    max_tries = 5
                    n_tries = 0
                    while n_tries <= max_tries:
                        try:
                            driver.find_element_by_xpath('//img[@class="wechat-qrcode"]').screenshot(img_file)
                        except:
                            time.sleep(1)
                            n_tries += 1
                        else:
                            print(f'n_tries={n_tries}')
                            break
                    # send qrcode
                    if request.group_id is None:  # private message
                        print(MultiBotClient.send_qq_private(user_id=request.user_id, msg='', img=img_file))
                    else:  # group message
                        print(MultiBotClient.send_qq_group(group_id=request.group_id, msg='', img=img_file))
                    # wait
                    time.sleep(30)
                    useful = ['low_login_enable', 'has_been_login',
                              'uid', 'utype', 'uid_key', 'fingerprint',
                              'traceid', 'TOK', 'hashkey']
                    driver.refresh()
                    cookies = driver.get_cookies()
                    result = ''
                    for i in useful:
                        found = False
                        for j in cookies:
                            if j['name'] == i:
                                result += f'{i}={j["value"]}; '
                                found = True
                                break
                        if not found:
                            print(f'{i} not found')
                    self.cookie_string = result[:-2]
                    success = (not driver.current_url == url)
                except:
                    driver.quit()
                    self.deactivate()
                    print('== SubNaoc Traceback ==')
                    traceback.print_exc()
                    return ResponseMsg(f'【{self.session_type}】登录失败，可能原因：\n'
                                       f'1. 扫码超时，请在准备好后重新录入；\n'
                                       f'2. 由于未知原因机器人无法将图片发给你。')
                else:
                    driver.quit()
                    if success:
                        return ResponseMsg(f'【{self.session_type}】登录成功，'
                                           f'回复[是/y]自动进行部署。')
                    else:
                        self.deactivate()
                        return ResponseMsg(f'【{self.session_type}】似乎没有登录成功，请重新操作。')
        else:  # third time
            self.deactivate()
            if request.msg == '是' or request.msg.lower()[0] == 'y':
                print(MultiBotClient.send_qq_private(user_id=ZYK_ID, msg=f'covid -a {self.cookie_string}'))
                # print(MultiBotClient.send_qq_group(group_id=BOT_COM_GROUP,
                #                                    msg=f'小青，covid -a {self.cookie_string}'))
                # print(MultiBotClient.send_qq_group(group_id=BOT_COM_GROUP,
                #                                    msg=f'SubNaocSession called by {self.user_id}'))
                return ResponseMsg(f'【{self.session_type}】自动发送成功，请等待17时的自动填报以确认部署成功。')
            else:
                return ResponseMsg(f'【{self.session_type}】不自动发送，可以手动给小青（{ZYK_ID}）发送以下内容部署填报：\n'
                                   f'addcovid {self.cookie_string}')
