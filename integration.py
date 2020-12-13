#!/usr/bin/python3.9

__author__ = 'ok@hustn.cn'

import sys
import time
from pathlib import Path
from pprint import pprint
from os import system, name

import gspread
import inquirer
from loguru import logger
from services.zenmoney import ZenMoney
from services.googlesheets import (
    GooSheet, make_tags_worksheet
)
from services import dialog

GOOGLE_CREDENTIALS_FILE = Path(
    'keys/zenMoneyToGoogleSheets-725b95ae6979.json')

ZEN_MONEY_CREDENTIALS_FILE = Path(
    'keys/zen_money_cred.json')


def pre_update_transaction(headers, transaction,
                           row: list) -> list:
    if not headers.id < len(row):
        headers.decrement()

    row[headers.outcomeCurrencyShortTitle] = transaction.outcome_currency_short_title
    row[headers.incomeCurrencyShortTitle] = transaction.income_currency_short_title
    row[headers.outcomeAccountName] = transaction.outcome_account_name
    row[headers.incomeAccountName] = transaction.income_account_name
    row[headers.subCategoryName] = transaction.sub_category
    row[headers.categoryName] = transaction.category
    row[headers.createdDate] = transaction.created
    row[headers.changedDate] = transaction.changed
    row[headers.comment] = transaction.comment
    row[headers.outcome] = transaction.outcome
    row[headers.income] = transaction.income
    row[headers.payee] = transaction.payee
    row[headers.date] = transaction.date
    row[headers.id] = transaction.id
    return row


@logger.catch()
def zen_to_google(credentials_file, months=12,
                  google_url=None, sheet_title='Тарнзакции'):
    # make google worksheet
    goo = GooSheet(
        GOOGLE_CREDENTIALS_FILE,
        url=google_url,
        sheet_title=sheet_title)

    if hasattr(goo, 'worksheet'):
        # make list transactions from google
        google_transactions: list = goo.worksheet.get(
            goo.range, value_render_option='FORMULA')

        #  make zen connection
        updated_count = 0
        zen = ZenMoney(credentials_file)
        diff = zen.get_diff()
        for transaction_obj in diff().sorted_transactions():
            transaction = zen.convert_related_data(transaction_obj)
            if not transaction.deleted:
                if ZenMoney.is_in_period(transaction.date, months):
                    found_id = goo.find_id_index_(
                        transaction.id, google_transactions)

                    if found_id:  # pre update row in google list
                        updated_count += 1
                        google_transactions[found_id] = \
                            pre_update_transaction(
                                goo.headers.from_zero(), transaction,
                                google_transactions[found_id])

                    else:  # Pre append in to google list
                        updated_count += 1
                        google_transactions.append(
                            pre_update_transaction(
                                row=goo.get_clear_row(),
                                headers=goo.headers.from_zero(),
                                transaction=transaction))

        #  Update google transactions
        goo.worksheet.batch_update([{
            'range': goo.range,
            'values': google_transactions}],
            value_input_option='USER_ENTERED')

        make_tags_worksheet(
            tags=zen.get_related_categories(),
            goo=goo, payees=zen.current_payees
        )

        return updated_count


@logger.catch()
def google_to_zen():
    goo = GooSheet(GOOGLE_CREDENTIALS_FILE)
    google_transactions: list = goo.worksheet.get(
        goo.range, value_render_option='FORMULA')

    changed = []
    head = goo.headers
    zen = ZenMoney(ZEN_MONEY_CREDENTIALS_FILE)
    diff = zen.get_diff()
    transactions: list = diff.transactions
    for transaction_obj in transactions:
        zen_trns = zen.make_named_transaction(transaction_obj)
        if not zen_trns.deleted:
            for goo_trns in google_transactions[1:]:  # without headers
                if len(goo_trns) == goo.headers.columns_count:
                    goo_id = goo_trns[head.id - 1]
                    if goo_id == zen_trns.id:
                        goo_changed = goo_trns[head.changedDate - 1]
                        goo_changed = zen.make_timestamp(goo_changed)

                        # preparing changes
                        if goo_changed > zen_trns.changed:
                            zen_trns.changed = goo_changed
                            zen_trns.comment = goo_trns[head.comment - 1]
                            zen_trns.payee = goo_trns[head.payee - 1]
                            changed.append(zen_trns().to_dict())

    response = zen.update(changed)
    result = response.to_dict().get('transaction')
    return len(result) if result else 0


def two_way_integration():
    google_to_zen()
    zen_to_google()


if __name__ == '__main__':
    # google_to_zen()
    # zen_to_google(ZEN_MONEY_CREDENTIALS_FILE)
    dialog.start()
