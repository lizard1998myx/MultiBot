try:
    from MultiBot import web_main, server_config
except ModuleNotFoundError:
    import sys
    sys.path.append(r'C:\Users\Yuxi\PycharmProjects\untitled')
    from MultiBot import web_main, server_config


if __name__ == '__main__':
    web_main({'host': '::',
              'port': server_config.FLASK_PORTS['Web6']})
