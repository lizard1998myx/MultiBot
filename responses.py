class Response:
    def __init__(self):
        pass


class ResponseMsg(Response):
    def __init__(self, text='', user_id=''):
        Response.__init__(self)
        self.user_id = user_id  # optional
        self.text = text
        self.at_list = []


class ResponseImg(Response):
    def __init__(self, file='', user_id=''):
        Response.__init__(self)
        self.user_id = user_id  # optional
        self.file = file


class ResponseMusic(Response):
    def __init__(self, name=None, singer=None, link=None, music_id=None, platform=None, user_id=''):
        Response.__init__(self)
        self.user_id = user_id  # optional
        self.name = name
        self.singer = singer
        self.link = link
        self.music_id = music_id
        self.platform = platform

    def info(self):
        return f'{self.name}\n{self.link}'


class ResponseCQFunc(Response):
    def __init__(self, func_name='', kwargs={}):
        Response.__init__(self)
        self.func_name = func_name
        self.kwargs = kwargs


class ResponseGrpMsg(Response):
    def __init__(self, group_id='', text=''):
        Response.__init__(self)
        self.group_id = group_id
        self.text = text
        self.at_list = []


class ResponseGrpImg(Response):
    def __init__(self, group_id='', file=''):
        Response.__init__(self)
        self.group_id = group_id
        self.file = file

