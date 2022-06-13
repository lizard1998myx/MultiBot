try:
    from MultiBot import my_qq_main
except ModuleNotFoundError:
    import sys
    sys.path.append(r'C:\Users\Yuxi\PycharmProjects\untitled')
    from MultiBot import my_qq_main


if __name__ == '__main__':
    my_qq_main()
