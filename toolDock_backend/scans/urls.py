from rest_framework.routers import DefaultRouter
from .views import ScanViewSet,ScanResultViewSet

router = DefaultRouter()
router.register(r'start', ScanViewSet, basename='scan')
router.register(r'results', ScanResultViewSet, basename='result')

urlpatterns = router.urls
