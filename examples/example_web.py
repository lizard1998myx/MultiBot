try:
    from MultiBot import integrate_web_main
except ModuleNotFoundError:
    import sys
    sys.path.append(r'C:\Users\Yuxi\PycharmProjects\untitled')
    from MultiBot import integrate_web_main


if __name__ == '__main__':
    integrate_web_main()
