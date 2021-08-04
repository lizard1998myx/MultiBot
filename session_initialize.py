from MultiBot.sessions.general import IntroSession, DescriptionSession, VersionSession, HelpSession, ErrorSession
from MultiBot.sessions.general import RepeatSession, IdentitySession
from MultiBot.sessions.counter import CounterSession
from MultiBot.sessions.turing import TuringSession
from MultiBot.sessions.student_info import InfoSession
from MultiBot.sessions.baidu_ocr import OcrSession
from MultiBot.sessions.qrcode import DeCodeSession, EnCodeSession
from MultiBot.sessions.cq_command import CQCommandSession, CQRebootSession
from MultiBot.sessions.cq_groups import CQGroupSuicideSession, CQGroupRandomSession
from MultiBot.sessions.weather import WeatherSession
from MultiBot.sessions.subcovid import SubcovidSession
from MultiBot.sessions.qq_schedule import QQScheduleSession
from MultiBot.sessions.wechat_schedule import WCScheduleSession
from MultiBot.sessions.classroom_schedule import ClassroomScheduleSession
from MultiBot.sessions.answer_box import AutoAnswerSession, AddAnswerSession
from MultiBot.sessions.baidu_search import AutoBaiduSession
from MultiBot.sessions.arxiv_brief import ArxivSession
from MultiBot.sessions.alias_box import AutoAliasSession, AddAliasSession
from MultiBot.sessions.translation import TranslationSession
from MultiBot.sessions.tencent_voice import ActiveAudioSession, PassiveAudioSession
from MultiBot.sessions.standby import StandbySession
from MultiBot.sessions.subucassik import SubucassikSession
from MultiBot.sessions.seplogin import SepLoginSession
from MultiBot.sessions.music import NetEaseSongSession
import os

NEW_SESSIONS = [IntroSession, DescriptionSession, VersionSession, HelpSession, ErrorSession, StandbySession,
                RepeatSession, IdentitySession, CounterSession, TuringSession, InfoSession,
                OcrSession, ActiveAudioSession, PassiveAudioSession,
                WeatherSession, TranslationSession, SubcovidSession, SubucassikSession, SepLoginSession,
                DeCodeSession, EnCodeSession,
                ClassroomScheduleSession, ArxivSession, AutoBaiduSession, NetEaseSongSession,
                AutoAnswerSession, AddAnswerSession, AutoAliasSession, AddAliasSession,
                CQCommandSession, CQRebootSession, CQGroupSuicideSession, CQGroupRandomSession]
NEW_SESSIONS_CRON = [QQScheduleSession, WCScheduleSession]

help_text = ''
for session_class in NEW_SESSIONS + NEW_SESSIONS_CRON:
    help_text += session_class('').help()
    help_text += '\n\n'

with open(os.path.join('..', 'data', 'help_description.txt'), 'w') as f:
    f.write(help_text[:-2])