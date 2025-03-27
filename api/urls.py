from django.urls import path
# from .views import signup_view,login_api
# from .views import ScanTyreView
# from .views import TyreScanResultsView
from .views import signup_view, login_api, ScanTyreView, TyreScanResultsView


urlpatterns = [
  path('signup/', signup_view),
    path('login/', login_api, name='login'),
        path('scan-tyre/', ScanTyreView.as_view(), name='scan-tyre'),
   path('api/tyrescan/results/', TyreScanResultsView.as_view(), name='tyrescan-results'),


]
