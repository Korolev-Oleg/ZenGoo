import json
from dataclasses import dataclass
from pathlib import Path

import pyperclip
from loguru import logger
import gspread

SETTINGS_FILE = '.settings'
if __name__ == '__main__':
    SETTINGS = Path('./') / SETTINGS_FILE
else:
    SETTINGS = Path('services') / SETTINGS_FILE


@dataclass
class Headers:
    """ Dataclass of transaction table headers
    Do not change the sequence! """
    __columns__ = 14 + 1
    __from_zero__ = False
    __column_id__ = iter(range(1, __columns__))  # sequential iterator
    date = next(__column_id__)
    categoryName = next(__column_id__)
    subCategoryName = next(__column_id__)
    payee = next(__column_id__)
    comment = next(__column_id__)
    outcomeAccountName = next(__column_id__)
    outcome = next(__column_id__)
    outcomeCurrencyShortTitle = next(__column_id__)
    incomeAccountName = next(__column_id__)
    income = next(__column_id__)
    incomeCurrencyShortTitle = next(__column_id__)
    createdDate = next(__column_id__)
    changedDate = next(__column_id__)
    id = next(__column_id__)

    columns_count = __columns__ - 1
    __excluded_fields__ = [
        'from_zero', 'iter_attrs', 'decrement', 'columns_count']

    def iter_attrs(self):
        for key in self.__dir__():
            if not key.startswith('_'):
                if key not in self.__excluded_fields__:
                    yield key, getattr(self, key)

    def decrement(self):
        for key, value in self.iter_attrs():
            setattr(self, key, value - 1)

    def __refresh(self):
        for key, value in self.iter_attrs():
            setattr(self, key, value + 1)

    def from_zero(self):
        if self.__from_zero__:
            self.__refresh()
        for key, value in self.iter_attrs():
            setattr(self, key, value - 1)
        self.__from_zero__ = True
        return self


# @dataclass
# class Services:
#     __start_col__ = 2
#     __columns__ = 2 + __start_col__
#     __column_id__ = iter(range(__start_col__, __columns__))  # sequential iterator
#     tags = next(__column_id__)
#     payee = next(__column_id__)
#     __excluded_fields__ = [
#         'iter_attrs', 'title']
#
#     def iter_attrs(self):
#         for key in self.__dir__():
#             if not key.startswith('_'):
#                 if key not in self.__excluded_fields__:
#                     yield key, getattr(self, key)
#
#     @property
#     def title(self):
#         return self.__class__.__name__


def read_creeds(creeds_file=None) -> dict:
    with open(creeds_file, 'r', encoding='utf-8') as creeds:
        return json.loads(creeds.read())


def update_creeds(credential_file, key, value):
    print(f'updating {key} {value}')
    creeds = read_creeds(credential_file)
    with open(credential_file, 'w', encoding='utf-8') as creeds_f:
        creeds[key] = value
        creeds_f.write(json.dumps(creeds))


