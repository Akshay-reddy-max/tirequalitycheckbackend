from django.urls import path
from .views import signup_view,login_api
from .views import ScanTyreView

urlpatterns = [
  path('signup/', signup_view),
    path('login/', login_api, name='login'),
        path('scan-tyre/', ScanTyreView.as_view(), name='scan-tyre'),

]
