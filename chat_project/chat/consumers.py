import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import Chat, Message, MessageEditHistory
from django.core.files.base import ContentFile
import base64
import uuid

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
        
        # Проверяем, является ли пользователь участником чата
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
            
        try:
            chat = await Chat.objects.aget(id=self.chat_id)
            if not chat.members.filter(id=user.id).exists():
                await self.close()
                return
        except Chat.DoesNotExist:
            await self.close()
            return
        
        # Присоединяемся к группе чата
        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Отправляем историю сообщений
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
        
        if message_type == 'chat_message':
            # Обработка нового сообщения
            text = text_data_json['text']
            media_data = text_data_json.get('media', None)
            
            # Создаём сообщение
            chat = await Chat.objects.aget(id=self.chat_id)
            message = Message(
                chat=chat,
                sender=user,
                text=text
            )
            
            # Обработка медиафайла
            if media_data:
                format, media_str = media_data.split(';base64,') 
                ext = format.split('/')[-1]
                media_file = ContentFile(
                    base64.b64decode(media_str),
                    name=f'{uuid.uuid4()}.{ext}'
                )
                message.media = media_file
            
            await message.asave()
            
            # Отправляем сообщение всем участникам чата
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message.id,
                    'sender': user.username,
                    'text': text,
                    'media_url': message.media.url if message.media else None,
                    'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
            )
        
        elif message_type == 'edit_message':
            # Редактирование сообщения
            message_id = text_data_json['message_id']
            new_text = text_data_json['new_text']
            
            try:
                message = await Message.objects.select_related('chat').aget(id=message_id, chat_id=self.chat_id)
                
                # Проверяем права на редактирование
                if message.sender != user and not message.chat.admin == user:
                    return
                
                # Сохраняем историю изменений
                await MessageEditHistory.objects.acreate(
                    message=message,
                    old_text=message.text,
                    edited_by=user
                )
                
                # Обновляем сообщение
                message.text = new_text
                await message.asave()
                
                # Отправляем обновлённое сообщение всем участникам
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
            except Message.DoesNotExist:
                pass
        
        elif message_type == 'delete_message':
            # Удаление сообщения
            message_id = text_data_json['message_id']
            
            try:
                message = await Message.objects.select_related('chat').aget(id=message_id, chat_id=self.chat_id)
                
                # Проверяем права на удаление
                if message.sender != user and not message.chat.admin == user:
                    return
                
                # Помечаем сообщение как удалённое
                message.is_deleted = True
                message.deleted_by = user
                await message.asave()
                
                # Отправляем информацию об удалении всем участникам
                await self.channel_layer.group_send(
                    self.chat_group_name,
                    {
                        'type': 'delete_message',
                        'message_id': message.id,
                        'deleted_by': user.username,
                    }
                )
            except Message.DoesNotExist:
                pass
    
    async def send_chat_history(self):
        """
        Отправка истории сообщений чата новому подключившемуся клиенту
        """
        messages = Message.objects.filter(chat_id=self.chat_id, is_deleted=False).order_by('created_at')[:50]
        
        async for message in messages:
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