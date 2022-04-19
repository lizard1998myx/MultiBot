from .argument import ArgSession
from ..responses import ResponseMsg
from ..paths import PATHS
import pandas as pd
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


class AccountBook:
    def __init__(self, book_name):
        self.table_file = os.path.join(ACCOUNT_DIR, f'{book_name}.xlsx')

    def append(self, platform, user_id,
               user_tag='nobody', category='expense',
               content='nothing', place='nowhere', amount=0, note=''):
        append_date, append_time = datetime.datetime.now().isoformat().split('T')

        # 读取原数据
        if os.path.exists(self.table_file):
            dfl = pd.read_excel(self.table_file).to_dict('records')
        else:
            # 新建表格
            dfl = []

        dfl.append({'date': append_date, 'time': append_time,
                    'platform': platform, 'user_id': user_id,
                    'user_tag': user_tag, 'category': category,
                    'content': content, 'place': place,
                    'amount': amount, 'note': note})

        # 保存数据
        pd.DataFrame(dfl).to_excel(self.table_file, index=False)


