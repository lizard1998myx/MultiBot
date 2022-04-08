from .argument import ArgSession, Argument
from ..responses import ResponseMsg
from ..paths import PATHS
import requests, datetime, bs4, os, pickle
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


CACHE_DIR = PATHS['cache']
webdriver_dir = PATHS['webdriver']


class ClassroomScheduleSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 30
        self.session_type = '教室查询'
        self.extend_commands = ['schedule', '教室']
        self.description = '通过爬虫程序查询空闲教室'
        self.arg_list = [Argument(key='date', alias_list=['-d', '-day'],
                                  required=True, get_next=True,
                                  ask_text='日期（yyyy-mm-dd），注意月和日都是两位数，需补0',
                                  help_text='查询教室的日期（yyyy-mm-dd格式），默认是今天；'
                                            '也可用整数表示天数之差（如0表示今天，7表示7天后）'),
                         Argument(key='building', alias_list=['-b'],
                                  required=False, get_next=True,
                                  help_text='查询某个楼的教室，默认是教一楼，发送“全部”、“-”关闭筛选，输出所有教室结果',
                                  default_value='教一楼'),
                         Argument(key='campus', alias_list=['-c'],
                                  required=False, get_next=True,
                                  help_text='查询的校区，默认是雁栖湖，也支持玉泉路和中关村',
                                  default_value='雁栖湖'),
                         Argument(key='confirm', alias_list=['-y'],
                                  required=True, get_next=False,
                                  ask_text='由于学校服务器带宽限制，实时查询需要等待一分钟左右，任意回复以开始查询'),
                         Argument(key='no-cache', alias_list=['-nc'],
                                  required=False, get_next=False,
                                  help_text='不启用缓存功能，实时查询教室，能保证信息为最新，'
                                            '但由于学校服务器带宽限制，需要等待一分钟左右')]
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        translations = {'今天': 0, '明天': 1, '后天': 2, '大后天': 3, '昨天': -1}

        # set campus
        campus_value = self.arg_dict['campus'].value.replace('校区', '')
        if campus_value == '玉泉路':
            campus_id = 1
        elif campus_value == '中关村':
            campus_id = 2
        elif campus_value == '雁栖湖':
            campus_id = 3
        else:
            self.deactivate()
            return ResponseMsg(f"【{self.session_type}】仅支持玉泉路、中关村和雁栖湖校区")

        # set date
        msg = self.arg_dict['date'].value
        if msg in translations.keys():
            n_delta = translations[msg]
        else:
            try:
                n_delta = int(msg)
            except ValueError:
                n_delta = 0
        try:
            target = datetime.date.fromisoformat(msg)
        except ValueError:
            target = datetime.date.today() + datetime.timedelta(days=n_delta)

        # initialize
        s_finder = ScheduleFinder(target=target, campus_id=campus_id,
                                  enable_cache=not self.arg_dict['no-cache'].called)
        s_finder.get_schedule_list()
        self.deactivate()
        return ResponseMsg(f"【{self.session_type}】\n"
                           f"{s_finder.report(self.arg_dict['building'].value)}")


class ClassroomScheduleUpdateSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 30
        self.session_type = '更新教室查询缓存'
        self.strict_commands = ['更新缓存']
        self.description = '手动进行教室查询缓存更新'
        self.arg_list = [Argument(key='day_start', alias_list=['-i'],
                                  required=False, get_next=True,
                                  help_text='起始天数',
                                  default_value='0'),
                         Argument(key='day_finish', alias_list=['-f'],
                                  required=False, get_next=True,
                                  help_text='结束天数',
                                  default_value='3'),
                         Argument(key='confirm', alias_list=['-y'],
                                  required=True,
                                  ask_text='由于学校服务器带宽限制，查询时间较长，任意回复以开始查询')]

    def internal_handle(self, request):
        self.deactivate()
        classroom_cache_update(day_start=int(self.arg_dict['day_start'].value),
                               day_finish=int(self.arg_dict['day_finish'].value))
        return ResponseMsg(f'【{self.session_type}】done')


