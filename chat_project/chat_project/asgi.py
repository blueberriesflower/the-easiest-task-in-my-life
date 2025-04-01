"""
ASGI config for chat_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_project.settings')

# Определяем корневое ASGI-приложение, которое будет обрабатывать разные типы протоколов
application = ProtocolTypeRouter({
    "http": get_asgi_application(), # Обработка HTTP-запросов
    "websocket": AuthMiddlewareStack( # Обработка WebSocket-соединений
    # AuthMiddlewareStack добавляет поддержку аутентификации пользователей
        # URLRouter маршрутизирует WebSocket-запросы по URL-шаблонам из chat.routing
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})
