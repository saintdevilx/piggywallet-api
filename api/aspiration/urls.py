from django.conf.urls import url
from django.urls import path

from api.aspiration.views import AspirationAPIView

urlpatterns = (
    url('^$', AspirationAPIView.as_view()),
    path('<uuid:pk>/', AspirationAPIView.as_view()),
)