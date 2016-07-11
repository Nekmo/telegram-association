import json

import os
import requests
import telebot
from expiringdict import ExpiringDict
from telebot import types

from .db import get_engine, get_session

NOMINATIM_URL = 'http://nominatim.openstreetmap.org/'
REVERSE_NOMINATIM_URL = '{}reverse'.format(NOMINATIM_URL)

MESSAGE = ("¡Te damos la bienvenida, {user}! ¡Te encuentras en un "
           "grupo donde habitan unas criaturas llamadas humanos! Recuerda "
           "saludarles y decirles de donde eres. \n"
           "Formato: @NickTelegram NickPokémonGO Color Lugar")

ALIAS_REQUIRED_ERROR = ('Lo siento! necesito que te pongas previamente '
                        'un alias en Telegram para comenzar el registro.\n'
                        'Android: http://bit.ly/29q58ex')

GEOLOCATION_REQUIRED = ('¡Tu nueva aventura comienza donde tú digas! Necesito que '
                        'me autorices a ver tu ubicación para saber por donde sueles '
                        'capturar. ¡No te preocupes! En ningún caso aparecerá información '
                        'como la calle.')

GEOLOCATION_CHOICE = '¡Geolocalización, te elijo a ti!'
MANUAL_GEOLOCATION_CHOICE = 'Aburrida introducción manual'
EXIT_CHOICE = 'Huir'

TRUE_CHOICE = 'Sí'
FALSE_CHOICE = 'No'

TEAMS = ['Amarillo', 'Azul', 'Rojo']
NO_TEAM = 'No lo sé/No tengo'


def query_nominatim(query):
    try:
        data = requests.get(NOMINATIM_URL, {'q': query, 'addressdetails': '1', 'format': 'json', 'limit': '1'}).json()
    except Exception:
        raise ValueError
    if not len(data) or not data[0]['address']:
        raise ValueError
    return data[0]


def reverse_nominatim(lat, lon):
    try:
        data = requests.get(REVERSE_NOMINATIM_URL, {'lat': lat, 'lon': lon, 'format': 'json'}).json()
        return data['address']
    except KeyError:
        raise ValueError


