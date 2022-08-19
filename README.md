# Telegram-бот для работы с API сайта Yandex.Practicum

Написанный на Python Telegram-бот обращается к API сервиса Yandex.Practicum и узнает статус домашней работы.

## Особенности / Features

- Раз в 10 минут бот делает запрос к API сервису Yandex.Practicum и проверяет статус отправленной на ревью домашней работы
- При обновлении статуса анализирует ответ API и отправляет соответствующее уведомление в Telegram
- Логирует работу и сообщает о проблемах сообщением в Telegram

## Стек технологий / Tech

- [Python](https://www.python.org/)
- [Python-telegram-bot](https://python-telegram-bot.org/)

## Как запустить проект / Installation
Клонировать репозиторий на свой компьютер
```
git clone git@github.com:gplakhotnikov/PROJECT_NAME.git
```

Установите зависимости, запустив команду pip3 install -r requirements.txt. После этого запустите файл homework.py для начала работы бота. 
```sh
pip3 install -r requirements.txt
python3 homework.py
```
## О разработчике / Development
(с) Grigory Plakhotnikov
