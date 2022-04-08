from .argument import ArgSession, Argument
from ..responses import ResponseMsg
import imaplib, email, tqdm, re


class EmailCasTrashSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 3*60
        self.session_type = '中科院邮箱清理'
        self.strict_commands = ['cstnet', '中科院邮箱', '邮箱清理', '邮件清理', '清理邮箱', '清理邮件']
        self.description = '清理科学院邮箱中的中科院之声、科学院院刊等邮件'
        agreement_text = ("\n注意：清理可能需要数分钟时间，默认清除最近30封邮件中的杂志邮件。\n\n"
                          "本插件原理是使用imaplib.IMAP4_SSL登录科学院邮箱服务器，自动清除邮件。" 
                          "所使用信息为一次性，不保存账号、密码和个人信息。\n"
                          "【下一步】\n" 
                          "确认仔细阅读上述条款且无异议，回复任意消息进入下一步。")
        self.arg_list = [Argument(key='agree', alias_list=['-y', '-a'],
                                  required=True,
                                  ask_text=agreement_text),
                         Argument(key='username', alias_list=['-u'],
                                  required=True, get_next=True,
                                  ask_text='邮箱地址'),
                         Argument(key='password', alias_list=['-p'],
                                  required=True, get_next=True,
                                  ask_text='密码（不是SEP密码）'),
                         Argument(key='num', alias_list=['-n'],
                                  required=False, get_next=True,
                                  help_text='查找范围（最近n个）',
                                  default_value=30),
                         ]
        self.detail_description = '举例，发送“cstnet -y -u xx@xx.cn -p 123456 -n 50”，' \
                                  '清除最近50篇邮件中的杂志邮件'

    def internal_handle(self, request):
        self.deactivate()

        # 参数检查
        num = self.arg_dict['num'].value
        try:
            num = int(num)
        except ValueError:
            return ResponseMsg(f'【{self.session_type}】参数错误')
        if num == 0:
            return ResponseMsg(f'【{self.session_type}】查找范围为零')

        # 初始化和登录
        mailbox = MyMailBox(user=self.arg_dict['username'].value,
                            pwd=self.arg_dict['password'].value)
        try:
            mailbox.login()
        except imaplib.IMAP4.error:
            return ResponseMsg(f'【{self.session_type}】登录失败')
        except imaplib.IMAP4_SSL.error:
            return ResponseMsg(f'【{self.session_type}】登录失败')

        # 获取uid列表
        total_uid_list = mailbox.get_uid_list()
        if num > 0:
            uid_list = total_uid_list[-1*num:]  # 最新值
        else:
            uid_list = total_uid_list[:-1*num]

        mail_list = trash_cas_magazine(mailbox=mailbox, to_trash=True, uid_list=uid_list, patterns=None)
        return ResponseMsg(f'【{self.session_type}】已清理{len(mail_list)}封杂志邮件。')


class MyMailBox:
    def __init__(self, user, pwd,
                 server='mail.cstnet.cn'):
        self.user = user
        self.pwd = pwd
        self.server = server
        self.imap = None

    def login(self):
        self.imap = imaplib.IMAP4_SSL(self.server)
        self.imap.login(self.user, self.pwd)
        self.imap.select(mailbox='INBOX', readonly=False)

    def logout(self):
        try:
            self.imap.logout()
        except:  # imaplib.IMAP4.abort
            pass

    def get_uid_list(self):
        # get list of bytes [b'1234', b'1597', b'1998']
        return self.imap.uid('search', None, 'ALL')[1][0].split()

    def get_msg_by_uid(self, uid):
        if isinstance(uid, str):
            uid = uid.encode()
        mail_data = self.imap.uid('fetch', uid, '(RFC822)')
        # return email.message_from_string(mail_data[1][0][1].decode('utf-8'))
        return email.message_from_bytes(mail_data[1][0][1])

    @staticmethod
    def get_header_in_msg(msg: email.message.Message, key: str):
        charset = email.header.decode_header(msg.get(key))[0][1]
        if charset is None:
            return email.header.decode_header(msg.get(key))[0][0]
        else:
            return email.header.decode_header(msg.get(key))[0][0].decode(charset)

    def get_brief_in_msg(self, msg: email.message.Message):
        # keys = ['Subject', 'From', 'To', 'Date']
        keys = msg.keys()
        brief = {}
        for key in keys:
            try:
                value = self.get_header_in_msg(msg=msg, key=key)
            except ValueError:
                continue
            else:
                brief[key] = value
        return brief

    def remove_by_uid(self, uid, to_trash=True):
        if to_trash:
            # self.imap.uid('STORE', uid, '+X-GM-LABELS', '\\Trash')
            self.imap.uid('copy', uid, 'Trash')
            self.imap.uid('STORE', uid, '+FLAGS', '(\\Deleted)')
        else:
            self.imap.uid('STORE', uid, '+FLAGS', '(\\Deleted)')


def trash_cas_magazine(mailbox: MyMailBox, to_trash=True, uid_list=None, patterns=None):
    if patterns is None:
        patterns = [r'“中科院之声”电子杂志第\d+期',
                    r'《中国科学院院刊》202\d年第\d+期目次']

    print('== Start Removal ==')

    if uid_list is None:
        ul = mailbox.get_uid_list()  # uid list (bytes)
    else:
        ul = uid_list
    msgs = {}
    subject_removed_list = []

    for u in tqdm.tqdm(ul):
        msgs[u] = mailbox.get_msg_by_uid(u)

    for u, msg in msgs.items():
        try:
            subject = mailbox.get_header_in_msg(msg, "Subject")
        except TypeError:  # no subject
            continue
        if isinstance(subject, bytes):
            print(f'Error: [{u}] {subject}')  # bytes subject
            continue
        for pattern in patterns:
            if re.match(pattern=pattern, string=subject):
                print(f'Removing: {subject}')
                subject_removed_list.append(subject)
                mailbox.remove_by_uid(u, to_trash=to_trash)
                break

    print('== Removal Done ==')
    return subject_removed_list