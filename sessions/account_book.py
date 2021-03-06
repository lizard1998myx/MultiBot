from .argument import ArgSession
from ..responses import ResponseMsg, ResponseImg
from ..paths import PATHS
from ..utils import image_filename
from ..permissions import get_permissions
from ..external.record_table import RecordTable, RecordNotFoundError
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime, os

ACCOUNT_DIR = os.path.join(PATHS['data'], 'accounts')
if os.path.exists(ACCOUNT_DIR):
    assert os.path.isdir(ACCOUNT_DIR), 'data目录下accounts文件发生冲突'
else:
    os.makedirs(ACCOUNT_DIR)


class AccountUpdateSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '记账'
        self.description = '添加记账条目'
        self._max_delta = 60
        self.strict_commands = ['记账', '账本']
        self.add_arg(key='book', alias_list=['-bk', '-b'],
                     required=False, get_next=True,
                     default_value=user_id,
                     help_text='最高一级，账本名称（默认QQ号）',
                     ask_text='账本名称是？')
        self.add_arg(key='user_tag', alias_list=['-user', '-u'],
                     required=False, get_next=True,
                     default_value='-',
                     help_text='本条记录用户标记')
        self.add_arg(key='category', alias_list=['-cat'],
                     required=False, get_next=True,
                     default_value='默认支出类型',
                     help_text='记录类型')
        self.add_arg(key='content', alias_list=['-c'],
                     required=True, get_next=True,
                     help_text='交易内容',
                     ask_text='交易的内容是？')
        self.add_arg(key='place', alias_list=['-p'],
                     required=False, get_next=True,
                     default_value='-',
                     help_text='交易地点或网购平台')
        self.add_arg(key='amount', alias_list=['-a'],
                     required=True, get_next=True,
                     help_text='交易金额（默认为支出，开头加上“+”表示收入）',
                     ask_text='交易的金额是？（默认为支出）')
        self.add_arg(key='note', alias_list=['-n'],
                     required=False, get_next=True,
                     default_value='-',
                     help_text='备注')
        self.default_arg = self.arg_list[3]  # content
        self.detail_description = '例如，发送“记账 -b my -cat 吃 -c 午饭 -p 食堂 -a 20”，' \
                                  '自动在账本“my”记录在食堂吃午饭花了20块钱。'

    def prior_handle_test(self, request):
        if request.platform != 'CQ':
            self.arg_dict['book'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        self.deactivate()

        try:
            amount = self.arg_dict['amount'].value
            if amount[0] not in ['+', '-']:
                amount = '-' + amount
            self.arg_dict['amount'].value = float(amount)
        except IndexError:
            return ResponseMsg(f'【{self.session_type}】失败：请输入金额')
        except ValueError:
            return ResponseMsg(f'【{self.session_type}】失败：金额格式有误')

        book = AccountBook(book_name=self.arg_dict['book'].value)

        record_item = {'platform': request.platform,
                       'user_id': request.user_id}
        for arg in self.arg_list:
            if arg.key != 'book':
                record_item[arg.key] = arg.value

        book.append(**record_item)

        return ResponseMsg(f'【{self.session_type}】成功')


class AccountViewSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '账本统计'
        self.description = '查看账本统计信息'
        self._max_delta = 60
        commands = []
        for a in ['查看', '统计']:
            for b in ['账本', '账单', '记账']:
                commands.append(a+b)
                commands.append(b+a)
        self.strict_commands = commands
        self.permissions = get_permissions().get('AccountView', {})
        self.add_arg(key='book', alias_list=['-bk', '-b'],
                     required=False, get_next=True,
                     default_value=user_id,
                     help_text='最高一级，账本名称（默认QQ号）',
                     ask_text='账本名称是？')
        self.add_arg(key='n-days', alias_list=['-nd', '-d'],
                     required=False, get_next=True,
                     default_value=7,
                     help_text='获取近n天的记账信息（默认7天）')
        self.add_arg(key='n-months', alias_list=['-nm', '-m'],
                     required=False, get_next=True,
                     help_text='获取前n个月的记账信息（默认不启用）')
        self.add_arg(key='category', alias_list=['-c'],
                     required=False, get_next=True,
                     default_value=None,
                     help_text='指定一个类别的内容')

    def prior_handle_test(self, request):
        if request.platform != 'CQ':
            self.arg_dict['book'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        self.deactivate()
        book = AccountBook(book_name=self.arg_dict['book'].value)
        cat = self.arg_dict['category'].value
        if not book.is_exist():
            return ResponseMsg(f'【{self.session_type}】账本不存在。')

        if self.arg_dict['n-months'].called:
            try:
                n = int(self.arg_dict['n-months'].value)
            except ValueError:
                return ResponseMsg(f'【{self.session_type}】输入数字有误。')
            else:
                statistics = book.statistics_month(months_back=n, category=cat)
        else:
            try:
                n = int(self.arg_dict['n-days'].value)
            except ValueError:
                return ResponseMsg(f'【{self.session_type}】输入数字有误。')
            else:
                statistics = book.statistics_recent(days_back=n, category=cat)

        return [ResponseMsg(f'【{self.session_type}】统计时间：\n'
                            f'{statistics["date_range"]}'),
                ResponseMsg(statistics['msg']),
                ResponseImg(statistics['img_pie']),
                ResponseImg(statistics['img_curve'])]


class AccountDelSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '账本删改'
        self.description = '删改账本条目'
        self._max_delta = 60
        commands = []
        for a in ['删除', '删改']:
            for b in ['账本', '账单']:
                commands.append(a+b)
                commands.append(b+a)
        self.strict_commands = commands
        self.permissions = get_permissions().get('AccountView', {})
        self.add_arg(key='book', alias_list=['-bk', '-b'],
                     required=False, get_next=True,
                     default_value=user_id,
                     help_text='最高一级，账本名称（默认QQ号）',
                     ask_text='账本名称是？')
        self.add_arg(key='n_items', alias_list=['-n'],
                     required=False, get_next=True,
                     default_value=5,
                     help_text='查阅的条目数')
        self.default_arg = None  # 没有缺省argument
        self.this_first_time = True
        self.record_table = None

    def prior_handle_test(self, request):
        if request.platform != 'CQ':
            self.arg_dict['book'].required = True  # 其他平台变更订阅属性

    def internal_handle(self, request):
        if self.this_first_time:
            self.this_first_time = False

            # 检查输入n_items
            try:
                n_items = int(self.arg_dict['n_items'].value)
                if n_items <= 0:
                    raise ValueError
            except ValueError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】数值输入有误')

            self.record_table = AccountBook(book_name=str(self.arg_dict['book'].value))
            record_list = self.record_table.find_all()[-n_items:]  # 只看一部分

            if len(record_list) == 0:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】未找到条目')
            else:
                return ResponseMsg(f'【{self.session_type} - 删除】找到以下条目：\n'
                                   f'{self.record_table.list_records(record_list=record_list)}\n'
                                   f'请回复需要删除条目的序号（正整数），回复其他内容以取消')

        else:  # 删除条目
            try:
                d_del = self.record_table.pop_by_index(index=request.msg, from_new=True)
            except ValueError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】退出')
            except RecordNotFoundError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】未找到相符记录，退出')
            except IndexError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】序号超出范围，退出')
            else:
                return ResponseMsg(f'【{self.session_type}】已删除条目:\n'
                                   f'{d_del}\n'
                                   f'请回复需继续删除的条目序号')


class AccountBook(RecordTable):
    def __init__(self, book_name):
        RecordTable.__init__(self,
                             table_file=os.path.join(ACCOUNT_DIR, f'{book_name}.xlsx'),
                             string_cols=['user_id'])

    def append(self, platform, user_id,
               user_tag='nobody', category='expense',
               content='nothing', place='nowhere', amount=0, note=''):
        append_date, append_time = datetime.datetime.now().isoformat().split('T')

        self.append_full({'date': append_date, 'time': append_time,
                          'platform': platform, 'user_id': user_id,
                          'user_tag': user_tag, 'category': category,
                          'content': content, 'place': place,
                          'amount': amount, 'note': note})

    @staticmethod
    def list_single_record(record) -> str:
        return f"{record['date'][-5:]} {record['time'][:5]} by {record['user_id']}\n" \
               f"{record['category']}/{record['content']}/{record['place']}/{record['amount']}"

    # via xgg 20220423
    def _plot_statistics(self, df, sort_by='category'):
        date_list = []
        for date_str in df['date']:
            date_list.append(datetime.date.fromisoformat(date_str))
        date_initial = min(date_list)
        date_last = max(date_list)
        date_final = date_last + datetime.timedelta(days=1)
        # 处理

        group = df.groupby(sort_by).sum()
        total = np.sum(df['amount'])

        # Chinese character
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = 'Microsoft Yahei'

        # plotA
        img_pie = image_filename(header='AccountBookPie', abs_path=True)
        fig, ax = plt.subplots()
        ax.pie(group['amount'], labels=group.index, autopct='%3.1f%%')
        fig.tight_layout()
        fig.savefig(img_pie)

        # plotB
        img_curve = image_filename(header='AccountBookCurve', abs_path=True)
        n_days = (date_final - date_initial).days
        xx = np.arange(n_days)
        # 标记三次
        delta_ticklabels = max(n_days//3, 1)
        xticklabels = [''] * n_days
        for j in range(0, n_days, delta_ticklabels):
            xticklabels[j] = (date_initial + datetime.timedelta(days=j)).isoformat()[-5:]
        # separate
        expenses_lines = {'total': np.zeros(shape=n_days)}
        for i in df.to_dict('records'):
            line_type = i[sort_by]
            if line_type not in expenses_lines.keys():
                expenses_lines[line_type] = np.zeros(shape=n_days)
            expenses_lines['total'][(i['date_obj'] - date_initial).days] += i['amount']
            expenses_lines[line_type][(i['date_obj'] - date_initial).days] += i['amount']
        # make figure
        fig, ax = plt.subplots()
        for line_type, y in expenses_lines.items():
            ax.plot(xx, y, label=line_type)
        ax.legend()
        ax.grid()
        ax.set(xticks=xx, xticklabels=xticklabels)
        fig.tight_layout()
        fig.savefig(img_curve)

        # reverse
        plt.rcParams['font.family'] = plt.rcParamsDefault['font.family']
        plt.rcParams['font.sans-serif'] = plt.rcParamsDefault['font.sans-serif']

        return {'msg': f'分类统计:\n{group.amount}\n总计:{total}',
                'img_pie': img_pie,
                'img_curve': img_curve,
                'date_range': f'{date_initial.isoformat()} - '
                              f'{(date_final - datetime.timedelta(days=1)).isoformat()}'}

    # expansion 20220531
    def statistics(self, date_initial: datetime.date, date_final: datetime.date, category=None):
        # 不使用isinstance(date, datetime.date)，因为datetime对象也会返回True
        assert type(date_initial) == datetime.date and type(date_final) == datetime.date
        df = pd.read_excel(self.table_file)
        # 将pandas dataframe中的string日期转为datetime.date对象
        date_list = []
        for date_str in df['date']:
            date_list.append(datetime.date.fromisoformat(date_str))
        df['date_obj'] = date_list  # 将datetime.date对象的列表放到dataframe中
        # 筛选数据到new_df
        new_df = df[(date_initial <= df['date_obj']) & (df['date_obj'] < date_final)]  # 日期筛选
        new_df = new_df[new_df['amount'] <= 0]  # 保留支出项
        new_df['amount'] *= -1

        if category is None:
            return self._plot_statistics(df=new_df, sort_by='category')
        else:
            new_df = new_df[new_df['category'] == category]
            return self._plot_statistics(df=new_df, sort_by='place')

    # 近n天
    def statistics_recent(self, days_back: int, **kwargs):
        assert isinstance(days_back, int) and days_back >= 0
        date_final = datetime.date.today() + datetime.timedelta(days=1)
        date_initial = datetime.date.today() - datetime.timedelta(days=days_back)
        return self.statistics(date_initial=date_initial, date_final=date_final, **kwargs)

    # 近第n月
    def statistics_month(self, months_back: int, **kwargs):
        assert isinstance(months_back, int) and months_back >= 0

        def previous_month(month_beginning_date: datetime.date):
            new_date = month_beginning_date - datetime.timedelta(days=1)
            return new_date.replace(day=1)

        this_month = datetime.date.today().replace(day=1)
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)

        if months_back == 0:  # this month
            return self.statistics(date_initial=this_month,
                                   date_final=tomorrow,
                                   **kwargs)
        elif months_back == 1:
            return self.statistics(date_initial=previous_month(this_month),
                                   date_final=this_month,
                                   **kwargs)
        else:
            month_list = [this_month]
            for _ in range(months_back):
                month_list.append(previous_month(month_list[-1]))
            return self.statistics(date_initial=month_list[-2],
                                   date_final=month_list[-1],
                                   **kwargs)



