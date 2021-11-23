import asyncio, os, logging, datetime, re
from typing import Optional, Union

from wechaty_puppet import FileBox, ScanStatus  # type: ignore
from wechaty_puppet import MessageType

from wechaty import Wechaty, Contact
from wechaty.user import Message, Room
from wechaty import Friendship, FriendshipType

from ...requests import Request
from ...responses import *
from ...utils import image_filename, format_filename
from ...distributor import Distributor, DistributorCron
from ...server_config import WECHATY_ENV

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TEST_ROOM = '@@a2fe9ff332cd6a97b741af5622746d9b29dfc22a1bafc767c874a0f5903fdca8'
TEST_ROOM_NAME = 'Testing'
BOT_NAME = 'Bot.Lizard'
FRIEND_KEY = '1234'
WHITE_LIST = ['小果果']


class MyBot(Wechaty):
    def __init__(self):
        super().__init__()

    async def on_message(self, msg: Message):
        """
        listen for message event
        """
        logging.debug('[MultiBot] Entered wechat porter')
        # 在任何情况下，把所有消息打包成Request交给分拣中心（Distributor），然后处理分拣中心发回的Response序列
        # Resqust打包
        request = Request()
        request.platform = 'Wechat'
        request.user_id = msg.talker().contact_id
        self_names = ['韩大佬', 'lzy', '林子逸', '子兔']
        bot_called = False

        if msg.is_self():
            # 如果消息来自自己
            return
        elif not msg.talker():
            return
        elif msg.talker().name == BOT_NAME:
            return
        else:
            bot_called = True
            print('[来自用户] {}'.format(request.user_id))

        room = msg.room()
        if room:
            print('[来自群聊] {}'.format(room.room_id))
            topic = await room.topic()
            if topic == TEST_ROOM_NAME:
                print('来自测试群')
                bot_called = True
                # await room.ready()
            else:
                print('来自一般群聊')
                bot_called = False
                # await room.ready()
                # return  # 不处理其他群聊消息
        # elif not msg.talker().is_friend():
        #     return
        elif not msg.talker().gender():
            if msg.talker().name in WHITE_LIST:
                pass
            else:
                # 用于排除公众号
                return

        if msg.type() == MessageType.MESSAGE_TYPE_TEXT:
            text = msg.text()
            # filter unsupported message
            unsupports = ['view it on mobile', 'view on the phone', '请在手机上查看']
            for pattern in unsupports:
                if pattern in text:
                    request.echo = True
                    request.msg = '【WechatPorter】不支持的消息段：{}'.format(text)
                    break

            # filter url & email address (only once)
            # not support two url now
            match = re.search(r'<a target="_blank" .*>(.*)</a>', text)
            if match:
                text = text.replace(match.group(0), match.group(1))

            # 呼叫检测
            for name in self_names:
                if name in text:
                    # 被叫到时
                    print(f'被叫到：[{name}] in [{text}]')
                    bot_called = True
                    text = text.strip()
                    while text[:len(name)] == name:
                        text = text[len(name):]
                    while text[-len(name):] == name:
                        text = text[:-len(name)]
                    for sign in [None, ',', '，', None]:
                        text = text.strip(sign)

            if not request.echo:
                request.msg = text
        elif msg.type() == MessageType.MESSAGE_TYPE_IMAGE:
            request.img = 'wait'
            """
            img = await msg.to_file_box()
            filename = image_filename(header='Wechat', post='-{}'.format(img.name))
            abs_path = os.path.abspath(os.path.join('..', 'temp', filename))
            await img.to_file(abs_path)
            request.img = abs_path
            """
        elif msg.type() == MessageType.MESSAGE_TYPE_AUDIO:
            request.aud = 'wait'
            """
            audio = await msg.to_file_box()
            filename = format_filename(header='Wechat', type='audio', post='-{}'.format(audio.name))
            abs_path = os.path.abspath(os.path.join('..', 'temp', filename))
            await audio.to_file(abs_path)
            request.aud = abs_path
            """
        else:
            request.echo = True
            request.msg = '【WechatPorter】不支持的消息段：{}'.format(str(msg.type()))

        print(f'==处理==\nID={request.user_id}\n'
              f'text={request.msg}\nimg={request.img}\naud={request.aud}')

        # 初始化分拣中心
        distributor = Distributor()

        async def get_responses():
            if request.img:
                img = await msg.to_file_box()
                filename = image_filename(header='Wechat', post='-{}'.format(img.name))
                abs_path = os.path.abspath(os.path.join('..', 'temp', filename))
                await img.to_file(abs_path)
                request.img = abs_path
            elif request.aud:
                audio = await msg.to_file_box()
                filename = format_filename(header='Wechat', type='audio', post='-{}'.format(audio.name))
                abs_path = os.path.abspath(os.path.join('..', 'temp', filename))
                await audio.to_file(abs_path)
                request.aud = abs_path
            return distributor.handle(request=request)

        async def send(x):
            try:
                if room:
                    await room.ready()
                await msg.say(x)
            except AssertionError:
                pass

        async def execute(response_list: list):
            print(response_list)
            for response in response_list:
                if isinstance(response, ResponseMsg):
                    await send(response.text)
                elif isinstance(response, ResponseImg):
                    await send(FileBox.from_file(path=response.file))
                elif isinstance(response, ResponseMusic):
                    await send(response.info())
                else:
                    await send('【WechatPorter】不支持的回复：{}'.format(request))

        # 在筛选后，把Request交给分拣中心，执行返回的Response序列
        if bot_called:
            # 符合呼出条件的，直接执行
            print('被叫到放行')
            await execute(response_list=await get_responses())
        elif distributor.use_active(request=request, save=False):
            # 不符合呼出条件的，若有活动Session对应，也可以执行
            print('有活动session，放行')
            await execute(response_list=await get_responses())
        else:
            return

        # await execute(response_list=distributor.handle(request=request))
        distributor.refresh_and_save()

    async def on_friendship(self, friendship: Friendship):
        contact = friendship.contact()
        await contact.ready()
        print(f'receive "friendship" message from {contact.name}')

        if friendship.type() == FriendshipType.FRIENDSHIP_TYPE_RECEIVE:
            if friendship.hello() == FRIEND_KEY:
                print('before accept ...')
                await friendship.accept()
                await asyncio.sleep(3)
                request = Request()
                request.platform = 'Wechat'
                request.user_id = '0'
                request.msg = 'hello'
                distributor = Distributor()
                response = distributor.handle(request=request)[0]
                await contact.say(response.text)
                print('after accept ...')
            else:
                print('not auto accepted, because verify message is: ' + friendship.hello())

    async def on_login(self, contact: Contact):  # 未作修改
        """login event. It will be triggered every time you login"""
        log.info(f'user: {contact} has login')

    async def on_scan(self, status: ScanStatus, qr_code: Optional[str] = None,
                      data: Optional[str] = None):  # 未作修改
        """scan event, It will be triggered when you scan the qrcode to login.
        And it will not be triggered when you have logined
        """
        contact = self.Contact.load(self.contact_id)
        await contact.ready()
        print(f'user <{contact}> scan status: {status.name} , '
              f'qr_code: {qr_code}')


