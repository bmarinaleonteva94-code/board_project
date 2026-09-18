from django.contrib import admin
from django.utils.html import format_html
from .models import Ad, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'author', 'category', 'price',
        'status_badge', 'is_published', 'created_at'
    )
    list_filter = ('status', 'category', 'is_published', 'created_at')
    list_editable = ('is_published',)
    search_fields = ('title', 'description', 'contact', 'author__username')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'preview_image')
    list_per_page = 20

    fieldsets = (
        ('Основное', {
            'fields': ('title', 'description', 'category', 'price', 'contact')
        }),
        ('Медиа', {
            'fields': ('image', 'preview_image')
        }),
        ('Модерация', {
            'fields': ('status', 'is_published', 'author')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_ads', 'reject_ads']

    @admin.display(description='Статус')
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:12px">{}</span>',
            colors.get(obj.status, '#999'),
            obj.get_status_display()
        )

    @admin.display(description='Превью')
    def preview_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:200px;border-radius:8px">',
                obj.image.url
            )
        return '—'

    @admin.action(description='✅ Одобрить выбранные')
    def approve_ads(self, request, queryset):
        n = queryset.update(status='approved')
        self.message_user(request, f'Одобрено объявлений: {n}')

    @admin.action(description='❌ Отклонить выбранные')
    def reject_ads(self, request, queryset):
        n = queryset.update(status='rejected')
        self.message_user(request, f'Отклонено объявлений: {n}')