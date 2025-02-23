from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from django.db.models import Q
from django.http import Http404
from django.core.exceptions import ValidationError
from django.db.models import F, ExpressionWrapper, DecimalField, Case, When

import math
from authentication.token import TokenAuthentication

from rampp2p.serializers import (
    AdListSerializer, 
    AdDetailSerializer,
    AdCreateSerializer, 
    AdUpdateSerializer,
    AdOwnerSerializer
)
from rampp2p.models import (
    Ad, 
    Peer, 
    PaymentMethod,
    FiatCurrency,
    CryptoCurrency,
    TradeType,
    PriceType,
    MarketRate
)

import logging
logger = logging.getLogger(__name__)

class AdListCreate(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        queryset = Ad.objects.filter(Q(deleted_at__isnull=True))

        wallet_hash = request.headers.get('wallet_hash')
        owner_id = request.query_params.get('owner_id')
        currency = request.query_params.get('currency')
        trade_type = request.query_params.get('trade_type')
        price_types = request.query_params.getlist('price_types')
        payment_types = request.query_params.getlist('payment_types')
        time_limits = request.query_params.getlist('time_limits')
        price_order = request.query_params.get('price_order')
        owned = request.query_params.get('owned', False)
        owned = owned == 'true'

        try:
            limit = int(request.query_params.get('limit', 0))
            page = int(request.query_params.get('page', 1))
        except ValueError as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)

        if limit < 0:
            return Response({'error': 'limit must be a non-negative number'}, status=status.HTTP_400_BAD_REQUEST)
        
        if page < 1:
            return Response({'error': 'invalid page number'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not owned:
            # If not fetching owned ads: fetch only public ads and those with trade amount > 0
            queryset = queryset.filter(Q(is_public=True) & Q(trade_amount__gt=0))
            if currency is None:
                return Response({'error': 'currency is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # filters
        if owner_id is not None:
            queryset = queryset.filter(owner_id=owner_id)

        if currency is not None:
            queryset = queryset.filter(Q(fiat_currency__symbol=currency))
        
        if trade_type is not None:
            queryset = queryset.filter(Q(trade_type=trade_type))
        
        if len(price_types) > 0:
            queryset = queryset.filter(Q(price_type__in=price_types))
        
        if len(payment_types) > 0:
            payment_types = list(map(int, payment_types))
            queryset = queryset.filter(payment_methods__payment_type__id__in=payment_types).distinct()

        if len(time_limits) > 0:
            time_limits = list(map(int, time_limits))
            queryset = queryset.filter(time_duration_choice__in=time_limits).distinct()

        market_rate = MarketRate.objects.filter(currency=currency)

        # Annotate to compute ad price based on price type (FIXED vs FLOATING)
        queryset = queryset.annotate(
            price=ExpressionWrapper(
                Case(
                    When(price_type=PriceType.FLOATING, then=(F('floating_price')/100 * market_rate.values('price'))),
                    default=F('fixed_price'),
                    output_field=DecimalField()
                ),
                output_field=DecimalField()
            )
        )

        # Order ads by price (if store listings) or created_at (if owned ads)
        # Default order: ascending, descending if trade type is BUY, 
        # `price_order` filter overrides this order
        if not owned:            
            order_field = 'price'
            if trade_type == TradeType.BUY: 
                order_field = '-price'
            if price_order is not None:
                order_field = 'price' if price_order == 'ascending' else '-price'
            queryset = queryset.order_by(order_field, 'created_at')
        else:
            queryset = queryset.filter(Q(owner__wallet_hash=wallet_hash)).order_by('-created_at')

        count = queryset.count()
        total_pages = page
        if limit > 0:
            total_pages = math.ceil(count / limit)

        offset = (page - 1) * limit
        paged_queryset = queryset[offset:offset + limit]

        context = { 'wallet_hash': wallet_hash }
        serializer = AdListSerializer(paged_queryset, many=True, context=context)
        data = {
            'ads': serializer.data,
            'count': count,
            'total_pages': total_pages
        }
        return Response(data, status.HTTP_200_OK)

    def post(self, request):
        try:
            wallet_hash = request.headers.get('wallet_hash')
            payment_methods = request.data.get('payment_methods')
            validate_payment_methods_ownership(wallet_hash, payment_methods)

        except ValidationError as err:
            return Response({'error': err.args[0]}, status=status.HTTP_403_FORBIDDEN)
    
        try:
            caller = Peer.objects.get(wallet_hash=wallet_hash)
        except Peer.DoesNotExist as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data.copy()
        data['owner'] = caller.id

        try:
            crypto = data['crypto_currency']
            data['crypto_currency'] = CryptoCurrency.objects.get(symbol=crypto).id
            
            fiat = data['fiat_currency']
            data['fiat_currency'] = FiatCurrency.objects.get(symbol=fiat).id
        except (CryptoCurrency.DoesNotExist, FiatCurrency.DoesNotExist) as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AdCreateSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdDetail(APIView):
    authentication_classes = [TokenAuthentication]
    
    def get_object(self, pk):
        try:
            ad = Ad.objects.get(pk=pk)
            if ad.deleted_at is not None:
                raise Ad.DoesNotExist
            return ad
        except Ad.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        ad = self.get_object(pk)
        wallet_hash = request.user.wallet_hash
        context = { 'wallet_hash': wallet_hash }
        serializer = None
        if ad.owner.wallet_hash == wallet_hash:
            serializer = AdOwnerSerializer(ad, context=context).data
        else:
            serializer = AdDetailSerializer(ad, context=context).data
        return Response(serializer, status=status.HTTP_200_OK)

    def put(self, request, pk):
        try:
            wallet_hash = request.user.wallet_hash
            payment_methods = request.data.get('payment_methods')
            self.validate_permissions(wallet_hash, pk)
            validate_payment_methods_ownership(wallet_hash, payment_methods)
        except ValidationError as err:
            return Response({'error': err.args[0]}, status=status.HTTP_403_FORBIDDEN)
        
        ad = self.get_object(pk)
        serializer = AdUpdateSerializer(ad, data=request.data)
        if serializer.is_valid():
            ad = serializer.save()
            context = { 'wallet_hash': wallet_hash }
            serializer = AdListSerializer(ad, context=context)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        try:
            wallet_hash = request.user.wallet_hash
            self.validate_permissions(wallet_hash, pk)
        except ValidationError as err:
            return Response({'error': err.args[0]}, status=status.HTTP_403_FORBIDDEN)
        
        # TODO: block deletion when ad has active orders
        
        ad = self.get_object(pk)
        ad.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def validate_permissions(self, wallet_hash, ad_id):
        '''
        Validates if caller is ad owner
        '''
        ad = Ad.objects.filter(Q(pk=ad_id) & Q(owner__wallet_hash=wallet_hash))
        if (not ad.exists()):
            raise ValidationError('No such Ad with owner exists')

def validate_payment_methods_ownership(wallet_hash, payment_method_ids):
    '''
    Validates if caller owns the payment methods
    '''
    payment_methods = PaymentMethod.objects.filter(Q(owner__wallet_hash=wallet_hash) & Q(id__in=payment_method_ids))
    if not payment_methods.exists():
        raise ValidationError('caller must be owner of payment method')