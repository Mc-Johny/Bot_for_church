import sqlite3
import textwrap

import requests
import vk_api
import telebot
from fpdf import FPDF
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from datetime import datetime as dt

import config
from molitvoslov import pr_every_day

vk_session = vk_api.VkApi(token=config.token)
vk = vk_session.get_api()
longpool = VkBotLongPoll(vk_session, config.group_id)
connection = None
admin = """Список администраторов"""
health_index = 0  # индекс колонки о здравии
deceased_index = 1  # индекс колонки об упокоении
bot = telebot.TeleBot(config.tg_token)


def get_connection():  # Производится соединение с базой
    global connection
    if connection is None:
        connection = sqlite3.connect("database.db")
    return connection


def check_reg(user_id):  # Проверка пользователя. Есть ли он в базе
    conn = get_connection()
    c = conn.cursor()
    c.execute(f'SELECT user_id FROM users WHERE user_id = {user_id}')
    result = c.fetchone()
    if result is None:
        return False
    return True


def register_new_user(user_id: int):  # Регистрация пользователя в базу
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO users (user_id, state_conversation, health, deceased) VALUES (?, ?, ?, ?)',
              (user_id, 0, 0, 0))
    conn.commit()


def conversation(user_id, state):
    """
    Если 1, то бот не реагирует ни на что.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute(f'UPDATE users SET state_conversation = {state} WHERE user_id = {user_id}')
    conn.commit()


def check_conversation(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(f'SELECT state_conversation FROM users WHERE user_id = {user_id}')
    res = c.fetchone()[0]
    if res == 1:
        return False
    else:
        return True


def load_attachment():
    """
    Загружает на сервера ВКонтакте сгенерированные до этого PDF файлы.
    Генерируется вложение.
    :return: 2 вложения(PDF о здравии, PDF об упокоении)
    """
    upload_h = vk_session.method("docs.getMessagesUploadServer", {"type": "doc", "peer_id": 563865233})
    upload_url_h = requests.post(upload_h['upload_url'], files={'file': open('output/health_notes.pdf', 'rb')}).json()
    doc_h = vk_session.method('docs.save', {'file': upload_url_h['file'], 'title': 'О здравии'})
    attachment_health_pdf = 'doc{}_{}'.format(doc_h['doc']['owner_id'], doc_h['doc']['id'])

    upload_d = vk_session.method("docs.getMessagesUploadServer", {"type": "doc", "peer_id": 563865233})
    upload_url_d = requests.post(upload_d['upload_url'], files={'file': open('output/deceased_notes.pdf', 'rb')}).json()
    doc_d = vk_session.method('docs.save', {'file': upload_url_d['file'], 'title': 'О упокоении'})
    attachment_deceased_pdf = 'doc{}_{}'.format(doc_d['doc']['owner_id'], doc_d['doc']['id'])
    return attachment_health_pdf, attachment_deceased_pdf


def create_keyboard(response, inline, user_id=None):
    keyboard = VkKeyboard(one_time=True, inline=False)
    if response == 'menu' or response == 'меню' or response == 'начать':
        keyboard.add_button('Таинства')
        keyboard.add_button('Молитвы', color=VkKeyboardColor.DEFAULT)
        keyboard.add_line()
        keyboard.add_button('Записки', color=VkKeyboardColor.DEFAULT)
        # keyboard.add_line()
        keyboard.add_button('Спросить', color=VkKeyboardColor.DEFAULT)
        keyboard.add_line()
        keyboard.add_button('Контакты', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_openlink_button('Оставить отзыв',
                                        link='https://f3.cool/Alnashi_Church?hl=ru')

    elif response == 'to_menu':
        if inline == 'support':
            menu = VkKeyboard(one_time=False, inline=True)
            menu.add_button('Меню', color=VkKeyboardColor.NEGATIVE)
            return menu.get_keyboard()
        elif inline == 'not_support':
            menu = VkKeyboard(one_time=True, inline=False)
            menu.add_button('Меню', color=VkKeyboardColor.NEGATIVE)
            return menu.get_keyboard()
    elif response == 'answer':
        if inline == 'support':
            menu = VkKeyboard(one_time=False, inline=True)
            menu.add_openlink_button('Ответить',
                                     link=f'https://vk.com/gim{config.group_id}?sel={user_id}')
            return menu.get_keyboard()
        elif inline == 'not_support':
            menu = VkKeyboard(one_time=True, inline=False)
            menu.add_openlink_button('Ответить',
                                     link=f'https://vk.com/gim{config.group_id}?sel={user_id}')
            return menu.get_keyboard()
    elif response == 'молитвы':
        keyboard.add_openlink_button('Молитва дня',
                                     link=pr_every_day['{}'.format(dt.today().weekday() + 1)])
        keyboard.add_line()
        keyboard.add_openlink_button('Основные молитвы',
                                     link='https://vk.cc/atBHq9')
        keyboard.add_line()
        keyboard.add_openlink_button('Утренние',
                                     link='https://vk.cc/atFzD1')
        keyboard.add_openlink_button('На сон грядущий',
                                     link='https://vk.cc/atFBjy')
        keyboard.add_line()
        keyboard.add_button('Ко Причастию')
        keyboard.add_line()
        keyboard.add_openlink_button('Ко Пресвятой Троице',
                                     link='https://vk.cc/atBN2U')
        keyboard.add_line()
        keyboard.add_openlink_button('Трем Святителям',
                                     link='https://vk.cc/atBRGj')
        keyboard.add_line()
        keyboard.add_openlink_button('Петру и Павлу',
                                     link='https://vk.cc/atBTv7')
        keyboard.add_line()
        keyboard.add_openlink_button('Акафист Николаю Чудотворцу',
                                     link='https://vk.cc/atBGt9')
        keyboard.add_line()
        keyboard.add_openlink_button('Ко Пресвятой Богородице',
                                     link='https://vk.cc/atBJVm')
        keyboard.add_line()
        keyboard.add_button('Меню', color=VkKeyboardColor.NEGATIVE)
        return keyboard.get_keyboard()
    elif response == 'ко причастию':
        keyboard.add_openlink_button('Последование к Причащению',
                                     link='https://vk.cc/atzNpP')
        keyboard.add_line()
        keyboard.add_openlink_button('Канон Иисусу Христу',
                                     link='https://vk.cc/atzL8T')
        keyboard.add_line()
        keyboard.add_openlink_button('Канон Богородице',
                                     link='https://vk.cc/atzLAK')
        keyboard.add_line()
        keyboard.add_openlink_button('Канон Ангелу-Хранителю',
                                     link='https://vk.cc/atzM43')
        keyboard.add_line()
        keyboard.add_openlink_button('Акафист ко Святому Причащению',
                                     link='https://vk.cc/atzOKn')
        keyboard.add_line()
        keyboard.add_openlink_button('Благодарственные молитвы',
                                     link='https://vk.cc/atzNj3')
        keyboard.add_line()
        keyboard.add_button('Меню', color=VkKeyboardColor.NEGATIVE)
    elif response == 'записки':
        keyboard.add_button('О Здравии', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Об Упокоении', color=VkKeyboardColor.PRIMARY)
        if user_id in admin:
            keyboard.add_line()
            keyboard.add_button('Печатать', color=VkKeyboardColor.DEFAULT)
        keyboard.add_line()
        keyboard.add_openlink_button('Правила',
                                     link='https://vk.cc/atsViE')
        keyboard.add_line()
        keyboard.add_button('Меню', color=VkKeyboardColor.NEGATIVE)
    elif response == 'о здравии':
        if inline == 'support':
            menu = VkKeyboard(one_time=False, inline=True)
            menu.add_button('Об Упокоении', color=VkKeyboardColor.PRIMARY)
            menu.add_line()
            menu.add_button('Меню', color=VkKeyboardColor.NEGATIVE)
            return menu.get_keyboard()
        elif inline == 'not_support':
            menu = VkKeyboard(one_time=True, inline=False)
            menu.add_button('Об Упокоении', color=VkKeyboardColor.PRIMARY)
            menu.add_line()
            menu.add_button('Меню', color=VkKeyboardColor.NEGATIVE)
            return menu.get_keyboard()
    elif response == 'об упокоении':
        if inline == 'support':
            menu = VkKeyboard(one_time=False, inline=True)
            menu.add_button('О Здравии', color=VkKeyboardColor.PRIMARY)
            menu.add_line()
            menu.add_button('Меню', color=VkKeyboardColor.NEGATIVE)
            return menu.get_keyboard()
        elif inline == 'not_support':
            menu = VkKeyboard(one_time=True, inline=False)
            menu.add_button('О Здравии', color=VkKeyboardColor.PRIMARY)
            menu.add_line()
            menu.add_button('Меню', color=VkKeyboardColor.NEGATIVE)
            return menu.get_keyboard()
    elif response == 'таинства':
        keyboard.add_openlink_button('Таинство Крещения',
                            link='https://vk.cc/atsGcX')
        keyboard.add_line()
        keyboard.add_openlink_button('Таинство Миропомазания',
                                     link='https://vk.cc/attirf')
        keyboard.add_line()
        keyboard.add_openlink_button('Таинство Покаяния(Исповедь)',
                                     link='https://vk.cc/attzdL')
        keyboard.add_line()
        keyboard.add_openlink_button('Таинство Причащения(Евхаристия)',
                                     link='https://vk.cc/attNKZ')
        keyboard.add_line()
        keyboard.add_openlink_button('Таинство Елеосвящения(Соборование)',
                                     link='https://vk.cc/atwWgs')
        keyboard.add_line()
        keyboard.add_openlink_button('Таинство Брака',
                                     link='https://vk.cc/atwYVs')
        keyboard.add_line()
        keyboard.add_openlink_button('Таинство Священства',
                                     link='https://vk.cc/atx1YJ')
        keyboard.add_line()
        keyboard.add_button('Меню', color=VkKeyboardColor.NEGATIVE)
    elif response == 'контакты':
        keyboard.add_openlink_button('Связаться с создателем',
                                     link='https://vk.com/im?sel=292995613')
        keyboard.add_line()
        keyboard.add_button('Меню', color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()


def put_names():
    """
    Берет из базы данных все имена и возвращает кортеж.

    :return: кортеж имен. Health name и Deceased.
    """
    conn = get_connection()
    health = conn.cursor()
    health.execute('SELECT health FROM notes WHERE health != \'None\'')
    names_h = health.fetchall()
    deceased = conn.cursor()
    deceased.execute('SELECT deceased FROM notes WHERE deceased != \'None\'')
    names_d = deceased.fetchall()
    name_list_one_h = [name.split(',') for l_n in names_h for name in l_n]
    health_name = []
    for name in name_list_one_h:
        health_name += name

    name_list_one_d = [name.split(',') for l_n in names_d for name in l_n]
    deceased_name = []
    for name in name_list_one_d:
        deceased_name += name
    return health_name, deceased_name


def check_notes(user_id):
    """
    Функция для проверки колонок health и deceased на присутствие 1.

    :param user_id: id пользователя
    :return: возвращает False, если обе колонки имеют значения 0
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute(f'SELECT health, deceased FROM users WHERE user_id = {user_id}')
    res = c.fetchone()
    if 1 in res:
        return True
    else:
        return False


