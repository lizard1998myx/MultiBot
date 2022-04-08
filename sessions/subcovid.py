from .general import Session
from ..responses import ResponseMsg
from ..paths import PATHS
import pytz, datetime, requests, csv, os, threading, time
import pandas as pd

ACCOUNT_LIST = os.path.join(PATHS['data'], 'subcovid_account_list.csv')
COOKIE_LIST = os.path.join(PATHS['data'], 'subcovid_cookie_list.csv')
COOKIE_INFO_LIST = os.path.join(PATHS['data'], 'subcovid_cookie_list_info.csv')


class SubcovidSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 3*60
        self.session_type = '自动填报插件'
        self.strict_commands = ['疫情填报', '填报', '国科大填报']
        self.description = '登记自动疫情填报，用于定时任务，唤起本插件以查看更多'
        self.is_first_time = True
        self.is_second_time = False
        self.username = None
        self.password = None
        self.to_save = False

    def handle(self, request):
        if self.is_first_time:
            self.is_first_time = False
            self.is_second_time = True
            notes_v1 = (f"【{self.session_type}】\n"
                        f"本插件基于github上的IanSmith123/ucas-covid19项目。"
                        f"原理是使用SEP账号密码登录一次获取cookies（临时身份证明），保存cookies，"
                        f"每天凌晨5点延续前一天的填报内容自动打卡（或回复“运行”手动执行）。\n\n"
                        f"如果填报信息有变动（如离校/返校），请在凌晨12点到5点之间手动填报一次；"
                        f"若由于代码更新等原因暂停填报，会在机器人测试群内告知。\n\n"
                        f"警告：程序不主动保存账号密码，但后者会不可避免地被存到聊天记录中，"
                        f"建议部署前修改SEP密码，当然，更安全的方式是自己部署。\n\n"
                        f"请仔细阅读上述条款，若无异议，请回复“同意”")
            notes_v2 = (f"【{self.session_type}】\n"
                        f"本插件基于github上的IanSmith123/ucas-covid19项目。"
                        f"服务器凌晨5点左右自动续报，若信息变动（如离校/返校），请在凌晨12点后手动填报一次。\n\n"
                        f"注意！！！！\n"
                        f"本程序仅用于解决忘记打卡这一问题，本人不对因为滥用此程序造成的后果负责，"
                        f"请在合理且合法的范围内使用本程序。\n\n"
                        f"请仔细阅读上述条款，若无异议，请回复“同意”")
            return ResponseMsg(notes_v2)
        elif self.is_second_time:
            self.is_second_time = False
            if request.msg == '同意':
                return ResponseMsg('【%s】请输入SEP账号（邮箱）' % self.session_type)
            elif request.msg == '运行':
                self.deactivate()
                result = daily_run()
                return ResponseMsg('【%s】成功%i个，失败%i个\n%s'
                                   % (self.session_type, result['success'], result['fail'], str(result['reasons'])))
            else:
                self.deactivate()
                return ResponseMsg('【%s】填报中止' % self.session_type)
        elif self.username is None:
            self.username = request.msg
            return ResponseMsg('【%s】请输入SEP密码' % self.session_type)
        elif self.password is None:
            self.deactivate()
            self.password = request.msg
            s = requests.Session()
            try:
                cookie = login(s, self.username, self.password)
            except ValueError as e:
                # 登录失败
                return ResponseMsg('【%s】%s' % (self.session_type, e.__str__()))
            save_cookie(cookie, user_id=self.user_id)
            responses = [ResponseMsg('【%s】录入成功：%s\n请不要重复填报' % (self.session_type, str(cookie)))]
            try:
                submit(s, get_daily(s, cookie), cookie)
            except ValueError as e:
                submit_result = e.__str__()
            else:
                submit_result = '填报成功'
            responses.append(ResponseMsg('【%s】自动进行一次填报并%s' % (self.session_type, submit_result)))
            return responses


def save_account(user, passwd):
    with open(ACCOUNT_LIST, 'a+', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['user', 'passwd'])
        writer.writerow({'user': user, 'passwd': passwd})


def save_cookie(cookie: dict, user_id=None):
    with open(COOKIE_LIST, 'a+', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=cookie.keys())
        writer.writerow(cookie)
    if user_id is not None:
        cookie['user_id'] = user_id
        with open(COOKIE_INFO_LIST, 'a+', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=cookie.keys())
            writer.writerow(cookie)


def save_list(user_list: list, filename: str):
    with open(filename, 'w', newline="") as f:
        first_time = True
        for generated_dict in user_list:
            if first_time:
                fieldnames = generated_dict.keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                first_time = False
            writer.writerow(generated_dict)


def read_account_list(filename=ACCOUNT_LIST):
    user_list = []
    with open(filename) as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_list.append(row)
    return user_list


def read_cookie_list(filename=COOKIE_LIST):
    user_list = []
    with open(filename) as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_list.append({'cookie': row})
    return user_list


def login(s: requests.Session, username, password):
    payload = {
        "username": username,
        "password": password
    }
    r = s.post("https://app.ucas.ac.cn/uc/wap/login/check",
               data=payload, verify=False)

    if r.json().get('m') == "操作成功":
        return requests.utils.dict_from_cookiejar(r.cookies)
    else:
        raise ValueError('登录失败：%s' % r.json().get('m'))


def get_daily(s: requests.Session, cookie=None):
    if cookie is None:
        daily = s.get("https://app.ucas.ac.cn/ncov/api/default/daily?xgh=0&app_id=ucas")
    else:
        daily = s.get("https://app.ucas.ac.cn/ncov/api/default/daily?xgh=0&app_id=ucas", cookies=cookie)
    j = daily.json()
    d = j.get('d', None)
    if d:
        return daily.json()['d']
    else:
        raise ValueError('获取昨日信息失败')


