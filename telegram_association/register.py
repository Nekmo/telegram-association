import sys
from telebot import types

from .utils.telegram import get_name
from .utils.geo import reverse_nominatim, query_nominatim
from .commands import Assistant
from .db import User, LocationZone

ALIAS_REQUIRED_ERROR = ('Lo siento! necesito que te pongas previamente '
                        'un alias en Telegram para comenzar el registro.\n'
                        'Android: http://bit.ly/29q58ex\n'
                        'iPhone: http://bit.ly/29MPAOM')

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


class Register(Assistant):
    commands = ('register',)

    def start(self, message):
        print('Register:')
        if message.chat.type != 'private':
            return self.bot.reply_to(message, '¡Este comando debe usarse por privado! Pulsa aquí -> @profOakBot <- '
                                              'para comenzar una conversación privada conmigo, y vuelve a ejecutar '
                                              'el comando.')
        if not message.from_user.username:
            try:
                return self.bot.reply_to(message, ALIAS_REQUIRED_ERROR)
            except AttributeError:
                return
        self.user_dict[message.from_user.id] = {}
        self.step_request_location(message)

    def step_request_location(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=3)
        markup.add(types.KeyboardButton(GEOLOCATION_CHOICE, request_location=True))
        markup.add(types.KeyboardButton(MANUAL_GEOLOCATION_CHOICE))
        markup.add(types.KeyboardButton(EXIT_CHOICE))
        msg = self.send_private(message, GEOLOCATION_REQUIRED, reply_markup=markup)
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
        elif message.location is None:
            self.bot.reply_to(message, 'La respuesta no es válida.')
            return self.step_request_location(message)
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
        if not message.text:
            return self.step_request_manual_location(message)
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
            zone, address.get('state_district', address.get('county', '-')), address.get('state', '-'),
            address['country']
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
        if not message.text:
            self.bot.send_message(message, 'Este campo es obligatorio.')
            return self.step_request_nick(message)
        self.bot.send_message(message.from_user.id, "Yo no tengo ni idea, ¡pero es un nombre muy bonito!")
        if not self.write_user_dict(message, 'nick', message.text):
            return
        return self.step_request_notifications(message)

    def step_request_notifications(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=2)
        for choice in [TRUE_CHOICE, FALSE_CHOICE]:
            markup.add(types.KeyboardButton(choice))
        msg = self.bot.send_message(message.from_user.id, '¿Deseas recibir notificaciones cuando se registre '
                                                          'alguien que capture por tu misma zona?',
                                    reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.step_get_notifications)

    def step_get_notifications(self, message):
        try:
            if not self.validate_choices(message, [TRUE_CHOICE, FALSE_CHOICE]):
                return self.step_request_notifications(message)
        except ValueError:
            return
        if not self.write_user_dict(message, 'notifications', True if message.text == TRUE_CHOICE else False):
            return
        try:
            self.step_finish(message)
        except Exception:
            import traceback
            print('Fallo en registro.')
            traceback.print_exc(file=sys.stdout)
            self.bot.send_message(message.from_user.id,
                                  'Ha ocurrido un problema durante el registro. Por favor, contacta con '
                                  '@nekmo para solicitar soporte.')

    def step_finish(self, message):
        data = self.user_dict.get(message.from_user.id)
        if not data:
            return self.bot.send_message(message.chat.id, '¡La sesión expiró antes de finalizar!')
        session = self.get_session()
        tg_userid = str(message.from_user.id)
        tg_username = message.from_user.username
        # AttributeError: 'sessionmaker' object has no attribute 'query'
        user = session.query(User).filter_by(tg_userid=tg_userid).first()
        is_new = False
        if user is None:
            is_new = True
            user = User()
            user.tg_userid = tg_userid
            location_zone = LocationZone()
        else:
            location_zone = session.query(LocationZone).filter_by(user=user).first()
        user.tg_username = tg_username
        user.pgo_username = data['nick']
        user.team = data['color']
        user.notifications = data['notifications']

        location_zone.suburb = data['address'].get('suburb')
        location_zone.town = data['address'].get('town')
        location_zone.city_district = data['address'].get('city_district')
        location_zone.city = data['address'].get('city')
        location_zone.county = data['address'].get('county')
        location_zone.state = data['address'].get('state')
        location_zone.country = data['address']['country']

        if is_new:
            session.add(user)
            try:
                session.flush()
            except Exception:
                # TODO: No sé si de verdad necesito el flush, pero en ocasiones falla.
                # puede debeser a fallos con el threading. Se prueba a continuar a pesar
                # del error.
                pass
            session.refresh(user)
            location_zone.user = user
            session.add(location_zone)
        session.commit()
        markup = types.ReplyKeyboardHide(selective=False)
        self.bot.send_message(message.chat.id, '¡Ya hemos terminado!', reply_markup=markup)

    def step_exit(self, message):
        markup = types.ReplyKeyboardHide(selective=False)
        self.bot.send_message(message.from_user.id, "{} huyó del combate con lágrimas en los ojos.".format(
            get_name(message.from_user)
        ), reply_markup=markup)

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