def notes_update(user_id, column=None, menu=0):
    """
    Функция для обновления значения в колонках. Если человек выбрал 'О здравии',
    то колонка health обновляет значение на 1. Если пользователь перешел в меню,
    то колонки health и deceased обнуляются.

    :param user_id: id пользователя
    :param column: название колонки, где нужно обновить значение до 1.
    :param menu: необязательный параметр(По умолчанию 0). Если передать 1, то колонки обнуляются
    :return: Ничего не возвращает
    """
    conn = get_connection()
    c = conn.cursor()
    if menu == 0:
        if column == 'health':
            c.execute(f'UPDATE users SET \'{column}\' = 1, deceased = 0 WHERE user_id = {user_id}')
        else:
            c.execute(f'UPDATE users SET \'{column}\' = 1, health = 0 WHERE user_id = {user_id}')
    else:
        c.execute(f'UPDATE users SET health = 0, deceased = 0 WHERE user_id = {user_id}')
    conn.commit()


def write_notes(name_or_names, user_id):
    """Функция для записи имен о здравии и о упокоении.

    :param name_or_names: имена, которые запишутся в базу
    :type name_or_names: str
    :param user_id: id пользователя
    :type user_id: int
    """

    conn = get_connection()
    c = conn.cursor()
    c.execute(f'SELECT health, deceased FROM users WHERE user_id = {user_id}')
    col = c.fetchone()
    if col.index(1) == health_index:
        c.execute('INSERT INTO notes (user_id, health) VALUES (?, ?)',
                  (user_id, name_or_names))
        conn.commit()
    elif col.index(1) == deceased_index:
        c.execute('INSERT INTO notes (user_id, deceased) VALUES (?, ?)',
                  (user_id, name_or_names))
        conn.commit()


