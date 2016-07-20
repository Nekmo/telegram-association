import telebot

from telegram_association.config import Config
from telegram_association.db import LocationZone
from telegram_association.help import Help
from telegram_association.register import Register
from telegram_association.results import Search
from telegram_association.utils.telegram import securize_message, get_name
from .db import get_engine, get_sessionmaker, User

MESSAGE = ("¡Te damos la bienvenida, {user}! ¡Te encuentras en un "
           "grupo donde habitan unas criaturas llamadas humanos!\n\n"
           "Para comenzar tu aventura, pulsa primero en @profOakBot "
           "para abrir el chat y luego escribe /register")


class AssociationBot(object):
    bot = None
    engine = None
    sessionmaker = None
    commands = (Register, Search, Help)

    def __init__(self, config_path):
        self.config = Config(config_path)
        self.init()

    def init(self):
        self.bot = telebot.TeleBot(self.config['api_token'])
        self.set_handlers()
        self.set_command_handlers()
        # 'sqlite:///db.sqlite3'
        self.engine = self.get_engine(self.config['db_url'])
        self.sessionmaker = self.get_sessionmaker()
        pass

    def set_command_handlers(self):
        for command in self.commands:
            cmd = command(self)
            cmd.set_handler()

    def get_engine(self, url):
        return get_engine(url)

    def get_sessionmaker(self, engine=None):
        engine = engine or self.engine
        return get_sessionmaker(engine)

    def get_session(self, sessionmaker=None, engine=None):
        sessionmaker = sessionmaker or self.sessionmaker
        engine = engine or self.engine
        session = sessionmaker()
        # session.configure(bind=engine)
        return session

    def set_handlers(self):
        # TODO:
        # self.set_handler(self.new_member, func=lambda m: True, content_types=['new_chat_member'])
        # self.set_handler(self.command_register, commands=['register', 'start'])
        # self.set_handler(self.command_all, commands=['all'])
        # self.set_handler(self.command_search, commands=['search'])
        pass

    def set_handler(self, command, *args, **kwargs):
        return self.bot.message_handler(*args, **kwargs)(securize_message(command))

    def new_member(self, message):
        self.bot.reply_to(message, MESSAGE.format(user=get_name(message.new_chat_member)))

    def poll(self):
        self.bot.polling(none_stop=True, interval=0)
