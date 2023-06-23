# E-commerce Creation with Django

Dokumentasi penggunaan script e-commerce dengan django

## Prerequisites

1. instalasi dengan `pip install requirements.txt`

## Processing
1. create new env `python -m venv env_ecom`
2. activate env `.\env_ecom\Scripts\activate`
3. Change database setting on `setting.py`
4. Migration data to Database
5. Create template for ecommerce. You can see my template on `/ecom/template/*html`
6. Membuat akun admin dengan `python manage.py createsuperuser`
7. Perintah untuk menjalankan script `python manage.py runserver`

### cybersecurity
Dalam e-commerce ini juga ditambahkan aspek cybersecurity
* SQL Injection
```code
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('paypal/', include('paypal.standard.ipn.urls')),
    path('', include('toko.urls', namespace='toko')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```
* Cross site scripting
```code
<form method="POST" name=" ">
            {% csrf_token %}
```
* No Rate Limiting
```code
from django_ratelimit.decorators import ratelimit
@ratelimit(key='user',rate='10/h')
```
```code
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGIN_ATTEMPS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPS_TIMEOUT = 300
```
* Access Control
```code
from django.contrib.auth.decorators import login_required, permission_required
@login_required
```