class ScheduleFinder:
    def __init__(self, target=datetime.date.today(), campus_id=3, enable_cache=True):
        self.target_date = target
        # self.term_id = '67862'  # Fall semester 2021
        # self.first_day = datetime.date(2021, 8, 30)
        self.term_id = '67863'  # Spring semester 2022
        self.first_day = datetime.date(2022, 2, 21)
        self.campus_id = campus_id  # Yanqi Lake=3, Yuquan Road=1, Zhongguan Village=2
        self.calender = self._get_calender()
        self.schedule_list = []
        self.enable_cache = enable_cache
        self.cache_dir = CACHE_DIR
        self.webdriver_dir = webdriver_dir

    def _get_calender(self):
        delta = (self.target_date - self.first_day).days
        n_week = delta // 7 + 1
        n_weekday = delta % 7
        weekdays = {0: '001', 1: '010', 2: '011', 3: '100', 4: '101', 5: '110', 6: '111'}  # Monday to Sunday
        weekdays_description = {0: '星期一', 1: '星期二', 2: '星期三', 3: '星期四',
                                4: '星期五', 5: '星期六', 6: '星期天'}
        return {'weekname': str(n_week), 'weekday_name': weekdays[n_weekday],
                'description': '%s 第%i周%s' % (
                self.target_date.isoformat(), n_week, weekdays_description[n_weekday])}

    @staticmethod
    def _get_schedule(schedule_tag):
        grid_list = []
        for t in schedule_tag.childGenerator():
            if not isinstance(t, str):
                grid_list.append(t)
        # get name of classroom
        classroom_name = grid_list[0].text
        # get course schedule
        course_list = []
        for grid_tag in grid_list[1:]:
            if grid_tag.img is None:  # empty
                course_list.append(None)
            else:
                course_list.append(grid_tag.img.attrs['title'])
        # find empty time
        morning, afternoon, evening = True, True, True
        for i in range(12):
            if course_list[i] is not None:
                if i < 4:
                    morning = False
                elif i < 8:
                    afternoon = False
                else:
                    evening = False
        return {'classroom': classroom_name, 'course_list': course_list,
                'morning': morning, 'afternoon': afternoon, 'evening': evening}

    def _get_soup_with_requests(self):
        # not functional, abandoned
        s = requests.Session()

        first_headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                         'Accept-Encoding': 'gzip, deflate', 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,ja;q=0.6',
                         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36',
                         'Connection': 'keep-alive', 'Host': 'jwjz.ucas.ac.cn', 'Pragma': 'no-cache',
                         'Cache-Control': 'no-cache', 'Upgrade-Insecure-Requests': '1'}

        second_headers = {'Host': 'jwjz.ucas.ac.cn',
                          'Connection': 'keep-alive',
                          'Content-Length': '64',
                          'Pragma': 'no-cache',
                          'Cache-Control': 'no-cache',
                          'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
                          'sec-ch-ua-mobile': '?0',
                          'Upgrade-Insecure-Requests': '1',
                          'Origin': 'https://jwjz.ucas.ac.cn',
                          'Content-Type': 'application/x-www-form-urlencoded',
                          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36',
                          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                          'Sec-Fetch-Site': 'same-origin',
                          'Sec-Fetch-Mode': 'navigate',
                          'Sec-Fetch-User': '?1',
                          'Sec-Fetch-Dest': 'document',
                          'Referer': 'https://jwjz.ucas.ac.cn/jiaowu/classroom/allclassroomforquery.asp',
                          'Accept-Encoding': 'gzip, deflate, br',
                          'Accept-Language': 'zh-CN,zh;q=0.9'}  # 'Cookie': 'ASPSESSIONIDSQDABCTS=JFAAMDMALJCOEHOOMIGKGEMO'}

        # payload = {'weekname': '8', 'weekday_name': '101', 'classroom': '', 'yq': '3', 'Submit': '%B2%E9+%D1%AF'}

        r0 = s.get('http://jwjz.ucas.ac.cn/jiaowu/classroom/allclassroomforquery0.asp?term=%s' % self.term_id,
                   headers=first_headers)  # verify
        # second_headers['Cookie'] = '%s=%s' % (s.cookies.keys()[0], s.cookies.values()[0])
        r1 = s.post('http://jwjz.ucas.ac.cn/jiaowu/classroom/allclassroomforquery.asp',
                    {'weekname': self.calender['weekname'],
                     'weekday_name': self.calender['weekday_name'], 'yq': f'{self.campus_id}'},
                    headers=second_headers, allow_redirects=False)
        r1.encoding = r1.apparent_encoding
        return bs4.BeautifulSoup(r1.text, 'html.parser')

    def _get_soup_with_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=self.webdriver_dir)
        try:
            url = f'http://jwjz.ucas.ac.cn/jiaowu/classroom/allclassroomforquery0.asp?term={self.term_id}'
            driver.get(url=url)
            driver.find_element_by_xpath(f'//input[@name="yq" '
                                         f'and @value="{self.campus_id}"]').click()
            driver.find_element_by_xpath(f'//input[@name="weekname" '
                                         f'and @value="{self.calender["weekname"]}"]').click()
            driver.find_element_by_xpath(f'//input[@name="weekday_name" '
                                         f'and @value="{self.calender["weekday_name"]}"]').click()
            driver.find_element_by_xpath('//input[@name="Submit"]').click()
            soup = bs4.BeautifulSoup(driver.page_source, 'html.parser')
        except Exception as e:
            driver.quit()
            raise e
        else:
            driver.quit()
        return soup

    def _get_tag_list(self):
        soup = self._get_soup_with_selenium()

        tag = soup.find('tr', {'bgcolor': '#EDD1F8'})
        tag_list = []
        for t in tag.nextSiblingGenerator():
            if not isinstance(t, str):  # empty row
                tag_list.append(t)
        return tag_list

    def get_schedule_list(self, tag_list=None):
        # read cache
        if self.enable_cache:
            cache_file_list = []
            for filename in os.listdir(self.cache_dir):
                if filename[:10] == 'classroom_':
                    cache_file_list.append(filename)
            cache_file_list.sort(reverse=True)  # new_ones_in_the_front
            for filename in cache_file_list:
                with open(os.path.join(self.cache_dir, filename), 'rb') as f:
                    results = pickle.load(f)
                    for r in results:
                        if r['target_date'] == self.target_date:
                            if r['campus_id'] == self.campus_id:
                                self.schedule_list = r['schedule_list']
                                return

        if tag_list is None:
            try:
                tag_list = self._get_tag_list()
            except BaseException:
                tag_list = []
        schedule_list = []
        for row_tag in tag_list:
            schedule_list.append(self._get_schedule(row_tag))
        self.schedule_list = schedule_list

    def report(self, building='教一楼'):
        if building in ['楼', '全部', 'all', '-']:
            building = ''
        if not self.schedule_list:
            url = 'http://jwjz.ucas.ac.cn/jiaowu/classroom/allclassroomforquery0.asp?term=%s' % self.term_id
            return '空闲教室未找到\n[%s]\n请手动前往：%s' % (self.calender['description'], url)

        morning_list = []
        afternoon_list = []
        evening_list = []
        allday_list = []
        for schedule in self.schedule_list:
            filtered = False
            filters = ['不排课', '室', '房', '运动场', '厅', '礼堂']
            if building not in schedule['classroom']:
                filtered = True
            for f in filters:
                if f in schedule['classroom']:
                    filtered = True
            if filtered:
                continue

            classroom_name = schedule['classroom'].replace(building, '')
            if schedule['morning']:
                morning_list.append(classroom_name)
            if schedule['afternoon']:
                afternoon_list.append(classroom_name)
            if schedule['evening']:
                evening_list.append(classroom_name)
            if schedule['morning'] and schedule['afternoon'] and schedule['evening']:
                allday_list.append(classroom_name)

        return '[%s]的空闲教室\n[%s]\n[上午]：%s\n[下午]：%s\n[晚上]：%s\n[全天]：%s' \
               % (building, self.calender['description'],
                  self._to_string(morning_list), self._to_string(afternoon_list),
                  self._to_string(evening_list), self._to_string(allday_list))

    @staticmethod
    def _to_string(s_list):
        result = ''
        for s in s_list:
            result += '%s, ' % s
        return result[:-2]


def classroom_cache_update(day_start=0, day_finish=2):
    results = []
    for day_delta in range(day_start, day_finish+1):
        target = datetime.date.today() + datetime.timedelta(days=day_delta)
        for campus_id in range(1, 4):
            s_finder = ScheduleFinder(target=target, campus_id=campus_id, enable_cache=False)
            s_finder.get_schedule_list()
            results.append({'target_date': target, 'campus_id': campus_id, 'schedule_list': s_finder.schedule_list})
    assert len(results) > 0, 'empty results error'
    with open(os.path.join(CACHE_DIR,
                           f'classroom_{datetime.date.today().isoformat()}_+{day_start}-{day_finish}'),
              'wb') as f:
        pickle.dump(results, f)

