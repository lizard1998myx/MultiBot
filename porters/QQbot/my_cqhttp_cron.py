import traceback, requests
from ...distributor import DistributorCron
from ...requests import Request
from ...responses import *
from ...server_config import CQHTTP_URL
from apscheduler.schedulers.blocking import BlockingScheduler
# fail to use AyncIO, 不知道BlockingScheduler会不会有bug（比如执行1min以上的代码）
# from apscheduler.schedulers.asyncio import AsyncIOScheduler


def cron_task():
    print('start task')

    # request打包
    request = Request()
    request.platform = 'CQ'
    request.user_id = ''
    request.from_scheduler = True

    # 初始化分拣中心
    distributor = DistributorCron()

    # 发送消息
    def send(message: str, user_id=None, group_id=None):
        if group_id is None:
            requests.get(f'{CQHTTP_URL}/send_private_msg',
                         {'user_id': user_id, 'message': message})
        else:
            requests.get(f'{CQHTTP_URL}/send_group_msg',
                         {'group_id': group_id, 'message': message})

    # 执行response
    def execute(response_list):
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
                            send(group_id=response.group_id, message=msg)
                        else:  # 用户
                            send(user_id=response.user_id, message=msg)
                        if msg_left != '':  # 这轮超出部分为0时
                            msg = msg_left
                        else:
                            msg = ''

                elif isinstance(response, ResponseGrpImg) or isinstance(response, ResponseImg):
                    img_msg = '[CQ:image,file=file:///%s]' % response.file.replace(':', ':\\')
                    if isinstance(response, ResponseGrpImg):
                        send(group_id=response.group_id, message=img_msg)
                    else:
                        send(user_id=response.user_id, message=img_msg)
                elif isinstance(response, ResponseMusic):
                    send(user_id=response.user_id,
                         message=f'[CQ:music,type={response.platform},id={response.music_id}]')
                else:
                    pass
            except:
                # 诸如发送失败等问题
                traceback.print_exc()

    execute(response_list=distributor.handle(request=request))
    distributor.refresh_and_save()


def main():
    scheduler = BlockingScheduler()
    scheduler.add_job(cron_task, 'cron', hour='*', minute='*')
    scheduler.start()

