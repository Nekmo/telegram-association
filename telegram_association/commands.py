from expiringdict import ExpiringDict
from telebot.apihelper import ApiException


PEER_ERROR = ('¡Tienes que hablar conmigo por privado primero! '
              'pulsa sobre mi nombre para iniciar una nueva conversación, y '
              'ya entonces podrás ejecutar los comandos.')


class Command(object):
    commands = None

    def __init__(self, main):
        self.main = main
        self.bot = main.bot
        self.get_session = main.get_session

    def send_private(self, message, *args, **kwargs):
        try:
            return self.bot.send_message(message.from_user.id, *args, **kwargs)
        except ApiException as e:
            if e.result.status_code == 400 and 'PEER_ID_INVALID' in e.result.text:
                return self.bot.send_message(message.chat.id, PEER_ERROR)
            raise e

    def set_handler(self):
        self.main.set_handler(self.start, commands=self.commands)

    def start(self, message):
        raise NotImplementedError


class Assistant(Command):
    def __init__(self, main):
        super().__init__(main)
        self.user_dict = ExpiringDict(300, 60 * 60 * 4)
