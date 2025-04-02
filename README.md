# WebSocket Chat Application

![Django](https://img.shields.io/badge/Django-5.1.7-green)
![Channels](https://img.shields.io/badge/Channels-4.2.2-blue)
![Redis](https://img.shields.io/badge/Redis-5.2.1-red)

Реализация чата на вебсокете с обменом сообщениями, историей редактирования и медиавложениями.

## 🌟 Фички

- 💬 Групповые и личные чаты
- ✏️ Редактирование и удаление сообщений
- 📎 Отправка медиафайлов (изображения, видео)
- 🕒 История изменений сообщений
- 🔐 Ролевая модель (администраторы/пользователи)
- ⚡ Технология WebSocket для мгновенных обновлений

## 🛠 Технологический стек

- **Backend**: Django 3.2 + Django Channels
- **Frontend**: Bootstrap 5 + Jinja2
- **Брокер сообщений**: Redis
- **ASGI-сервер**: Daphne

## 🚀 Установка

### Требования
- Python 3.8+
- Redis 5+

### Инструкция

1. Клонируйте репозиторий

2. Настройте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate    # Windows
```

3. Установите зависимости
```bash
pip install -r requirements.txt
```

4. Настройте базу данных в settings.py
5. Примените миграции:
```bash
python manage.py migrate
```
6. Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

## 🏃 Запуск

1. Запустите Redis (в отдельном терминале):
```bash
redis-server
```
2. Запустите ASGI-сервер:
```bash
daphne chat_project.asgi:application
```
3. Запустите worker (опционально, в другом терминале):
```bash
python manage.py runworker
```
4. Откройте в браузере:
http://localhost:8000

5. Поставьте мне зачет