def get_name(name_data):
    return ' '.join(filter(lambda x: x, [name_data.first_name, name_data.last_name]))


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
    engine = None
    user_dict = ExpiringDict(300, 60 * 60 * 4)

    def __init__(self, config_path):
        self.config = Config(config_path)
        self.init()

    def init(self):
        self.bot = telebot.TeleBot(self.config['api_token'])
        self.set_handlers()
        self.engine = get_engine('sqlite:///db.sqlite3')

    def get_engine(self, url):
        return get_engine(url)

    def get_session(self, engine=None):
        engine = engine or self.engine
        return get_session(engine)

    def set_handlers(self, bot=None):
        bot = bot or self.bot
        bot.message_handler(func=lambda m: True, content_types=['new_chat_member'])(self.new_member)
        # bot.message_handler(func=lambda m: True, content_types=['location'])(self.user_location)
        bot.message_handler(commands=['register', 'start'])(self.command_register)

    def new_member(self, message):
        self.bot.reply_to(message, MESSAGE.format(user=get_name(message.new_chat_member)))

    def command_register(self, message):
        print('Register:')
        if not message.from_user.username:
            try:
                return self.bot.reply_to(ALIAS_REQUIRED_ERROR, message)
            except AttributeError:
                return
        self.user_dict[message.chat.id] = {}
        self.step_request_location(message)

    def step_request_location(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=3)
        markup.add(types.KeyboardButton(GEOLOCATION_CHOICE, request_location=True))
        markup.add(types.KeyboardButton(MANUAL_GEOLOCATION_CHOICE))
        markup.add(types.KeyboardButton(EXIT_CHOICE))
        msg = self.bot.send_message(message.from_user.id, GEOLOCATION_REQUIRED, reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.step_get_location)

    def step_get_location(self, message):
        try:
            if not self.validate_choices(message, [EXIT_CHOICE, MANUAL_GEOLOCATION_CHOICE, GEOLOCATION_CHOICE], True):
                return self.step_request_manual_location(message)
        except ValueError:
            return
        if message.text == GEOLOCATION_CHOICE and not message.location:
            self.bot.reply_to(message, 'Parece que tu versión de Telegram no soporta geolocalización.')
            return self.step_request_manual_location(message)
        elif message.text == EXIT_CHOICE:
            return self.step_exit(message)
        elif message.text == MANUAL_GEOLOCATION_CHOICE:
            return self.step_request_manual_location(message)
        try:
            address = reverse_nominatim(message.location.latitude, message.location.longitude)
        except ValueError:
            self.bot.reply_to(message, '¡Lo siento! No he podido interpretar la dirección. Se va a iniciar '
                                       'el modo manual.')
            return self.step_request_manual_location(message)
        self.process_address(address, message)

    def step_request_manual_location(self, message):
        markup = types.ForceReply(selective=False)
        msg = self.bot.send_message(message.from_user.id, "Introduce la dirección completa", reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.step_get_manual_location)

    def step_get_manual_location(self, message):
        try:
            data = query_nominatim(message.text)
        except ValueError:
            self.bot.reply_to(message, 'Estoy buscando esa dirección, pero no encuentro nada. ¿Por qué '
                                       'no pruebas a volver a escribirla?')
            return self.step_request_manual_location(message)
        self.bot.send_location(message.from_user.id, data['lat'], data['lon'])
        self.process_address(data['address'], message)

    def process_address(self, address, message):
        zone = ' '.join(list(filter(lambda x: x,
                                    [address.get('suburb'), address.get('city_district'), address.get('town'),
                                     address.get('city')])))
        self.bot.reply_to(message, 'Información útil encontrada: {}, {} {} {}'.format(
            zone, address.get('state_district', address.get('county', '-')), address['state'], address['country']
        ))
        if not self.write_user_dict(message, 'address', address):
            return
        self.step_request_color(message)

    def step_request_color(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=len(TEAMS) + 1)
        for team in TEAMS:
            markup.add(types.KeyboardButton(team))
        markup.add(types.KeyboardButton(NO_TEAM))
        msg = self.bot.send_message(message.from_user.id, '¿Cual es tu equipo?', reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.step_get_color)

    def step_get_color(self, message):
        try:
            if not self.validate_choices(message, TEAMS + [NO_TEAM]):
                return self.step_request_color(message)
        except ValueError:
            return
        color = message.text if message.text in TEAMS else None
        if not self.write_user_dict(message, 'color', color):
            return
        self.step_request_nick(message)

    def step_request_nick(self, message):
        markup = types.ForceReply(selective=False)
        msg = self.bot.send_message(message.from_user.id, "¿Y cómo te llamas en Pokémon GO?", reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.step_get_nick)

    def step_get_nick(self, message):
        self.bot.send_message(message.from_user.id, "Yo no tengo ni idea, ¡pero es un nombre muy bonito!")
        if not self.write_user_dict(message, 'nick', message.text):
            return
        return self.step_finish(message)

    def step_request_notifications(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=2)
        for team in [TRUE_CHOICE, FALSE_CHOICE]:
            markup.add(types.KeyboardButton(team))
        markup.add(types.KeyboardButton(NO_TEAM))
        msg = self.bot.send_message(message.from_user.id, '¿Deseas recibir notificaciones cuando se registre '
                                                          'alguien que viva cerca tuya?',
                                    reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.step_get_color)

    def step_finish(self, message):
        data = self.user_dict.get(message.chat.id)
        if not data:
            return self.bot.send_message(message.chat.id, '¡La sesión expiró antes de finalizar!')
        print(data)

    def step_exit(self, message):
        markup = types.ReplyKeyboardHide(selective=False)
        self.bot.send_message(message.from_user.id, "{} huyó del combate con lágrimas en los ojos.".format(
            get_name(message.from_user)
        ), reply_markup=markup)

    def validate_choices(self, message, choices, valid_none_message=False):
        if message.text is None and valid_none_message:
            return True
        if message.text.startswith('/'):
            self.bot.reply_to(message, 'Se ha comenzado otro comando. ¡Hasta otra!')
            raise ValueError
        elif message.text not in choices:
            self.bot.reply_to(message, '¡No puedes elegir esa opción!')
            return False
        return True

    def write_user_dict(self, message, key, value):
        if not message.chat.id in self.user_dict:
            try:
                self.bot.send_message(message.chat.id, 'Sesión expirada. Finalizando.')
            except Exception:
                pass
            return False
        self.user_dict[message.chat.id][key] = value
        return True

    def poll(self):
        self.bot.polling(none_stop=False, interval=0)
