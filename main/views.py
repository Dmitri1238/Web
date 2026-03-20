from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from .forms import RegisterForm
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Book, Comment
from .models import Category
from .models import Rating
from .models import UserProfile
import json
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import logging
logger = logging.getLogger(__name__)
from django.contrib.auth.decorators import login_required
from .forms import UserForm, UserProfileForm
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.contrib.auth.decorators import user_passes_test
import random

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    from django.contrib.auth.forms import AuthenticationForm
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def home(request):
    categories = Category.objects.all()

    counts = {}
    for cat in categories:
        counts[cat.slug] = Book.objects.filter(category=cat).count()

    # Выбираем 10 случайных книг
    books = Book.objects.order_by('?')[:10]

    # Собираем рейтинг пользователя для этих книг
    book_ratings = {}
    for book in books:
        rating_obj = Rating.objects.filter(user=request.user, book=book).first()
        book_ratings[book.id] = rating_obj.rating if rating_obj else 0

    return render(request, 'home.html', {
        'categories': categories,
        'count_literature': counts.get('literature', 0),
        'count_prose': counts.get('prose', 0),
        'count_comics': counts.get('comics', 0),
        'count_fairy_tales': counts.get('fairy_tales', 0),
        'books': books,
        'user_ratings': book_ratings,
    })

@login_required
def category_view(request, category):
    category_map = {
        'literature': ('Литература', 'main/literature.html'),
        'prose': ('Проза', 'main/prose.html'),
        'comics': ('Комиксы', 'main/comics.html'),
        'fairy_tales': ('Сказки', 'main/fairy_tales.html'),
    }
    category_name, template_name = category_map.get(category, ('Категория', 'main/catalog.html'))

    category_obj = get_object_or_404(Category, slug=category)
    books = Book.objects.filter(category=category_obj)

    # Для каждого книги получить текущий рейтинг пользователя
    book_ratings = {}
    for book in books:
        rating_obj = Rating.objects.filter(user=request.user, book=book).first()
        book_ratings[book.id] = rating_obj.rating if rating_obj else 0

    context = {
        'user_ratings': book_ratings,
        'category_name': category_name,
        'books': books,
        'book_ratings': book_ratings,  # Передаем словарь с рейтингами
    }
    return render(request, template_name, context)

@login_required
def catalog_view(request):
    categories = Category.objects.all()
    books = Book.objects.all()

    # Собираем рейтинги пользователя по всем книгам (если нужно)
    book_ratings = {}
    for book in books:
        rating_obj = Rating.objects.filter(user=request.user, book=book).first()
        book_ratings[book.id] = rating_obj.rating if rating_obj else 0

    context = {
        'books': books,
        'categories': categories,
        'user_ratings': book_ratings,
    }
    return render(request, 'main/catalog.html', context)

@login_required
def add_to_cart(request, book_id):
    cart = request.session.get('cart', {})
    book_id_str = str(book_id)
    cart[book_id_str] = cart.get(book_id_str, 0) + 1
    request.session['cart'] = cart
    return JsonResponse({'success': True, 'message': 'Книга добавлена в корзину', 'cart_count': sum(cart.values())})

@login_required
def cart_view(request):
    cart = request.session.get('cart', {})

    cart_items = []
    total_price = 0

    for book_id_str, quantity in cart.items():
        try:
            book_id = int(book_id_str)
            book = Book.objects.get(id=book_id)
        except (ValueError, Book.DoesNotExist):
            continue  # пропускаем, если не нашли книгу

        total_item_price = book.price * quantity
        total_price += total_item_price

        cart_items.append({
            'book': book,
            'quantity': quantity,
            'total_price': total_item_price,
        })

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }

    return render(request, 'cart.html', context)

@login_required
@require_POST
def remove_from_cart(request, book_id):
    cart = request.session.get('cart', {})

    book_id_str = str(book_id)
    if book_id_str in cart:
        del cart[book_id_str]
        request.session['cart'] = cart

    return redirect('cart')  # Перенаправление обратно в корзину

@login_required
@require_POST
def rate_book(request, book_id):
    data = json.loads(request.body)
    rating_value = int(data.get('rating', 0))
    if not (1 <= rating_value <= 5):
        return JsonResponse({'error': 'Invalid rating'}, status=400)

    book = get_object_or_404(Book, id=book_id)

    try:
        with transaction.atomic():
            # Обновляем или создаем оценку внутри транзакции
            rating_obj, created = Rating.objects.update_or_create(
                user=request.user,
                book=book,
                defaults={'rating': rating_value}
            )
        # Рассчитываем среднюю оценку
        ratings = Rating.objects.filter(book=book).values_list('rating', flat=True)
        average = round(sum(ratings) / len(ratings), 1) if ratings else 0
        return JsonResponse({'average': average})
    except Exception as e:
        # Логируем ошибку
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_average_rating(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    ratings = Rating.objects.filter(book=book).values_list('rating', flat=True)
    if ratings:
        avg = round(sum(ratings) / len(ratings), 1)
    else:
        avg = 0
    return JsonResponse({'average': avg})

@login_required
def profile(request):
    user = request.user
    try:
        userprofile = user.userprofile
    except UserProfile.DoesNotExist:
        userprofile = None

    # Словарь статусов
    statuses = {
        'user': 'Пользователь',
        'moderator': 'Модератор',
        'admin': 'Админ'
    }

    context = {
        'user': user,
        'userprofile': userprofile,
        'statuses': statuses,
    }

    return render(request, 'profile.html', context)

@login_required
def profile_edit(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('profile')
    else:
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=profile)

    return render(request, 'profile_edit.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@login_required
@require_http_methods(["DELETE"])
def delete_rating(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    try:
        rating = Rating.objects.get(user=request.user, book=book)
        rating.delete()
        ratings = Rating.objects.filter(book=book).values_list('rating', flat=True)
        average = round(sum(ratings) / len(ratings), 1) if ratings else 0
        return JsonResponse({'success': True, 'average': average})
    except Rating.DoesNotExist:
        return JsonResponse({'error': 'Rating not found'}, status=404)
@login_required
def add_comment_view(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        comment_text = request.POST.get('comment')
        if comment_text:
            Comment.objects.create(book=book, content=comment_text, user=request.user)
            return redirect('book_detail', pk=book.id)
    return render(request, 'add_comment.html', {'book': book})

@login_required
def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    
    # Получение всех книг (или только выбранной книги)
    books = Book.objects.all()

    # Создание словаря с рейтингами пользователя
    user_ratings = {}
    for bk in books:
        try:
            rating_obj = Rating.objects.get(user=request.user, book=bk)
            user_ratings[str(bk.id)] = rating_obj.rating
        except Rating.DoesNotExist:
            user_ratings[str(bk.id)] = 0

    # Передача контекста в шаблон
    context = {
        'book': book,
        'user_ratings': user_ratings,
    }
    return render(request, 'main/book_detail.html', context)

@login_required
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.method == 'POST':
        is_moderator = request.user.groups.filter(name='Модератор').exists()
        if comment.user == request.user or request.user.is_superuser or is_moderator:
            comment.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))

@user_passes_test(lambda u: u.is_superuser)
@login_required
def delete_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        book.delete()
        return redirect('catalog')
    return render(request, 'main/confirm_delete.html', {'book': book})

@login_required
def about(request):
    return render(request, 'about.html')

@login_required
def courses(request):
    return render(request, 'courses.html')

@login_required
def confirmation(request):
    course_name = request.GET.get('course', 'неизвестный курс')
    return render(request, 'confirmation.html', {'course_name': course_name})