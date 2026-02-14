from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from .forms import RegisterForm
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Book
from .models import Category
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

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

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def home(request):
    categories = Category.objects.all()

    counts = {}
    for cat in categories:
        counts[cat.slug] = Book.objects.filter(category=cat).count()

    return render(request, 'home.html', {
        'categories': categories,
        'count_literature': counts.get('literature', 0),
        'count_prose': counts.get('prose', 0),
        'count_comics': counts.get('comics', 0),
        'count_fairy_tales': counts.get('fairy-tales', 0),
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

    context = {
        'category_name': category_name,
        'books': books,
    }
    return render(request, template_name, context)

@login_required
def catalog_view(request):
    books = Book.objects.all()
    return render(request, 'literature.html', {'books': books})

@login_required
def add_to_cart(request, book_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        cart[book_id] = cart.get(book_id, 0) + 1
        request.session['cart'] = cart
        # Можно добавить сообщение или редирект
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
@login_required
def cart_view(request):
    cart = request.session.get('cart', {})

    cart_items = []
    total_price = 0

    for book_id_str, quantity in cart.items():
        # Обратите внимание, что ключи могут быть строками, а не целыми числами
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

@require_POST
def remove_from_cart(request, book_id):
    cart = request.session.get('cart', {})

    book_id_str = str(book_id)
    if book_id_str in cart:
        del cart[book_id_str]
        request.session['cart'] = cart

    return redirect('cart')  # Перенаправление обратно в корзину