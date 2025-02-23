from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from django.core.exceptions import ValidationError
from django.http import Http404

from authentication.token import TokenAuthentication

from rampp2p.utils.contract import create_contract
from rampp2p.validators import *
from rampp2p.models import (
    StatusType,
    Order,
    Peer,
    Contract,
    Transaction,
    Recipient,
    Arbiter,
    TradeType
)
from rampp2p.serializers import (
    ContractSerializer, 
    ContractDetailSerializer,
    TransactionSerializer, 
    RecipientSerializer
)

import logging
logger = logging.getLogger(__name__)

class ContractList(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        queryset = Contract.objects.all()

        # TODO pagination

        serializer = ContractSerializer(queryset, many=True)
        return Response(serializer.data, status.HTTP_200_OK)

class ContractDetail(APIView):
    authentication_classes = [TokenAuthentication]

    def get_object(self, pk):
        try:
            order = Order.objects.get(pk=pk)
            contract = Contract.objects.get(order__id=order.id)
            return contract
        except (Order.DoesNotExist, Contract.DoesNotExist):
            raise Http404

    def get(self, request, pk):
        contract_instance = self.get_object(pk)
        contract_serializer = ContractDetailSerializer(contract_instance)

        transactions = Transaction.objects.filter(contract__id=contract_instance.id)

        tx_data = []
        for _, tx in enumerate(transactions):
            tx_outputs = Recipient.objects.filter(transaction__id=tx.id)
            data = {}
            data["txn"] = TransactionSerializer(tx).data
            data["txn"]["outputs"] = RecipientSerializer(tx_outputs, many=True).data
            tx_data.append(data)

        response = {
            "contract": contract_serializer.data,
            "timestamp": contract_instance.created_at.timestamp(),
            "transactions": tx_data
        }
        return Response(response, status=status.HTTP_200_OK)

class CreateContract(APIView):
    authentication_classes = [TokenAuthentication]
    
    def post(self, request, pk):
        try:
            self.validate_permissions(request.user.wallet_hash, pk)
            validate_status(pk, StatusType.CONFIRMED)
            
            order = Order.objects.get(pk=pk)
            arbiter = Arbiter.objects.get(pk=request.data.get('arbiter'))
            params = self.get_params(arbiter.public_key, order)

        except (Order.DoesNotExist, Arbiter.DoesNotExist, ValidationError) as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)
        
        generate = False
        address = None
        timestamp = None
        contract = Contract.objects.filter(order__id=pk)

        if not contract.exists():
            # Create contract (& address) if not already existing
            contract = Contract.objects.create(order=order)
            generate = True
        else:
            contract = contract.first()
            # (Re)generate contract address if:
            #   - address is None
            #   - arbiter is None
            #   - arbiter has been changed
            if ((contract.address is None) 
                or (order.arbiter is None) 
                or (order.arbiter.id != arbiter.id)):
                generate = True
            else:
                # return contract if already existing
                address = contract.address
        
        timestamp = contract.created_at.timestamp()
        if generate:
            # if contract.address != None:
                # unsubscribe to contract address
            contract.address = None
            contract.save()
            # Execute subprocess
            create_contract(
                order_id=contract.order.id,
                arbiter_pubkey=params['arbiter_pubkey'], 
                seller_pubkey=params['seller_pubkey'], 
                buyer_pubkey=params['buyer_pubkey'],
                timestamp=timestamp
            )
        
        # update order arbiter
        order.arbiter = arbiter
        order.save()
        
        response = {
            'success': True,
            'data': {
                'order': order.id,
                'contract': contract.id,
                'timestamp': timestamp,
                'arbiter_address': order.arbiter.address,
                'buyer_address': params['buyer_address'],
                'seller_address': params['seller_address']
            }
        }
        
        if not (address is None):
            response['data']['contract_address'] = address
        
        return Response(response, status=status.HTTP_200_OK)

    def get_params(self, arbiter_pubkey, order: Order):

        seller_pubkey = None
        buyer_pubkey = None
        seller_address = None
        buyer_address = None

        if order.ad_snapshot.trade_type == TradeType.SELL:
            seller_pubkey = order.ad_snapshot.ad.owner.public_key
            buyer_pubkey = order.owner.public_key
            seller_address = order.ad_snapshot.ad.owner.address
            buyer_address = order.owner.address
        else:
            seller_pubkey = order.owner.public_key
            buyer_pubkey = order.ad_snapshot.ad.owner.public_key
            seller_address = order.owner.address
            buyer_address = order.ad_snapshot.ad.owner.address

        if (arbiter_pubkey is None or 
            seller_pubkey is None or 
            buyer_pubkey is None or
            seller_address is None or
            buyer_address is None):
            raise ValidationError('contract parameters are required')
        
        params = {
            'arbiter_pubkey': arbiter_pubkey,
            'seller_pubkey': seller_pubkey,
            'buyer_pubkey': buyer_pubkey,
            'seller_address': seller_address,
            'buyer_address': buyer_address,
        }

        return params
    
    def validate_permissions(self, wallet_hash, pk):
        '''
        Owners of SELL ads can set order statuses to CONFIRMED.
        Owners of orders for sell ads can set order statuses to CONFIRMED.
        '''

        try:
            caller = Peer.objects.get(wallet_hash=wallet_hash)
            order = Order.objects.get(pk=pk)
        except Peer.DoesNotExist or Order.DoesNotExist:
            raise ValidationError('Peer/Order DoesNotExist')

        seller = None
        if order.ad_snapshot.trade_type == TradeType.SELL:
            seller = order.ad_snapshot.ad.owner
        else:
            seller = order.owner
    
        # require caller is seller
        if caller.wallet_hash != seller.wallet_hash:
            raise ValidationError('caller must be seller')