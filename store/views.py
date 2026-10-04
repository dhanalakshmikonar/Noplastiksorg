from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Case, IntegerField, Value, When
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .forms import CleanUserCreationForm, EmailAuthenticationForm
from .email_notifications import send_branded_email
from .models import Product, Cart, CartItem
import razorpay


# =========================
# HOME
# =========================
def home(request):
    featured_products = Product.objects.only('id', 'name', 'price', 'image').order_by(
        Case(
            When(name__icontains='neuromaze', then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
        'created_at',
    )[:4]
    return render(request, 'home.html', {'featured_products': featured_products})


# =========================
# CATALOG
# =========================
def catalog(request):
    products = Product.objects.only('id', 'name', 'price', 'image').order_by('name')
    return render(request, 'catalog.html', {'products': products})


# =========================
# REGISTER
# =========================
def register(request):
    error = None
    if request.method == 'POST':
        form = CleanUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            verify_url = request.build_absolute_uri(
                reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
            )
            subject = 'Verify your BrainyBoss email address'
            message = (
                f"Hello,\n\nPlease verify your email address to activate your BrainyBoss account:\n"
                f"{verify_url}\n\nIf you did not create this account, you can ignore this message."
            )
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            except Exception:
                # Don't leave an unusable pending account if delivery couldn't be attempted.
                user.delete()
                error = "We couldn't send the verification email. Please try again later or contact support."
            else:
                return render(request, 'register.html', {'form': CleanUserCreationForm(), 'verification_sent': True})
    else:
        form = CleanUserCreationForm()

    return render(request, 'register.html', {'form': form, 'error': error})


def verify_email(request, uidb64, token):
    try:
        user_id = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and not user.is_active and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=['is_active'])
        return render(request, 'email_verified.html', {'verified': True})
    return render(request, 'email_verified.html', {'verified': False})


class EmailLoginView(LoginView):
    template_name = 'login.html'
    authentication_form = EmailAuthenticationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.get_user()
        send_branded_email(
            kind='successful login',
            subject='New sign-in to your Noplastiks account',
            template='login_notification',
            context={
                'customer_name': user.get_full_name() or user.get_username(),
                'login_at': timezone.localtime(),
            },
        )
        return response


# =========================
# LOGOUT
# =========================
def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile(request):
    return render(request, 'profile.html')


# =========================
# ADD TO CART
# =========================
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if not request.user.is_authenticated:
        request.session['pending_cart_product_id'] = product.pk
        return redirect(f"{reverse('login')}?next={reverse('cart')}")

    _add_product_to_cart(request.user, product)

    return redirect('cart')


def _add_product_to_cart(user, product):
    cart, _ = Cart.objects.get_or_create(user=user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save(update_fields=['quantity'])


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
    pending_product_id = request.session.pop('pending_cart_product_id', None)
    if pending_product_id:
        pending_product = Product.objects.filter(pk=pending_product_id).first()
        if pending_product:
            _add_product_to_cart(request.user, pending_product)

    items = cart.cartitem_set.select_related('product').all()

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
    items = cart.cartitem_set.select_related('product').all()
    order_items = list(items)
    total = sum(item.product.price * item.quantity for item in order_items)

    # Clearing the cart before sending makes a refresh of this success page
    # unable to send the same cart notification a second time.
    if order_items:
        items.delete()
        send_branded_email(
            kind='new order',
            subject='New order placed - Noplastiks',
            template='order_placed',
            context={
                'customer_name': request.user.get_full_name() or request.user.get_username(),
                'customer_email': request.user.email,
                'items': order_items,
                'total': total,
                'placed_at': timezone.localtime(),
            },
        )

    return render(request, "success.html")


# =========================
# CONTACT
# =========================
def contact(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        message = request.POST.get("message", "").strip()

        form_data = {"name": name, "email": email, "message": message}
        if not name or not email or not message:
            return render(request, "contact.html", {
                **form_data,
                "error": "Please complete all fields before sending your message.",
            })

        try:
            validate_email(email)
        except ValidationError:
            return render(request, "contact.html", {
                **form_data,
                "error": "Please enter a valid email address.",
            })

        sent = send_branded_email(
            kind='contact form submission',
            subject='New contact message - Noplastiks',
            template='contact_submission',
            context=form_data,
            reply_to=email,
        )
        if not sent:
            return render(request, "contact.html", {
                **form_data,
                "error": "We couldn't send your message right now. Please try again later.",
            })
        return render(request, "contact.html", {"success": True})

    return render(request, "contact.html")
