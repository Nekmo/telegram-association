import shlex

import sys
import traceback

from sqlalchemy import or_

from telegram_association.db import LocationZone, User
from telegram_association.commands import Command
from telegram_association.utils.paste import paste

MAX_PUBLIC_RESULTS = 4


class Search(Command):
    commands = ('search',)

    def start(self, message):
        query = message.text.split(' ', 1)  # Remove /command
        if len(query) < 2:
            return self.bot.send_message(message.chat.id, "Introduzca un término de búsqueda.")
        try:
            words = shlex.split(query[1])
        except ValueError:
            return self.bot.send_message(message.chat.id, '¡Comprueba que no haya comillas sin cerrar en la '
                                                          'búsqueda y que la sintaxis es correcta!')
        fields = [LocationZone.city, LocationZone.city_district, LocationZone.county, LocationZone.town,
                  LocationZone.suburb, LocationZone.country, LocationZone.state, User.team, User.pgo_username,
                  User.tg_username]
        filter_ = [or_(*[getattr(field, 'ilike')('{}%'.format(word)) for field in fields]) for word in words]
        queryset = self.get_session().query(User).filter(*filter_).join(LocationZone)
        self.command_all(message, queryset)

    def command_all(self, message, queryset=None):
        order = (LocationZone.country, LocationZone.state, LocationZone.county,
                 LocationZone.city, LocationZone.city_district, LocationZone.town,
                 LocationZone.suburb)
        users = []
        if queryset is None:
            queryset = self.get_session().query(User).join(LocationZone)
        try:
            for user in queryset.order_by(*order):
                users.append('http://telegram.me/{} - {} - {} - {}'.format(
                    user.tg_username, user.pgo_username, user.team, ' '.join([str(zone) for zone in
                                                                              user.location_zones])))
        except Exception:
            traceback.print_exc(file=sys.stdout)
            return self.bot.send_message(message.chat.id, 'Error al realizar la búsqueda. Inténtelo más tarde. '
                                                          'Si el error persiste, contacte a @nekmo')
        to = message.chat.id if len(users) <= MAX_PUBLIC_RESULTS else message.from_user.id
        body = '\n'.join(users) or 'Sin resultados'
        if len(users) > MAX_PUBLIC_RESULTS:
            self.bot.send_message(message.chat.id, paste(body) or 'Error desconocido al usar Paste')
        else:
            self.bot.send_message(to, body, disable_notification=True)