bot: Optional[MyBot] = None


async def tick(bot: Wechaty):
    # find a specific room, and say something to it.
    # room = bot.Room.load(TEST_ROOM)
    room = await bot.Room.find(TEST_ROOM_NAME)
    await room.ready()

    async def send(x):
        try:
            m_list = await room.member_list()
            ids = []
            print(f'length={len(m_list)}')
            for m in m_list:
                print(f'== 用户信息 {m.name} ==')
                print(f'id= {m.contact_id}')
                print(f'room alias= {await room.alias(member=m)}')
                print(f'user alias= {await m.alias()}')
                ids.append(m.contact_id)
            await room.say(some_thing=x)
        except AssertionError:
            pass

    await send(f'报时，现在时间是：{datetime.datetime.now()}')
    # await send('hello world !')


async def schedule(bot: Wechaty):
    # request打包
    request = Request()
    request.platform = 'Wechat'
    request.user_id = ''

    # 初始化分拣中心
    distributor = DistributorCron()

    async def execute(response_list):
        for response in response_list:
            if isinstance(response, ResponseGrpMsg):
                await send_to_group(group_id=response.group_id,
                                    x=response.text, at_list=response.at_list)
            elif isinstance(response, ResponseGrpImg):
                await send_to_group(group_id=response.group_id,
                                    x=FileBox.from_file(path=response.file))
            else:
                pass

    async def send_to_group(group_id, x, at_list=[]):
        # group_id as name (topic)
        try:
            room = await bot.Room.find(group_id)
            if not room:
                print('no room [{}] found'.format(group_id))
                return
            else:
                await room.ready()
                at_ids = []
                if at_list:
                    # 如果需要at，先获取群成员列表
                    members = await room.member_list()
                    for member in members:
                        # 对每个群成员依次检测
                        for at in at_list:
                            # 与用户名与id检测
                            if at in [member.name, member.contact_id]:
                                at_ids.append(member.contact_id)
                                break
                            # 群昵称检测，每个成员检查一次
                            room_alias = await room.alias(member=member)
                            if room_alias and at in room_alias:
                                at_ids.append(member.contact_id)
                                break
                await room.say(x, mention_ids=at_ids)
        except AssertionError:
            pass

    await execute(response_list=distributor.handle(request=request))
    distributor.refresh_and_save()


async def bot_main():
    """doc"""
    # pylint: disable=W0603
    global bot
    bot = MyBot()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(tick, 'interval', seconds=2000, args=[bot])
    scheduler.add_job(schedule, 'cron', hour='*', minute=0, args=[bot])
    scheduler.start()
    await bot.start()


def main():
    # os.environ['WECHATY_PUPPET_SERVICE_ENDPOINT'] = '127.0.0.1:8080'
    os.environ['WECHATY_PUPPET_SERVICE_ENDPOINT'] = WECHATY_ENV['endpoint']
    os.environ['WECHATY_PUPPET_SERVICE_TOKEN'] = WECHATY_ENV['token']
    os.environ['WECHATY_PUPPET'] = 'wechaty-puppet-service'
    asyncio.run(bot_main())