from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from store.admin import brainyboss_admin_site

urlpatterns = [
    path('admin/', brainyboss_admin_site.urls),
    path('', include('store.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
