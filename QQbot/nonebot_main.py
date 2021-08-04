import nonebot, logging
from os import path
import MultiBot.QQbot.nonebot_config as config

logging.basicConfig(format=' %(asctime)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)


if __name__ == '__main__':
    nonebot.init(config)
    nonebot.load_builtin_plugins()
    nonebot.load_plugins(
        path.join(path.dirname(__file__), 'nonebot_plugins'),
        'nonebot_plugins'
    )
    nonebot.run()