def names(name_list):
    """
    Принимает имена в виде строки и возвращает красиво оформленный текст

    :return:
    """
    text = textwrap.dedent(', '.join(name_list)).strip()
    return textwrap.fill(text, width=65)


def gen_pdf():
    health_pdf = FPDF()  # А4 с портретной ориентацией. Единица измерения: mm(миллиметр)
    deceased_pdf = FPDF()
    health_pdf.add_page()
    deceased_pdf.add_page()
    health_pdf.add_font('Segoe Print', '', 'fonts/segoepr.ttf', uni=True)  # Segoe Print
    deceased_pdf.add_font('Segoe Print', '', 'fonts/segoepr.ttf', uni=True)
    health_pdf.add_font('Corbel', '', 'fonts/corbel.ttf', uni=True)
    deceased_pdf.add_font('Corbel', '', 'fonts/corbel.ttf', uni=True)
    health, deceased = put_names()
    health_pdf.set_font('Segoe Print')
    deceased_pdf.set_font('Segoe Print')
    health_pdf.set_font_size(30)
    deceased_pdf.set_font_size(30)
    health_pdf.set_text_color(76, 78, 75)
    deceased_pdf.set_text_color(76, 78, 75)
    health_pdf.image(name='images/крест.png', x=50, y=4, type='PNG')
    health_pdf.image(name='images/крест.png', x=143, y=4, type='PNG')
    deceased_pdf.image(name='images/крест.png', x=36, y=4, type='PNG')
    deceased_pdf.image(name='images/крест.png', x=157, y=4, type='PNG')
    health_pdf.cell(185, 5, txt='О ЗДРАВИИ', align='C', ln=1)
    deceased_pdf.cell(185, 5, txt='ОБ УПОКОЕНИИ', align='C', ln=1)
    health_pdf.set_xy(10, 20)
    deceased_pdf.set_xy(10, 20)
    health_pdf.set_font('Corbel')
    deceased_pdf.set_font('Corbel')
    health_pdf.set_font_size(18)
    deceased_pdf.set_font_size(18)
    health_pdf.set_text_color(0, 0, 0)
    deceased_pdf.set_text_color(0, 0, 0)
    health_pdf.write(h=8, txt=names(health))
    deceased_pdf.write(h=8, txt=names(deceased))
    health_pdf.output('output/health_notes.pdf')
    deceased_pdf.output('output/deceased_notes.pdf')


