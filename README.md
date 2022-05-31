# MultiBot

运行于QQ、微信公众号、网页上的聊天机器人

sessions目录下有一些插件可供参考

## 插件举例

聊天：闲聊、天气、点歌、翻译、留言查询

记录：订阅、记账、任务提醒

工具：问答机、同义词机、OCR、定时任务、语音识别、二维码

管理：ipv6地址、执行命令、权限管理、远程唤醒

科研：arxiv搜索、天体轨迹、宇宙学计算

爬虫：空教室、疫情风险和感染数据、疫情填报、出校申报、查成绩

## 说明

已更新3.5.1版本，要求python版本在3.8以上，否则无法解析f字符串

## 安装

```sh
$ cd /home
$ git clone https://github.com/lizard1998myx/MultiBot
$ pip install -r ./MultiBot/requirements
```

### 使用

```python
import MultiBot
MultiBot.integrate_server_main()  # 第一种：运行命令行版本
MultiBot.integrate_web_main()  # 第二种：运行Web版本
```

### 问题解决

1. api问题请查看api_tokens.py中的说明，并将获取的token存到data目录下的表格中；

2. import时遇到“Unable to find zbar shared library”：

```sh
$ apt install libzbar-dev
```
