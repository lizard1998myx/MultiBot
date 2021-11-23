from .sessions.general import IntroSession, DescriptionSession, VersionSession, HelpSession, ErrorSession, HistorySession
from .sessions.general import RepeatSession, IdentitySession
from .sessions.counter import CounterSession
from .sessions.turing import TuringSession
from .sessions.student_info import InfoSession
from .sessions.baidu_ocr import OcrSession
from .sessions.qrcode import DeCodeSession, EnCodeSession
from .sessions.cq_command import CQCommandSession, CQRebootSession
from .sessions.cq_groups import CQGroupSuicideSession, CQGroupRandomSession
from .sessions.weather import WeatherSession
from .sessions.subcovid import SubcovidSession
from .sessions.schedule import QQScheduleSession, WCScheduleSession
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
from .sessions.music import NetEaseSongSession
from .sessions.covid_regions import CovidRiskSession, CovidRiskUpdateSession
from .sessions.subnaoc import SubNaocSession
from .sessions.user_note_search import UserNoteSession
from .paths import PATHS
import os

NEW_SESSIONS = [IntroSession, DescriptionSession, VersionSession, HelpSession, ErrorSession, HistorySession,
                StandbySession, RepeatSession, IdentitySession, CounterSession, TuringSession, InfoSession,
                OcrSession, ActiveAudioSession, PassiveAudioSession,
                WeatherSession, TranslationSession,
                SubcovidSession, SubucassikSession, SepLoginSession, SubNaocSession, UserNoteSession,
                DeCodeSession, EnCodeSession,
                ClassroomScheduleSession, ClassroomScheduleUpdateSession,
                CovidRiskSession, CovidRiskUpdateSession,
                ArxivSession, AutoBaiduSession, NetEaseSongSession,
                AutoAnswerSession, AddAnswerSession, AutoAliasSession, AddAliasSession,
                CQCommandSession, CQRebootSession, CQGroupSuicideSession, CQGroupRandomSession]
NEW_SESSIONS_CRON = [QQScheduleSession, WCScheduleSession]

help_text = ''
for session_class in NEW_SESSIONS + NEW_SESSIONS_CRON:
    help_text += session_class('').help()
    help_text += '\n\n'

with open(os.path.join(PATHS['data'], 'help_description.txt'), 'w') as f:
    f.write(help_text[:-2])