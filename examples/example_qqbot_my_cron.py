try:
    from MultiBot import my_qq_main_cron
except ModuleNotFoundError:
    import sys
    sys.path.append(r'C:\Users\Yuxi\PycharmProjects\untitled')
    from MultiBot import my_qq_main_cron


if __name__ == '__main__':
    my_qq_main_cron()
