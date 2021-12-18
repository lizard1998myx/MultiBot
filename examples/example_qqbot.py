try:
    from MultiBot import qq_main
except ModuleNotFoundError:
    import sys
    sys.path.append(r'C:\Users\Yuxi\PycharmProjects\untitled')
    from MultiBot import qq_main


if __name__ == '__main__':
    qq_main(plugin_module_name='MultiBot.porters.QQbot.nonebot_plugins')
