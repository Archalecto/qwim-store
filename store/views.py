from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Category, Review, Order, OrderItem
from django.db.models import Q, Count
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True)

    # Поиск
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    # Фильтр по категории
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    # Фильтр по платформе
    platform = request.GET.get('platform')
    if platform:
        products = products.filter(platform__iexact=platform)

    # Фильтр по цене
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        try:
            products = products.filter(price__gte=float(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            products = products.filter(price__lte=float(price_max))
        except ValueError:
            pass

    # Сортировка
    sort = request.GET.get('sort', 'new')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    else:
        products = products.order_by('-created_at')

    # Список платформ для фильтра (из реально существующих товаров)
    platforms = Product.objects.filter(is_active=True).values_list(
        'platform', flat=True
    ).distinct().order_by('platform')

    # Пагинация — 12 товаров на страницу
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    cart = request.session.get('cart', {})
    cart_count = sum(cart.values())

    return render(request, 'store/product_list.html', {
        'category': category,
        'categories': categories,
        'products': page_obj,          # теперь page_obj вместо queryset
        'page_obj': page_obj,
        'platforms': platforms,
        'selected_platform': platform or '',
        'selected_sort': sort,
        'price_min': price_min or '',
        'price_max': price_max or '',
        'query': query or '',
        'cart_count': cart_count,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    reviews = Review.objects.filter(product=product).order_by('-created_at')
    screenshots = product.images.all()  # скриншоты через related_name='images'

    similar_products = Product.objects.filter(
        tags__in=product.tags.all()
    ).exclude(id=product.id).annotate(
        same_tags=Count('tags')
    ).order_by('-same_tags')[:4]

    if request.method == 'POST':
        name = request.POST.get('name')
        text = request.POST.get('text')
        rating = request.POST.get('rating')

        if name and text and rating:
            Review.objects.create(
                product=product,
                name=name,
                text=text,
                rating=int(rating),  # ИСПРАВЛЕНО: приводим к int
            )
            return redirect('product_detail', slug=product.slug)

    return render(request, 'store/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'screenshots': screenshots,
        'similar_products': similar_products,
    })


def cart_view(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(id__in=cart.keys())

    cart_items = []
    total = 0

    for product in products:
        quantity = cart[str(product.id)]
        subtotal = product.price * quantity
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal,
        })
        total += subtotal

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total,
    })


@login_required
def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})

    if str(product_id) in cart:
        cart[str(product_id)] += 1
    else:
        cart[str(product_id)] = 1

    request.session['cart'] = cart
    return redirect('cart')


def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})

    if str(product_id) in cart:
        del cart[str(product_id)]

    request.session['cart'] = cart
    return redirect('cart')


@login_required
def checkout(request):
    cart = request.session.get('cart', {})

    if not cart:
        return redirect('product_list')  # ИСПРАВЛЕНО: редирект на корректный URL

    return render(request, 'store/checkout.html')
    # ИСПРАВЛЕНО: убран недостижимый второй render (success.html никогда не вызывался)


@login_required
def process_order(request):
    # ИСПРАВЛЕНО: убрана дублирующаяся функция process_order
    # (в оригинале было две функции с одним именем — выполнялась только последняя)

    if request.method != 'POST':
        return redirect('checkout')

    cart = request.session.get('cart', {})

    if not cart:
        return redirect('product_list')

    products = Product.objects.filter(id__in=cart.keys())

    order = Order.objects.create(
        user=request.user,
        is_paid=True,
    )

    keys_given = []
    errors = []

    for product in products:
        quantity = cart[str(product.id)]

        for i in range(quantity):
            key_obj = product.digitalkey_set.filter(is_used=False).first()

            if key_obj:
                key_obj.is_used = True
                key_obj.save()

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price=product.price,
                    quantity=1,
                    key=key_obj.key,
                )

                keys_given.append(key_obj.key)
            else:
                errors.append(f"Нет ключей для {product.name}")

    request.session['cart'] = {}

    return render(request, 'store/success.html', {
        'keys': keys_given,
        'errors': errors,
    })


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/my_orders.html', {
        'orders': orders,
    })


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'store/register.html', {'form': form})


# НОВЫЙ VIEW: личный кабинет
@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    total_orders = orders.count()
    total_spent = sum(
        sum(item.price * item.quantity for item in order.orderitem_set.all())
        for order in orders
    )
    recent_orders = orders[:3]

    return render(request, 'store/profile.html', {
        'total_orders': total_orders,
        'total_spent': total_spent,
        'recent_orders': recent_orders,
        'orders': orders,
    })