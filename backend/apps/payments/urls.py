from rest_framework.routers import SimpleRouter

from apps.payments.views import PaymentViewSet

router = SimpleRouter()
router.register("", PaymentViewSet, basename="payment")

urlpatterns = router.urls
