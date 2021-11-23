from ...server_config import FLASK_PORTS, CQHTTP_URL
import flask, threading, requests, os

PLATFORM = 'CQ'
SERVER_ACTIVE = True

app = flask.Flask(__name__)
# app.debug = True


@app.route('/', methods=['GET', 'POST'])
def service():
    CQHttpPorter.execute_form(flask.request.form.to_dict())
    return {}


class CQHttpPorter:
    @staticmethod
    def execute_form(form_dict: dict):
        user_id = form_dict.get('user_id')
        group_id = form_dict.get('group_id')
        assert (user_id is None) ^ (group_id is None)
        msg = form_dict.get('msg', '')
        img = form_dict.get('img')
        if img is not None:
            img = os.path.abspath(img)
            msg += '[CQ:image,file=file:///%s]' % img.replace(':', ':\\')
        requests.get('%s/send_msg' % CQHTTP_URL, {'user_id': user_id, 'group_id': group_id,
                                                  'message': msg})


def main():
    if SERVER_ACTIVE:
        threading.Thread(target=app.run, kwargs={'port': FLASK_PORTS[PLATFORM]}, daemon=True).start()