"""
URL configuration for softbooks project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # App URLs
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounting/', include('accounting.urls')),
    path('invoicing/', include('invoicing.urls')),
    path('expenses/', include('expenses.urls')),
    path('banking/', include('banking.urls')),
    path('reports/', include('reports.urls')),
    path('inventory/', include('inventory.urls')),
    path('fixed-assets/', include('fixed_assets.urls')),
    path('hr/', include('hr.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
