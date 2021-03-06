from .sessions.general import IntroSession, DescriptionSession, VersionSession, HelpSession, \
                              ErrorSession, HistorySession, RepeatSession, IdentitySession, EchoSession
from .sessions.counter import CounterSession
from .sessions.turing import TuringSession
from .sessions.student_info import InfoSession
from .sessions.baidu_ocr import OcrSession
from .sessions.qrcode import DeCodeSession, EnCodeSession
from .sessions.cq_command import CQCommandSession, CQRebootSession
from .sessions.cq_groups import CQGroupSuicideSession, CQGroupRandomSession
from .sessions.weather import WeatherSession, WindMapSession
from .sessions.subcovid import SubcovidSession, SubcovidManualSession
from .sessions.schedule import QQScheduleSession, WCScheduleSession, WCEScheduleSession
from .sessions.classroom_schedule import ClassroomScheduleSession, ClassroomScheduleUpdateSession
from .sessions.answer_box import AutoAnswerSession, AddAnswerSession
from .sessions.baidu_search import AutoBaiduSession
from .sessions.arxiv_brief import ArxivSession
from .sessions.alias_box import AutoAliasSession, AddAliasSession
from .sessions.translation import TranslationSession
from .sessions.tencent_voice import ActiveAudioSession, PassiveAudioSession
from .sessions.standby import StandbySession
from .sessions.subucassik import SubucassikSession
from .sessions.seplogin import SepLoginSession
from .sessions.music import MusicSession
from .sessions.covid_regions import CovidRiskSession, CovidRiskUpdateSession
from .sessions.subnaoc import SubNaocSession
from .sessions.user_note_search import UserNoteSession
from .sessions.wake_on_lan import WolSession
from .sessions.subscription import AddSubscriptionSession, DelSubscriptionSession, ListSubscriptionSession
from .sessions.popular import NbnhhshSession, BookOfAnswersSession, WebImgSession, \
                              FocusCubeSession, AsoulCnkiSession, UpSideDownTextSession, SlscqSession
from .sessions.perms_add import AddPermissionSession, DelPermissionSession
from .sessions.astropy import AstroPlotSession
from .sessions.cosmology import CosmoPlotSession
from .sessions.ipv6addr import Ipv6AddrSession
from .sessions.system_command import SystemCmdSession
from .sessions.covid_data import CovidDataSession, CovidDataUpdateSession
from .sessions.email_cas_trash import EmailCasTrashSession
from .sessions.account_book import AccountUpdateSession, AccountViewSession, AccountDelSession
from .sessions.reminder import AddReminderSession, DelReminderSession, ListReminderSession, \
                               UpdateReminderSession, CheckReminderSession
from .sessions.log_debug import LogSession
from .paths import PATHS
import os

# ?????????????????????sessions
NEW_SESSIONS = [IntroSession, DescriptionSession, VersionSession, HelpSession, ErrorSession, HistorySession,
                StandbySession, RepeatSession, IdentitySession, EchoSession, CounterSession, TuringSession,
                OcrSession, ActiveAudioSession, PassiveAudioSession,
                WeatherSession, WindMapSession, TranslationSession,
                NbnhhshSession, BookOfAnswersSession, WebImgSession,
                FocusCubeSession, AsoulCnkiSession, UpSideDownTextSession, SlscqSession,
                SubcovidSession, SubcovidManualSession, SubucassikSession, SepLoginSession,
                SubNaocSession, EmailCasTrashSession,
                UserNoteSession, InfoSession,
                DeCodeSession, EnCodeSession, WolSession,
                ClassroomScheduleSession, ClassroomScheduleUpdateSession,
                CovidRiskSession, CovidRiskUpdateSession, CovidDataSession, CovidDataUpdateSession,
                ArxivSession, AstroPlotSession, CosmoPlotSession, AutoBaiduSession, MusicSession,
                AutoAnswerSession, AddAnswerSession, AutoAliasSession, AddAliasSession,
                AddSubscriptionSession, DelSubscriptionSession, ListSubscriptionSession,
                AccountUpdateSession, AccountViewSession, AccountDelSession,
                AddReminderSession, DelReminderSession, ListReminderSession,
                UpdateReminderSession, CheckReminderSession,
                AddPermissionSession, DelPermissionSession, Ipv6AddrSession, SystemCmdSession,
                CQCommandSession, CQRebootSession, CQGroupSuicideSession, CQGroupRandomSession]

# ????????????????????????sessions
NEW_SESSIONS_CRON = [QQScheduleSession, WCScheduleSession, WCEScheduleSession]

# LogSession
LOG_SESSION = LogSession

# ??????????????????????????????
help_text = ''
for session_class in NEW_SESSIONS + [LOG_SESSION] + NEW_SESSIONS_CRON:
    help_text += session_class('').brief_help()
    help_text += '\n'

with open(os.path.join(PATHS['data'], 'help_description.txt'), 'w') as f:
    f.write(help_text[:-2])

