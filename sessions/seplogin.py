from .argument import ArgSession, Argument
from ..responses import ResponseMsg, ResponseImg
from ..utils import format_filename
from ..paths import PATHS
import requests, os, bs4
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

TEMP_DIR = PATHS['temp']
webdriver_dir = PATHS['webdriver']

# 2021-12-06: 更新新版验证码，ehall cookies多次尝试

class SepLoginSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 3*60
        self.session_type = 'SEP登录插件'
        self.strict_commands = ['sep', 'ehall', 'cookie', '登录']
        self.description = '登录SEP&服务大厅并获取cookie，已接入SIK'
        agreement_text = ("\n自动化登录SEP&服务大厅并获取cookie，出现报错请联系管理员（回复“更多”获取联系方式）。\n" 
                          "【警告】\n"
                          "本插件原理是使用爬虫登录SEP和国科大办事大厅。" 
                          "所使用信息为一次性，不保存账号、密码、cookie和个人信息。\n" 
                          "【下一步】\n" 
                          "确认仔细阅读上述条款且无异议，回复任意消息进入下一步。")
        self.arg_list = [Argument(key='agree', alias_list=['-y', '-a'],
                                  required=True,
                                  ask_text=agreement_text),
                         Argument(key='username', alias_list=['-u'],
                                  required=True, get_next=True,
                                  ask_text='SEP用户名（邮箱）'),
                         Argument(key='password', alias_list=['-p'],
                                  required=True, get_next=True,
                                  ask_text='SEP密码'),
                         Argument(key='exams', alias_list=['-e'],
                                  required=False, get_next=False,
                                  help_text='查询上学期的成绩（学期id为64758、64759）'),
                         Argument(key='no-ehall', alias_list=['-ne'],
                                  required=False, get_next=False,
                                  help_text='不登录ehall获取cookie（更快）'),
                         ]
        self.loginer = None
        self._cookie_string = None
        self.times_get_in = 0
        self.detail_description = '举例，发送“sep -y -u xx@xx.cn -p 123456”，' \
                                  '然后输入验证码，登陆成功后，回复yes进入SIK自动申报。'

    def internal_handle(self, request):
        self.times_get_in += 1
        if self.times_get_in == 1:
            self.loginer = SepLogin(username=self.arg_dict['username'].value,
                                    password=self.arg_dict['password'].value)
            self.loginer.get_basic_cookie()
            code_img = format_filename(header='SepLogin', type='image', post='.jpg')
            code_img_dir = os.path.join(TEMP_DIR, code_img)
            self.loginer.get_code(code_filename=code_img_dir)
            return [ResponseMsg(f'【{self.session_type}】请输入验证码'), ResponseImg(file=code_img_dir)]
        elif self.times_get_in == 2:
            # self.deactivate()
            responses = []
            self.loginer.code = request.msg
            try:
                self.loginer.login_sep()
            except KeyError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】登陆失败，请检查账号/密码/验证码并重试。')
            if self.arg_dict['exams'].called:
                for term_id in [64758, 64759]:
                    responses.append(ResponseMsg(f'【{self.session_type}】学期{term_id}成绩：\n'
                                                 f'{self.loginer.get_exams(term_id=term_id)}'))
            if self.arg_dict['no-ehall'].called:
                self.deactivate()
            else:
                self._cookie_string = self.loginer.login_ehall()
                responses += [ResponseMsg(f'【{self.session_type}】已获取cookie字符串\n{self._cookie_string}'),
                              ResponseMsg(f'【{self.session_type}】是否继续进行SIK申报？')]
            return responses
        elif self.times_get_in == 3:
            self.deactivate()
            if request.msg == '是' or request.msg.lower()[0] == 'y':
                return [ResponseMsg(f'【{self.session_type}】自动调用SIK中...'),
                        request.new(msg=f'SIK -y -c "{self._cookie_string}"')]
            else:
                return ResponseMsg(f'【{self.session_type}】不调用SIK，结束')
        else:
            self.deactivate()


