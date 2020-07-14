from __future__ import print_function
import os
from googleapiclient.discovery import build
from google.oauth2 import service_account

SAMPLE_SPREADSHEET_ID = os.environ.get('SAMPLE_SPREADSHEET_ID')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

TABLE = os.environ.get('TABLE')
CRED_FILE = os.environ.get('CRED_FILE')

service = build('sheets', 'v4',
                credentials=service_account.Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES))
sheet = service.spreadsheets()
sheet_ids = {}


def get_table(range):
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=range).execute()
    values = result.get('values', [])
    return values


def get_tables(ranges):
    result = sheet.values().batchGet(spreadsheetId=SAMPLE_SPREADSHEET_ID, ranges=ranges).execute()
    return {r: result.get('valueRanges', [{}] * (i + 1))[i].get('values', []) for i, r in enumerate(ranges)}


def update_table(range, values):
    body = {'values': values}
    request = sheet.values().update(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=range,
                                    valueInputOption='RAW', body=body).execute()


def append_table(range, values):
    body = {'values': values}
    request = sheet.values().append(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=range,
                                    valueInputOption='RAW', body=body).execute()


def clear_table(range):
    # body = {}
    request = sheet.values().clear(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                   range=range).execute()


# Удаляет строчку из таблицы со сдвигом вверх
def delete_row(range, start_index):
    sheet_id = get_sheet_id(range)
    body = {'requests': [{
        'deleteDimension': {
            'range': {
                'sheetId': sheet_id,
                'dimension': 'ROWS',
                'startIndex': start_index,
                'endIndex': start_index + 1
            }}}]}
    return sheet.batchUpdate(spreadsheetId=SAMPLE_SPREADSHEET_ID, body=body).execute()


# Получаем ID страницы из таблицы и сохраняет в памяти для дальнейшего использования
def get_sheet_id(range):
    sheet_id = sheet_ids.get(range)
    if sheet_id is None:
        response = sheet.get(spreadsheetId=SAMPLE_SPREADSHEET_ID, ranges=[range]).execute()
        sheet_id = response['sheets'][0]['properties']['sheetId']
        sheet_ids[range] = sheet_id
    return sheet_id


def refresh_table(range, values):
    clear_table(range)
    update_table(range, values)


# Функции для работы с полученными таблицами
# Возвращает столбец с указанным названием в виде списка
def get_col_from_table(table, col_name):
    headers = table[0]
    if col_name in headers:
        col_idx = headers.index(col_name)
        return [row[col_idx] for row in table]
    return []


# Возвращает строку для которой найдется значение value в столбце col_name
def find_row_in_table(table, values):
    # values = [(col_name, value), ...]
    headers = table[0]
    if all([val[0] in headers for val in values]):
        for i, row in enumerate(table):
            if row and all([str(val[1]) == str(row[headers.index(val[0])]) for val in values]):
                data = {h: row[j] for j, h in enumerate(headers) if j < len(row)}
                data['row_i'] = i + 1  # В таблице отсчет с 1
                data['row'] = row
                return data
    return {}
