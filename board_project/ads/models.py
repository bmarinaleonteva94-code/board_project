from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Category(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('Слаг', max_length=100, unique=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Ad(models.Model):
    STATUS_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]

    title = models.CharField('Заголовок', max_length=200)
    description = models.TextField('Описание')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2, default=0)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Категория', related_name='ads'
    )
    contact = models.CharField('Контакт', max_length=200, blank=True)
    image = models.ImageField('Изображение', upload_to='ads/', blank=True, null=True)
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='pending')
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Автор', related_name='ads'
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    is_published = models.BooleanField('Опубликовано', default=True)

    class Meta:
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('ad_detail', args=[self.pk])

    @property
    def price_display(self):
        if self.price and self.price > 0:
            return f'{self.price:.0f} ₽'
        return 'Бесплатно'