import re, requests
from selenium import webdriver
import urllib
from selenium.webdriver.chrome.options import Options
from .argument import Argument, ArgSession
from ..responses import ResponseMusic, ResponseMsg
from ..paths import PATHS

# 2021-12-12: 支持api，优化点歌
webdriver_dir = PATHS['webdriver']


class MusicSession(ArgSession):
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
                                  default_value=1,
                                  ask_text='要返回多少条结果（默认1条）',
                                  help_text='返回结果数目'),
                         Argument(key='163', alias_list=['-163'],
                                  help_text='使用网易云音乐（默认qq音乐）')
                         ]
        self.unsent_songs = []
        self._max_songs_once = 10
        self.default_arg = self.arg_list[0]
        self.this_first_time = True

    def internal_handle(self, request):
        if self.this_first_time:
            self.this_first_time = False
            try:
                num = int(self.arg_dict['num'].value)
            except ValueError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】输入条数有误')
            if self.arg_dict['163'].called:
                self.unsent_songs = search_songs_via_api_163(search_str=self.arg_dict['key'].value,
                                                             n_results=num)
            else:
                self.unsent_songs = search_songs_via_api_qq(search_str=self.arg_dict['key'].value,
                                                            n_results=num)

        # 读取本次的歌曲数
        responses = []
        if len(self.unsent_songs) == 0:
            self.deactivate()
            return ResponseMsg(f'【{self.session_type}】未找到')
        elif len(self.unsent_songs) > self._max_songs_once:
            for music in self.unsent_songs[:self._max_songs_once]:
                responses.append(ResponseMusic(**music))
            self.unsent_songs = self.unsent_songs[self._max_songs_once:]
            responses.append(ResponseMsg(f'【{self.session_type}】还有{len(self.unsent_songs)}首未发送，回复任意继续'))
        else:
            self.deactivate()
            for music in self.unsent_songs:
                responses.append(ResponseMusic(**music))
        return responses


# 爬虫版本，废弃不用
def search_songs(search_str, webdriver_dir=webdriver_dir):
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


# 2021-12-12: 直接调用api
# via https://github.com/MeetWq/mybot/blob/master/src/plugins/music/data_source.py
def search_songs_via_api_163(search_str, n_results):
    url = 'https://music.163.com/api/cloudsearch/pc'
    params = {
        's': search_str,
        'type': 1,
        'offset': 0,
        'limit': n_results
    }
    r = requests.post(url, params=params)
    new_list = []
    try:
        for song in r.json()['result']['songs']:
            new_list.append({'name': song['name'], 'link': f'https://music.163.com/song?id={song["id"]}',
                             'music_id': song['id'], 'platform': '163'})
        return new_list
    except KeyError:  # 空白未找到
        return new_list


def search_songs_via_api_qq(search_str, n_results):
    url = 'https://c.y.qq.com/soso/fcgi-bin/client_search_cp'
    params = {
        'p': 1,
        'n': n_results,
        'w': search_str,
        'format': 'json'
    }
    r = requests.get(url, params=params)

    new_list = []
    for song in r.json()['data']['song']['list']:
        new_list.append({'name': song['songname'],
                         'link': f'https://y.qq.com/n/ryqq/songDetail/{song["songid"]}',
                         'music_id': song['songid'], 'platform': 'qq'})
    return new_list