class SepLogin:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.code = None
        self.cookie_dict = {}
        self.basic_cookie = ''
        self.webdriver_dir = webdriver_dir
        self.exam_cookie_updated = False

    def get_basic_cookie(self):
        sep_url = 'http://sep.ucas.ac.cn/'
        sep_headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                                 'image/avif,image/webp,image/apng,*/*;'
                                 'q=0.8,application/signed-exchange;v=b3;q=0.9',
                       'Accept-Encoding': 'gzip, deflate',
                       'Accept-Language': 'zh-CN,zh;q=0.9',
                       'Connection': 'keep-alive',
                       'Host': 'sep.ucas.ac.cn',
                       'Upgrade-Insecure-Requests': '1',
                       'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                                     'Chrome/92.0.4515.107 Safari/537.36}',
                       }
        resp_sep = requests.get(url=sep_url, headers=sep_headers)
        cookie = resp_sep.headers['Set-Cookie']
        self.basic_cookie = cookie
        name = cookie.split('=')[0]  # JSESSIONID
        value = cookie.lstrip(f'{name}=').rstrip('; Path=/')
        self.cookie_dict[name] = value

    def get_code(self, code_filename):
        # jpg file
        # code_url = 'http://sep.ucas.ac.cn/randomcode.jpg'
        code_url = 'http://sep.ucas.ac.cn/changePic'
        code_headers = {'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Accept-Encoding': 'gzip, deflate',
                        'Accept-Language': 'zh-CN,zh;q=0.9',
                        'Connection': 'keep-alive',
                        'Cookie': self.basic_cookie,
                        'Host': 'sep.ucas.ac.cn',
                        'Referer': 'http://sep.ucas.ac.cn/',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                                      'Chrome/92.0.4515.107 Safari/537.36}',
                        }
        resp_code = requests.get(url=code_url, headers=code_headers)
        with open(code_filename, 'wb') as f:
            f.write(resp_code.content)

    def login_sep(self):
        login_url = 'http://sep.ucas.ac.cn/slogin'
        login_headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                                   'image/avif,image/webp,image/apng,*/*;'
                                   'q=0.8,application/signed-exchange;v=b3;q=0.9',
                         'Accept-Encoding': 'gzip, deflate',
                         'Accept-Language': 'zh-CN,zh;q=0.9',
                         'Cache-Control': 'max-age=0',
                         'Connection': 'keep-alive',
                         'Content-Length': '82',
                         'Content-Type': 'application/x-www-form-urlencoded',
                         'Cookie': self.basic_cookie,
                         'Host': 'sep.ucas.ac.cn',
                         'Origin': 'http://sep.ucas.ac.cn',
                         'Referer': 'http://sep.ucas.ac.cn/',
                         'Upgrade-Insecure-Requests': '1',
                         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                                       'Chrome/92.0.4515.107 Safari/537.36}',
                         }
        login_form = {'userName': self.username,
                      'pwd': self.password,
                      'certCode': self.code,
                      'sb': 'sb',
                      }
        resp_login = requests.post(url=login_url, data=login_form, headers=login_headers)
        new_cookie_key = 'sepuser'
        new_cookie_value = resp_login.history[0].cookies[new_cookie_key]
        self.cookie_dict[new_cookie_key] = new_cookie_value

    def login_ehall(self):
        max_retires = 3
        retires = 0
        while retires <= max_retires:
            retires += 1
            try:
                ehall_url = 'http://sep.ucas.ac.cn/portal/site/416/2095'
                self.update_cookie(url=ehall_url, domain='.ucas.ac.cn')
                result = self.make_cookie_string(cookie_names=['sepuser', 'vjuid', 'vjvd', 'vt'])
                return result
            except KeyError:
                continue
        raise Exception('fail to get ehall cookies')

    def update_cookie(self, url, domain=".ucas.ac.cn"):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=self.webdriver_dir)
        try:
            driver.implicitly_wait(1)  # 等待3秒
            driver.get(url)
            driver.implicitly_wait(0.5)
            driver.delete_all_cookies()
            for c_name, c_value in self.cookie_dict.items():
                driver.add_cookie({"domain": domain,
                                   "name": c_name,
                                   "value": c_value,
                                   "path": '/',
                                   "expires": None})
            driver.get(url)
            print(driver.current_url)
            for cookie_item in driver.get_cookies()[::-1]:
                # make sure new ones updated into the cookie_dict
                print(cookie_item)
                self.cookie_dict[cookie_item['name']] = cookie_item['value']
            print(self.cookie_dict)
            driver.quit()
        except Exception as e:
            driver.quit()
            raise e
        return

    def get_exams(self, term_id=64758):
        if self.exam_cookie_updated:
            # this will save some time
            pass
        else:
            # erase the undefined 'JSESSIONID' and get a new one
            self.update_cookie(url='http://sep.ucas.ac.cn/portal/site/226/821')
            self.exam_cookie_updated = True
        url = f'http://jwxk.ucas.ac.cn/score/yjs/{term_id}'
        cookie_string = self.make_cookie_string(cookie_names=['sepuser', 'JSESSIONID'])
        headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                             'image/avif,image/webp,image/apng,*/*;'
                             'q=0.8,application/signed-exchange;v=b3;q=0.9',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,'
                                      'zh-TW;q=0.7,ja;q=0.6',
                   'Connection': 'keep-alive',
                   'Cookie': cookie_string,
                   'Host': 'jwxk.ucas.ac.cn',
                   'Referer': 'http://jwxk.ucas.ac.cn/notice/view/1',
                   'Upgrade-Insecure-Requests': '1',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                 'AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/92.0.4515.107 Safari/537.36}',
                   }
        resp = requests.get(url=url, headers=headers)
        soup = bs4.BeautifulSoup(resp.text, 'html.parser')
        tag = soup.find('table', {'class': 'table table-striped table-bordered table-advance table-hover'})
        col_names = []
        for col_name_tag in tag.findChild('thead').findChildren('th'):
            col_names.append(col_name_tag.text)
        n_cols = len(col_names)
        row_list = []
        for row_tag in tag.findChild('tbody').findChildren('tr'):
            row_element_tags = row_tag.findChildren('td')
            row_dict = {}
            for i_col in range(n_cols):
                row_dict[col_names[i_col]] = row_element_tags[i_col].text.strip()
            row_list.append(row_dict)
        return row_list

    def make_cookie_string(self, cookie_names):
        cookie_string = ''
        for cookie_name in cookie_names:
            cookie_string += f'{cookie_name}={self.cookie_dict[cookie_name]}; '
        cookie_string = cookie_string[:-2]
        print(cookie_string)
        return cookie_string