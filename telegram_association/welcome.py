from telebot import types

from telegram_association.commands import Command, Assistant
from telegram_association.db import Group
from telegram_association.utils.telegram import is_admin, get_name

CHANGE_MESSAGE_CHOICE = 'Cambiar el mensaje'
ENABLE_MESSAGE_CHOICE = 'Activar mensaje'
DISABLE_MESSAGE_CHOICE = 'Desactivar mensaje'
NONE_CHOICE = 'No hacer nada'
MESSAGE_OPTIONS = [CHANGE_MESSAGE_CHOICE, ENABLE_MESSAGE_CHOICE, DISABLE_MESSAGE_CHOICE, NONE_CHOICE]

MESSAGE = ("¡Te damos la bienvenida, $user! ¡Te encuentras en un "
           "grupo donde habitan unas criaturas llamadas humanos!\n\n"
           "Para comenzar tu aventura, pulsa primero en @profOakBot "
           "para abrir el chat y luego escribe /register")

class Welcome(Assistant):
    commands = ('welcome',)

    def set_handler(self):
        self.main.set_handler(self.start, commands=self.commands)
        self.main.set_handler(self.new_member, func=lambda m: True, content_types=['new_chat_member'])

    def start(self, message):
        if message.chat.type not in ['supergroup', 'group']:
            return self.bot.send_message(message.chat.id, '¡Es necesario ejecutar este comando desde el grupo!')
        if not is_admin(self.bot, message):
            return self.bot.send_message(message.chat.id, '¡Es necesario ser administrador para ejecutar este comando!')
        self.user_dict[(message.chat.id, message.from_user.id)] = None
        self.step_request_change_welcome(message)

    def step_request_change_welcome(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=2, selective=True)
        for choice in MESSAGE_OPTIONS:
            markup.add(types.KeyboardButton(choice))
        msg = self.bot.send_message(message.chat.id, '¿Qué deseas hacer con el mensaje de bienvenida?',
                                    reply_markup=markup, reply_to_message_id=message.message_id)
        self.bot.register_next_step_handler(msg, self.step_get_change_welcome)

    def step_get_change_welcome(self, message):
        if not (message.chat.id, message.from_user.id) in self.user_dict:
            return self.bot.register_next_step_handler(message, self.step_get_change_welcome)
        try:
            if not self.validate_choices(message, MESSAGE_OPTIONS):
                return self.step_request_change_welcome(message)
        except ValueError:
            return
        if message.text == NONE_CHOICE:
            return self.bot.send_message(message.chat.id, '¡Hasta pronto!')
        if message.text in [ENABLE_MESSAGE_CHOICE, DISABLE_MESSAGE_CHOICE]:
            return self.save(message, enabled=True if message.text == ENABLE_MESSAGE_CHOICE else False)
        self.step_request_welcome_message(message)

    def step_request_welcome_message(self, message):
        markup = types.ForceReply(selective=True)
        msg = self.bot.send_message(message.chat.id, "Dime por favor el nuevo mensaje de bienvenida",
                                    reply_markup=markup, reply_to_message_id=message.message_id)
        self.bot.register_next_step_handler(msg, self.step_get_welcome_message)

    def step_get_welcome_message(self, message):
        if not message.text:
            self.bot.send_message(message.chat.id, 'Este campo es obligatorio.')
            return self.step_request_welcome_message(message)
        self.bot.send_message(message.chat.id, "¡Perfecto!")
        return self.save(message, welcome_message=message.text)

    def save(self, message, enabled=None, welcome_message=None):
        session = self.get_session()
        tg_chat_id = str(message.chat.id)
        group = session.query(Group).filter_by(tg_chat_id=tg_chat_id).first()
        is_new = False
        if group is None:
            is_new = True
            group = Group()
        group.tg_chat_id = tg_chat_id
        group.tg_chat_name = message.chat.username
        if enabled is not None:
            group.welcome_enabled = enabled
        if welcome_message is not None:
            group.welcome_message = welcome_message
        if is_new:
            session.add(group)
        session.commit()
        self.bot.send_message(message.chat.id, '¡Cambios aplicados!')

    def new_member(self, message):
        session = self.get_session()
        tg_chat_id = str(message.chat.id)
        group = session.query(Group).filter_by(tg_chat_id=tg_chat_id).first()
        enabled = True
        welcome_message = MESSAGE
        if group:
            enabled = group.welcome_enabled
            welcome_message = group.welcome_message or welcome_message
        if not enabled:
            return
        self.bot.reply_to(message, welcome_message.replace('$user', get_name(message.new_chat_member)))

