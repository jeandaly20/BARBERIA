from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from pagos.urls import urlpatterns_api as pagos_api_urls
from pagos.urls import urlpatterns_redirect as pagos_redirect_urls

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='frontend:login', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/auth/', include('usuarios.urls')),
    path('api/', include('citas.urls')),
    path('api/pagos/', include(pagos_api_urls)),
    path('pagos/', include(pagos_redirect_urls)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('app/', include('frontend.urls')),
]
