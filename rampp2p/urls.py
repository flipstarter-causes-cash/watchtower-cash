from django.urls import path

from .views.ad import (
  # AdListCreate,
  AdList,
  AdDetail
)

from .views.payment import (
  PaymentTypeList,
  PaymentTypeDetail,
  PaymentMethodListCreate,
  PaymentMethodDetail
)

from .views.peer import (
  PeerList,
  PeerDetail,
)

from .views.currency import (
  FiatCurrencyList,
  FiatCurrencyDetail,
  CryptoCurrencyList,
  CryptoCurrencyDetail
)

from .views.order import (
  OrderList,
  OrderDetail,
  OrderStatusList
)

from .views.feedback import (
  ArbiterFeedbackListCreate,
  PeerFeedbackListCreate,
  FeedbackDetail,
)

urlpatterns = [
  path('ad/', AdList.as_view(), name='ad-list-create'),
  path('ad/<int:pk>/', AdDetail.as_view(), name='ad-detail'),
  path('payment-type/', PaymentTypeList.as_view(), name='payment-type-list-create'),
  path('payment-type/<int:pk>', PaymentTypeDetail.as_view(), name='payment-type-detail'),
  path('payment-method/', PaymentMethodListCreate.as_view(), name='payment-method-list'),
  path('payment-method/<int:pk>', PaymentMethodDetail.as_view(), name='payment-method-detail'),
  path('peer/', PeerList.as_view(), name='peer-list-create'),
  path('peer/<int:pk>', PeerDetail.as_view(), name='peer-detail'),
  path('currency/fiat/', FiatCurrencyList.as_view(), name='fiat-list-create'),
  path('currency/fiat/<int:pk>', FiatCurrencyDetail.as_view(), name='fiat-detail'),
  path('currency/crypto/', CryptoCurrencyList.as_view(), name='crypto-list-create'),
  path('currency/crypto/<int:pk>', CryptoCurrencyDetail.as_view(), name='crypto-detail'),

  path('order/', OrderList.as_view(), name='order-list-create'),
  path('order/<int:pk>', OrderDetail.as_view(), name='order-detail'),
  path('order/<int:order_id>/status', OrderStatusList.as_view(), name='order-status-list'),
  
  path('feedback/arbiter', ArbiterFeedbackListCreate.as_view(), name='arbiter-feedback-list-create'),
  path('feedback/<int:feedback_id>', FeedbackDetail.as_view(), name='feedback-detail'),
  path('feedback/peer', PeerFeedbackListCreate.as_view(), name='peer-feedback-list-create'),
]