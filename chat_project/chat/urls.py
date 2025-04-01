from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('chats/', views.chat_list, name='chat_list'),  # публичная страница
    path('accounts/login/', auth_views.LoginView.as_view(template_name='chat/login.html'), name='login'),
    # Аутентификация
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Чаты
    path('', views.chat_list, name='chat_list'),
    path('create/', views.chat_create, name='chat_create'),
    path('<int:chat_id>/', views.chat_detail, name='chat_detail'),
    
    # Поиск пользователей
    path('search/users/', views.search_users, name='search_users'),
    
    # Действия с сообщениями
    path('message/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('message/<int:message_id>/history/', views.message_history, name='message_history'),
]