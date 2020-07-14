import pickle
import re
from datetime import datetime, timedelta
import time
from logging import INFO, DEBUG
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException

from logger_utils import get_logger

logger = get_logger('browser', INFO)


chrome_options = webdriver.ChromeOptions()
# chrome_options.add_argument('--proxy-server=socks5://3.12.34.63:7778')
chrome_options.add_argument('--window-size=1600,700')

allowed_ports = ['Donsak', 'Phangan', 'Samui', 'Tao', 'Chumpon', 'Chumphon', 'Surat Thani']  # Пока не используется
allowed_ports_lower = [p.lower() for p in allowed_ports]

# Названия источников для парсинга
sources = ['Raja', 'Lomprayah', 'Songserm', 'Seatran']


def chrome_options_no_gui(no_gui=True):
    if no_gui:
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')


# Парсинг таблицы с расписанием
def raja_parse_loaded_table(table):
    outcome_table = []

    # Получение остальных строк
    trs = table.find_elements_by_tag_name('tr')
    for i, tr in enumerate(trs):
        if i == 0:
            continue
        tds = tr.find_elements_by_tag_name('td')
        row = [td.text for td in tds[1:]]
        if 'comment' in tr.get_attribute('class'):
            logger.debug('comment пропущен')
            continue

        # Обработка названия портов отправления и прибытия
        route = row[0].split(' - ')
        from_phangan = 'phangan' in route[0].lower()
        to_phangan = 'phangan' in route[1].lower()
        port_is_allowed = any(map(lambda x: x in row[0].lower(), allowed_ports_lower))
        if (not from_phangan and not to_phangan or
                from_phangan and not to_phangan and not port_is_allowed):
            continue

        # Причесывание вывода
        route[0], route[1], pier = clean_data(route[0], route[1])

        price = re.match(r'(?P<price>\d+)\..*', row[4])
        price = price.group('price') if price else row[4]
        row = route + [pier] + row[1:4] + [price] + [sources[0]]  # Raja
        outcome_table.append(row)

        logger.debug('new row ' + str(row))

    # logger.info('\n' + '\n'.join(outcome_table))
    return outcome_table


# Обработка страницы после нажатия на кнопку формы
def raja_parse_route_table(i, driver):
    outcome_table = []

    route_s = Select(driver.find_element_by_id('route'))  # Объект для множественного выбора
    route_s.select_by_index(i)  # Установка элемента множественного выбора
    route_text = route_s.first_selected_option.text
    route_text_lower = route_text.lower()
    logger.info('Направление ' + route_text)

    # Проверка выбранного порта по списку допустимых портов
    port_is_allowed = any(map(lambda x: x in route_text_lower, allowed_ports_lower))
    if not port_is_allowed or port_is_allowed and 'phangan' not in route_text_lower:
        logger.debug('Направление ' + route_text + ' пропущено')
        return []

    button = driver.find_element_by_id('button')  # Кнопка отправки формы
    button.click()
    # Нужно подождать, пока сменится страница
    timer = time.monotonic()
    table_loaded = False
    error = False
    while True:
        if time.monotonic() - timer > 60:
            error = True
            logger.error('Превышено время ожидания таблицы с расписанием')
            break
        try:
            # Попытка найти элемент таблицы с расписанием
            table = driver.find_element_by_class_name('table-booking')
        except NoSuchElementException:
            logger.debug('Нет таблицы, ждем')
            time.sleep(1)
        else:
            table_loaded = True
            break
    if table_loaded:
        outcome_table = raja_parse_loaded_table(table)
        logger.info('Найдено строк ' + str(len(outcome_table)))
    driver.back()
    return outcome_table


