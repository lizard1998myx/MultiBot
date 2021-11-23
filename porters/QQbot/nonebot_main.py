import nonebot, logging, os
from . import nonebot_config as config
from ...paths import PATHS

logging.basicConfig(format=' %(asctime)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)


def main(plugin_module_name='nonebot_plugins'):
    nonebot.init(config)
    nonebot.load_builtin_plugins()
    nonebot.load_plugins(
        os.path.join(PATHS['cqbot'], 'nonebot_plugins'),
        plugin_module_name
    )
    nonebot.run()