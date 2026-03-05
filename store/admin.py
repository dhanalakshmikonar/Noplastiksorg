from django.contrib import admin
from .models import Product


class PublicAdminSite(admin.AdminSite):
    def has_permission(self, request):
        return True   # allow access without login


public_admin_site = PublicAdminSite(name="public_admin")

public_admin_site.register(Product)

from django.contrib import admin
from .models import Product

admin.site.register(Product)