# Получение необходимой информации с сайта https://www.rajaferryport.com/
def raja_parse(driver):
    url = 'https://www.rajaferryport.com/?act=b&title=ticket'
    try:
        driver.get(url)
        # Закрытие модального окна
        try:
            modal = driver.find_element_by_id('myModal')
            btn = modal.find_element_by_class_name('close')
            btn.click()
        except NoSuchElementException:
            pass

        # Клик по радиокнопке "One Way"
        logger.debug('Клик по кнопке One Way')
        rout_types = driver.find_elements_by_id('route_type')
        rout_types[1].click()

        # Выбор маршрута <select>
        route = driver.find_element_by_id('route')
        # Нужно получить таблицу для каждого направления
        route_s = Select(route)  # Объект для множественного выбора
        route_s.select_by_index(1)

        # Выбор пассажирского отправления
        logger.debug('Выбор пассажирского отправления')
        ticket_type = driver.find_element_by_id('type')
        ticket_type_s = Select(ticket_type)
        ticket_type_s.select_by_visible_text('Passenger')

        # Ввод даты расписания
        logger.debug('Ввод даты расписания')
        alternate_start = driver.find_element_by_id('alternate_start')
        day = datetime.now() + timedelta(days=1)  # На день вперед
        alternate_start.clear()
        alternate_start.send_keys(day.strftime('%A, %d %B, %Y'))

        outcome_table = []
        # Получение таблиц для каждого направления
        logger.debug('Получение таблиц для каждого направления')
        for i in range(len(route_s.options)):
            # Пропускаем первый элемент без значения
            if i == 0:
                continue
            outcome_table.extend(raja_parse_route_table(i, driver))
            # outcome_table.extend(outcome_table)
        logger.info('Получено ' + str(len(outcome_table)) + ' строк')
        return outcome_table
    except Exception as err:
        logger.exception('Exception occured')
    return None


# Причесывает данные from, to, pier для вывода в таблицу
def clean_data(from_text, to_text):
    from_text_lower = from_text.lower()
    to_text_lower = to_text.lower()
    from_phangan = 'phangan' in from_text.lower()
    to_phangan = 'phangan' in to_text.lower()
    if from_phangan:
        pier = re.match(r'.*\((?P<pier>.*)\)', to_text)
    elif to_phangan:
        pier = re.match(r'.*\((?P<pier>.*)\)', from_text)
    else:
        pier = None
    pier = pier.group('pier') if pier else ''

    from_text = re.sub(r'(\(.*\))', '', from_text).strip()
    to_text = re.sub(r'(\(.*\))', '', to_text).strip()
    pier = re.sub(r' pier| Pier|RajaFerryPort ', '', pier, flags=re.I).strip()

    # Если указан Donsak
    if not pier and 'donsak' in from_text_lower+to_text_lower:
        pier = 'Donsak'
    from_text = from_text.replace('Donsak', 'Surat Thani')
    to_text = to_text.replace('Donsak', 'Surat Thani')

    return from_text, to_text, pier


# Парсинг таблицы с расписанием
def lomp_parse_loaded_table(table, from_text):
    outcome_table = []

    from_span = table.find_element_by_class_name('destinations')
    from_phangan = 'phangan' in from_span.text.lower()
    # Получение остальных строк
    trs = table.find_elements_by_tag_name('tr')
    today = datetime.now() + timedelta(days=1)
    today = today.date().strftime('%d/%m/%Y')
    for i, tr in enumerate(trs):
        tr_text_lower = tr.text.lower()
        sum_text_lower = from_text.lower() + tr_text_lower
        to_phangan = 'phangan' in tr_text_lower
        if i == 0 or (not from_phangan and not to_phangan):
            continue

        port_is_allowed = any(map(lambda x: x in tr_text_lower, allowed_ports_lower))
        if from_phangan and not port_is_allowed or 'airport' in sum_text_lower:
            logger.debug('Порт ' + tr_text_lower + ' пропущен')
            continue

        tds = tr.find_elements_by_tag_name('td')
        row = [td.text for td in tds[0:]]
        to_text = row[0]

        # Причесывание вывода
        from_text, to_text, pier = clean_data(from_text, to_text)

        row = [from_text, to_text, pier, today] + row[1:3] + row[4:] + [sources[1]]  # ['Lomprayah']
        r1 = row[4].splitlines()
        r2 = row[5].splitlines()
        for j in range(len(r1)):
            row_ = row + []
            row_[4] = r1[j]
            row_[5] = r2[j]
            outcome_table.append(row_)
            logger.debug('new row ' + str(row_))

    # logger.info('\n' + '\n'.join(outcome_table))
    return outcome_table


