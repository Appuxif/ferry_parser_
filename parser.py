import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
from logging import INFO, DEBUG

from mygoogleapi import get_table, refresh_table
from browser import start_parse_raja, start_parse_lomp, allowed_ports_lower, clean_data, sources
from logger_utils import get_logger

logger = get_logger('parser', INFO)

# Вырезает таблицу для конкретного источника из полученной гугл таблицы
def get_source_table(google_table, source):
    logger.debug('Вырезаем таблицу ' + source)
    headers = google_table[0]
    source_i = headers.index('source')
    pop_indexes = []
    source_table = []
    for i, row in enumerate(google_table):
        try:
            if row[source_i] == source:
                pop_indexes.append(i)
                source_table.append(row)
        except:
            logger.exception(row)
    pop_indexes.reverse()
    for i in pop_indexes:
        google_table.pop(i)
    return source_table


# Обработка таблицы с расписанием
def song_parse_route_table(table):
    outcome_table = []
    trs = table.find_all('tr')
    # from_text = ''
    from_text = trs[1].text.strip()
    logger.debug('from_text ' + from_text)

    from_phangan = 'phangan' in from_text.lower()
    today = datetime.now() + timedelta(days=1)
    today = today.date().strftime('%d/%m/%Y')
    last_dest = ''  # Последння строка с пунктов назначения
    for tr in trs[2:]:
        tds = tr.find_all('td')
        if len(tds) < 4:
            to_text = last_dest
        else:
            to_text = tds.pop(0).text
        to_text_lower = to_text.lower()
        to_phangan = 'phangan' in to_text_lower
        logger.debug('to_text_lower ' + to_text_lower)
        if not from_phangan and not to_phangan:
            continue

        pier_is_allowed = any(map(lambda x: x in to_text_lower, allowed_ports_lower))
        if from_phangan and not pier_is_allowed:
            logger.debug('Порт ' + to_text_lower + ' пропущен')
            continue

        # Причесывание вывода
        from_text, to_text, pier = clean_data(from_text, to_text)

        # if from_phangan:
        #     pier = re.match(r'.*\((?P<pier>.*)\)', to_text)
        # elif to_phangan:
        #     pier = re.match(r'.*\((?P<pier>.*)\)', from_text)
        # else:
        #     pier = None
        # pier = pier.group('pier') if pier else ''
        #
        # from_text = re.sub(r'(\(.*\))', '', from_text).strip()
        # to_text = re.sub(r'(\(.*\))', '', to_text).strip()
        # pier = re.sub(r' pier| Pier|RajaFerryPort ', '', pier, flags=re.I).strip()

        row = [td.text for td in tds]
        row = [from_text, to_text, pier, today] + row + [sources[2]]  #['Songserm']
        last_dest = to_text
        logger.debug('new row ' + str(row))
        outcome_table.append(row)
    logger.info('Найдено строк ' + str(len(outcome_table)))
    return outcome_table


# Получение необходимой информации с сайта https://songserm.com/
def song_parse():
    url = 'https://songserm.com/pages/service'
    r = requests.get(url)
    if r.status_code != 200:
        return []

    outcome_table = []
    # ID элементов div, в которых находится информация
    table_ids = ['table-tao', 'table-chumphon', 'table-phangan', 'table-samui']
    page = BeautifulSoup(r.text, 'html.parser')
    for t_id in table_ids:
        table = page.find('div', id=t_id)
        outcome_table.extend(song_parse_route_table(table))
    logger.info('Получено ' + str(len(outcome_table)) + ' строк')
    return outcome_table


# Запуск парсинга информации с сайта https://songserm.com/pages/service. Тут браузер не нужен
def start_parse_song():
    logger.info('Парсинг сайта songserm.com')
    song_table = song_parse()
    return song_table


def seat_get_destination(elem):
    from_span = elem.find_next('span')
    from_text = from_span.text.strip()
    pier_a = from_span.find_next('a')
    from_text += ' (' + pier_a.text.strip() + ')'
    from_time_span = pier_a.find_next('span')
    from_time_text = from_time_span.text.strip()
    from_time_text = re.match(r'.*(?P<time>\d{2}:\d{2}).*', from_time_text)
    if from_time_text and 'time' in from_time_text.groupdict():
        from_time_text = from_time_text.group('time')
    else:
        from_time_text = ''
    from_text = re.sub(r' pier| Pier', '', from_text, flags=re.I).strip()
    return from_text, from_time_text


