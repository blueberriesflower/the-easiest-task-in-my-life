from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from .models import Chat, Message, MessageEditHistory
from .forms import RegisterForm, LoginForm, ChatCreateForm, MessageForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse


def register_view(request):
    """
    Обработка регистрации нового пользователя.
    """
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('chat_list')
    else:
        form = RegisterForm()
    return render(request, 'chat/register.html', {'form': form})

def login_view(request):
    """
    Обработка входа пользователя.
    """
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('chat_list')
    else:
        form = LoginForm()
    return render(request, 'chat/login.html', {'form': form})

@login_required
def logout_view(request):
    """
    Обработка выхода пользователя.
    """
    logout(request)
    return redirect('login')

@login_required
def chat_list(request):
    """
    Отображение списка чатов пользователя.
    """
    chats = request.user.chats.all().order_by('-created_at')
    return render(request, 'chat/chat_list.html', {'chats': chats})

@login_required
def chat_create(request):
    """
    Создание нового чата.
    """
    if request.method == 'POST':
        form = ChatCreateForm(request.POST)
        if form.is_valid():
            chat = form.save(commit=False)
            if form.cleaned_data['is_group']:
                chat.admin = request.user
            chat.save()
            chat.members.add(request.user)
            for member in form.cleaned_data['members']:
                chat.members.add(member)
            return redirect('chat_detail', chat_id=chat.id)
    else:
        form = ChatCreateForm()
    return render(request, 'chat/chat_create.html', {'form': form})

@login_required
def chat_detail(request, chat_id):
    """
    Отображение чата и обработка сообщений.
    """
    chat = get_object_or_404(Chat, id=chat_id, members=request.user)
    messages = Message.objects.filter(chat=chat, is_deleted=False).order_by('created_at')[:50]
    
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.chat = chat
            message.sender = request.user
            message.save()
            return redirect('chat_detail', chat_id=chat.id)
    else:
        form = MessageForm()
    
    return render(request, 'chat/chat_detail.html', {
        'chat': chat,
        'messages': messages,
        'form': form,
    })

@login_required
def search_users(request):
    """
    Поиск пользователей для добавления в чат.
    """
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query))
    else:
        users = User.objects.none()
    
    return JsonResponse({
        'users': [{'id': user.id, 'username': user.username} for user in users]
    })

@login_required
def edit_message(request, message_id):
    """
    Редактирование сообщения (AJAX).
    """
    if request.method == 'POST' and request.is_ajax():
        message = get_object_or_404(Message, id=message_id)
        
        # Проверяем права на редактирование
        if message.sender != request.user and not message.chat.admin == request.user:
            return JsonResponse({'status': 'error', 'message': 'Нет прав на редактирование'})
        
        new_text = request.POST.get('text', '')
        if new_text:
            # Сохраняем историю изменений
            MessageEditHistory.objects.create(
                message=message,
                old_text=message.text,
                edited_by=request.user
            )
            
            # Обновляем сообщение
            message.text = new_text
            message.save()
            
            return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'})

@login_required
def delete_message(request, message_id):
    """
    Удаление сообщения (AJAX).
    """
    if request.method == 'POST' and request.is_ajax():
        message = get_object_or_404(Message, id=message_id)
        
        # Проверяем права на удаление
        if message.sender != request.user and not message.chat.admin == request.user:
            return JsonResponse({'status': 'error', 'message': 'Нет прав на удаление'})
        
        # Помечаем сообщение как удалённое
        message.is_deleted = True
        message.deleted_by = request.user
        message.save()
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'})

@login_required
def message_history(request, message_id):
    """
    Просмотр истории изменений сообщения.
    """
    message = get_object_or_404(Message, id=message_id)
    if not message.chat.members.filter(id=request.user.id).exists():
        return redirect('chat_list')
    
    history = MessageEditHistory.objects.filter(message=message).order_by('-edited_at')
    return render(request, 'chat/message_history.html', {
        'message': message,
        'history': history,
    })