from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


class UserProfile(models.Model):
    """Профиль с флагом бана."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    is_banned = models.BooleanField('Забанен', default=False)
    ban_reason = models.CharField('Причина бана', max_length=255, blank=True)
    banned_at = models.DateTimeField('Дата бана', null=True, blank=True)
    banned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='banned_users', verbose_name='Кто забанил'
    )

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'{self.user.username}{" 🚫" if self.is_banned else ""}'

    def ban(self, reason='', by=None):
        self.is_banned = True
        self.ban_reason = reason
        self.banned_at = timezone.now()
        self.banned_by = by
        self.save()
        # Снимаем все объявления с публикации
        self.user.ads.update(status='rejected', is_published=False)

    def unban(self):
        self.is_banned = False
        self.ban_reason = ''
        self.banned_at = None
        self.banned_by = None
        self.save()


class Category(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('Слаг', max_length=100, unique=True)
    icon = models.CharField('Иконка (emoji)', max_length=8, blank=True, default='📦')
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['order', 'name']

    def __str__(self):
        return f'{self.icon} {self.name}' if self.icon else self.name

    @property
    def approved_count(self):
        return self.ads.filter(status='approved', is_published=True).count()


class AdQuerySet(models.QuerySet):
    def approved(self):
        return self.filter(status='approved', is_published=True)

    def pending(self):
        return self.filter(status='pending')

    def rejected(self):
        return self.filter(status='rejected')

    def search(self, q):
        if not q:
            return self
        return self.filter(
            models.Q(title__icontains=q) |
            models.Q(description__icontains=q) |
            models.Q(contact__icontains=q)
        )


class Ad(models.Model):
    STATUS_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]

    title = models.CharField('Заголовок', max_length=200, db_index=True)
    description = models.TextField('Описание')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2, default=0)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Категория', related_name='ads'
    )
    contact = models.CharField('Контакт', max_length=200, blank=True)
    image = models.ImageField('Изображение', upload_to='ads/', blank=True, null=True)
    status = models.CharField(
        'Статус', max_length=10, choices=STATUS_CHOICES,
        default='pending', db_index=True
    )
    is_published = models.BooleanField('Опубликовано', default=True)

    # Модерация
    moderation_note = models.TextField('Комментарий модератора', blank=True)
    moderated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='moderated_ads', verbose_name='Модератор'
    )
    moderated_at = models.DateTimeField('Дата модерации', null=True, blank=True)

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Автор', related_name='ads'
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    objects = AdQuerySet.as_manager()

    class Meta:
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_published', '-created_at']),
            models.Index(fields=['category', 'status']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('ad_detail', args=[self.pk])

    @property
    def price_display(self):
        if self.price and self.price > 0:
            return f'{self.price:.0f} ₽'
        return 'Бесплатно'

    def approve(self, by=None, note=''):
        self.status = 'approved'
        self.is_published = True
        self.moderation_note = note
        self.moderated_by = by
        self.moderated_at = timezone.now()
        self.save()

    def reject(self, by=None, note=''):
        self.status = 'rejected'
        self.is_published = False
        self.moderation_note = note
        self.moderated_by = by
        self.moderated_at = timezone.now()
        self.save()