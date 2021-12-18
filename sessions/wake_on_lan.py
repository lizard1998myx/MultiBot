from .argument import ArgSession, Argument
from ..responses import ResponseMsg
import socket
import struct


class WolSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 3*60
        self.session_type = '局域网唤醒'
        self.strict_commands = ['wol']
        self.description = 'WOL唤醒局域网计算机'
        self.arg_list = [Argument(key='password', alias_list=['-pwd'],
                                  required=True, get_next=True,
                                  ask_text='请输入口令（四位）',
                                  help_text='密码口令，符合才可唤醒'),
                         Argument(key='macaddress', alias_list=['-mac'],
                                  default_value='B0:7B:25:1F:41:EF',
                                  help_text='目标MAC地址')]
        self._password = '2333'
        self.detail_description = '仅供管理员使用，输入密码远程启动计算机。'

    def internal_handle(self, request):
        self.deactivate()
        if str(self.arg_dict['password'].value) == self._password:
            mac_addr = self.arg_dict['macaddress'].value
            try:
                wake_on_lan(mac_addr)
                return ResponseMsg(f'【{self.session_type}】已对{mac_addr}发送唤醒指令')
            except ValueError:
                return ResponseMsg(f'【{self.session_type}】MAC地址格式错误')
        else:
            return ResponseMsg(f'【{self.session_type}】口令无效')


# from https://www.douban.com/note/300037894/
def wake_on_lan(macaddress):
    if len(macaddress) == 12:
        pass
    elif len(macaddress) == 12 + 5:
        sep = macaddress[2]
        macaddress = macaddress.replace(sep, '')
    else:
        raise ValueError('Incorrect MAC address format')
    data = ''.join(['FFFFFFFFFFFF', macaddress * 16])
    send_data = b''
    for i in range(0, len(data), 2):
        byte_dat = struct.pack('B', int(data[i: i + 2], 16))
        send_data = send_data + byte_dat
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(send_data, ('255.255.255.255', 7))
    sock.close()