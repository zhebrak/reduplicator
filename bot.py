# coding: utf-8

import argparse
import configparser
import json
import logging
import random
import re

from functools import partial

from telegram import Updater


logging.basicConfig(
    filename='reduplicator.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('reduplicator')


class ReduplicatorException(Exception):
    pass


def in_groups_only_answer_if_called_by_name(func):
        def inner(self, bot, update):
            if not update.message.chat.type == 'group' or re.search(bot.username, update.message.text, flags=re.I):
                return func(self, bot, update)

        return inner


class Reduplicator(object):
    CONFIG_PATH = 'reduplicator.conf'

    def __init__(self, token_key):
        self.config = configparser.ConfigParser()
        self.config.read([self.CONFIG_PATH])

        self.updater = Updater(token=self.config.get('main', token_key))
        self.dispatcher = self.updater.dispatcher
        self.bot = self.updater.bot

        self.mode_map = {
            'repeat': {}
        }

    def start(self):
        self.dispatcher.addTelegramCommandHandler("help", self.get_help)
        self.dispatcher.addTelegramCommandHandler("start", self.get_help)

        self.dispatcher.addTelegramCommandHandler("repeat", self.repeat_mode)
        self.dispatcher.addTelegramCommandHandler("norepeat", self.norepeat_mode)

        self.dispatcher.addTelegramRegexHandler("^[^/].*", self.reduplicate)
        self.dispatcher.addErrorHandler(self.error)

        self.updater.start_polling()
        self.updater.idle()

    @in_groups_only_answer_if_called_by_name
    def get_help(self, bot, update):
        message = 'Лексическая редупликация — фономорфологическое явление, ' \
                  'состоящее в удвоении начального слога, основы (полностью или частично) или слова.\n\n' \
                  '/help — для вывода помощи\n' \
                  '/repeat — для включения режима повторения\n' \
                  '/norepeat — для выключения режима повторения'
        bot.sendMessage(update.message.chat_id, text=message)

    @in_groups_only_answer_if_called_by_name
    def repeat_mode(self, bot, update):
        self.mode_map['repeat'][update.message.chat_id] = True
        bot.sendMessage(update.message.chat_id, text='Режим повторения включен!')

    @in_groups_only_answer_if_called_by_name
    def norepeat_mode(self, bot, update):
        self.mode_map['repeat'][update.message.chat_id] = False
        bot.sendMessage(update.message.chat_id, text='Режим повторения выключен!')

    @in_groups_only_answer_if_called_by_name
    def reduplicate(self, bot, update):
        try:
            regex = re.compile('[а-яА-Я]*')
            replacer = partial(self.reduplicate_word, repeat=self.mode_map['repeat'].get(update.message.chat_id))
            message = regex.sub(replacer, update.message.text)

            if message == update.message.text:
                raise ReduplicatorException

            message = re.sub('^@{} '.format(bot.username), '', message, flags=re.I)
            bot.sendMessage(update.message.chat_id, text=message)

        except ReduplicatorException:
            choices = json.loads(self.config.get('main', 'answers'))
            bot.sendMessage(update.message.chat_id, text=random.choice(choices))

    @staticmethod
    def reduplicate_word(match_object, repeat=False):
        vowels = 'аеёиоуыэюя'
        vowel_map = {
            'а': 'я',
            'о': 'ё',
            'у': 'ю',
            'э': 'е',
            'ы': 'и'
        }

        word = match_object.group(0)

        def replacer(inner_match_object):
            if not inner_match_object.end(0) == len(word):
                letter = inner_match_object.group(0)[-1].lower()
                replaced = 'ху{}'.format(vowel_map.get(letter, letter))

                if inner_match_object.group(0)[0].isupper():
                    replaced = replaced.capitalize()

                if repeat:
                    replaced = '{}-{}'.format(word, replaced)

                return replaced

        regex = re.compile('[^{}]*([{}])'.format(vowels, vowels), flags=re.I)
        return regex.sub(replacer, word, 1) or word

    def error(self, bot, update, error):
        logger.warn('\n'.join([update, error]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action='store_true', help="for using test bot")
    args = parser.parse_args()

    token_key = 'token'
    if args.test:
        token_key = 'token_test'

    bot = Reduplicator(token_key)
    bot.start()


if __name__ == '__main__':
    main()
