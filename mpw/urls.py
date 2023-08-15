"""mpw URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
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
import notifications
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.views.static import serve

from api.fcm_django.rest_framework import FCMDeviceAuthorizedViewSet
from lib.cashfree.webhook import PayoutWebhookResponse
from lib.utils import logger
from mpw import settings
from django.conf.urls.static import static



urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin_view/', include(('admin_view.urls', 'transaction') , namespace='admin_view')),
    # API urls
    path('api/register/notification_token/', FCMDeviceAuthorizedViewSet.as_view({'post': 'create'}),
         name='create_fcm_device'),
    #url('^api/inbox/notifications/', include(notifications.urls, namespace='notifications')),
    path('app_version_update.xml', TemplateView.as_view(template_name="app_version_update.html", content_type='text/xml')),
    url(r'api/phone_login/', include(('api.phone_auth.urls', 'phone_auth'), namespace='phone_auth'), ),
    url(r'api/user/', include(('api.user.urls', 'user'), namespace='user'), ),
    url(r'api/saving/', include(('api.saving_goal.urls', 'saving_goal'), namespace='saving_goal'), ),
    url(r'api/payment/', include(('api.payment.urls', 'payment_api'), namespace='payment'), ),
    url(r'api/aspiration/', include(('api.aspiration.urls', 'aspiration_api'), namespace='aspiration'), ),
    url(r'api/rewards/', include(('api.reward.urls', 'rewards_api'), namespace='rewards')),
    path('email/', include(('emailtemplates.urls', 'email_template'), namespace='email_template'))
]