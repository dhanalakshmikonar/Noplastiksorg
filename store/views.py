from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from .forms import CleanUserCreationForm
from .models import Product, Cart, CartItem
import razorpay


# =========================
# HOME
# =========================
def home(request):
    return render(request, 'home.html')


# =========================
# CATALOG
# =========================
def catalog(request):
    products = Product.objects.all()
    return render(request, 'catalog.html', {'products': products})


# =========================
# REGISTER
# =========================
def register(request):
    if request.method == 'POST':
        form = CleanUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = CleanUserCreationForm()

    return render(request, 'register.html', {'form': form})


# =========================
# LOGOUT
# =========================
def logout_view(request):
    logout(request)
    return redirect('home')


# =========================
# ADD TO CART
# =========================
@login_required
def add_to_cart(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    # EMAIL NOTIFICATION
    message = f"""
Product Added To Cart

Customer: {request.user.username}
Customer Email: {request.user.email}

Product: {product.name}
Price: ₹{product.price}
Quantity: {cart_item.quantity}
"""

    send_mail(
        "Cart Update - Product Added",
        message,
        settings.EMAIL_HOST_USER,
        ["konardhanalakshmi@gmail.com"],
        fail_silently=False,
    )

    return redirect('cart')


# =========================
# REMOVE ITEM
# =========================
@require_POST
@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect('cart')


# =========================
# CART VIEW
# =========================
@login_required
def cart_view(request):

    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.cartitem_set.all()

    total = sum(item.product.price * item.quantity for item in items)

    return render(request, 'cart.html', {
        'items': items,
        'total': total
    })


# =========================
# CHECKOUT (RAZORPAY)
# =========================
@login_required
def checkout(request):

    cart = Cart.objects.get(user=request.user)
    items = cart.cartitem_set.all()

    total = sum(item.product.price * item.quantity for item in items)

    if total == 0:
        return redirect('cart')

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    payment = client.order.create({
        "amount": int(total * 100),
        "currency": "INR",
        "payment_capture": 1
    })

    return render(request, "payment.html", {
        "payment": payment,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "total": total
    })


# =========================
# PAYMENT SUCCESS
# =========================
@login_required
def payment_success(request):

    cart = Cart.objects.get(user=request.user)
    items = cart.cartitem_set.all()

    total = sum(item.product.price * item.quantity for item in items)

    admin_message = f"""
New Order Received!

Customer: {request.user.username}
Email: {request.user.email}

Order Details:
"""

    for item in items:
        admin_message += f"{item.product.name} - Qty: {item.quantity}\n"

    admin_message += f"\nTotal Amount: ₹{total}"

    send_mail(
        "New Order Placed - Noplastiks",
        admin_message,
        settings.EMAIL_HOST_USER,
        ["konardhanalakshmi@gmail.com"],
        fail_silently=False,
    )

    # CUSTOMER MAIL
    customer_message = f"""
Thank you for shopping with Noplastiks!

Order Summary:
"""

    for item in items:
        customer_message += f"{item.product.name} - Qty: {item.quantity}\n"

    customer_message += f"\nTotal Paid: ₹{total}"

    send_mail(
        "Order Confirmation - Noplastiks",
        customer_message,
        settings.EMAIL_HOST_USER,
        [request.user.email],
        fail_silently=False,
    )

    items.delete()

    return render(request, "success.html")


# =========================
# CONTACT
# =========================
def contact(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        mail_message = f"""
New Contact Form Submission

Name: {name}
Email: {email}

Message:
{message}
"""

        send_mail(
            "New Contact Message - Noplastiks",
            mail_message,
            settings.EMAIL_HOST_USER,
            ["konardhanalakshmi@gmail.com"],
            fail_silently=False,
        )

        return render(request, "contact.html", {"success": True})

    return render(request, "contact.html")