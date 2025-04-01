import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import PermissionDenied
from .models import Chat, Message, MessageEditHistory


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Асинхронный потребитель для обработки WebSocket соединений чата.
    """
    
    async def connect(self):
        """
        Обработка подключения нового клиента.
        """
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'
        user = self.scope['user']
        
        if not user.is_authenticated:
            await self.close()
            return
            
        # Используем sync_to_async для синхронных операций с БД
        chat = await sync_to_async(Chat.objects.get)(id=self.chat_id)
        is_member = await sync_to_async(chat.members.filter(id=user.id).exists)()
        
        if not is_member:
            await self.close()
            return
            
        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )
        await self.accept()
        await self.send_chat_history()
    
    async def disconnect(self, close_code):
        """
        Обработка отключения клиента.
        """
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Обработка полученных данных от клиента
        """
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']
        user = self.scope['user']
        
        if message_type == 'edit_message':
            await self.handle_edit_message(text_data_json, user)
        elif message_type == 'delete_message':
            await self.handle_delete_message(text_data_json, user)
        # ... обработка обычных сообщений ...

    async def handle_edit_message(self, data, user):
        message_id = data['message_id']
        new_text = data['new_text']
        
        try:
            message = await sync_to_async(Message.objects.select_related('chat', 'sender').get)(
                id=message_id, 
                chat_id=self.chat_id
            )
            
            # Проверка прав
            if message.sender != user and not message.chat.admin == user:
                raise PermissionDenied("Нет прав на редактирование")
            
            # Сохраняем историю
            await sync_to_async(MessageEditHistory.objects.create)(
                message=message,
                old_text=message.text,
                edited_by=user
            )
            
            # Обновляем сообщение
            message.text = new_text
            await sync_to_async(message.save)()
            
            # Отправляем изменения всем
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    'type': 'edit_message',
                    'message_id': message.id,
                    'new_text': new_text,
                    'edited_by': user.username,
                    'edited_at': message.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
            )
        except (Message.DoesNotExist, PermissionDenied) as e:
            print(f"Ошибка редактирования: {e}")

    async def handle_delete_message(self, data, user):
        message_id = data['message_id']
        
        try:
            message = await sync_to_async(Message.objects.select_related('chat', 'sender').get)(
                id=message_id,
                chat_id=self.chat_id
            )
            
            # Проверка прав
            if message.sender != user and not message.chat.admin == user:
                raise PermissionDenied("Нет прав на удаление")
            
            # "Мягкое" удаление
            message.is_deleted = True
            message.deleted_by = user
            await sync_to_async(message.save)()
            
            # Уведомляем всех
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    'type': 'delete_message',
                    'message_id': message.id,
                    'deleted_by': user.username,
                }
            )
        except (Message.DoesNotExist, PermissionDenied) as e:
            print(f"Ошибка удаления: {e}")
    
    async def send_chat_history(self):
        """
        Отправка истории сообщений чата новому подключившемуся клиенту
        """
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
    
    async def chat_message(self, event):
        """
        Отправка нового сообщения всем клиентам в чате
        """
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event['message_id'],
            'sender': event['sender'],
            'text': event['text'],
            'media_url': event.get('media_url', None),
            'created_at': event['created_at'],
        }))
    
    async def edit_message(self, event):
        """
        Отправка информации об изменении сообщения всем клиентам в чате
        """
        await self.send(text_data=json.dumps({
            'type': 'edit_message',
            'message_id': event['message_id'],
            'new_text': event['new_text'],
            'edited_by': event['edited_by'],
            'edited_at': event['edited_at'],
        }))
    
    async def delete_message(self, event):
        """
        Отправка информации об удалении сообщения всем клиентам в чате
        """
        await self.send(text_data=json.dumps({
            'type': 'delete_message',
            'message_id': event['message_id'],
            'deleted_by': event['deleted_by'],
        }))