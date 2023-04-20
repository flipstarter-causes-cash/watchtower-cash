from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from django.http import Http404
from django.core.exceptions import ValidationError
from typing import List

from ..base_serializers import (
    AdSerializer,
    AdWriteSerializer
)

from ..base_models import (
    Ad,
    Peer,
    PaymentMethod
)

class AdListCreate(APIView):
  def get(self, request):
    queryset = Ad.objects.filter(is_deleted=False)

    # TODO pagination

    owner = request.query_params.get('owner', None)
    if owner is not None:
        queryset = queryset.filter(Q(owner=owner))

    serializer = AdSerializer(queryset, many=True)
    return Response(serializer.data, status.HTTP_200_OK)

  def post(self, request):
    
    payment_method_ids = request.data.get('payment_methods', None)
    if payment_method_ids is None:
      return Response({'error': 'payment_method_ids is None'}, status=status.HTTP_400_BAD_REQUEST)
    
    wallet_hash = request.data.get('wallet_hash', None)
    if wallet_hash is None:
      return Response({'error': 'wallet_hash is None'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        caller = Peer.objects.get(wallet_hash=wallet_hash)
    except Peer.DoesNotExist:
      raise Http404
    
    # TODO: verify the signature

    try:
      self.validate_payment_methods(wallet_hash, payment_method_ids)
    except ValidationError as err:
      return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)
    
    data = request.data
    data['owner'] = caller.id

    serializer = AdWriteSerializer(data=data)
    if serializer.is_valid():
      serializer.save()
      return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
  
  def validate_payment_methods(self, wallet_hash, payment_method_ids: List[int]):

    '''
    Validates if caller owns the payment methods
    '''

    # for payment_method in  payment_methods:
    #    if payment_method.owner != caller
    #           raise error

    try:
        caller = Peer.objects.get(wallet_hash=wallet_hash)
    except Peer.DoesNotExist:
        raise ValidationError('peer DoesNotExist')

    payment_methods = PaymentMethod.objects.filter(Q(id__in=payment_method_ids))
    for payment_method in payment_methods:
        if payment_method.owner.wallet_hash != caller.wallet_hash:
            raise ValidationError('invalid payment method, not caller owned')

class AdDetail(APIView):
  def get_object(self, pk):
    try:
      return Ad.objects.get(pk=pk)
    except Ad.DoesNotExist:
      raise Http404

  def get(self, request, pk):
    ad = self.get_object(pk)
    if ad.is_deleted:
      return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = AdSerializer(ad)
    return Response(serializer.data, status=status.HTTP_200_OK)

  def put(self, request, pk):

    # TODO: verify the signature

    wallet_hash = request.data.get('wallet_hash', None)
    if wallet_hash is None:
        return Response({'error': 'wallet_hash is None'}, status=status.HTTP_400_BAD_REQUEST)

    try:
      self.validate_permissions(wallet_hash, pk)
    except ValidationError as err:
      return Response({'error': err.args[0]}, status=status.HTTP_403_FORBIDDEN)

    # get payload
    price_type = request.data.get('price_type', None)
    fixed_price = request.data.get('fixed_price', None)
    floating_price = request.data.get('floating_price', None)
    trade_floor = request.data.get('trade_floor', None)
    trade_ceiling = request.data.get('trade_ceiling', None)
    crypto_amount = request.data.get('crypto_amount', None)
    time_limit = request.data.get('time_limit', None)
    
    ad = self.get_object(pk)

    if trade_floor is not None or trade_ceiling is not None:

        if trade_floor is None:
            # fetch saved trade_floor
            trade_floor = ad.trade_floor
        
        if trade_ceiling is None:
            # fetch saved trade_ceiling
            trade_ceiling = ad.trade_ceiling
        
        if trade_floor >= trade_ceiling:
            return Response(
                {'error': 'trade_floor must be less than trade_ceiling'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    if trade_floor is not None:
      ad.trade_floor = trade_floor
    
    if trade_ceiling is not None:
      ad.trade_ceiling = trade_ceiling

    if price_type is not None:
      ad.price_type = price_type

    if fixed_price is not None:
      ad.fixed_price = fixed_price

    if floating_price is not None:
      ad.floating_price = floating_price

    if crypto_amount is not None:
      ad.crypto_amount = crypto_amount

    if time_limit is not None:
      ad.time_limit = time_limit

    ad.save()
    serializer = AdSerializer(ad)
    return Response(serializer.data, status=status.HTTP_200_OK)
  
  def delete(self, request, pk):

    wallet_hash = request.data.get('wallet_hash', None)
    if wallet_hash is None:
        return Response({'error': 'wallet_hash is None'}, status=status.HTTP_400_BAD_REQUEST)
  
    try:
      self.validate_permissions(wallet_hash, pk)
    except ValidationError as err:
      return Response({'error': err.args[0]}, status=status.HTTP_403_FORBIDDEN)
    
    ad = self.get_object(pk)
    ad.is_deleted = True
    ad.deleted_at = timezone.now()
    ad.save()
    return Response(status=status.HTTP_204_NO_CONTENT)
  
  def validate_permissions(self, wallet_hash, ad_id):
    '''
    Validates if caller is ad owner
    '''

    try:
      ad = Ad.objects.get(pk=ad_id)
      caller = Peer.objects.get(wallet_hash=wallet_hash)
    except Ad.DoesNotExist or Peer.DoesNotExist:
      raise ValidationError('ad or peer does not exist')
    
    if caller.wallet_hash != ad.owner.wallet_hash:
      raise ValidationError('caller must be ad owner')