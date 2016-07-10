import json

import telebot
from telebot import types

MESSAGE = ("¡Te damos la bienvenida, {user}! ¡Te encuentras en un "
           "grupo donde habitan unas criaturas llamadas humanos! Recuerda "
           "saludarles y decirles de donde eres. \n"
           "Formato: @NickTelegram NickPokémonGO Color Lugar")

ALIAS_REQUIRED_ERROR = ('Lo siento! necesito que te pongas previamente '
                        'un alias en Telegram para comenzar el registro.\n'
                        'Android: http://bit.ly/29q58ex')


class Config(dict):
    def __init__(self, path, **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.read(self.path)

    def read(self, path):
        path = path or self.path
        self.clear()
        self.update(json.load(open(path)))


class AssociationBot(object):
    bot = None

    def __init__(self, config_path):
        self.config = Config(config_path)
        self.init()

    def init(self):
        self.bot = telebot.TeleBot(self.config['api_token'])
        self.set_handlers()

    def set_handlers(self, bot=None):
        bot = bot or self.bot
        bot.message_handler(func=lambda m: True, content_types=['new_chat_member'])(self.new_member)
        bot.message_handler(commands=['register', 'start'])(self.command_register)

    def new_member(self, message):
        print('New member: ', str(message))
        user = ' '.join(filter(lambda x: x, [message.new_chat_member.first_name, message.new_chat_member.last_name]))
        self.bot.reply_to(message, MESSAGE.format(user=user))

    def command_register(self, message):
        print('register!')
        if not message.from_user.username:
            return self.bot.reply_to(ALIAS_REQUIRED_ERROR, message)
        markup = types.ReplyKeyboardMarkup(row_width=1)
        markup.add(types.KeyboardButton('Dar mi posición', request_location=True))
        self.bot.send_message(message.from_user.id, '¡Necesito saber tu localización!', reply_markup=markup)


    def poll(self):
        print('Run!')
        self.bot.polling(none_stop=False, interval=0)
