try:
    from MultiBot import integrate_server_main
except ModuleNotFoundError:
    import sys
    sys.path.append(r'C:\Users\Yuxi\PycharmProjects\untitled')
    from MultiBot import integrate_server_main


if __name__ == '__main__':
    integrate_server_main()