def submit(s: requests.Session, old: dict, cookie=None):
    new_daily = {
        'realname': old['realname'],
        'number': old['number'],
        'szgj_api_info': old['szgj_api_info'],
        'szgj': old['szgj'],
        'old_sfzx': old['sfzx'],
        'sfzx': old['sfzx'],
        'szdd': old['szdd'],
        'ismoved': 0,  # 如果前一天位置变化这个值会为1，第二天仍然获取到昨天的1，而事实上位置是没变化的，所以置0
        # 'ismoved': old['ismoved'],
        'tw': old['tw'],
        'bztcyy': old['bztcyy'],
        # 'sftjwh': old['sfsfbh'],  # 2020.9.16 del
        # 'sftjhb': old['sftjhb'],  # 2020.9.16 del
        'sfcxtz': old['sfcxtz'],
        'sfyyjc': old['sfyyjc'],
        'jcjgqr': old['jcjgqr'],
        # 'sfjcwhry': old['sfjcwhry'],  # 2020.9.16 del
        # 'sfjchbry': old['sfjchbry'],  # 2020.9.16 del
        'sfjcbh': old['sfjcbh'],
        'jcbhlx': old['jcbhlx'],
        'sfcyglq': old['sfcyglq'],
        'gllx': old['gllx'],
        'sfcxzysx': old['sfcxzysx'],
        'old_szdd': old['szdd'],
        'geo_api_info': old['old_city'],  # 保持昨天的结果
        'old_city': old['old_city'],
        'geo_api_infot': old['geo_api_infot'],
        'date': datetime.datetime.now(tz=pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d"),
        'fjsj': old['fjsj'],  # 返京时间
        'ljrq': old['ljrq'],  # added
        'qwhd': old['qwhd'],  # added
        'chdfj': old['chdfj'],  # added
        'jcbhrq': old['jcbhrq'],
        'glksrq': old['glksrq'],
        'fxyy': old['fxyy'],
        'jcjg': old['jcjg'],
        'jcjgt': old['jcjgt'],
        'qksm': old['qksm'],
        'remark': old['remark'],
        'jcjgqk': old['jcjgqk'],
        'jcwhryfs': old['jcwhryfs'],
        'jchbryfs': old['jchbryfs'],
        'gtshcyjkzt': old['gtshcyjkzt'],  # add @2020.9.16
        'jrsfdgzgfxdq': old['jrsfdgzgfxdq'],  # add @2020.9.16
        'jrsflj': old['jrsflj'],  # add @2020.9.16
        'app_id': 'ucas'}
    print(old['realname'])

    if cookie is None:
        r = s.post("https://app.ucas.ac.cn/ncov/api/default/save", data=new_daily)
    else:
        r = s.post("https://app.ucas.ac.cn/ncov/api/default/save",
                   data=new_daily, cookies=cookie)
    result = r.json()
    if result.get('m') != "操作成功":
        raise ValueError('提交失败：%s' % r.json().get("m"))


# get yesterday infos automatically
def get_info(csv_filename):
    df = pd.read_csv(csv_filename)
    new_records = []
    for cookie in df.to_dict('records'):
        s = requests.Session()
        yesterday = get_daily(s=s, cookie=cookie)
        cookie.update(yesterday)
        new_records.append(cookie)
    return new_records


def run(user=None, passwd=None, cookie=None):
    s = requests.Session()
    if cookie is None:
        login(s, user, passwd)
        yesterday = get_daily(s)
        submit(s, yesterday)
    else:
        submit(s=s, old=get_daily(s=s, cookie=cookie), cookie=cookie)


def daily_run():
    return daily_run_demo()


def daily_run_classic():
    user_list = read_cookie_list() + read_account_list()
    success = 0
    fail = 0
    reasons = []
    for user_dict in user_list:
        try:
            run(**user_dict)
            success += 1
        except ValueError as e:
            fail += 1
            reasons.append(str(e))
    return {'success': success, 'fail': fail, 'reasons': reasons}


class SubThread(threading.Thread):
    def __init__(self, user_dict):
        threading.Thread.__init__(self)
        self.user_dict = user_dict
        self.success = False
        self.unexpected_error = False
        self.fail_reason = ''

    def run(self):
        try:
            run(**self.user_dict)
            self.success = True
        except ValueError as e:
            self.fail_reason = str(e)
        except Exception as e:
            self.unexpected_error = True
            self.fail_reason = str(e)


def daily_run_demo():
    # user_list = read_cookie_list() + read_account_list()
    user_list = read_cookie_list()
    thread_list = []
    for user_dict in user_list:
        thread_list.append(SubThread(user_dict=user_dict))
        thread_list[-1].start()
    while True:
        time.sleep(0.1)
        still_alive = False
        for thread in thread_list:
            if thread.is_alive():
                still_alive = True
                break
        if still_alive:
            continue
        else:
            break
    success = 0
    fail = 0
    unexpected_error = 0
    reasons = []
    for thread in thread_list:
        if thread.unexpected_error:
            fail += 1
            unexpected_error += 1
            reasons.append(thread.fail_reason)
        elif thread.success:
            success += 1
        else:
            fail += 1
            reasons.append(thread.fail_reason)
    if unexpected_error:
        print(reasons)
        return {'success': success, 'fail': -1*fail, 'reasons': reasons}
    else:
        return {'success': success, 'fail': fail, 'reasons': reasons}
