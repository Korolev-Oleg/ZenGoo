
from integration import *
import os

import inquirer
import pyperclip
from loguru import logger


def default_question():
    return [
        inquirer.List(
            0,
            message='Выбирите действие',
            choices=[
                '1) ZenMoney -> GoogleSh',
                '2) GoogleSh -> ZenMoney',
                '3) ZenMoney <> GoogleSh',
                '4) Настройки',
                '5) Выход']
        )
    ]


def month_question():
    return [
        inquirer.Text(
            1,
            message='Кол-во месяцев',
            default=12
        )
    ]


def settings_question():
    return [
        inquirer.List(
            0,
            message='Выбирите действие',
            choices=[
                '1) Скопировать email сервисного аккаунта',
                '2) Изменить ссылку на google sheet',
                '3) Изменить sheet title'
            ]
        )
    ]


def change_google_link_question():
    return [
        inquirer.Text(
            'google_url',
            message="Ссылка на google sheet")
    ]


def change_google_sheet_title(current):
    return [
        inquirer.Text(
            'sheet_title',
            message='Title',
            default=current
        )]


@logger.catch()
def start():
    while True:
        settings: dict
        default: inquirer.prompt
        changed_google_url = None

        broke = 0
        while True:
            # run default question
            default = inquirer.prompt(
                default_question())

            # set months
            if default[0].count('1)') or default[0].count('3)'):
                month = inquirer.prompt(
                    month_question())[1]
                month = month.replace('\x08', '')
                default[1] = int(month)

            clear()

            # if choice settings
            settings: inquirer.prompt = {}
            if default[0].count('4)'):
                settings = inquirer.prompt(
                    settings_question())

                # copy service email
                if settings[0].count('1)'):
                    email = GooSheet.get_service_email(
                        GOOGLE_CREDENTIALS_FILE)
                    pyperclip.copy(email)
                    clear()
                    print('Скопировано {}'.format(email))

                # change google sheet url
                if settings[0].count('2)'):
                    changed_google_url = inquirer.prompt(
                        change_google_link_question()
                    )['google_url']

                # change sheet title
                if settings[0].count('3)'):
                    current_title = GooSheet.get_title(
                        GOOGLE_CREDENTIALS_FILE)

                    sheet_title = inquirer.prompt(
                        change_google_sheet_title(current_title)
                    )['sheet_title']

                    GooSheet.update_creeds(
                        GOOGLE_CREDENTIALS_FILE,
                        key='sheet_title',
                        value=sheet_title)
            else:
                clear()
                break

        # preparing settings
        if changed_google_url:
            google_url = changed_google_url
        elif not GooSheet.get_current_url(GOOGLE_CREDENTIALS_FILE):
            google_url = input('Введите google sheet url:\n')
        else:
            google_url = False

        # ZenMoney -> GoogleSh
        if default[0].count('1)'):
            months = default[1]
            updated_count = zen_to_google(
                ZEN_MONEY_CREDENTIALS_FILE,
                months=months,
                google_url=google_url)

            print('Обновлено транзакций: {}, за период {} месяц(ев)'.format(
                updated_count, default[1]))

        # GoogleSh -> ZenMoney
        elif default[0].count('2)'):
            updated_count = google_to_zen()
            print('Обновлено транзакций:', updated_count)

        # ZenMoney <> GoogleSh
        elif default[0].count('3)'):
            two_way_integration(months=default[1])

        # Exit
        elif default[0].count('5)'):
            sys.exit()


def clear():
    os.system('cls') if os.name == 'nt' else os.system('clear')
