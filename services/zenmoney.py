import json
import time
from os import system, name
from pathlib import Path
from getpass import getpass
from dataclasses import dataclass

from datetime import datetime
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from loguru import logger
import zenmoney


# from services.dialog import clear


class ZenMoney(zenmoney.Request):
    api = None
    oauth: zenmoney.OAuth2
    credentials: dict
    current_diff: zenmoney.diff
    datetime_format: str = '%d.%m.%Y, %H:%M:%S'
    datetime_format_old: str = '%Y.%m.%d %H.%M.%S'
    current_tags: list[str] = []
    current_payees: list

    def __init__(self, credentials_file: Path):
        self.read_credentials(credentials_file)
        print('Подключение к ZenMoney...')
        while not self.api:
            try:
                self.token = zenmoney.OAuth2(
                    consumer_key=self.credentials['consumer_key'],
                    consumer_secret=self.credentials['consumer_secret'],
                    username=self.credentials['username'],
                    password=self.credentials['password'])
                super().__init__(self.token.token)
                self.api = True

            except zenmoney.exception.ZenMoneyException as e:
                logger.error(f'Неверный логин или пароль!')
                self.credentials['username'] = ''
                self.credentials['password'] = ''
                self.input_credentials()

        self.save_credentials(credentials_file)

    def update(self, transactions: list) -> zenmoney.diff:
        return self.diff(
            zenmoney.Diff(
                **{
                    'serverTimestamp': self.get_diff().serverTimestamp,
                    'transaction': transactions
                }
            )
        )

    @staticmethod
    def make_named_transaction(attr) -> dataclass:
        """ Syntax sugar """

        @dataclass
        class NamedTransaction:
            income = attr.income
            outcomeInstrument = attr.outcomeInstrument
            outcomeAccount = attr.outcomeAccount
            deleted = attr.deleted
            incomeInstrument = attr.incomeInstrument
            incomeAccount = attr.incomeAccount
            latitude = attr.latitude
            date = attr.date
            originalPayee = attr.originalPayee
            viewed = attr.viewed
            id = attr.id
            changed = attr.changed
            created = attr.created
            user = attr.user
            payee = attr.payee
            outcome = attr.outcome
            merchant = attr.merchant
            # to_dict = attr.to_dict
            comment = attr.comment
            incomeBankID = attr.incomeBankID
            outcomeBankID = attr.outcomeBankID
            longitude = attr.longitude
            opIncomeInstrument = attr.opIncomeInstrument
            opOutcomeInstrument = attr.opOutcomeInstrument
            reminderMarker = attr.reminderMarker
            opIncome = attr.opIncome
            opOutcome = attr.opOutcome
            hold = attr.hold
            qrCode = attr.qrCode
            tag = attr.tag

            __excluded_fields__ = ['to_list_', 'to_dict']
            if hasattr(attr, 'category'):
                category = attr.category
            if hasattr(attr, 'sub_category'):
                sub_category = attr.sub_category
            if hasattr(attr, 'outcome_account_name'):
                outcome_account_name = attr.outcome_account_name
            if hasattr(attr, 'outcome_currency_short_title'):
                outcome_currency_short_title = attr.outcome_currency_short_title
            if hasattr(attr, 'income_account_name'):
                income_account_name = attr.income_account_name
            if hasattr(attr, 'income_currency_short_title'):
                income_currency_short_title = attr.income_currency_short_title

            def to_list_(self):
                trans_list = []
                for key in dir(self):
                    if not key.startswith('_'):
                        if key not in self.__excluded_fields__:
                            trans_list.append(getattr(self, key))
                return trans_list

            def to_dict(self):
                dict_ = {}
                for key in dir(self):
                    if not key.startswith('_'):
                        if key not in self.__excluded_fields__:
                            dict_.setdefault(key, getattr(self, key))
                return dict_

        return NamedTransaction

    def get_related_categories(self):
        # [[], [], []]
        related = []
        excluded = []
        for tag in self.current_diff.tag:
            column = []
            if tag.parent:
                category = self.get_tag(tag.parent)
                if category.title not in excluded:
                    column.append(category.title)  # [0] categories
                    for sub_category in self.current_diff.tag:
                        if sub_category.parent:
                            sub_parent = self.get_tag(sub_category.parent)
                            if sub_parent.id == category.id:
                                column.append(sub_category.title)  # sub categories
                    excluded.extend([i for i in column])
            else:
                if tag.title not in excluded:
                    related.append([tag.title])
            if column:
                related.append(column)

        return related

    @property
    def current_payees(self) -> list:
        return self.current_diff().get_payees()

    def get_tag(self, tag_id):
        for tag in self.current_diff.tag:
            if tag.id == tag_id:
                return tag

    def get_category_title(self, tag_ids):
        if tag_ids:
            sub_tag = self.get_tag(tag_ids[0])
            if sub_tag.parent:
                cat_tag = self.get_tag(sub_tag.parent)
                return cat_tag.title
            else:
                return sub_tag.title

        return ''

    def get_subcategory_title(self, tag_ids):
        if tag_ids:
            sub_tag = self.get_tag(tag_ids[0])
            if sub_tag.parent:
                cat_tag = self.get_tag(sub_tag.parent)
                return sub_tag.title
        return ''

    @staticmethod
    def fix_money_value(value):
        if not value:
            return ''
        else:
            return value

    def get_account_name(self, account_id, payment):
        if payment:
            for account in self.current_diff().account:
                if account.id == account_id:
                    return account.title
        else:
            return ''

    def get_instrument_short_title(self, transaction_instrument_id, payment):
        if payment:
            for instrument in self.current_diff.instrument:
                if transaction_instrument_id == instrument.id:
                    return instrument.shortTitle
        else:
            return ''

    def get_diff(self, sort_by_date=True) -> dataclass:
        """ Syntax sugar """
        diff = self.diff(zenmoney.Diff(**{'serverTimestamp': 1}))

        @dataclass
        class NamedDiff:
            account = diff.account
            company = diff.company
            currentClientTimeStamp = diff.currentClientTimestamp
            instrument = diff.instrument
            serverTimestamp = diff.serverTimestamp
            tag = diff.tag
            to_dict = diff.to_dict
            transactions = diff.transaction
            user = diff.user

            def sorted_transactions(self):
                self.transactions.sort(
                    key=lambda item: datetime.strptime(item.date, '%Y-%m-%d'))
                return self.transactions

            def get_payees(self) -> list:
                payees = []
                for transaction in self.transactions:
                    if transaction.payee:
                        if transaction.payee not in payees:
                            payees.append(transaction.payee)
                return payees

        self.current_diff = NamedDiff
        return NamedDiff

    def read_credentials(self, credentials_file):
        if credentials_file.exists():
            with open(credentials_file, 'r') as file:
                credentials = file.read()
                if credentials:
                    self.credentials = json.loads(credentials)
                else:
                    self.credentials = self.make_credentials()

        self.input_credentials()
        self.save_credentials(credentials_file)
        return self.credentials

    def input_credentials(self):
        for key in self.credentials.__iter__():
            if not self.credentials.__getitem__(key):

                if key == "password":
                    value = getpass(prompt="password: ")
                else:
                    clear()
                    value = input('Введите ZenMoney {}: '
                                  .format(key.replace('_', ' ')))

                self.credentials[key] = value

    def save_credentials(self, credentials_file):
        with open(credentials_file, 'w') as cred:
            cred.write(json.dumps(self.credentials))

    @staticmethod
    def make_credentials():
        return {
            "consumer_key": "",
            "consumer_secret": "",
            "username": "",
            "password": ""
        }

    def convert_related_data(self, named_transaction):
        """ Makes a string representation of related transaction fields
            required to write to google sheets"""
        setattr(named_transaction,
                "category",
                self.get_category_title(
                    named_transaction.tag))

        setattr(named_transaction,
                "sub_category",
                self.get_subcategory_title(
                    named_transaction.tag))

        setattr(named_transaction,
                "outcome",
                self.fix_money_value(
                    named_transaction.outcome))

        setattr(named_transaction,
                "outcome_account_name",
                self.get_account_name(
                    named_transaction.incomeAccount,
                    named_transaction.outcome))

        setattr(named_transaction,
                "created",
                format_date(
                    named_transaction.created))

        setattr(named_transaction,
                "outcome_currency_short_title",
                self.get_instrument_short_title(
                    named_transaction.outcomeInstrument,
                    named_transaction.outcome))

        setattr(named_transaction,
                "income",
                self.fix_money_value(
                    named_transaction.income))

        setattr(named_transaction,
                "income_account_name",
                self.get_account_name(
                    named_transaction.outcomeAccount,
                    named_transaction.income))

        setattr(named_transaction,
                "changed",
                format_date(
                    named_transaction.changed))

        setattr(named_transaction,
                "income_currency_short_title",
                self.get_instrument_short_title(
                    named_transaction.incomeInstrument,
                    named_transaction.income))

        return self.make_named_transaction(named_transaction)

    @staticmethod
    def is_in_period(transaction_date_str, months: int = 12):
        """ Checks if the transaction is included in the period
        starting from the current date - 12 months """
        if not months:
            months = 12
        transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d')
        months = relativedelta(months=int(months))
        return transaction_date >= (datetime.now() - months)

    def make_timestamp(self, str_date):
        try:
            timetuple = datetime.strptime(
                str_date, self.datetime_format).timetuple()
        except ValueError:
            timetuple = datetime.strptime(
                str_date, self.datetime_format_old).timetuple()

        return int(time.mktime(timetuple))


def format_date(timestamp) -> str:
    date_ = datetime.fromtimestamp(timestamp)
    return date_.strftime(ZenMoney.datetime_format)


def clear():
    system('cls') if name == 'nt' else system('clear')
