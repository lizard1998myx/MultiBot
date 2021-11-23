import os
import getpass

PATHS = {}

if os.environ['COMPUTERNAME'] == 'YUXI-HP15':
    PATHS['base'] = r'C:\Users\Yuxi\PycharmProjects\untitled\MultiBot3'
else:
    PATHS['base'] = r'C:\Users' + f'\\{getpass.getuser()}' + r'\PycharmProjects\untitled\MultiBot'

PATHS['temp'] = os.path.join(PATHS['base'], 'temp')  # temp dir
PATHS['cache'] = os.path.join(PATHS['temp'], 'cache')  # cache for classroom search etc.
PATHS['history'] = os.path.join(PATHS['temp'], 'history')  # store plugins call history
PATHS['data'] = os.path.join(PATHS['base'], 'data')
PATHS['box'] = os.path.join(PATHS['data'], 'box')  # answer box & alias box
# PATHS['cqhttp'] = os.path.join(PATHS['base'], 'porters', 'QQbot', 'cqhttp')
PATHS['cqhttp'] = r'C:\Users\Yuxi\PycharmProjects\untitled\MultiBot\QQbot\cqhttp'
PATHS['cqbot'] = os.path.join(PATHS['base'], 'porters', 'QQbot')
PATHS['webtemp'] = os.path.join(PATHS['base'], 'porters', 'WebApp', 'static', 'temp')

PATHS['webdriver'] = r'C:\Users\Yuxi\PycharmProjects\untitled\chromedriver.exe'  # for selenium
