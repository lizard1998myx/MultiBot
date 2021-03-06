from nonebot import CommandSession, on_command
from nonebot import on_natural_language, NLPSession, IntentCommand
from ....requests import Request
from ....responses import *
from ....distributor import Distributor
from ....utils import image_url_to_path
from ....paths import PATHS
import os, logging, traceback
import html, json, xml  # for json/xml object interpretation

# BLACKLIST = [3288849221]
BLACKLIST = [3288849221]


@on_natural_language(only_to_me=False, only_short_message=False, allow_empty_message=True)
async def _(session: NLPSession):
    return IntentCommand(100.0, 'porter', args={'message': session.msg_text})


@on_command('porter')
async def porter(session: CommandSession):
    logging.debug('=========== [MultiBot] Entered nonebot porter ==========')
    # 在任何情况下，把所有消息打包成Request交给分拣中心（Distributor），然后处理分拣中心发回的Response序列
    # Resqust打包
    request = Request()
    request.platform = 'CQ'
    request.user_id = str(session.ctx['user_id'])

    self_id = str(session.self_id)
    self_names = ['韩大佬', 'lzy', '林子逸', '子兔', 'xsx', '小石像']
    bot_called = False

    if request.user_id == self_id:
        logging.debug('=========== [MultiBot] Left nonebot porter ==========')
        return
    elif request.user_id in BLACKLIST:
        logging.debug('=========== [MultiBot] Left nonebot porter ==========')
        return

    if '[CQ:at,qq={}]'.format(self_id) in session.ctx['raw_message']:
        # 被at时
        bot_called = True

    if 'group_id' in session.ctx.keys():
        request.group_id = str(session.ctx['group_id'])
    else:
        # 私聊时
        bot_called = True

    for message in session.ctx['message']:
        if message['type'] == 'text' and request.msg is None:
            text = message['data']['text'].strip()

            # 呼叫检测
            for name in self_names:
                if name in text:
                    # 被叫到时
                    bot_called = True
                    text = text.strip()
                    while text[:len(name)] == name:
                        text = text[len(name):]
                    while text[-len(name):] == name:
                        text = text[:-len(name)]
                    for sign in [None, ',', '，', None]:
                        text = text.strip(sign)

            # 消息段检测
            if '请使用' in text and '新版手机QQ' in text:
                request.echo = True
                request.msg = '【NonebotPorter】不支持的消息段："%s"' % text
                continue

            # 空文本检测
            if text != '':
                request.msg = text
        elif message['type'] == 'image' and request.img is None:
            # 先不下载图片，获取response时下载
            request.img = message['data']['url']
            # request.img = image_url_to_path(message['data']['url'], header='QQBot')
        elif message['type'] == 'record' and request.aud is None:
            request.aud = os.path.join(PATHS['cqhttp'], 'data', 'voices', message['data']['file'])
        elif message['type'] == 'location':
            request.loc = {'longitude': float(message['data']['lon']),
                           'latitude': float(message['data']['lat'])}
        elif message['type'] == 'json':
            json_data = json.loads(html.unescape(message['data']['data']))
            interpretable = False
            # 尝试解析为location
            if json_data.get('app') == 'com.tencent.map':
                try:
                    loc = {'longitude': float(json_data['meta']['Location.Search']['lng']),
                           'latitude': float(json_data['meta']['Location.Search']['lat'])}
                    request.loc = loc
                    interpretable = True
                    print(f'== 位置解析成功= {loc} ==')
                except:
                    pass
            if not interpretable:  # 无法解析
                request.echo = True
                data_str = ''
                for k, v in json_data.items():
                    data_str += f'{k}= {v}\n'
                request.msg = f"【NonebotPorter】无法识别的JSON消息段：" \
                              f"{data_str}"
                continue
        elif message['type'] == 'xml':
            xml_data = xml.etree.ElementTree.fromstring(html.unescape(message['data']['data']))
            interpretable = False
            if xml_data.attrib.get('brief') == '[位置]':
                try:
                    raw_list = xml_data.attrib['actionData'].split('&')
                    loc = {}
                    for s in raw_list:
                        if s[:3] == 'lat':
                            loc['latitude'] = float(s.split('=')[1])
                        elif s[:3] == 'lon':
                            loc['longitude'] = float(s.split('=')[1])
                    assert len(loc) == 2
                    request.loc = loc
                    interpretable = True
                    print(f'== 位置解析成功= {loc} ==')
                except:
                    pass
            if not interpretable:  # 无法解析
                request.echo = True
                data_str = ''
                for k, v in xml_data.attrib.items():
                    data_str += f'{k}= {v}\n'
                request.msg = f"【NonebotPorter】无法识别的XML消息段：" \
                              f"{data_str}"
                continue
        elif message['type'] not in ['face', 'at', 'anonymous', 'share', 'reply']:
            request.echo = True
            request.msg = f"【NonebotPorter】不支持的消息段[{message['type']}]：" \
                          f"{str(message).replace('CQ:', '$CQ$:')}"
            continue

    # 初始化分拣中心
    distributor = Distributor()

    # 获取Response序列，同时下载图片，若出错则返回错误信息
    def get_responses():
        if request.img:
            request.img = image_url_to_path(request.img, header='QQBot')
        response_list = distributor.handle(request=request)
        return response_list

    # 用于执行Response序列
    async def execute(response_list: list):
        for response in response_list:
            try:
                if isinstance(response, ResponseMsg) or isinstance(response, ResponseGrpMsg):
                    msg = response.text
                    for at_id in response.at_list:
                        msg += '[CQ:at,qq=%s]' % str(at_id)

                    # 过长文本多次发送
                    max_length = 2000
                    while len(msg) > 0:
                        msg_left = msg[max_length:]  # msg超出maxL的部分
                        msg = msg[:max_length]  # msg只保留maxL内的部分
                        if isinstance(response, ResponseMsg):  # 私聊
                            await session.send(message=msg)
                        else:  # 群消息
                            await session.bot.send_group_msg(group_id=response.group_id, message=msg)
                        if msg_left != '':  # 这轮超出部分为0时
                            msg = msg_left
                        else:
                            msg = ''

                elif isinstance(response, ResponseMusic):
                    await session.send(message=f'[CQ:music,type={response.platform},id={response.music_id}]')
                elif isinstance(response, ResponseImg) or isinstance(response, ResponseGrpImg):
                    # 需要在盘符之后加入一个反斜杠，并且不使用双引号
                    img_msg = '[CQ:image,file=file:///%s]' % os.path.abspath(response.file).replace(':', ':\\')
                    if isinstance(response, ResponseImg):
                        await session.send(message=img_msg)
                    else:
                        await session.bot.send_group_msg(group_id=response.group_id, message=img_msg)
                elif isinstance(response, ResponseCQFunc):
                    try:
                        output = await eval('session.bot.%s' % response.func_name)(**response.kwargs)
                    except AttributeError:
                        await session.send('【NonebotPorter】不支持的函数：%s' % response.func_name)
                    except TypeError:
                        await session.send('【NonebotPorter】不支持的参数：%s' % str(response.kwargs))
                    except SyntaxError:
                        await session.send('【NonebotPorter】语法错误')
                    else:
                        await execute(distributor.process_output(output=output))  # 递归处理新的Response序列
            except:
                # 诸如发送失败等问题
                logging.error(traceback.format_exc())

    # 在筛选后，把Request交给分拣中心，执行返回的Response序列
    if bot_called:
        # 符合呼出条件的，直接执行
        await execute(response_list=get_responses())
    elif distributor.use_active(request=request, save=False):
        # 不符合呼出条件的，若有活动Session对应，也可以执行
        await execute(response_list=get_responses())
    else:
        logging.debug('=========== [MultiBot] Left nonebot porter ==========')
        return

    # 刷新并保存最新的session信息
    distributor.refresh_and_save()

    logging.debug('=========== [MultiBot] Completed nonebot porter ==========')
