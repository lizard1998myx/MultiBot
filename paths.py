import os
import getpass
import socket
import sys

PATHS = {}

# base path
if sys.platform == 'win32':
    if socket.gethostname() == 'YUXI-HP15':
        PATHS['base'] = r'C:\Users\Yuxi\PycharmProjects\untitled\MultiBot'
    else:  # as PycharmProjects
        PATHS['base'] = r'C:\Users' + f'\\{getpass.getuser()}' + r'\PycharmProjects\untitled\MultiBot'
elif sys.platform == 'linux':  # docker platform
    PATHS['base'] = '/home/MultiBot'
else:
    raise Exception('unspecified system')

# important directories
# 用于指定QQ机器人的插件目录
PATHS['cqbot'] = os.path.join(PATHS['base'], 'porters', 'QQbot')
# 存放webapp的临时文件，用于网页端的图片显示
PATHS['webtemp'] = os.path.join(PATHS['base'], 'porters', 'WebApp', 'static', 'temp')

# file storage directories
PATHS['temp'] = os.path.join(PATHS['base'], 'temp')  # temp dir
PATHS['cache'] = os.path.join(PATHS['temp'], 'cache')  # cache for classroom search etc.
PATHS['history'] = os.path.join(PATHS['temp'], 'history')  # store plugins call history
PATHS['data'] = os.path.join(PATHS['base'], 'data')
PATHS['box'] = os.path.join(PATHS['data'], 'box')  # answer box & alias box

# program directories
# QQ机器人基于cqhttp，需要指定cqhttp的路径来读取录音文件
# PATHS['cqhttp'] = os.path.join(PATHS['base'], 'porters', 'QQbot', 'cqhttp')
PATHS['cqhttp'] = r'C:\Users\Yuxi\PycharmProjects\untitled\mbot_programs\cqhttp'
# 一些爬虫用到了selenium，需要指定一个chromedriver
PATHS['webdriver'] = r'C:\Users\Yuxi\PycharmProjects\untitled\chromedriver.exe'  # for selenium

# create directories
for dir_name in ['temp', 'cache', 'history', 'data', 'box', 'webtemp']:
    if not os.path.exists(PATHS[dir_name]):
        os.mkdir(PATHS[dir_name])