# import main function from porters
from .porters.ConsoleIO.console_porter import main as console_main
from .porters.EMail.email_porter import main as email_main
from .porters.QQbot.nonebot_main import main as qq_main
from .porters.QQbot.cq_server import main as qq_server_main
from .porters.QQbot.my_cqhttp_porter import main as my_qq_main
from .porters.QQbot.my_cqhttp_cron import main as my_qq_main_cron
from .porters.WCbot.wc_porter import main as wc_main
from .porters.WCPublic.wcp_flask import main as wcp_main
from .porters.WCEnterprise.wce_flask import main as wce_main
from .porters.WCEnterprise.wce_flask import cron_main as wce_main_cron
from .porters.WebApp.web_app import main as web_main
from .porters.WebApp.integrate_web import main as integrate_web_main
from .porters.Service.integral_service import main as integrate_server_main

from .porters.Service.clients import MultiBotClient

