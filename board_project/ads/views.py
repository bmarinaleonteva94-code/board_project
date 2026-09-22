from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Ad, Category, UserProfile, User
from .forms import AdForm, RegisterForm, AdSearchForm
from .decorators import not_banned


# ============================================
# ПУБЛИЧНЫЕ: лента + поиск
# ============================================
def ad_list(request):
    form = AdSearchForm(request.GET or None)

    ads = Ad.objects.approved().select_related('category', 'author')

    if form.is_valid():
        q = form.cleaned_data.get('q')
        cats = form.cleaned_data.get('category')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        sort = form.cleaned_data.get('sort') or '-created_at'
        only_free = form.cleaned_data.get('only_free')
        has_photo = form.cleaned_data.get('has_photo')

        ads = ads.search(q)
        if cats:
            ads = ads.filter(category__in=cats)
        if min_price is not None:
            ads = ads.filter(price__gte=min_price)
        if max_price is not None:
            ads = ads.filter(price__lte=max_price)
        if only_free:
            ads = ads.filter(price=0)
        if has_photo:
            ads = ads.exclude(image='').exclude(image__isnull=True)

        ads = ads.order_by(sort)
    else:
        ads = ads.order_by('-created_at')

    # Категории со счётчиками (только одобренных)
    categories = Category.objects.annotate(
        cnt=Count('ads', filter=Q(ads__status='approved', ads__is_published=True))
    ).order_by('order', 'name')

    paginator = Paginator(ads, 12)
    page = paginator.get_page(request.GET.get('page'))

    # Сохраняем GET-параметры без page — для пагинации
    params = request.GET.copy()
    params.pop('page', None)

    context = {
        'page_obj': page,
        'form': form,
        'categories': categories,
        'query_params': params.urlencode(),
        'total_count': ads.count(),
        'has_filters': any([
            request.GET.get('q'),
            request.GET.getlist('category'),
            request.GET.get('min_price'),
            request.GET.get('max_price'),
            request.GET.get('only_free'),
            request.GET.get('has_photo'),
        ]),
    }
    return render(request, 'ads/ad_list.html', context)


# AJAX-подсказки для поиска
def ad_search_suggest(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    ads = Ad.objects.approved().search(q)[:8]
    return JsonResponse({
        'results': [
            {'id': a.id, 'title': a.title, 'url': a.get_absolute_url()}
            for a in ads
        ]
    })


def ad_detail(request, pk):
    ad = get_object_or_404(Ad.objects.select_related('category', 'author'), pk=pk)
    if ad.status != 'approved' and ad.author != request.user and not request.user.is_staff:
        messages.warning(request, 'Объявление ещё не прошло модерацию.')
        return redirect('ad_list')
    return render(request, 'ads/ad_detail.html', {'ad': ad})


# ============================================
# АВТОРИЗАЦИЯ
# ============================================
def register_view(request):
    if request.user.is_authenticated:
        return redirect('ad_list')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('ad_list')
    else:
        form = RegisterForm()
    return render(request, 'ads/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('ad_list')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            profile = getattr(user, 'profile', None)
            if profile and profile.is_banned:
                messages.error(request, f'Ваш аккаунт забанен: {profile.ban_reason or "—"}')
                return render(request, 'ads/login.html', {'form': form})
            login(request, user)
            messages.success(request, 'Вы вошли в систему.')
            return redirect(request.GET.get('next') or 'ad_list')
    else:
        form = AuthenticationForm()
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-input'})
    return render(request, 'ads/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('ad_list')


def banned_view(request):
    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    return render(request, 'ads/banned.html', {'profile': profile})


# ============================================
# КАБИНЕТ
# ============================================
@login_required
@not_banned
def ad_create(request):
    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.author = request.user
            ad.status = 'pending'
            ad.save()
            messages.success(request, 'Объявление отправлено на модерацию.')
            return redirect('my_ads')
    else:
        form = AdForm()
    return render(request, 'ads/ad_create.html', {'form': form})


@login_required
def my_ads(request):
    ads = request.user.ads.select_related('category').all()
    return render(request, 'ads/my_ads.html', {'ads': ads})


@login_required
@not_banned
def ad_delete(request, pk):
    ad = get_object_or_404(Ad, pk=pk, author=request.user)
    if request.method == 'POST':
        ad.delete()
        messages.success(request, 'Объявление удалено.')
    return redirect('my_ads')


# ============================================
# МОДЕРАЦИЯ (staff)
# ============================================
def is_moderator(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(is_moderator)
def moderation_queue(request):
    """Очередь объявлений на модерации."""
    status = request.GET.get('status', 'pending')
    if status not in ('pending', 'approved', 'rejected', 'all'):
        status = 'pending'

    ads = Ad.objects.select_related('category', 'author').all()
    if status != 'all':
        ads = ads.filter(status=status)
    else:
        ads = ads.order_by('-created_at')

    paginator = Paginator(ads, 20)
    page = paginator.get_page(request.GET.get('page'))

    stats = {
        'pending': Ad.objects.pending().count(),
        'approved': Ad.objects.approved().count(),
        'rejected': Ad.objects.rejected().count(),
        'banned_users': UserProfile.objects.filter(is_banned=True).count(),
    }

    return render(request, 'ads/moderation.html', {
        'page_obj': page,
        'status': status,
        'stats': stats,
    })


@user_passes_test(is_moderator)
@require_POST
def moderate_ad(request, pk):
    """Одобрить/отклонить/удалить объявление."""
    ad = get_object_or_404(Ad, pk=pk)
    action = request.POST.get('action')
    note = request.POST.get('note', '').strip()

    if action == 'approve':
        ad.approve(by=request.user, note=note)
        messages.success(request, f'«{ad.title}» одобрено.')
    elif action == 'reject':
        ad.reject(by=request.user, note=note)
        messages.warning(request, f'«{ad.title}» отклонено.')
    elif action == 'delete':
        title = ad.title
        ad.delete()
        messages.error(request, f'«{title}» удалено.')
    else:
        messages.error(request, 'Неизвестное действие.')

    # AJAX-ответ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect(request.META.get('HTTP_REFERER') or 'moderation_queue')


# ============================================
# БАН/РАЗБАН ПОЛЬЗОВАТЕЛЕЙ
# ============================================
@user_passes_test(is_moderator)
def users_list(request):
    """Список пользователей для модерации."""
    q = request.GET.get('q', '').strip()
    users = User.objects.select_related('profile').annotate(
        ad_count=Count('ads')
    ).order_by('-date_joined')

    if q:
        users = users.filter(username__icontains=q)

    paginator = Paginator(users, 30)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'ads/users.html', {'page_obj': page, 'q': q, 'banned_count': UserProfile.objects.filter(is_banned=True).count(),})


@user_passes_test(is_moderator)
@require_POST
def ban_user(request, user_id):
    from django.contrib.auth.models import User
    target = get_object_or_404(User, pk=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target)

    if target.is_staff or target.is_superuser:
        messages.error(request, 'Нельзя забанить администратора.')
        return redirect('users_list')

    action = request.POST.get('action')
    reason = request.POST.get('reason', '').strip()

    if action == 'ban':
        profile.ban(reason=reason or 'Нарушение правил', by=request.user)
        messages.warning(request, f'Пользователь {target.username} забанен.')
    elif action == 'unban':
        profile.unban()
        messages.success(request, f'Пользователь {target.username} разбанен.')

    return redirect(request.META.get('HTTP_REFERER') or 'users_list')


def banned_view(request):
    """Страница для забаненных пользователей."""
    profile = None
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
    return render(request, 'ads/banned.html', {'profile': profile})