from .argument import ArgSession, Argument
from ..responses import ResponseMsg
from ..permissions import get_permissions
from ..server_config import FLASK_PORTS
import re, subprocess, os


class Ipv6AddrSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = 'ipv6地址'
        self.description = '获取服务器ipv6地址'
        self._max_delta = 60
        self.strict_commands = ['ipv6', 'v6']
        self.arg_list = [Argument(key='link', alias_list=['-l'],
                                  help_text='返回链接'),
                         Argument(key='detail', alias_list=['-d'],
                                  help_text='返回ipconfig全文')
                         ]
        self.default_arg = None
        self.permissions = get_permissions().get('Ipv6AddrSession', {})

    def internal_handle(self, request):
        self.deactivate()
        addr_list = get_local_ipv6_address()
        responses = []
        if len(addr_list) == 0:
            responses.append(ResponseMsg(f'【{self.session_type}】未找到ipv6地址'))
        response_msg = f'【{self.session_type}】服务器的ipv6地址是：'
        for addr in addr_list:
            response_msg += f'\n{addr}'
        responses.append(ResponseMsg(response_msg))
        if self.arg_dict['link'].called:
            for addr in addr_list:
                responses.append(ResponseMsg(f'[{addr}]:{FLASK_PORTS["Web6"]}\n'))
        if self.arg_dict['detail'].called:
            with os.popen('ipconfig') as f:
                responses.append(ResponseMsg(f.read()))
        return responses


# 获取ipv6地址
# 引用自：http://blog.sina.com.cn/s/blog_3fe961ae0100zjo5.html
# 有修改
def get_local_ipv6_address():
    """
     This function will return your local machine's ipv6 address if it exits.
     If the local machine doesn't have a ipv6 address,then this function return None.
     This function use subprocess to execute command "ipconfig", then get the output
     and use regex to parse it ,trying to  find ipv6 address.
    """

    getIPV6_process = subprocess.Popen("ipconfig", stdout=subprocess.PIPE)
    output = (getIPV6_process.stdout.read())
    ipv6_pattern = '(([a-f0-9]{1,4}:){7}[a-f0-9]{1,4})'
    ms = re.findall(ipv6_pattern, str(output))
    addr_list = []
    for m in ms:
        addr_list.append(m[0])

    # m = re.search(ipv6_pattern, str(output))
    # if m is not None:
    #     return m.group()
    # else:
    #     return None

    # 通常第一个是固定ip，第二个是临时ip
    return addr_list
