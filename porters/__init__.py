"""
porters目录下的文件用于将机器人对接到各个平台
它们将平台上的消息打包成request交给分拣中心处理，并根据分拣中心返回的responses构造回复来发送给平台上的用户
子目录中各*_porter.py或*_main.py中的main函数可用于启动这些接口
参考目前的porter创建新的porter（如基于mirai的QQ机器人）也很方便
"""
