from django.urls import path
from . import views

urlpatterns = [
    path('', views.ad_list, name='ad_list'),
    path('suggest/', views.ad_search_suggest, name='ad_search_suggest'),
    path('ad/<int:pk>/', views.ad_detail, name='ad_detail'),
    path('banned/', views.banned_view, name='banned'),

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    path('create/', views.ad_create, name='ad_create'),
    path('my/', views.my_ads, name='my_ads'),
    path('ad/<int:pk>/delete/', views.ad_delete, name='ad_delete'),

    path('moderation/', views.moderation_queue, name='moderation_queue'),
    path('moderation/<int:pk>/', views.moderate_ad, name='moderate_ad'),
    path('moderation/users/', views.users_list, name='users_list'),
    path('moderation/users/<int:user_id>/ban/', views.ban_user, name='ban_user'),
]