import sys
from expiringdict import ExpiringDict
from telebot.apihelper import ApiException
import traceback

PEER_ERROR = ('¡Tienes que hablar conmigo por privado primero! '
              'pulsa sobre mi nombre para iniciar una nueva conversación, y '
              'ya entonces podrás ejecutar los comandos.')
CREATOR = '@nekmo'


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
        def catch_command_error(fn):
            def wrapper(message, *args, **kwargs):
                try:
                    return fn(message, *args, **kwargs)
                except Exception as e:
                    print('Ha ocurrido un error! Message: {} Exception: {}'.format(message, e))
                    traceback.print_exc(file=sys.stdout)
                    self.bot.send_message(message.chat.id, '¡Nadie es perfecto! El comando ha fallado. Vuelve a '
                                                           'intentarlo más tarde. Si sigue dando problemas, '
                                                           'comunícate con {}. Error: {}'.format(CREATOR, e))
            return wrapper

        self.main.set_handler(catch_command_error(self.start), commands=self.commands)

    def start(self, message):
        raise NotImplementedError


class Assistant(Command):
    def __init__(self, main):
        super().__init__(main)
        self.user_dict = ExpiringDict(300, 60 * 60 * 4)

    def validate_choices(self, message, choices, valid_none_message=False):
        if message.text is None and valid_none_message:
            return True
        if message.text and message.text.startswith('/'):
            self.bot.reply_to(message, 'Se ha comenzado otro comando. ¡Hasta otra!')
            raise ValueError
        elif message.text not in choices:
            self.bot.reply_to(message, '¡No puedes elegir esa opción!')
            return False
        return True

    def write_user_dict(self, message, key, value):
        if message.from_user.id not in self.user_dict:
            try:
                self.bot.send_message(message.chat.id, 'Sesión expirada. Finalizando.')
            except Exception:
                pass
            return False
        self.user_dict[message.from_user.id][key] = value
        return True

