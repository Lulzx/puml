#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(message)s')
import requests
from telegram import InlineQueryResultPhoto, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from uuid import uuid4
import zlib
import re

DIAGRAM = re.compile("(?P<full>@startuml\n(.+(\n)*)+@enduml)")


def deflate_and_encode(plantuml_text):
    zlibbed_str = zlib.compress(plantuml_text)
    compressed_string = zlibbed_str[2:-4]
    return encode(compressed_string)


def encode(data):
    res = ""
    for i in range(0, len(data), 3):
        if i + 2 == len(data):
            res += _encode3bytes(data[i], data[i + 1], 0)
        elif i + 1 == len(data):
            res += _encode3bytes(data[i], 0, 0)
        else:
            res += _encode3bytes(data[i], data[i + 1], data[i + 2])
    return res


def _encode3bytes(b1, b2, b3):
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F
    res = ""
    res += _encode6bit(c1 & 0x3F)
    res += _encode6bit(c2 & 0x3F)
    res += _encode6bit(c3 & 0x3F)
    res += _encode6bit(c4 & 0x3F)
    return res


def _encode6bit(b):
    if b < 10:
        return chr(48 + b)
    b -= 10
    if b < 26:
        return chr(65 + b)
    b -= 26
    if b < 26:
        return chr(97 + b)
    b -= 26
    if b == 0:
        return '-'
    if b == 1:
        return '_'
    return '?'


def get_uml(message):
    match = DIAGRAM.search(message)
    if match:
        return match.groupdict()['full']


logging.basicConfig(format='%(name)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def start(bot, update):
    keyboard = [[InlineKeyboardButton("Help 🙇🏻", callback_data='''help'''),
                 InlineKeyboardButton("UML 🤔", callback_data='''uml'''), InlineKeyboardButton("Examples ℹ️", callback_data='''examples''')],

                [InlineKeyboardButton('Try me inline!', switch_inline_query_current_chat='')]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('''*PlantUML* is an _open-source tool_ allowing users to easily create _UML Diagrams_ from simple textual description.\n\n●  *Create UML diagrams on the fly*, with support for the PlantUML markup language.\n●  *Share quick sketches of concepts* with your fellow programmers, available as _inline query_ too, so that changes are visible in _real time_.\n●  *Quickly create sequence diagrams* as PlantUML makes very _complex diagrams_ from few lines of "code".\n\n*Alright! Now, Send code.* :)''', reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

def button(bot, update):
    query = update.callback_query
    
    if query.data == "help":
        bot.edit_message_text(text='''<b>Diagrams are defined using a simple and intuitive language.</b> <a href="http://plantuml.com/PlantUML_Language_Reference_Guide.pdf">See PlantUML Language Reference Guide</a>.\n\n<b>Images</b> can be generated in PNG, <a href="http://plantuml.com/svg">in SVG</a> or <a href="http://plantuml.com/latex">in LaTeX</a> format. It is also possible to generate <a href="http://plantuml.com/ascii-art">ASCII art diagrams</a> (only for sequence diagrams).''', chat_id=query.message.chat_id, message_id=query.message.message_id, parse_mode=ParseMode.HTML)
    elif query.data == "uml":
        bot.edit_message_text(text='''<b>Unified Modeling</b> <a href="http://telegra.ph/Unified-Modeling-Language-07-27">Language</a> <a href="https://en.wikipedia.org/wiki/Unified_Modeling_Language">​</a>''', chat_id=query.message.chat_id, message_id=query.message.message_id, parse_mode=ParseMode.HTML)
    elif query.data == "examples":
        bot.edit_message_text(text='''_The sequence_ *->* is used to draw a message between two participants. Participants do not have to be explicitly declared.
To have a _dotted arrow_, you use *-->*

It is also possible to use *<-* and *<--*. That does not change the drawing, but _may improve readability_. *Note that this is only true for sequence diagrams, rules are different for the other diagrams.*

```
@startuml
Alice -> Bob: Authentication Request
Bob --> Alice: Authentication Response

Alice -> Bob: Another authentication Request
Alice <-- Bob: another authentication Response
@enduml
```''', chat_id=query.message.chat_id, message_id=query.message.message_id, parse_mode=ParseMode.MARKDOWN)


def help(bot, update):
    update.message.reply_text(
        '*Need help? Visit:* http://plantuml.com or start again for examples.', parse_mode=ParseMode.MARKDOWN
    )


def inlinequery(bot, update):
    query = update.inline_query.query
    uml = get_uml(query)
    global url
    if uml:
        url = "http://plantuml.com/plantuml/png/{}".format(
            deflate_and_encode(uml.encode()))
    results =[(
        InlineQueryResultPhoto(
            id=uuid4(),
            thumb_url=url,
            photo_url=url))]

    bot.answer_inline_query(update.inline_query.id, results)


def pic(bot, update):
    uml = get_uml(update.message.text)
    if uml:
        url = "http://plantuml.com/plantuml/png/{}".format(
            deflate_and_encode(uml.encode()))
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        link = "http://plantuml.com/plantuml/uml/{}".format(deflate_and_encode(uml.encode()))
        png = "http://plantuml.com/plantuml/png/{}".format(deflate_and_encode(uml.encode()))
        svg = "http://plantuml.com/plantuml/svg/{}".format(deflate_and_encode(uml.encode()))
        bot.sendPhoto(update.message.chat_id, resp.raw, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Link", url="{}".format(link)), InlineKeyboardButton(text="PNG", url="{}".format(png)), InlineKeyboardButton(text="SVG", url="{}".format(svg))], [InlineKeyboardButton(text="Share with your friend!",switch_inline_query="{}".format(uml))]]))


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    try:
        token = sys.argv[1]
    except IndexError:
        token = os.environ.get("TOKEN")
    updater = Updater(token)
    dp = updater.dispatcher
    print('Ready to rock..!')
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(MessageHandler(Filters.text, pic))
    dp.add_handler(InlineQueryHandler(inlinequery))
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
