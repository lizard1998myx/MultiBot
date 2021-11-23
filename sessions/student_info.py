import csv, datetime, difflib, os
from .general import Session
from ..responses import ResponseMsg
from ..paths import PATHS


INFO_TABLE = os.path.join(PATHS['data'], 'GNB_student_info.csv')
TOTAL_TABLE = os.path.join(PATHS['data'], 'GNB_total_info.csv')


class InfoSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self._max_delta = 2*60
        self.session_type = '学生信息搜索'
        self.strict_commands = ['搜索', '查找', 'search']
        self.description = '从数据库中搜索学生信息'
        self.permissions = {'Console': [], 'CQ': ['315887212', '378277058']}
        self.is_first_time = True

    def handle(self, request):
        if self.is_first_time:
            self.is_first_time = False
            return ResponseMsg('【%s】请输入学生姓名' % self.session_type)
        else:
            self.deactivate()
            name = request.msg
            total_list = search_name(infolist=get_total_list(), name=name)
            partial_list = search_name(infolist=get_info_list(), name=name)
            # if matched in total (1 found) but not in partial (1+ found)
            if len(partial_list) > len(total_list):
                student_list = total_list
            else:
                student_list = total_list + partial_list
            if len(student_list) == 0:
                return ResponseMsg('【%s】未找到符合条件的学生' % self.session_type)
            else:
                response_list = []
                for student in student_list:
                    student_string = ''
                    for key, value in student.items():
                        student_string += '[%s] %s\n' % (key, value)
                    response_list.append(ResponseMsg(student_string[:-1]))
                return response_list


def read_csv(filename):
    result = []
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            result.append(row)
    return result


def search_birth(info_list, birth_date_tag='出生日期', name_tag='姓名', split_symble='-', days_pre=2):
    date = datetime.date.today() + datetime.timedelta(days=days_pre)
    result_list = []
    for student in info_list:
        birth_dates = student[birth_date_tag].split(split_symble)
        if date.month == int(birth_dates[1]) and date.day == int(birth_dates[2]):
            result_list.append('%s(%2i-%2i)' % (student[name_tag], date.month, date.day))
    return result_list


def get_info_list(filename=INFO_TABLE):
    return read_csv(filename=filename)


def get_total_list(filename=TOTAL_TABLE):
    return read_csv(filename=filename)


def search_name(infolist, name: str, name_tag='姓名'):
    student_list = []
    max_sim = 0
    for student in infolist:
        sim = cal_sim(name, student[name_tag])
        if sim == 0:
            continue
        elif sim > max_sim:
            max_sim = sim
            student_list = [student]
        elif sim == max_sim:
            student_list.append(student)
    return student_list


def cal_sim(s1, s2):
    if s1 in s2 or s2 in s1:
        return 1.0
    else:
        return difflib.SequenceMatcher(None, s1, s2).quick_ratio()