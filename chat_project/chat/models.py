from django.db import models
from django.contrib.auth.models import User


class Chat(models.Model):
    """
    Модель чата
    """
    name = models.CharField(max_length=255, verbose_name="Название чата")
    members = models.ManyToManyField(User, related_name="chats", verbose_name="Участники")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    is_group = models.BooleanField(default=False, verbose_name="Групповой чат")
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="admin_chats", verbose_name="Администратор")

    class Meta:
        verbose_name = "Чат"
        verbose_name_plural = "Чаты"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class Message(models.Model):
    """
    Модель сообщения в чате.
    """
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages", verbose_name="Чат")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages", verbose_name="Отправитель")
    text = models.TextField(verbose_name="Текст сообщения", blank=True, null=True)
    media = models.FileField(upload_to='chat_media/', verbose_name="Медиафайл", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отправки")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата изменения")
    is_deleted = models.BooleanField(default=False, verbose_name="Удалено")
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="deleted_messages", verbose_name="Кто удалил")

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ['created_at']
    def __str__(self):
        return f"Сообщение от {self.sender.username} в {self.chat.name}"
    
class MessageEditHistory(models.Model):
    """
    История изменений сообщений.
    """
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="edit_history", verbose_name="Сообщение")
    old_text = models.TextField(verbose_name="Предыдущий текст")
    edited_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Кто изменил")
    edited_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата изменения")

    class Meta:
        verbose_name = "История изменения сообщения"
        verbose_name_plural = "История изменений сообщений"
        ordering = ['-edited_at']

    def __str__(self):
        return f"Изменение сообщения {self.message.id} пользователем {self.edited_by.username}"