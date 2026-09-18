from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator

from .models import Ad, Category
from .forms import AdForm, RegisterForm


# ---------- ПУБЛИЧНЫЕ ----------
def ad_list(request):
    ads = Ad.objects.filter(status='approved', is_published=True).select_related(
        'category', 'author'
    )

    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')

    if q:
        ads = ads.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category:
        ads = ads.filter(category__slug=category)

    paginator = Paginator(ads, 12)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page,
        'categories': Category.objects.all(),
        'q': q,
        'current_category': category,
    }
    return render(request, 'ads/ad_list.html', context)


def ad_detail(request, pk):
    ad = get_object_or_404(Ad, pk=pk)
    if ad.status != 'approved' and ad.author != request.user:
        messages.warning(request, 'Объявление ещё не прошло модерацию.')
        return redirect('ad_list')
    return render(request, 'ads/ad_detail.html', {'ad': ad})


# ---------- АВТОРИЗАЦИЯ ----------
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
            login(request, form.get_user())
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


# ---------- КАБИНЕТ ----------
@login_required
def ad_create(request):
    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.author = request.user
            ad.status = 'pending'
            ad.save()
            messages.success(
                request,
                'Объявление отправлено на модерацию. После проверки оно появится в ленте.'
            )
            return redirect('my_ads')
    else:
        form = AdForm()
    return render(request, 'ads/ad_create.html', {'form': form})


@login_required
def my_ads(request):
    ads = request.user.ads.select_related('category').all()
    return render(request, 'ads/my_ads.html', {'ads': ads})


@login_required
def ad_delete(request, pk):
    ad = get_object_or_404(Ad, pk=pk, author=request.user)
    if request.method == 'POST':
        ad.delete()
        messages.success(request, 'Объявление удалено.')
    return redirect('my_ads')