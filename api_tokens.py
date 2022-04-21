import pandas as pd
from .paths import PATHS
import os

TOKEN_FILE = os.path.join(PATHS['data'], 'api_tokens.xlsx')
TOKEN_DICT = {}

try:
    for record in pd.read_excel(TOKEN_FILE).to_dict('records'):
        TOKEN_DICT[record['api']] = record['token']
except FileNotFoundError:
    # 新建文件
    api_list = ['OCR_APP_ID', 'OCR_API_KEY', 'OCR_SECRET_KEY',
                'TCT_APPID', 'TCT_SECRET_ID', 'TCT_SECRET_KEY',
                'TURING_API_KEY', 'CAIYUN_API_TOKEN',
                'BAIDU_MAP_API_TOKEN', 'CAIYUN_TRANS_TOKEN',
                'WCP_TOKEN', 'WCP_APP_ID', 'WCP_APP_SECRET',
                'SENDER_NAME', 'SENDER_ADDR', 'SENDER_PWD',
                'SERVER_IP']
    pd.DataFrame({'api': api_list,
                  'token': [''] * len(api_list)}).to_excel(TOKEN_FILE, index=False)
    print(f'【MultiBot】please update your api tokens in {TOKEN_FILE}')

# planB
# for i in api_list:
#     exec(f"{i} = TOKEN_DICT['{i}']")

# 百度OCR接口，技术文档： https://cloud.baidu.com/doc/OCR/s/dk3iqnq51
OCR_APP_ID = TOKEN_DICT.get('OCR_APP_ID')
OCR_API_KEY = TOKEN_DICT.get('OCR_API_KEY')
OCR_SECRET_KEY = TOKEN_DICT.get('OCR_SECRET_KEY')

# 腾讯云API，用于语音识别，技术文档： https://cloud.tencent.com/product/asr
TCT_APPID = TOKEN_DICT.get('TCT_APPID')
TCT_SECRET_ID = TOKEN_DICT.get('TCT_SECRET_ID')
TCT_SECRET_KEY = TOKEN_DICT.get('TCT_SECRET_KEY')

# 图灵聊天机器人接口，技术文档： https://www.kancloud.cn/turing/www-tuling123-com/718227
TURING_API_KEY = TOKEN_DICT.get('TURING_API_KEY')

# 彩云天气api，技术文档： https://open.caiyunapp.com/Main_Page
CAIYUN_API_TOKEN = TOKEN_DICT.get('CAIYUN_API_TOKEN')
# 百度地图开放平台，技术文档： http://lbsyun.baidu.com/index.php?title=webapi/guide/webservice-geocoding
BAIDU_MAP_API_TOKEN = TOKEN_DICT.get('BAIDU_MAP_API_TOKEN')

# 彩云小译api，技术文档在彩云天气那里
CAIYUN_TRANS_TOKEN = TOKEN_DICT.get('CAIYUN_TRANS_TOKEN')

# QQ机器人的实现及文档如下
# NoneBot的教程： https://docs.nonebot.dev/
# go-cqhttp页面： https://github.com/Mrs4s/go-cqhttp
# OneBot标准的描述页面： https://github.com/howmanybots/onebot

# 微信机器人的实现及文档如下
# Python版教程： https://github.com/wechaty/python-wechaty-getting-started
# Python版项目： https://github.com/wechaty/python-wechaty
# 主页： https://wechaty.js.org/

# 微信公众号
WCP_TOKEN = TOKEN_DICT.get('WCP_TOKEN')
WCP_APP_ID = TOKEN_DICT.get('WCP_APP_ID')
WCP_APP_SECRET = TOKEN_DICT.get('WCP_APP_SECRET')
# 需要在微信公众平台加入IP白名单才可以

# 邮箱
SENDER_NAME = TOKEN_DICT.get('SENDER_NAME')
SENDER_ADDR = TOKEN_DICT.get('SENDER_ADDR')
SENDER_PWD = TOKEN_DICT.get('SENDER_PWD')

SENDER = {'name': SENDER_NAME,
          'address': SENDER_ADDR,
          'pwd': SENDER_PWD}

SERVER_IP = TOKEN_DICT.get('SERVER_IP')
