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
from .models import Notification
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
from django.core.paginator import Paginator
from .models import CourseRegistration
from datetime import datetime
from django.views.decorators.http import require_GET
from django.contrib import messages
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from .models import PaymentRequest

from django.contrib.auth.decorators import login_required, user_passes_test
import re


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

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('home')

    return render(request, 'login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def home(request):

    # Получение всех категорий
    categories = Category.objects.all()

    # Подсчет количества книг в каждой категории
    counts = {}
    for cat in categories:
        counts[cat.slug] = Book.objects.filter(category=cat).count()

    # Получение номера страницы из GET-запроса
    page_number = request.GET.get('page', 1)

    # Получение всех книг
    all_books = Book.objects.all()

    # Создание пагинатора — по 10 книг на страницу
    paginator = Paginator(all_books, 10)
    try:
        page_obj = paginator.get_page(page_number)
    except:
        page_obj = paginator.get_page(1)

    # Получение рейтинга для текущего пользователя по каждой книге
    book_ratings = {}
    for book in page_obj.object_list:
        rating_obj = Rating.objects.filter(user=request.user, book=book).first()
        book_ratings[book.id] = rating_obj.rating if rating_obj else 0

    # Проверка роли — является ли пользователь админом или модератором
    user_profile = getattr(request.user, 'userprofile', None)
    user_is_admin_or_mod = False
    if user_profile and user_profile.status in ['admin', 'moderator']:
        user_is_admin_or_mod = True

    # Получение баланса (предполагается, что есть поле 'balance')
    balance = user_profile.balance if user_profile else 0

    # Получение только что неподтвержденных
    notifications_queryset = Notification.objects.filter(user=request.user, read=False)

    # Передача уведомлений в шаблон
    notifications = list(notifications_queryset)

    # Пометка уведомлений как прочитанных после получения
    notifications_queryset.update(read=True)


    # Передача всех переменных в шаблон
    return render(request, 'home.html', {
        'categories': categories,
        'count_literature': counts.get('literature', 0),
        'count_prose': counts.get('prose', 0),
        'count_comics': counts.get('comics', 0),
        'count_fairy_tales': counts.get('fairy_tales', 0),
        'books': page_obj,
        'user_ratings': book_ratings,
        'paginator': paginator,
        'page_obj': page_obj,
        'user_is_admin_or_mod': user_is_admin_or_mod,
        'balance': balance,
        'notifications': notifications,
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

    # Собираем рейтинги пользователя по всем книгам
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
    book = get_object_or_404(Book, pk=book_id)
    cart = request.session.get('cart', {})

    book_id_str = str(book_id)
    item = cart.get(book_id_str)

    if isinstance(item, dict):
        # Уже есть такая книга, увеличиваем количество
        item['quantity'] += 1
    elif item:
        # Было число, превращаем его в словарь
        quantity = item + 1
        cart[book_id_str] = {
            'price': float(book.price),
            'quantity': quantity
        }
    else:
        # Добавляем новую книгу
        cart[book_id_str] = {
            'price': float(book.price),
            'quantity': 1
        }

    request.session['cart'] = cart
    request.session.modified = True

    total_items = sum(i['quantity'] for i in cart.values())  # подсчет общего количества книг

    return JsonResponse({'success': True, 'message': 'Книга добавлена в корзину', 'cart_count': total_items})

@login_required
def cart_view(request):
    from decimal import Decimal
    cart = request.session.get('cart', {})

    cart_items = []
    total_price = Decimal('0.00')  # Используйте Decimal для точных расчетов

    for book_id_str, item in cart.items():
        try:
            book_id = int(book_id_str)
            quantity = int(item['quantity'])
            book = Book.objects.get(id=book_id)
        except (ValueError, Book.DoesNotExist):
            continue  # пропускаем неверные данные

        total_item_price = book.price * quantity
        total_price += total_item_price

        cart_items.append({
            'book': book,
            'quantity': quantity,
            'total_price': total_item_price,
        })

    # Получаем профиль пользователя или создаем новый
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    balance = user_profile.balance

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'balance': balance,
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

BAD_WORDS = ['плохоеслово1', 'плохо', 'плохая книга']

def censor_text(text):
    for bad_word in BAD_WORDS:
        pattern = re.compile(re.escape(bad_word), re.IGNORECASE)
        # Заменяем каждое вхождение слова на звёздочки
        text = pattern.sub('*' * len(bad_word), text)
    return text
@login_required
def add_comment_view(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        comment_text = request.POST.get('comment')
        if comment_text:
            # применяем цензуру
            censored_comment = censor_text(comment_text)
            # создаем комментарий с цензурой
            Comment.objects.create(book=book, content=censored_comment, user=request.user)
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
        is_moderator = (
            hasattr(request.user, 'userprofile') and
            request.user.userprofile.status == 'moderator'
        )

        if comment.user == request.user or request.user.is_superuser or is_moderator:
            comment.delete()

    return redirect(request.META.get('HTTP_REFERER', '/'))

@user_passes_test(lambda u: u.is_superuser)
@login_required
def delete_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        book.delete()
        return redirect('homе')
    return render(request, 'main/confirm_delete.html', {'book': book})

@login_required
def about(request):
    return render(request, 'about.html')

@login_required
def courses(request):
    registrations = CourseRegistration.objects.filter(user=request.user)
    return render(request, 'courses.html', {'registrations': registrations})

@login_required
@require_POST
def delete_registration(request, reg_id):
    try:
        reg = CourseRegistration.objects.get(id=reg_id, user=request.user)
        reg.delete()
        return JsonResponse({'status': 'ok'})
    except CourseRegistration.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Registration not found'})

@require_GET
@login_required
def get_registrations(request):
    registrations = CourseRegistration.objects.filter(user=request.user)
    data = []
    for reg in registrations:
        data.append({
            'id': reg.id,
            'course': reg.course_name,
            'date': reg.date_created.strftime('%d-%m-%Y'),
            'time': reg.time if reg.time else '',
        })
    return JsonResponse(data, safe=False)

@require_POST
@login_required
def save_registration(request):
    print(request.body)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    # Используем keys 'course' и 'time' — они должны соответствовать тому, что передаете из JS
    course_name = data.get('course')
    time_str = data.get('time')

    if not time_str or not course_name:
        return JsonResponse({'status': 'error', 'message': 'Missing data'}, status=400)

    # Проверка времени
    try:
        datetime.strptime(time_str, '%H:%M')
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid time format'}, status=400)

    # Создаем или обновляем регистрацию
    reg, created = CourseRegistration.objects.get_or_create(
        user=request.user,
        course_name=course_name,
        defaults={'time': time_str}
    )

    if not created:
        reg.time = time_str
        reg.save()

    return JsonResponse({'status': 'ok'})

@login_required
def course_video(request, course_name):
    registration = get_object_or_404(
        CourseRegistration,
        user=request.user,
        course_name=course_name
    )

    return render(request, 'course_video.html', {
        'course_name': course_name,
        'course_time_start': registration.time  # 👈 ВОТ ЭТО ГЛАВНОЕ
    })

def is_admin_or_moderator(user):
    try:
        return user.userprofile.status in ['admin', 'moderator']
    except UserProfile.DoesNotExist:
        return False

@user_passes_test(is_admin_or_moderator)
def add_book(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        author = request.POST.get('author')
        cover = request.FILES.get('cover')
        price = request.POST.get('price')
        try:
            price_value = float(price)
        except (TypeError, ValueError):
            # Обработка ошибки: например, сообщение пользователю
            return render(request, 'add_book.html', {
                'categories': Category.objects.all(),
                'error': 'Введите корректную цену'
            })

        category = Category.objects.get(id=category_id)

        # Создаем книгу
        Book.objects.create(
            title=title,
            category=category,
            author=author,
            price=price_value,
            image=cover,
        )

        return redirect('home')

    return render(request, 'add_book.html', {'categories': categories})

@login_required
def make_payment(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        if not cart:
            messages.error(request, 'У вас пустая корзина.', extra_tags='error')
            return redirect('cart')
        
        profile = request.user.userprofile
        total_amount = Decimal('0.00')

        for item_id, item_info in cart.items():
            if isinstance(item_info, dict):
                price = Decimal(str(item_info['price']))
                quantity = int(item_info['quantity'])
            else:
                price = Decimal(str(item_info))
                quantity = 1
            total_amount += price * quantity

        #если корзина не пуста...
        if profile.balance < total_amount:
            messages.error(request, 'На вашем счёте недостаточно средств для оплаты.', extra_tags='error')
            return redirect('cart')

        profile.balance -= total_amount
        profile.save()

        request.session['cart'] = {}
        request.session.modified = True

        messages.success(request, f'Оплата прошла успешно! Снято {total_amount} рублей.')
        return redirect('cart')
    return redirect('cart')

@login_required
def recharge_balance(request):
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        if amount > 0:
            profile = request.user.userprofile
            profile.balance += amount
            profile.save()
            messages.success(request, f'Вы успешно пополнили баланс на {amount} рублей.')
        else:
            messages.error(request, 'Некорректная сумма.')
        return redirect('home')

@login_required
def payment_request_form(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        # дополнительные поля по необходимости
        
        # Сохраняем заявку
        PaymentRequest.objects.create(
            user=request.user,
            amount=amount,
            status='pending'
        )
        
        messages.add_message(request, messages.INFO, 'Заявка успешно отправлена', extra_tags='user-{}'.format(request.user.id))
        return redirect('home')
    return render(request, 'payment_request_form.html')

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def admin_payment_requests_view(request):
    requests = PaymentRequest.objects.all()
    return render(request, 'admin_payment_requests.html', {'requests': requests})

@login_required
def submit_payment_request(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        goal = request.POST.get('goal')
        history = request.POST.get('history')
        comment = request.POST.get('comment')

        # Проверка наличия данных
        if not amount or not goal:
            # Например, отправить сообщение и вернуться
            messages.error(request, 'Пожалуйста, заполните все обязательные поля.')
            return redirect('payment_request_form')

        # Создаем заявку
        PaymentRequest.objects.create(
            user=request.user,
            amount=amount,
            goal=goal,
            history=history,
            comment=comment
        )

        # После успешной отправки перенаправляем
        Notification.objects.create(
            user=request.user,  # кому именно!
            text='Заявка успешно отправлена.'
        )
        return redirect('home')

    return redirect('payment_request_form')

def reject_payment_request(request, request_id):
    if request.method == 'POST':
        pr = get_object_or_404(PaymentRequest, id=request_id)
        # Логика отклонения
        pr.status = 'rejected'
        pr.save()
        # Удаляем заявку после отклонения
        pr.delete()
        Notification.objects.create(
            user=pr.user,  # кому именно!
            text='Заявка отклонена'
        )
    return redirect('admin_payment_requests')

@login_required
def approve_payment_request(request, request_id):
    pr = get_object_or_404(PaymentRequest, id=request_id)
    if request.method == 'POST':
        # Добавляем сумму на баланс пользователя
        user_profile = pr.user.userprofile
        user_profile.balance += Decimal(pr.amount)
        user_profile.save()

        # Меняем статус и удаляем заявкуrequest.session
        pr.status = 'approved'
        pr.save()
        pr.delete()
        Notification.objects.create(
            user=pr.user,  # кому именно!
            text='Ваша заявка одобрена, баланс пополнен.'
        )
        return redirect('admin_payment_requests')