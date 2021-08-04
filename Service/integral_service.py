from MultiBot.ConsoleIO.console_porter import ConsolePorter
from MultiBot.EMail.email_porter import MailPorter
from MultiBot.QQbot.cq_server import CQHttpPorter
from MultiBot.server_config import FLASK_PORTS
import flask, threading, time

app = flask.Flask(__name__)
# app.debug = True
FLASK_PORTS['Integral']


@app.route('/', methods=['GET', 'POST'])
def service():
    form = flask.request.form.to_dict()
    print(form)
    platform = form.get('platform', 'Console')
    if platform == 'Console':
        ConsolePorter.execute_form(form)
    elif platform == 'Mail':
        MailPorter.execute_form(form)
    elif platform == 'CQ':
        CQHttpPorter.execute_form(form)
    return {}


if __name__ == '__main__':
    print('Welcome to Integral MultiBot Interface!')
    print('Initiating...')
    time.sleep(0.5)
    threading.Thread(target=app.run, kwargs={'port': FLASK_PORTS['Integral']}, daemon=True).start()
    time.sleep(3)
    # app.run(port=FLASK_PORTS['Integral'])
    while True:
        ConsolePorter.interface(input('Integral MultiBot:'))
