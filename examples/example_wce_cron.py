try:
    from MultiBot import wce_main_cron
except ModuleNotFoundError:
    import sys
    sys.path.append(r'C:\Users\Yuxi\PycharmProjects\untitled')
    from MultiBot import wce_main_cron


if __name__ == '__main__':
    wce_main_cron()
