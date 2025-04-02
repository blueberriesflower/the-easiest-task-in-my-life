import json
import asyncio
import base64
import uuid
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import PermissionDenied
from .models import Chat, Message, MessageEditHistory

from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from .models import Chat, Message, MessageEditHistory

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_id = None
        self.user = None
        self.chat_group_name = None

    async def connect(self):
        await self.accept()  # Принимаем соединение сразу
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.user = self.scope['user']
        self.chat_group_name = f'chat_{self.chat_id}'

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        try:
            # Быстрая проверка участия в чате
            is_member = await sync_to_async(
                Chat.objects.filter(
                    id=self.chat_id,
                    members__id=self.user.id
                ).exists
            )()
            
            if not is_member:
                await self.close(code=4003)
                return

            # Добавляем в группу с таймаутом
            await asyncio.wait_for(
                self.channel_layer.group_add(
                    self.chat_group_name,
                    self.channel_name
                ),
                timeout=2.0
            )
            
            await self.send_chat_history()
            
        except asyncio.TimeoutError:
            await self.close(code=4004)
        except Exception as e:
            print(f"Connection error: {str(e)}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        if hasattr(self, 'chat_group_name') and self.chat_group_name:
            try:
                await asyncio.wait_for(
                    self.channel_layer.group_discard(
                        self.chat_group_name,
                        self.channel_name
                    ),
                    timeout=200000.0
                )
            except (asyncio.TimeoutError, Exception):
                pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            handler = {
                'chat_message': self.handle_new_message,
                'edit_message': self.handle_edit_message,
                'delete_message': self.handle_delete_message
            }.get(data.get('type'))
            
            if handler:
                await handler(data)
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            await self.send_error(f"Processing error: {str(e)}")

    async def handle_new_message(self, data):
        """Обработка нового сообщения"""
        text = data.get('text', '').strip()
        if not text and 'media' not in data:
            raise ValueError("Сообщение не может быть пустым")

        # Создание сообщения
        message = await sync_to_async(Message.objects.create)(
            chat_id=self.chat_id,
            sender=self.user,
            text=text,
            media=data.get('media')
        )

        # Отправка всем участникам
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'chat_message',
                'message_id': message.id,
                'sender': self.user.username,
                'text': message.text,
                'media_url': message.media.url if message.media else None,
                'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        )

    async def handle_edit_message(self, data):
        """Обработка редактирования сообщения"""
        message = await self.get_message(data['message_id'])
        await self.check_edit_permission(message)

        # Сохранение истории
        await sync_to_async(MessageEditHistory.objects.create)(
            message=message,
            old_text=message.text,
            edited_by=self.user
        )

        # Обновление сообщения
        message.text = data['new_text']
        await sync_to_async(message.save)()

        # Рассылка изменений
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'message_edited',
                'message_id': message.id,
                'new_text': message.text,
                'edited_by': self.user.username,
                'edited_at': message.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        )

    async def handle_delete_message(self, data):
        """Обработка удаления сообщения"""
        message = await self.get_message(data['message_id'])
        await self.check_delete_permission(message)

        # Мягкое удаление
        message.is_deleted = True
        message.deleted_by = self.user
        await sync_to_async(message.save)()

        # Уведомление участников
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'message_deleted',
                'message_id': message.id,
                'deleted_by': self.user.username
            }
        )

    # Вспомогательные методы
    async def get_message(self, message_id):
        """Получение сообщения с проверкой"""
        message = await sync_to_async(Message.objects.select_related('chat', 'sender').get)(
            id=message_id,
            chat_id=self.chat_id,
            is_deleted=False
        )
        return message

    async def check_edit_permission(self, message):
        """Проверка прав на редактирование"""
        if message.sender != self.user and not message.chat.admin == self.user:
            raise PermissionDenied("Нет прав на редактирование")

    async def check_delete_permission(self, message):
        """Проверка прав на удаление"""
        if message.sender != self.user and not message.chat.admin == self.user:
            raise PermissionDenied("Нет прав на удаление")

    async def send_chat_history(self):
        """Отправка истории сообщений"""
        messages = await sync_to_async(list)(
            Message.objects.filter(chat_id=self.chat_id, is_deleted=False)
                          .order_by('created_at')[:50]
                          .select_related('sender')
        )
        
        for message in messages:
            await self.send(text_data=json.dumps({
                'type': 'chat_message',
                'message_id': message.id,
                'sender': message.sender.username,
                'text': message.text,
                'media_url': message.media.url if message.media else None,
                'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }))

    async def send_error(self, error_msg):
        """Отправка ошибки клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_msg
        }))

    # Обработчики рассылки
    async def chat_message(self, event):
        """Обработка нового сообщения для рассылки"""
        await self.send(text_data=json.dumps(event))

    async def message_edited(self, event):
        """Обработка редактирования для рассылки"""
        await self.send(text_data=json.dumps(event))

    async def message_deleted(self, event):
        """Обработка удаления для рассылки"""
        await self.send(text_data=json.dumps(event))