import nonebot
from ....distributor import DistributorCron
from ....requests import Request
from ....responses import *


@nonebot.scheduler.scheduled_job('cron', hour='*')
async def _():
    bot = nonebot.get_bot()

    # request打包
    request = Request()
    request.platform = 'CQ'
    request.user_id = ''

    # 初始化分拣中心
    distributor = DistributorCron()

    async def execute(response_list):
        for response in response_list:
            if isinstance(response, ResponseGrpMsg):
                msg = response.text
                for at_id in response.at_list:
                    msg += '[CQ:at,qq=%s]' % str(at_id)
                await bot.send_group_msg(group_id=response.group_id, message=msg)
            elif isinstance(response, ResponseGrpImg):
                img_msg = '[CQ:image,file=file:///%s]' % response.file.replace(':', ':\\')
                await bot.send_group_msg(group_id=response.group_id, message=img_msg)
            else:
                pass

    await execute(response_list=distributor.handle(request=request))
    distributor.refresh_and_save()