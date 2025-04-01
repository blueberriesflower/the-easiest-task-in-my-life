from django.urls import re_path
from . import consumers

# Список WebSocket URL-шаблонов для маршрутизации соединений
websocket_urlpatterns = [
    # Определяем путь для WebSocket-соединений чата
    # r'ws/chat/(?P<chat_id>\w+)/$' - URL-шаблон, где:
    #   - 'ws/chat/' - префикс WebSocket-соединений чата
    #   - (?P<chat_id>\w+) - именованная группа, захватывающая ID чата (состоящий из буквенно-цифровых символов)
    # as_asgi() - преобразует consumer в ASGI-приложение
    re_path(r'ws/chat/(?P<chat_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
]