from rest_framework.routers import DefaultRouter
from .views import ScanViewSet,ScanResultViewSet, ScanHistoryViewSet

router = DefaultRouter()
router.register(r'start', ScanViewSet, basename='scan')
router.register(r'results', ScanResultViewSet, basename='result')
router.register(r'histories', ScanHistoryViewSet, basename='history')

urlpatterns = router.urls
