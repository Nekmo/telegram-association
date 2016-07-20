from telegram_association.commands import Command


REQUIRED_PRIVATE = """\
¡No puedes usar esto aquí! Escríbeme por privado ( @profOakBot ) y vuelve a probarlo. ¡Así evitamos el flood!
"""

HELP = (
    "¡Hola a todos! ¡Bienvenidos al mundo de POKÉMON! "
    "¡Me llamo OAK! ¡Pero la gente me llama el PROFESOR POKÉMON!\n\n"
    "Normalmente me encargo de estudiar a los POKÉMON... ¡Pero mi hobby "
    "es registrar entrenadores!\n"
    "En cuando te registre en mi nueva Pokédex de entrenadores, ¡otros "
    "jugadores podrán quedar contigo para capturar POKÉMONS juntos!\n\n"
    "Usa /register para registrarte. ¡Sólo lleva un momento!\n"
    "Para buscar otros jugadores, usa /search <búsqueda>. Por ejemplo, "
    "/search Málaga rojo.\n\n"
    "¡Te espera un mundo de sueños y aventuras con los POKÉMON! ¡Adelante!"
)


class Help(Command):
    commands = ('start', 'help')

    def start(self, message):
        if message.chat.type != 'private':
            return self.bot.send_message(message.from_user.id, REQUIRED_PRIVATE)
        self.bot.send_message(message.from_user.id, HELP)
