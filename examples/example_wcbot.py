try:
    from MultiBot import wc_main
except ModuleNotFoundError:
    import sys
    sys.path.append(r'C:\Users\Yuxi\PycharmProjects\untitled')
    from MultiBot import wc_main


if __name__ == '__main__':
    wc_main()
