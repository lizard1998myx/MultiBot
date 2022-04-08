from .argument import ArgSession, Argument
from ..responses import ResponseMsg
from ..paths import PATHS
import os, pickle, datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException


CACHE_DIR = PATHS['cache']
webdriver_dir = PATHS['webdriver']


class CovidRiskSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 3*60
        self.session_type = '疫情风险区域查询'
        self.strict_commands = ['risk', 'region', '风险', '区域']
        self.description = '查找全国疫情中高风险区域'
        self.arg_list = [Argument(key='region', alias_list=['-r'],
                                  required=True, get_next=True,
                                  ask_text='要查找的区域（省市级别）'),
                         Argument(key='no-cache', alias_list=['-nc'],
                                  help_text='不启用缓存，需要搜索更长时间')
                         ]
        self.default_arg = self.arg_list[0]
        self.newser = CovidNews()
        self.detail_description = '举例，发送“risk -r 福建”，查找福建的中高风险区。'

    def internal_handle(self, request):
        self.deactivate()
        if self.arg_dict['no-cache'].called or not self.newser.load_cache():
            self.newser.load()
        region_keyword = self.arg_dict["region"].value.replace('中国', '').replace('全国', '')
        msg = self.newser.get_region(region_keyword=region_keyword)
        if msg:
            return ResponseMsg(f'【{self.session_type}】\n{msg}')
        else:  # empty
            return ResponseMsg(f'【{self.session_type}】未找到该地区风险区数据。')


class CovidRiskUpdateSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 30
        self.session_type = '更新疫情风险区域缓存'
        self.strict_commands = ['风险区域缓存']
        self.description = '手动进行疫情风险区域缓存更新'
        self.arg_list = [Argument(key='confirm', alias_list=['-y'],
                                  required=True,
                                  ask_text='查询时间较长，任意回复以开始查询')]

    def internal_handle(self, request):
        self.deactivate()
        covid_region_cache_update()
        return ResponseMsg(f'【{self.session_type}】done')


class CovidNews:
    def __init__(self):
        self.webdriver_dir = webdriver_dir
        self.region_book = {}
        self.cache_header = 'covid-region'
        self.cache_dir = CACHE_DIR

    def save_cache(self):
        print(self.region_book)
        with open(os.path.join(CACHE_DIR,
                               f'{self.cache_header}_{datetime.date.today().isoformat()}'),
                  'wb') as f:
            pickle.dump(self.region_book, f)

    def load_cache(self):
        cache_file_list = []
        for filename in os.listdir(self.cache_dir):
            if filename[:len(self.cache_header)] == self.cache_header:
                cache_file_list.append(filename)
        cache_file_list.sort(reverse=True)  # new ones in the front
        if cache_file_list:
            with open(os.path.join(self.cache_dir, cache_file_list[0]), 'rb') as f:
                self.region_book = pickle.load(f)
            return True
        else:
            return False

    def load(self):
        url = 'http://bmfw.www.gov.cn/yqfxdjcx/risk.html'
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=self.webdriver_dir)
        try:
            driver.get(url)
            # 防止元素被遮挡
            driver.set_window_size(1920, 1080)

            def update_book(level='h'):
                for e in driver.find_elements_by_xpath(f'//table[@class="{level}-table"]/..'):
                    l = e.text.split('\n')
                    if l[0] in self.region_book.keys():
                        self.region_book[l[0]] += l[1:]
                    else:
                        self.region_book[l[0]] = l[1:]

            for level in ['h', 'm']:
                while driver.find_element_by_xpath(f'//div[@class="{level}-content"]//div[@class="pages-box"]'
                                                   f'/button[@id="nextPage"]').is_enabled():
                    update_book(level=level)
                    max_attempts = 2
                    attempts = 0
                    driver.implicitly_wait(time_to_wait=0.1)
                    while attempts < max_attempts:
                        attempts += 1
                        try:
                            driver.find_element_by_xpath(f'//div[@class="{level}-content"]//div[@class="pages-box"]'
                                                         f'/button[@id="nextPage"]').click()
                            break
                        except StaleElementReferenceException as e:
                            if attempts < max_attempts:
                                driver.implicitly_wait(time_to_wait=0.1)
                            else:
                                raise e
                update_book(level=level)
                if level == 'h':
                    driver.find_element_by_xpath('//div[@class="r-middle"]').click()
            driver.quit()
        except Exception as e:
            driver.quit()
            raise e

    def get_region(self, region_keyword):
        msg = ''
        for key in self.region_book:
            if region_keyword in key:
                msg += f'[{key}]\n'
                for i, area in enumerate(self.region_book[key]):
                    msg += f'{i+1}. {area}\n'
        return msg[:-1]


def covid_region_cache_update():
    cns = CovidNews()
    cns.load()
    cns.save_cache()