from rest_framework.routers import DefaultRouter
from .views import ScanViewSet

router = DefaultRouter()
router.register(r'start', ScanViewSet, basename='scan')
# router.register(r'results/<uuid:pk>/', ResultView, basename='result )

urlpatterns = router.urls
