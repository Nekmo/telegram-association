import requests
from expiringdict import ExpiringDict
from telebot.apihelper import ApiException
from unidecode import unidecode

from telegram_association.commands import Command

ERROR = '¡En estos momentos no es posible usar la pokédex!'

TYPE_TRANSLATES = {
    'fuego': 'fire',
    'hada': 'fairy',
    'hielo': 'ice',
    'lucha': 'fighting',
    'normal': 'normal',
    'planta': 'grass',
    'psíquico': 'psychic',
    'roca': 'rock',
    'siniestro': 'dark',
    'tierra': 'ground',
    'veneno': 'poison',
    'volador': 'flying',
    'eléctrico': 'electric',
    'agua': 'water',
    'acero': 'steel',
    'bicho': 'bug',
    'dragón': 'dragon',
    'fantasma': 'ghost',
}

TYPE_TRANSLATES_REVERSE = {v: k for k, v in TYPE_TRANSLATES.items()}

POKEMON_BODY = """\
#{id} <b>{name}</b> - {types} - {weight:.1f}kg {height:.1f}m https://img.pokemondb.net/artwork/{name}.jpg
"""

TRANSLATES = {
    'half_damage_from': '1/2 daño por',
    'no_damage_from': 'no daño por',
    'half_damage_to': '1/2 daño a',
    'double_damage_from': 'x2 daño por',
    'no_damage_to': 'no daño a',
    'double_damage_to': 'x2 daño a',
}

API_URL = 'http://pokeapi.co/api/v2/{type}/{value}'


cache = ExpiringDict(300, 60 * 60 * 18)


class Pokedex(Command):
    commands = ('pokedex',)

    def start(self, message):
        query = message.text.split(' ', 1)  # Remove /command
        if len(query) < 2:
            return self.bot.send_message(message.chat.id, "Introduzca un término de búsqueda.")
        query = unidecode(query[1].lower())
        if query in TYPE_TRANSLATES or query in TYPE_TRANSLATES.values():
            query = TYPE_TRANSLATES.get(query, query)
            return self.search_type(message, query)
        return self.search_pokemon(message, query)

    def search_type(self, message, name):
        data = self.request(message, 'type', name, ['damage_relations'])
        if data.get('damage_relations') is None:
            return self.bot.send_message(message.chat.id, ERROR)
        cache[name] = data
        damage_relations = {key: ', '.join([TYPE_TRANSLATES_REVERSE.get(t['name'], t['name']) for t in value])
                            for key, value in data['damage_relations'].items() if value}
        damage_relations = ['<b>{}</b>: {}'.format(TRANSLATES.get(key, key), value)
                            for key, value in damage_relations.items()]
        body = '\n'.join(damage_relations) or '¡Sin resultados!'
        self.bot.send_message(message.chat.id, body, parse_mode='html')

    def search_pokemon(self, message, name_or_id):
        data = self.request(message, 'pokemon', name_or_id, ['detail', 'id'])
        if data.get('detail') == 'Not found.':
            cache[name_or_id] = data
            return self.bot.send_message(message.chat.id, '¡No hay ningún pokémon con ese nombre en la pokédex!')
        if data.get('id') is None:
            return self.bot.send_message(message.chat.id, ERROR)
        cache[name_or_id] = data
        types = [TYPE_TRANSLATES_REVERSE.get(t['type']['name'], t['type']['name']) for t in data['types']]
        body = POKEMON_BODY.format(id=data['id'], name=data['name'], weight=data.get('weight', 0) / 10,
                                   height=data.get('height', 0) / 10,
                                   types=', '.join(['<i>{}</i>'.format(t) for t in types]))
        self.bot.send_message(message.chat.id, body, parse_mode='html')

    def request(self, message, type, value, required):
        if value in cache:
            return cache[value]
        try:
            data = requests.get(API_URL.format(type=type, value=value)).json()
        except Exception:
            self.bot.send_message(message.chat.id, ERROR)
            raise ApiException(message, lambda x: x, False)
        for req in required:
            if req in data:
                cache[value] = data
                break
        return data

