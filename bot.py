# coding: utf-8

import configparser
import json
import logging
import random
import re

from telegram import Updater


logging.basicConfig(
    filename='reduplicator.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('reduplicator')

config = configparser.ConfigParser()
config.read(['reduplicator.conf'])


class ReduplicatorException(Exception):
    pass


def reduplicate(bot, update):
    try:
        if update.message.chat.type == 'group' and not re.search(bot.username, update.message.text, flags=re.I):
            return

        regex = re.compile('[а-яА-Я]*')
        message = regex.sub(reduplicate_word, update.message.text)
        if message == update.message.text:
            raise ReduplicatorException

        message = re.sub('^@{} '.format(bot.username), '', message, flags=re.I)
        bot.sendMessage(update.message.chat_id, text=message)

    except ReduplicatorException:
        choices = json.loads(config.get('main', 'answers'))
        bot.sendMessage(update.message.chat_id, text=random.choice(choices))


def reduplicate_word(match_object):
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
            letter = inner_match_object.group(0)[-1]
            replaced = 'ху{}'.format(vowel_map.get(letter, letter))

            if inner_match_object.group(0)[0].isupper():
                replaced = replaced.capitalize()

            return replaced

    regex = re.compile('[^{}]*([{}])'.format(vowels, vowels), flags=re.I)
    return regex.sub(replacer, word, 1) or word


def error(bot, update, error):
    logger.warn('\n'.join([update, error]))


def main():
    updater = Updater(token=config.get('main', 'token'))
    dp = updater.dispatcher

    dp.addTelegramRegexHandler(".*", reduplicate)
    dp.addErrorHandler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
