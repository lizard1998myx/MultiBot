from .argument import Argument, ArgSession
from ..responses import ResponseMsg
import requests, datetime, json

COOKIE_STR = 'sepuser="123==  "; vjuid=123; vjvd=123; vt=123'
COOKIE = {'Cookie': COOKIE_STR}


def get_idendities(cookies=COOKIE):
    url_post = 'https://ehall.ucas.ac.cn/site/data-source/detail'
    url_get1 = 'https://ehall.ucas.ac.cn/site/user/get-identitys?agent_uid=&starter_depart_id=68859&test_uid=0'
    url_get2 = 'https://ehall.ucas.ac.cn/site/form/start-data?app_id=740&node_id=&userview=1'
    headers = {'Content-Type': 'application/x-www-form-urlencoded',
               'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36',
               'X-Requested-With': 'XMLHttpRequest'}
    r10a_data = {'id': 10, 'inst_id': 0, 'app_id': 740,
                 'params[change]': '{"170":{"type":"one"}}',
                 'starter_depart_id': 68859, 'test_uid': 0}
    r10b_data = {'id': 10, 'inst_id': 0, 'app_id': 740,
                 'params[change]': '{"171":{"type":"one","date":{"rxsj":"Y"}}}',
                 'starter_depart_id': 68859, 'test_uid': 0}
    r59a_data = {'id': 59, 'inst_id': 0, 'app_id': 740,
                 'params[change]': '{"171":{"type":"one","date":{"rxsj":"Y"}}}',
                 'starter_depart_id': 68859, 'test_uid': 0}

    r10a = requests.post(url=url_post, data=r10a_data, headers=headers, cookies=cookies, verify=False)
    r10b = requests.post(url=url_post, data=r10b_data, headers=headers, cookies=cookies, verify=False)
    r59a = requests.post(url=url_post, data=r59a_data, headers=headers, cookies=cookies, verify=False)
    rget1 = requests.get(url=url_get1, headers=headers, cookies=cookies, verify=False)
    rget2 = requests.get(url=url_get2, headers=headers, cookies=cookies, verify=False)

    results = {'r10a': r10a, 'r10b': r10b, 'r59a': r59a, 'rget1': rget1, 'rget2': rget2}

    # r10a results
    results.update({'英文名': r10a.json()['d']['list']['170ywm'],
                    '手机号': r10a.json()['d']['list']['170lxdh'],
                    '身份证号': r10a.json()['d']['list']['170zjhm'],
                    '电子邮箱': r10a.json()['d']['list']['170dzyx'],})
    # r10b results
    results.update({'培养单位': r10b.json()['d']['list']['171pydw'],
                    '培养层次': r10b.json()['d']['list']['171pycc'],
                    '攻读专业': r10b.json()['d']['list']['171gdzy']})
    # r59a results
    results.update({'培养单位代码': r59a.json()['d']['list']['dept_sn'],
                    '班级': r59a.json()['d']['list']['class']})
    # rget1 results (for multiple student numbers)
    # results.update({'学号': rget1.json()['d'][0]['number']})
    # rget2 results
    results.update({'姓名': rget2.json()['d']['data']['1533']['User_18'],
                    '学号': rget2.json()['d']['data']['1533']['User_19'],
                    '性别': rget2.json()['d']['data']['1533']['User_20']})

    form1533 = rget2.json()['d']['data']['1533']
    """{'User_18': 'xxname', 'User_19': '2020280025xxxxxxxx', 
    'User_20': '男', 'User_27': '188xxxx0000', 'User_56': 'xxname',
     'Calendar_28': '', 'Calendar_29': '', 
     'Calendar_30': '2021-08-02T19:45:51+08:00', 'Calendar_57': '2021-08-02T19:45:51+08:00'}"""
    form1533.update({'Input_21': r59a.json()['d']['list']['dept_sn'],  # 培养单位代码
                     'Input_22': r10b.json()['d']['list']['171pydw'],  # 培养单位
                     'Input_23': r10b.json()['d']['list']['171gdzy'],  # 攻读专业
                     'Input_25': r59a.json()['d']['list']['class'],    # 班级
                     'Input_61': r10b.json()['d']['list']['171pycc']   # 培养层次
                     })

    results['form1533'] = form1533
    return results


def sub_sik(cookies=COOKIE, form=None, delta_days=1):
    url = 'https://ehall.ucas.ac.cn/site/apps/launch'
    headers = {'Content-Type': 'application/x-www-form-urlencoded',
               'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36',
               'X-Requested-With': 'XMLHttpRequest'}
    if form is None:
        form = get_idendities(cookies=cookies)['form1533']
    target_date = datetime.date.today() + datetime.timedelta(days=delta_days-1)  # 时区修正
    form.update({"Radio_31": {"value": "1", "name": "是yes"},  # 回所科研
                 "Radio_32": {"value": "2", "name": "否no"},  # 其他行程
                 "Radio_71": {"name": "是yes", "value": "1"},
                 "Radio_81": {"value": "2", "name": "否no"},  # 是否离京
                 "Calendar_28": f"{target_date.isoformat()}T16:00:00.000Z",
                 "Calendar_29": f"{target_date.isoformat()}T16:00:00.000Z",
                 "SelectV2_62": [{"value": 3, "name": "3"}],  # 临时类别
                 "ShowHide_58": "",
                 "ShowHide_64": "",
                 "ShowHide_72": "",
                 "Validate_77": "",
                 "DataSource_63": "",
                 "DataSource_66": "",
                 "DataSource_67": "",
                 "RepeatTable_33": [{"Input_69": "", "Input_41": "",
                                     "Input_42": "", "Calendar_43": 'null',
                                     "Calendar_44": 'null', "Input_45": ""}]})

    data_string = json.dumps({"app_id": "740", "node_id": "", "form_data": {"1533": form}, "userview": 1})
    data = {'data': data_string, 'starter_depart_id': 68859, 'test_uid': 0}

    return requests.post(url=url, data=data, headers=headers, cookies=cookies, verify=False)


class SubucassikSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 30
        self.session_type = '自动申报插件'
        self.strict_commands = ['sik', '申报', '行程']
        self.description = '登记自动行程申报，感谢zyk师兄提供的代码指导'
        agreement_text = ("\n正式版SIK行程自动申报，出现报错请联系开发者（回复“更多”获取联系方式），" 
                          "特别感谢zyk师兄提供的代码指导。" 
                          "退出本插件并发送“申报图示”获取图片说明。\n" 
                          "【警告】\n" 
                          "本插件原理是使用爬虫登录国科大办事大厅，后台可以获取到身份证号、联系方式等敏感信息。" 
                          "开发者承诺该版本插件所使用信息为一次性，不保存cookie，不主动获取保存其他个人信息。\n" 
                          "【半自动操作流程（推荐）】\n"
                          f"无视后续所有流程直到插件报错或等待{self._max_delta}秒，"
                          "回复“sep”或“ehall”直接登录并获取cookie，再进入本插件进行申报。\n" 
                          "【纯手动操作流程（电脑浏览器）】\n" 
                          "1. 打开新标签页，按F12进入开发者模式，选择上方network选项卡；\n" 
                          "2. 进入https://ehall.ucas.ac.cn/，若自动登录则进入下一步，" 
                          "若需要登录，请登录完毕后重新进行上一步；\n" 
                          "3. 查看名为index（列表最上方）的条目，" 
                          "与“General”、“Response Headers”等并列的应该还有“Request Headers”；\n" 
                          "4. 在“Resquest Headers”一项中，有一条“Cookie”，" 
                          "是内容类似于“sepuser=\"aBcDeF== \"; vjuid=123; vjvd=123ab; vt=123”的字符串，复制它即可。\n" 
                          "【下一步】\n" 
                          "完成以上内容后，呼叫本插件，确认仔细阅读上述条款且无异议，回复任意消息进入下一步。")
        self.arg_list = [Argument(key='agree', alias_list=['-y', '-a'],
                                  required=True,
                                  ask_text=agreement_text),
                         Argument(key='cookie', alias_list=['-c'],
                                  required=True, get_next=True,
                                  ask_text='请输入cookie字符串'
                                           '（形如：“sepuser="aBcDeF==  "; vjuid=123; vjvd=123ab; vt=123”）'),
                         Argument(key='initial', alias_list=['-i'],
                                  required=True, get_next=True,
                                  ask_text='起始天数（距离今天）'),
                         Argument(key='final', alias_list=['-f'],
                                  required=True, get_next=True,
                                  ask_text='结束天数（距离今天）'),
                         Argument(key='print_identities', alias_list=['-p'],
                                  help_text='返回身份信息，用于检验')
                         ]
        self.is_first_time = True
        self.is_second_time = False
        self.cookies = None
        self._identities = None
        self.delta_start = None
        self.delta_end = None
        self.detail_description = '举例，发送“sik -y -i 0 -f 100”，然后回复cookie字符串，' \
                                  '自动登录并申报今天起100天内的出校。增加“-p”参数会打印身份信息。'

    def internal_handle(self, request):
        self.deactivate()
        results = []
        cookies = {'Cookie': self.arg_dict['cookie'].value}
        self._identities = get_idendities(cookies=cookies)
        if self.arg_dict['print_identities'].called:
            results.append(ResponseMsg(f'【{self.session_type}】登录获取个人信息如下：\n{self._identities}'))
        delta_i = int(self.arg_dict['initial'].value)
        delta_f = int(self.arg_dict['final'].value)
        date_i = datetime.date.today() + datetime.timedelta(days=delta_i)
        date_f = datetime.date.today() + datetime.timedelta(days=delta_f)
        msg = {}
        for delta in range(delta_i, delta_f + 1):
            resp = sub_sik(cookies=cookies,
                           form=self._identities['form1533'], delta_days=delta)
            if resp.json().get('e') != 0:  # fail
                msg[delta] = resp.text
        res_msg = f'【{self.session_type}】填报完毕。\n' \
                  f'日期{date_i.isoformat()}至{date_f.isoformat()}\n'
        if len(msg) == 0:
            res_msg += '全部成功。'
        else:
            res_msg += f'有{len(msg)}个填报失败，信息：\n{msg}'
        results.append(ResponseMsg(res_msg))
        return results