# Обработка страницы после выбора направления
def lomp_parse_destination_table(i, driver):
    outcome_table = []

    destination_s = Select(driver.find_element_by_id('destination'))  # Объект для множественного выбора
    destination_s.select_by_index(i)  # Установка элемента множественного выбора
    destination_text = destination_s.first_selected_option.text
    logger.info('Направление ' + destination_text)

    # Проверка выбранного порта по списку допустимых портов
    port_is_allowed = any(map(lambda x: x in destination_text.lower(), allowed_ports_lower))
    if not port_is_allowed:
        logger.debug('Порт ' + destination_text + ' не нужен')
        return []

    # Нужно подождать, пока сменится страница
    timer = time.monotonic()
    table_loaded = False
    error = False
    while True:
        if time.monotonic() - timer > 60:
            error = True
            logger.error('Превышено время ожидания таблицы с расписанием')
            break
        try:
            # Попытка найти элемент таблицы с расписанием
            table = driver.find_element_by_id('timetable')
            from_span = table.find_element_by_class_name('destinations')
            if destination_text.lower() not in from_span.text.lower():
                logger.debug('Таблица не обновилась, ждем')
                time.sleep(0.3)
                continue
            else:
                table_loaded = True
                break
        except NoSuchElementException:
            logger.debug('Нет таблицы, ждем')
            time.sleep(1)
        else:
            table_loaded = True
            break
    if table_loaded:
        outcome_table = lomp_parse_loaded_table(table, destination_text)
        logger.info('Найдено строк ' + str(len(outcome_table)))
    return outcome_table


# Получение необходимой информации с сайта https://lomprayah.com/
def lomp_parse(driver):
    url = 'https://lomprayah.com/timetable'
    try:
        driver.get(url)

        # Выбор маршрута <select>
        destination = driver.find_element_by_id('destination')
        # Нужно получить таблицу для каждого направления
        destination_s = Select(destination)  # Объект для множественного выбора

        outcome_table = []
        # Получение таблиц для каждого направления
        logger.debug('Получение таблиц для каждого направления')
        for i in range(len(destination_s.options)):
            outcome_table.extend(lomp_parse_destination_table(i, driver))
            # outcome_table.extend(outcome_table)
        logger.info('Получено ' + str(len(outcome_table)) + ' строк')
        return outcome_table

    except Exception as err:
        logger.exception('Exception occured')
    return None


# Запуск парсинга информации с сайта https://www.rajaferryport.com/
def start_parse_raja(no_gui=True):
    logger.info('Парсинг сайта www.rajaferryport.com')
    chrome_options_no_gui(no_gui)
    with webdriver.Chrome(chrome_options=chrome_options) as driver:
        raja_tables = raja_parse(driver)
    return raja_tables


# Запуск парсинга информации с сайта https://lomprayah.com/
def start_parse_lomp(no_gui=True):
    logger.info('Парсинг сайта lomprayah.com')
    chrome_options_no_gui(no_gui)
    with webdriver.Chrome(chrome_options=chrome_options) as driver:
        lomp_tables = lomp_parse(driver)
    return lomp_tables


def main(no_gui=True):
    chrome_options_no_gui(no_gui)
    # raja_tables = start_parse_raja()
    # print(raja_tables)
    lomp_tables = start_parse_lomp(no_gui)
    print(lomp_tables)


if __name__ == '__main__':
    main(False)