class GooSheet:
    range = 'A:AA'
    headers = Headers()
    sheet_title: str
    google_sheet_url: str
    google_sheet_url: str
    worksheet_headers: list
    credential_file: Path
    spreadsheet: gspread.Spreadsheet
    worksheet: gspread.models.Worksheet

    # services = Services()

    def __init__(self, credential_file: Path, url=None, sheet_title=None):
        print('Подключение к google sheets...')
        self.sheet_title = self.get_title(credential_file)
        self.credential_file = credential_file
        self.set_work_sheet_url(url)
        self.make_spreadsheet()

    def set_work_sheet_url(self, change_url=None):
        if not change_url:
            self.google_sheet_url = self.get_current_url(
                self.credential_file)
        else:
            self.google_sheet_url = change_url
            self.update_creeds(
                self.credential_file,
                key='sheet_url', value=str(change_url))

    def set_worksheet_headers(self):
        try:
            self.worksheet_headers = self.worksheet.get(self.range)[0]
        except KeyError:
            headers = '\t'.join([str(attr) for attr, _ in Headers().iter_attrs()])
            logger.error('\nВ таблице отсутсвуют заголовки:\n{}'.format(
                headers))
            print('Скопированы в буфер.')
            pyperclip.copy(headers)
            exit()

    @logger.catch()
    def make_spreadsheet(self):
        account = gspread.service_account(str(self.credential_file))
        try:
            self.spreadsheet = account.open_by_url(self.google_sheet_url)
        except gspread.exceptions.NoValidUrlKeyFound:
            logger.error('\nЗадан не валидный google sheet url')
            update_creeds(self.credential_file,
                          key='sheet_url',
                          value=input('Введите google sheet url: '))

        if self.sheet_title:
            try:
                self.worksheet = self.spreadsheet.worksheet(self.sheet_title)
            except gspread.exceptions.WorksheetNotFound:
                logger.error('\nНе найден лист с именем {}'.format(
                    self.sheet_title))
                exit()
            except gspread.exceptions.APIError:
                service_email = self.get_service_email(self.credential_file)
                logger.error('\nОшибка доступа! Откройте доступ '
                             'сервисному аккаунту: \nСкопировано! {}'
                             .format(service_email))

                pyperclip.copy(service_email)
                exit()
            except AttributeError:
                logger.error("'GooSheet' object has no attribute 'spreadsheet'")

            self.set_worksheet_headers()
            self.check_table()
            return self.worksheet

    def check_table(self, worksheet: gspread.models.Worksheet = None):
        if worksheet:
            worksheet_headers: list = worksheet.get(self.range)[0]
        else:
            worksheet_headers = self.worksheet_headers

        for key, value in self.headers.iter_attrs():
            if key not in worksheet_headers:
                logger.error('В таблице отсутсвует заголовок {}'.format(key))
            else:
                setattr(self.headers, key,
                        worksheet_headers.index(key) + 1)

    @staticmethod
    def find_id_index_(transaction_id: str, transactions_list: list[list]):
        found_count = 0
        found_index = None
        for index, transaction in enumerate(transactions_list):
            if transaction_id in transaction:
                found_index = index
                found_count += 1

        if found_index:
            if found_count > 1:
                logger.warning(
                    'Колличество транзакий с id  {id} -- ({co})'.format(
                        id=transaction_id,
                        co=found_count))
                logger.warning('Перезаписана только первая!')
            return found_index

        return False

    @staticmethod
    def update_creeds(credential_file, key, value):
        creeds = read_creeds(credential_file)
        with open(credential_file, 'w') as creeds_f:
            creeds[key] = value
            creeds_f.write(json.dumps(creeds))

    @staticmethod
    def get_current_url(creeds_file):
        url = read_creeds(creeds_file).get('sheet_url')
        if not url:
            url = input('Введите google sheet url: ')
            update_creeds(creeds_file, key='sheet_url', value=url)
        return url

    @staticmethod
    def get_service_email(creeds_file):
        return read_creeds(creeds_file).get('client_email')

    @staticmethod
    def get_title(creeds_file):
        sheet_title = read_creeds(creeds_file).get('sheet_title')
        if not sheet_title:
            sheet_title = input('Введите имя листа: ')
            update_creeds(creeds_file, key='sheet_title', value=sheet_title)

        return sheet_title

    def get_clear_row(self, worksheet=None):
        if worksheet:
            worksheet_headers: list = worksheet.get(self.range)[0]
        else:
            worksheet_headers = self.worksheet_headers
        return ['' for i in range(len(worksheet_headers))]


def write_tags(payees, tags: list, worksheet: gspread.models.Worksheet):
    worksheet.batch_update([{
        'range': f'C1:{len(tags)}',
        'values': tags
    }, {
        'range': 'A1:A100',
        'values': [[p] for p in payees]
    }],
        value_input_option='USER_ENTERED')


def make_tags_worksheet(payees, tags, goo: GooSheet):
    try:
        worksheet = goo.spreadsheet.worksheet('Tags')
        goo.spreadsheet.values_clear(range='Tags!A1:J1000')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = goo.spreadsheet.add_worksheet(
            'Tags',
            cols=99,
            rows=len(tags) + 100
        )

    write_tags(payees, tags, worksheet)


def set_data_validation(goo):
    ws = goo.spreadsheet.worksheet('DropDown')
    from gspread import utils
    body = utils.filter_dict_values({
        'valueInputOption': 'USER_ENTERED',
        'setDataValidation': {
            'range': {
                'sheetId': ws.id,
                'startRowIndex': 2,
                'endRowIndex': 999,
                'startColumnIndex': 1,
                'endColumnIndex': 2
            },
            'rule': {
                'condition': {
                    'type': 'ONE_OF_RANGE',
                    'values': [
                        {
                            'userEnteredValue': '=Tags!B:B'
                        }
                    ]
                },
                'inputMessage': 'Выбирите категорию',
                'strict': True
            }
        }
    })
    goo.spreadsheet.values_batch_update(
        body=body)


if __name__ == '__main__':
    creeds_path = Path('../keys/zenMoneyToGoogleSheets-725b95ae6979.json')
    c = read_creeds(creeds_path)
    print(c['sheet_title'])
