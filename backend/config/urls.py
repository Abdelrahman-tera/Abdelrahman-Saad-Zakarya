from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/token/', obtain_auth_token, name='api_token_auth'),
    
    # OpenAPI Schema and Interactive Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Modular ERP Business Domains
    path('api/core/', include('apps.core.urls')),
    path('api/accounting/', include('apps.accounting.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/sales/', include('apps.sales.urls')),
    path('api/purchasing/', include('apps.purchasing.urls')),
    path('api/manufacturing/', include('apps.manufacturing.urls')),
    path('api/quality/', include('apps.quality.urls')),
    path('api/traceability/', include('apps.traceability.urls')),
    path('api/costing/', include('apps.costing.urls')),
    path('api/tax-egypt/', include('apps.tax_egypt.urls')),
]