def delete_names():
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM notes')
    conn.commit()


def main():
    while True:
        for event in longpool.check():
            inline = 'not_support'
            if event.type == VkBotEventType.MESSAGE_NEW and event.obj.client_info['keyboard']:
                if 'open_link' in event.obj.client_info['button_actions']:
                    if 'inline_keyboard' in event.obj.client_info:
                        if event.obj.client_info['inline_keyboard']:
                            inline = 'support'
                        elif not event.obj.client_info['inline_keyboard']:
                            inline = 'not_support'
                    elif 'inline_keyboard' not in event.obj.client_info:
                        inline = 'not_support'
                    user_id = event.obj.message['from_id']
                    if not check_reg(user_id):
                        register_new_user(user_id)
                    if not check_notes(user_id) and check_conversation(user_id):
                        text = event.obj.message['text'].lower()
                        if text == 'начать':
                            vk.messages.send(
                                user_id=user_id,
                                message='Доброго времени суток! \nЯ бот Свято—Троицкого храма с.Алнаши.\n'
                                        'Я могу дать вам полезную '
                                        'информацию.\nВыберите нужный вам раздел.\n\n☦ Храни вас Господь! ☦',
                                keyboard=create_keyboard(text, inline=inline),
                                random_id=get_random_id()
                            )
                        elif text == 'молитвы':
                            vk.messages.send(
                                user_id=user_id,
                                message='Выберите нужную вам молитву.\n'
                                        'Нажмите кнопку «Меню» или напишите Меню,'
                                        ' чтобы вернуться обратно.\n\n'
                                        '☦ Храни вас Господь! ☦',
                                keyboard=create_keyboard(text, inline=inline),
                                random_id=get_random_id()
                            )
                        elif text == 'спросить':
                            conversation(user_id, 1)
                            vk.messages.send(
                                user_id=user_id,
                                message='Напишите свой сформулированный вопрос.\n'
                                        'Соблюдайте нормы этикета.'
                                        'Любой вопрос без смысла будет проигнорирован.\n'
                                        'После отправки вопроса ожидайте ответа в этом же разделе.\n\n'
                                        '☦ Храни вас Господь! ☦',
                                keyboard=create_keyboard('to_menu', inline=inline),
                                random_id=get_random_id()
                            )
                        elif text == 'записки':
                            vk.messages.send(
                                user_id=user_id,
                                message='Перед тем как воспользоваться записками - ознакомьтесь с правилами!\n'
                                        'Нажмите кнопку «Меню» или напишите Меню,'
                                        ' чтобы вернуться обратно.\n\n'
                                        '☦ Храни вас Господь! ☦',
                                keyboard=create_keyboard(text, inline=inline, user_id=user_id),
                                random_id=get_random_id()
                            )
                        elif text == 'о здравии':
                            notes_update(user_id, 'health')
                            vk.messages.send(
                                user_id=user_id,
                                message='☦О ЗДРАВИИ☦\nЗапишите имена о здравии.\n'
                                        'Так же вы можете записать имена усопших,'
                                        ' либо выйти в меню нажав на соответствующую кнопку.',
                                keyboard=create_keyboard(text, inline, user_id),
                                random_id=get_random_id()
                            )
                        elif text == 'об упокоении':
                            notes_update(user_id, 'deceased')
                            vk.messages.send(
                                user_id=user_id,
                                message='☦ОБ УПОКОЕНИИ☦\nЗапишите имена усопших.\n'
                                        'Так же вы можете записать имена о здравии,'
                                        ' либо выйти в меню нажав на соответствующую кнопку.',
                                keyboard=create_keyboard(text, inline, user_id),
                                random_id=get_random_id()
                            )
                        elif text == 'печатать' and user_id in admin:
                            vk.messages.send(
                                user_id=user_id,
                                message='Секундочку ⏳',
                                keyboard=None,
                                random_id=get_random_id()
                            )
                            gen_pdf()
                            bot.send_message(545999762, 'О здравии:')
                            with open('output/health_notes.pdf', 'rb') as f:
                                bot.send_document(545999762, f)
                            bot.send_message(545999762, 'Об упокоении:')
                            with open('output/deceased_notes.pdf', 'rb') as f:
                                bot.send_document(545999762, f)
                            delete_names()
                            vk.messages.send(
                                user_id=user_id,
                                message='Готово!\nДокументы для распечатки доступны в Telegram.',
                                keyboard=create_keyboard('menu', inline=inline),
                                # attachment=list(load_attachment()),
                                random_id=get_random_id()
                            )
                        elif text == 'таинства':
                            vk.messages.send(
                                user_id=user_id,
                                message='Вы находитесь в разделе таинства.\n'
                                        'Нажмите кнопку «Меню» или напишите Меню,'
                                        ' чтобы вернуться обратно.\n\n'
                                        '☦ Храни вас Господь! ☦',
                                keyboard=create_keyboard(text, inline=inline),
                                random_id=get_random_id()
                            )
                        elif text == 'ко причастию':
                            vk.messages.send(
                                user_id=user_id,
                                message='Перед тем, как прочитать молитвы ко причастию, рекомендуется ознакомится'
                                        ' с последованием ко Святому Причащению.\n'
                                        'Нажмите кнопку «Меню» или напишите Меню,'
                                        ' чтобы вернуться обратно.\n\n'
                                        '☦ Храни вас Господь! ☦',
                                keyboard=create_keyboard(text, inline=inline),
                                random_id=get_random_id()
                            )
                        elif text == 'контакты':
                            vk.messages.send(
                                user_id=user_id,
                                message='Администратор: [id139206079|Михаил Иванов]\n'
                                        'Почта для связи с администратором: mihalic_mihal@mail.ru\n\n'
                                        'Создатель бота: [id292995613|Иван Шабалин]',
                                keyboard=create_keyboard(text, inline=inline),
                                random_id=get_random_id()
                            )
                        elif text == 'меню':
                            conversation(user_id, 0)
                            vk.messages.send(
                                user_id=user_id,
                                message='Основное меню.\n'
                                        'Выберите интересующий вас раздел.',
                                keyboard=create_keyboard(text, inline=inline),
                                random_id=get_random_id()
                            )
                        else:
                            vk.messages.send(
                                user_id=user_id,
                                message='Я не понимаю ввод с клавиатуры\n'
                                        'Возвращайтесь в меню, чтобы найти нужный вам раздел.\n'
                                        'Если вы хотели задать вопрос, то выберите в меню раздел «Спросить».',
                                keyboard=create_keyboard('to_menu', inline=inline),
                                random_id=get_random_id()
                            )
                    elif not check_conversation(user_id) and not check_notes(user_id):
                        text = event.obj.message['text']
                        vk.messages.markAsRead(
                            peer_id=user_id
                        )
                        if text.lower() != 'меню':
                            vk.messages.send(
                                user_id="""Id администраторов""",
                                message=f'[id{user_id}|Пользователь] задал вопрос:\n' + text + '\n\nПосторайтесь '
                                                                                               'ответить на него быстрее.',
                                keyboard=create_keyboard('answer', inline, user_id),
                                random_id=get_random_id()
                            )
                        else:
                            conversation(user_id, 0)
                            vk.messages.send(
                                user_id=user_id,
                                message='Основное меню.\n'
                                        'Выберите интересующий вас раздел.',
                                keyboard=create_keyboard(text.lower(), inline),
                                random_id=get_random_id()
                            )
                    elif check_notes(user_id):
                        text = event.obj.message['text']
                        vk.messages.markAsRead(
                            peer_id=user_id
                        )
                        if text.lower() != 'меню':
                            if text.lower() == 'о здравии':
                                notes_update(user_id, 'health')
                                vk.messages.send(
                                    user_id=user_id,
                                    message='☦О ЗДРАВИИ☦\nЗапишите имена о здравии.\n'
                                            'Так же вы можете записать имена усопших,'
                                            ' либо выйти в меню нажав на соответствующую кнопку.',
                                    keyboard=create_keyboard(text.lower(), inline, user_id),
                                    random_id=get_random_id()
                                )
                            elif text.lower() == 'об упокоении':
                                notes_update(user_id, 'deceased')
                                vk.messages.send(
                                    user_id=user_id,
                                    message='☦ОБ УПОКОЕНИИ☦\nЗапишите имена усопших.\n'
                                            'Так же вы можете записать имена о здравии,'
                                            ' либо выйти в меню нажав на соответствующую кнопку.',
                                    keyboard=create_keyboard(text.lower(), inline, user_id),
                                    random_id=get_random_id()
                                )
                            else:
                                write_notes(text, user_id)
                                if inline == 'not_support':
                                    vk.messages.send(
                                        user_id=user_id,
                                        message=' ',
                                        keyboard=create_keyboard(text.lower(), inline, user_id),
                                        random_id=get_random_id()
                                    )
                        else:
                            notes_update(user_id, menu=1)
                            vk.messages.send(
                                user_id=user_id,
                                message='Основное меню.'
                                        'Выберите интересующий вас раздел.',
                                keyboard=create_keyboard(text.lower(), inline=inline),
                                random_id=get_random_id()
                            )
                else:
                    vk.messages.send(
                        user_id=event.obj.message['from_id'],
                        message='Доброго времени суток!\nКак я вижу, вы используйте неофициальный клиент.\n'
                                'Настоятельно рекомендую вам использовать официальный клиент ВКонтакте,'
                                'т.к. вам не будет доступен функционал\n\n'
                                '☦ Храни вас Господь! ☦',
                        keyboard=None,
                        random_id=get_random_id()
                    )


if __name__ == '__main__':
    main()