# Обработка таблицы с расписанием
def seat_parse_route_table(table, outcome_table_main=None):
    outcome_table = []
    trs = table.find_all('tr')
    # from_text = ''
    # from_text = trs[1].text.strip()
    # logger.debug('from_text ' + from_text)
    #
    # from_phangan = 'phangan' in from_text.lower()
    today = datetime.now() + timedelta(days=1)
    today = today.date().strftime('%d/%m/%Y')
    # last_dest = ''  # Последння строка с пунктов назначения
    for tr in trs[1:]:
        tds = tr.find_all('td')
        from_text, from_time_text = seat_get_destination(tds[0])
        from_text_lower = from_text.lower()
        from_phangan = 'phangan' in from_text_lower
        from_allowed = any(map(lambda x: x in from_text_lower, allowed_ports_lower))
        to_text, to_time_text = seat_get_destination(tds[1])
        to_text_lower = to_text.lower()
        to_allowed = any(map(lambda x: x in to_text_lower, allowed_ports_lower))
        to_phangan = 'phangan' in to_text.lower()
        sum_text_lower = from_text_lower + to_text_lower

        if not from_allowed or not to_allowed or not from_time_text or not to_time_text or\
                not from_phangan and from_allowed and not to_phangan or from_phangan and not to_allowed or\
                'any hotel' in sum_text_lower or 'airport' in sum_text_lower or 'town' in sum_text_lower:
            logger.debug('Направление ' + from_text + ' ' + to_text + ' пропущено')
            continue

        # Причесывание выводов
        if from_phangan:
            from_text = re.sub(r'(\(.*\))', '', from_text).strip()
        if to_phangan:
            to_text = re.sub(r'(\(.*\))', '', to_text).strip()

        price = re.match(r'(?P<price>\d*[,.]?\d*).*', tds[3].text.strip())
        price = price.group('price') if price and 'price' in price.groupdict() else ''

        # Причесывание вывода
        from_text, to_text, pier = clean_data(from_text, to_text)

        row = [from_text, to_text, pier, today, from_time_text, to_time_text, price, sources[3]]  #'Seatran']
        if row not in outcome_table_main:
            logger.debug('new row ' + str(row))
            outcome_table.append(row)
        else:
            logger.debug('row ' + str(row) + ' passed')
    logger.info('Найдено строк ' + str(len(outcome_table)))
    return outcome_table


# Получение необходимой информации с сайта https://seatrandiscovery.com/
def seat_parse():
    url = 'https://www.seatrandiscovery.com/trip-schedules.html#from_ferry'
    r = requests.get(url)
    if r.status_code != 200:
        return []

    outcome_table = []
    # ID элементов div, в которых находится информация
    page = BeautifulSoup(r.text, 'html.parser')
    form = page.find('form', id='bookfrm')
    div = form.next_sibling.next_sibling
    divs = div.find_all('div', class_='thepet2')
    page.get('id')
    for div in divs:
        table = div.find('table')
        outcome_table.extend(seat_parse_route_table(table, outcome_table))
    logger.info('Получено ' + str(len(outcome_table)) + ' строк')
    return outcome_table


# Запуск парсинга информации с сайта https://www.seatrandiscovery.com/trip-schedules.html#from_ferry. Браузер не нужен
def start_parse_seat():
    logger.info('Парсинг сайта seatrandiscovery.com')
    seat_table = seat_parse()
    return seat_table


# Функции для парсинга соответствующего ресурса
parsing_dict = {
    sources[0]: start_parse_raja,
    sources[1]: start_parse_lomp,
    sources[2]: start_parse_song,
    sources[3]: start_parse_seat,
}


# Парсинг ресурса rajaferryport и подготовка таблицы для импорта
def process_parsing(google_table, new_google_table, source):
    # Парсинг источника. Получение спарсенной таблицы
    parsed_table = parsing_dict[source]()
    old_table = get_source_table(google_table, source)
    # Если парсинг удался, то такую таблицу надо заменить/обновить
    new_google_table.extend(parsed_table or old_table)
    # if parsed_table:
    #     # Получение таблицы для источника https://www.rajaferryport.com/ из гугл таблицы
    #     # Вырезание даных для этого источника из таблицы
    #     # google_table.extend(parsed_table)
    #
    # else:
    #     new_google_table.extend(parsed_table)


# Основная функция
def main():
    # Получение гугл таблицы
    new_google_table = []
    google_table = get_table('ferry')

    # Сбор информации
    process_parsing(google_table, new_google_table, source=sources[0])  # Raja
    process_parsing(google_table, new_google_table, source=sources[1])  # Lomprayah
    process_parsing(google_table, new_google_table, source=sources[2])  # Songserm
    process_parsing(google_table, new_google_table, source=sources[3])  # Seatran

    # Импорт таблицы
    if new_google_table:
        refresh_table('ferry', [google_table[0]] + sorted(new_google_table + google_table[1:], key=lambda x: x[4]))


if __name__ == '__main__':
    main()
