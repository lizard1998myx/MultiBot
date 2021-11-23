import pickle, os, traceback, time
from .session_initialize import NEW_SESSIONS, NEW_SESSIONS_CRON
from .responses import Response, ResponseMsg
from .requests import Request
from .paths import PATHS

ACTIVE_SESSIONS = os.path.join(PATHS['data'], 'active_sessions.data')
HISTORY_DIR = PATHS['history']
SAVE_HISTORY = True


# 分拣中心，对于每个来自各聊天软件接口的Request，寻找活动的Session或创建合适的Session
class Distributor:
    def __init__(self):
        self.active_sessions = []  # 初始化活动Session列表
        self.current_session = None  # 暂存Session，用于和各聊天软件接口沟通
        self._load_sessions()  # 载入存在硬盘里的活动Session
        self._new_session = NEW_SESSIONS  # 创建新Session时的列表
        self._max_iterate = 10

    # 载入硬盘里的活动Session，不做任何判断
    def _load_sessions(self):
        try:
            with open(ACTIVE_SESSIONS, 'rb') as f:
                self.active_sessions = pickle.load(f)
        except FileNotFoundError:
            self._save_sessions()
        except EOFError:
            self._save_sessions()

    # 把活动Session列表保存回硬盘中
    def _save_sessions(self):
        with open(ACTIVE_SESSIONS, 'wb') as f:
            pickle.dump(self.active_sessions, f)

    # 刷新活动Session表（检查）并保存
    def refresh_and_save(self, save=True):
        new_list = []
        for session in self.active_sessions:
            if session.is_active():
                new_list.append(session)
        self.active_sessions = new_list
        if save:
            self._save_sessions()

    # 检查request是否在活动Session表中，若在，则返回True并将session放到current_session中
    def use_active(self, request, save=True):
        self.refresh_and_save(save=save)
        # 在活动Session表中检查，若有符合的（用户id相同并且Request合法），采用该Session的处理方法
        if not request.echo:
            for session in self.active_sessions:
                if request.user_id == session.user_id:
                    if session.is_legal_request(request=request):
                        session.refresh()
                        self.current_session = session
                        return True
                    else:  # 相同id但Request不合法，对应Session会被关闭
                        session.deactivate()
        # request需要echo或不存在活动session时，返回False
        # echo一般是预处理出现问题时返回报错使用的
        return False

    # 处理任意Request，返回Response序列
    def handle(self, request, debug=True):
        session = None
        if self.use_active(request=request):
            # 若在活动Session表中，采用该Session的处理方法
            # .use_active方法将current_session置为[active_session]
            session = self.current_session
            pass
            # return make_list(self.current_session.handle(request=request))
        else:
            # 如果没有符合条件的活动Session，新建一个Session（Possibility最高者）
            self.current_session = None
            max_possibility = 0
            for session_class_candidate in self._new_session:
                session_candidate = session_class_candidate(user_id=request.user_id)
                if session_candidate.is_legal_request(request=request):
                    possibility = session_candidate.probability_to_call(request=request)
                    if possibility > max_possibility:
                        session = session_candidate
                        max_possibility = possibility
            if max_possibility > 0:
                # 把新Session存入内存的表中，把Request交给新Session处理
                self.active_sessions.append(session)
                self.current_session = session
                if SAVE_HISTORY:
                    filename = os.path.join(HISTORY_DIR, f'{request.platform}_{session.session_type}_{time.time()}.txt')
                    with open(filename, 'w') as f:
                        f.write(f'platform={request.platform}\n'
                                f'user_id={request.user_id}\n'
                                f'session={session.session_type}\n'
                                f'time={time.time()}')

        # 统一处理current_session
        if session is not None:
            responses = []
            try:
                raw_results = make_list(session.handle(request=request))
                for r in raw_results:
                    if isinstance(r, Response):
                        responses.append(r)
                    elif isinstance(r, Request):  # iterate handling requests
                        self._max_iterate -= 1
                        if self._max_iterate <= 0:
                            pass
                        else:
                            responses += self.handle(request=r, debug=debug)
            except:
                session.deactivate()
                if debug:
                    # 如果debug，将错误信息返回
                    responses.append(ResponseMsg(traceback.format_exc()))
                    # 不debug则返回空气
            finally:
                return responses
        else:  # 若没有active session，且Possibility均为0，不返回Response
            return []

    # 在原Session中继续处理output，返回后续的Response序列
    def process_output(self, output):
        assert self.current_session is not None
        self.current_session.refresh()
        return make_list(self.current_session.process_output(output=output))


# 定时器的分拣中心，接收来自定时器的Request
class DistributorCron(Distributor):
    def __init__(self):
        Distributor.__init__(self)
        self._new_session = NEW_SESSIONS_CRON  # 定时器专属的新Session列表


# 把原始response转化为序列
def make_list(raw_response):
    if isinstance(raw_response, list):
        return raw_response
    else:
        return [raw_response]
