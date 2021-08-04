import re
from selenium import webdriver
import urllib
from selenium.webdriver.chrome.options import Options
from MultiBot.sessions.argument import Argument, ArgSession
from MultiBot.responses import ResponseMusic


class NetEaseSongSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 30
        self.session_type = '点歌插件'
        self.strict_commands = ['song', 'music', '音乐', '点歌']
        self.arg_list = [Argument(key='key', alias_list=['-k'],
                                  required=True, get_next=True,
                                  ask_text='请输入搜索关键词',
                                  help_text='搜索关键词'),
                         Argument(key='num', alias_list=['-n'],
                                  required=False, get_next=True,
                                  ask_text='要返回多少条结果（默认1条）',
                                  help_text='返回结果数目'),
                         ]
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        self.deactivate()
        if self.arg_dict['num'].called:
            num = int(self.arg_dict['num'].value)
        else:
            num = 1
        responses = []
        for music in search_songs(search_str=self.arg_dict['key'].value)[:num]:
            responses.append(ResponseMusic(**music))
        return responses


def search_songs(search_str='北京',
                 webdriver_dir=r'C:\Users\Yuxi\PycharmProjects\untitled\chromedriver.exe'):
    url = f'https://music.163.com/#/search/m/?s={urllib.parse.quote(search_str)}&type=1'
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=webdriver_dir)
        driver.get(url)
        driver.switch_to.frame('g_iframe')
        raw_list = driver.find_elements_by_xpath('//div[@class="srchsongst"]//div[@class="td w0"]'
                                                 '/div[@class="sn"]/div[@class="text"]/a')
        new_list = []
        for element in raw_list:
            name = element.text
            song_link = element.get_attribute('href')
            m = re.match(r'https://music.163.com/song\?id=(\d+)', song_link)
            if m:
                music_id = m.group(1)
                new_list.append({'name': name, 'link': song_link,
                                 'music_id': music_id, 'platform': '163'})
        driver.quit()
        print(new_list)
        return new_list
    except Exception as e:
        driver.quit()
        raise e

