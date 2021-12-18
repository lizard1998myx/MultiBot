class Request:
    def __init__(self):
        self.platform = None
        self.user_id = None
        self.group_id = None
        self.msg = None
        self.img = None
        self.aud = None  # audio
        self.loc = None
        self.attachment = None
        self.echo = False
        self.from_scheduler = False  # 表示来自schedule

    def new(self, msg=None, img=None):
        new_req = Request()
        new_req.platform = self.platform
        new_req.user_id = self.user_id
        new_req.group_id = self.group_id
        new_req.msg = msg
        new_req.img = img
        return new_req

    def info(self):
        return f'properties: {self.platform}, {self.user_id}, {self.group_id}\n' \
               f'content: \nmsg="{self.msg}",\nimg={self.img},\n' \
               f'aud={self.aud}, loc={self.loc}, att={self.attachment}'