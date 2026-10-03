from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count
from django.urls import reverse

from .models import Cart, CartItem, Product


class BrainyBossAdminSite(admin.AdminSite):
    site_header = "BrainyBoss Operations"
    site_title = "BrainyBoss Admin"
    index_title = "Store overview"
    index_template = "admin/brainyboss_index.html"

    def index(self, request, extra_context=None):
        extra_context = dict(extra_context or {})
        product_url = reverse(f"{self.name}:store_product_changelist")
        cart_url = reverse(f"{self.name}:store_cart_changelist")
        cart_item_url = reverse(f"{self.name}:store_cartitem_changelist")
        extra_context["dashboard_stats"] = [
            {"label": "Products", "value": Product.objects.count(), "url": product_url},
            {"label": "Shopping carts", "value": Cart.objects.count(), "url": cart_url},
            {"label": "Items in carts", "value": CartItem.objects.count(), "url": cart_item_url},
            {
                "label": "Low stock (5 or fewer)",
                "value": Product.objects.filter(stock__lte=5).count(),
                "url": product_url,
            },
        ]
        extra_context["recent_products"] = [
            {
                "name": product.name,
                "price": product.price,
                "stock": product.stock,
                "url": reverse(
                    f"{self.name}:store_product_change", args=(product.pk,)
                ),
            }
            for product in Product.objects.only("id", "name", "price", "stock")
            .order_by("-created_at")[:5]
        ]
        return super().index(request, extra_context=extra_context)


# Keep Django's conventional "admin" namespace so built-in admin links resolve.
brainyboss_admin_site = BrainyBossAdminSite(name="admin")


@admin.register(Product, site=brainyboss_admin_site)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock", "created_at")
    list_editable = ("price", "stock")
    list_filter = ("created_at",)
    search_fields = ("name", "description")
    ordering = ("name",)
    list_per_page = 25
    date_hierarchy = "created_at"
    save_on_top = True


@admin.register(Cart, site=brainyboss_admin_site)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "item_count")
    search_fields = ("user__username", "user__email")
    list_per_page = 25
    list_select_related = ("user",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(product_count=Count("cartitem"))

    @admin.display(description="Distinct products")
    def item_count(self, obj):
        return obj.product_count


@admin.register(CartItem, site=brainyboss_admin_site)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("product", "cart", "quantity")
    search_fields = ("product__name", "cart__user__email", "cart__user__username")
    list_per_page = 50
    list_select_related = ("product", "cart", "cart__user")


brainyboss_admin_site.register(User, UserAdmin)
brainyboss_admin_site.register(Group, GroupAdmin)
