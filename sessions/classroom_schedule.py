from MultiBot.sessions.argument import ArgSession, Argument
from MultiBot.responses import ResponseMsg
import requests, datetime, bs4


class ClassroomScheduleSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 30
        self.session_type = '教室查询'
        self.extend_commands = ['schedule', '教室']
        self.description = '通过爬虫程序查询空闲教室（由于校园网后台更新，目前脚本已失效）'
        self.arg_list = [Argument(key='date', alias_list=['-d', '-day'],
                                  required=True, get_next=True,
                                  ask_text='日期（yyyy-mm-dd）',
                                  help_text='查询教室的日期，默认是今天，或用整数表示天数之差'),
                         Argument(key='building', alias_list=['-b'],
                                  required=False, get_next=True,
                                  help_text='查询某个楼的教室，默认是教一楼',
                                  default_value='教一楼')]
        self.default_arg = self.arg_list[0]

    def internal_handle(self, request):
        translations = {'今天': 0, '明天': 1, '后天': 2, '大后天': 3, '昨天': -1}
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
        s_finder = ScheduleFinder(target=target)
        s_finder.get_schedule_list()
        self.deactivate()
        return ResponseMsg(f"【{self.session_type}】\n"
                           f"{s_finder.report(self.arg_dict['building'].value)}")


class ScheduleFinder:
    def __init__(self, target=datetime.date.today()):
        self.target_date = target
        self.first_day = datetime.date(2021, 3, 8)
        self.term_id = '64758'  # Spring semester 2021
        self.campus_id = '3'  # Yanqi Lake Campus
        self.calender = self._get_calender()
        self.schedule_list = []

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

    def _get_tag_list(self):
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
                     'weekday_name': self.calender['weekday_name'], 'yq': self.campus_id},
                    headers=second_headers, allow_redirects=False)
        r1.encoding = r1.apparent_encoding
        soup = bs4.BeautifulSoup(r1.text, 'html.parser')

        tag = soup.find('tr', {'bgcolor': '#EDD1F8'})
        tag_list = []
        for t in tag.nextSiblingGenerator():
            if not isinstance(t, str):  # empty row
                tag_list.append(t)
        return tag_list

    def get_schedule_list(self, tag_list=None):
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
        if not self.schedule_list:
            url = 'http://jwjz.ucas.ac.cn/jiaowu/classroom/allclassroomforquery0.asp?term=%s' % self.term_id
            return '空闲教室未找到\n[%s]\n请手动前往：%s' % (self.calender['description'], url)

        morning_list = []
        afternoon_list = []
        evening_list = []
        allday_list = []
        for schedule in self.schedule_list:
            if building not in schedule['classroom']:
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

        return '%s的空闲教室\n[%s]\n上午：%s\n下午：%s\n晚上：%s\n全天：%s' \
               % (building, self.calender['description'],
                  self._to_string(morning_list), self._to_string(afternoon_list),
                  self._to_string(evening_list), self._to_string(allday_list))

    @staticmethod
    def _to_string(s_list):
        result = ''
        for s in s_list:
            result += '%s, ' % s
        return result[:-2]
