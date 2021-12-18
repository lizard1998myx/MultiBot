import nonebot, traceback
from ....distributor import DistributorCron
from ....requests import Request
from ....responses import *


@nonebot.scheduler.scheduled_job('cron', hour='*', minute='*')
async def _():
    bot = nonebot.get_bot()

    # request打包
    request = Request()
    request.platform = 'CQ'
    request.user_id = ''
    request.from_scheduler = True

    # 初始化分拣中心
    distributor = DistributorCron()

    async def execute(response_list):
        for response in response_list:
            try:
                if isinstance(response, ResponseGrpMsg) or isinstance(response, ResponseMsg):
                    msg = response.text
                    for at_id in response.at_list:
                        msg += '[CQ:at,qq=%s]' % str(at_id)

                    # 过长文本多次发送
                    max_length = 2000
                    while len(msg) > 0:
                        msg_left = msg[max_length:]  # msg超出maxL的部分
                        msg = msg[:max_length]  # msg只保留maxL内的部分
                        if isinstance(response, ResponseGrpMsg):  # 群聊
                            await bot.send_group_msg(group_id=response.group_id, message=msg)
                        else:  # 用户
                            await bot.send_private_msg(user_id=response.user_id, message=msg)
                        if msg_left != '':  # 这轮超出部分为0时
                            msg = msg_left
                        else:
                            msg = ''

                elif isinstance(response, ResponseGrpImg) or isinstance(response, ResponseImg):
                    img_msg = '[CQ:image,file=file:///%s]' % response.file.replace(':', ':\\')
                    if isinstance(response, ResponseGrpImg):
                        await bot.send_group_msg(group_id=response.group_id, message=img_msg)
                    else:
                        await bot.send_private_msg(user_id=response.user_id, message=img_msg)
                elif isinstance(response, ResponseMusic):
                    await bot.send_private_msg(user_id=response.user_id,
                                               message=f'[CQ:music,type={response.platform},id={response.music_id}]')
                else:
                    pass
            except:
                # 诸如发送失败等问题
                traceback.print_exc()

    await execute(response_list=distributor.handle(request=request))
    distributor.refresh_and_save()