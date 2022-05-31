from .general import Session
from ..responses import ResponseMsg
from ..paths import PATHS
from ..utils import format_filename
import os, pickle

LOG_DIR = os.path.join(PATHS['temp'], 'debug')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


class LogSession(Session):
    def __init__(self, user_id):
        Session.__init__(self, user_id=user_id)
        self.session_type = '报错记录'
        self.description = '后台模块，用于记录报错信息'
        self._max_delta = 60

    def handle(self, request):
        self.deactivate()
        if not request.msg:  # empty reply
            return [ResponseMsg(f'【{self.session_type}】不记录报错信息。'),
                    request]
        elif request.msg.lower()[0] in ['y', '是', '好']:
            self._save_log()
            return ResponseMsg(f'【{self.session_type}】报错信息记录完毕。')
        else:
            return [ResponseMsg(f'【{self.session_type}】不记录报错信息。'),
                    request]

    def _save_log(self):
        filename = os.path.join(LOG_DIR, format_filename(header='Debug', type='log', post='', abs_path=False))
        with open(filename, 'wb') as f:
            pickle.dump(self.log, file=f)


