from .general import Session
from ..responses import ResponseMsg
from .argument import Argument, ArgSession
from ..paths import PATHS
import pytz, datetime, requests, csv, os, threading, time
import pandas as pd

ACCOUNT_LIST = os.path.join(PATHS['data'], 'subcovid_account_list.csv')
COOKIE_LIST = os.path.join(PATHS['data'], 'subcovid_cookie_list.csv')
COOKIE_INFO_LIST = os.path.join(PATHS['data'], 'subcovid_cookie_list_info.csv')


# 2022-04-11 Manual SubCovid
class SubcovidManualSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 3*60
        self.session_type = '手动填报插件'
        self.strict_commands = ['手动填报']
        self.description = '通过cookie手动进行疫情填报，配合订阅进行定时任务'
        self.arg_list = [Argument(key='uukey', alias_list=['-u'],
                                  required=True, get_next=True,
                                  help_text='cookie的UUkey参数'),  # 实际发现是小写
                         Argument(key='eai-sess', alias_list=['-e'],
                                  required=True, get_next=True,
                                  help_text='cookie的eai-sess参数')
                         ]
        self.detail_description = '使用SubcovidSession获取cookies，配合订阅功能使用'

    def internal_handle(self, request):
        self.deactivate()
        cookie = {'UUkey': self.arg_dict['uukey'].value,  # UUKey或UUkey应该都可以
                  'eai-sess': self.arg_dict['eai-sess'].value}

        s = requests.Session()
        try:
            yesterday = get_daily(s=s, cookie=cookie)
        except ValueError:
            return ResponseMsg(f'【{self.session_type}】获取昨日失败。')

        if yesterday['szdd'] != "国内":
            return ResponseMsg(f'【{self.session_type}】获取昨日信息中：所在地点不是国内，请手动填报。')

        # 体温
        if int(yesterday['tw']) > 4:
            return ResponseMsg(f'【{self.session_type}】获取昨日信息中：体温大于 37.3 度，请手动填报。')

        if yesterday['jrsflj'] == '是':
            return ResponseMsg(f'【{self.session_type}】获取昨日信息中：近日有离京经历，请手动填报。')

        try:
            submit(s=s, old=yesterday, cookie=cookie)
        except ValueError as e:
            return ResponseMsg(f'【{self.session_type}】{str(e)}')
        else:
            return ResponseMsg(f'【{self.session_type}】{yesterday["realname"]}填报成功。')


# Auto SubCovid
class SubcovidSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 3*60
        self.session_type = '自动填报插件'
        self.strict_commands = ['疫情填报', '填报', '国科大填报']
        self.description = '国科大疫情填报辅助，基于github.com/IanSmith123/ucas-covid19'
        self.is_first_time = True
        self.is_second_time = False
        self.username = None
        self.password = None
        self.to_save = False
        self.cookie = None

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
                        f"基于github项目IanSmith123/ucas-covid19的自动填报插件。\n\n"
                        f"使用方法（登录成功后选择）：\n"
                        f"1）订阅：获取cookie生成手动填报指令，可改时间、随时取消，每日汇报填报情况；\n"
                        f"2）录入：登记信息并由服务器凌晨4时左右自动填报，需联系管理取消，不汇报情况；\n"
                        f"3）填报一次或仅返回获取的cookie。\n\n"
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
            self.password = request.msg
            # 尝试登录
            s = requests.Session()
            try:
                self.cookie = login(s, self.username, self.password)
                return ResponseMsg(f'【{self.session_type}】获取cookie成功，'
                                   f'回复“订阅”以自动订阅（建议使用，可随时取消订阅），'
                                   f'或回复“录入”将信息记入表格凌晨自动填报（适用非QQ平台），'
                                   f'或回复“填报”进行一次手动填报，'
                                   f'回复其他则不进行仍和操作。')
            except ValueError as e:
                # 登录失败
                self.deactivate()
                return ResponseMsg('【%s】%s' % (self.session_type, e.__str__()))
        else:
            self.deactivate()
            submit_command = f'手动填报'
            for k, v in self.cookie.items():
                submit_command += f' --{k.lower()} {v}'  # 转为小写防止出错
            if request.msg == '订阅':
                return [ResponseMsg(f'【{self.session_type}】订阅中...\n"{submit_command}"\n'
                                    f'建议定时任务时间设定在早上7~9点（如回复8.5表示每天08:30填报），'
                                    f'订阅功能需要加好友后才能收取消息，'
                                    f'之后发送“取消订阅”可删除对应定时任务。'),
                        request.new(msg=f'订阅 -msg "{submit_command}"')]
            elif request.msg == '录入':
                save_cookie(self.cookie, user_id=self.user_id)
                return ResponseMsg(f'【{self.session_type}】录入成功：{self.cookie}\n'
                                   f'请不要重复填报')
            elif request.msg == '填报':
                return [ResponseMsg(f'【{self.session_type}】填报中...'),
                        request.new(msg=submit_command)]
            else:
                return ResponseMsg(f'【{self.session_type}】不进行任何操作，您的cookie是：\n{self.cookie}')


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
