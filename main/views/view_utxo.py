from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.db.models import (
    Q,
    F,
    Func,
    OuterRef,
    Exists,
    CharField,
    IntegerField,
    BooleanField,
    ExpressionWrapper,
    TextField,
    Case,
    When
)
from django.db.models.functions import Cast, Coalesce
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.contrib.postgres.fields import JSONField
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from main.models import (
    Transaction,
    Wallet,
    Token,
    CashNonFungibleToken,
)
from main.tasks import rescan_utxos
from main.throttles import ScanUtxoThrottle
from main.utils.address_validator import *
from main.utils.address_converter import *


class Round(Func):
    function = "ROUND"
    template = "%(function)s(%(expressions)s::numeric, 0)"


def parse_boolean_query_param(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.lower().strip()

        if normalized == "true": return True
        elif normalized == "false": return False

        return None

    return None


def _get_token_utxos(query, is_cashtoken=False, is_cashtoken_nft=None, show_address_index=False, minting_baton=None, confirmed=None):
    qs = Transaction.objects.filter(query)
    if minting_baton is not None and not is_cashtoken:
        subquery = Exists(
            Token.objects.annotate(
                minting_baton=Cast(KeyTextTransform('minting_baton', 'nft_token_group_details'), JSONField()),
            ).annotate(
                minting_baton_txid=Cast(KeyTextTransform('txid', 'minting_baton'), CharField()),
                minting_baton_index=Cast(KeyTextTransform('index', 'minting_baton'), IntegerField()),
            ).filter(
                minting_baton_txid=OuterRef("txid"),
                minting_baton_index=OuterRef("index"),
            ).values('tokenid')
        )
        if minting_baton:
            qs = qs.filter(subquery)
        else:
            qs = qs.exclude(subquery)

    if isinstance(confirmed, bool):
        qs = qs.filter(blockheight__isnull=not confirmed)

    utxos_values = qs.all().annotate(
        vout=F('index'),
        capability=(F('cashtoken_nft__capability')),
        commitment=(F('cashtoken_nft__commitment')),
        cashtoken_nft_details=F('cashtoken_nft__info__nft_details'),
        token_type=F('token__token_type'),
        block=F('blockheight__number'),
        tokenid=F('token__tokenid'),
        token_name=F('token__name'),
        decimals=F('token__decimals'),
        token_ticker=F('token__token_ticker'),
        amount=Cast('amount', output_field=TextField()),
        is_cashtoken=ExpressionWrapper(
            Q(token__tokenid=settings.WT_DEFAULT_CASHTOKEN_ID),
            output_field=BooleanField()
        )
    )

    if is_cashtoken:
        if is_cashtoken_nft is None:
            annotate_token_info = lambda field: Case(
                When(cashtoken_nft_id__isnull=False, then=F(f"cashtoken_nft__{field}")),
                default=F(f"cashtoken_ft__{field}")
            )
            utxos_values = utxos_values.annotate(
                tokenid=annotate_token_info("category"),
                token_name=annotate_token_info("info__name"),
                decimals=annotate_token_info("info__decimals"),
                token_ticker=annotate_token_info("info__symbol")
            )
        elif is_cashtoken_nft:
            utxos_values = utxos_values.annotate(
                tokenid=F('cashtoken_nft__category'),
                token_name=F('cashtoken_nft__info__name'),
                decimals=F('cashtoken_nft__info__decimals'),
                token_ticker=F('cashtoken_nft__info__symbol')
            )
        else:
            utxos_values = utxos_values.annotate(
                tokenid=F('cashtoken_ft__category'),
                token_name=F('cashtoken_ft__info__name'),
                decimals=F('cashtoken_ft__info__decimals'),
                token_ticker=F('cashtoken_ft__info__symbol')
            )

    if show_address_index:
        utxos_values = utxos_values.annotate(
            wallet_index=F('address__wallet_index'),
            address_path=F('address__address_path')
        ).values(
            'txid',
            'vout',
            'amount',
            'value',
            'tokenid',
            'token_name',
            'token_ticker',
            'decimals',
            'token_type',
            'capability',
            'commitment',
            'cashtoken_nft_details',
            'block',
            'wallet_index',
            'address_path',
            'is_cashtoken'
        )
    else:
        utxos_values = utxos_values.values(
            'txid',
            'vout',
            'amount',
            'value',
            'tokenid',
            'token_name',
            'token_ticker',
            'decimals',
            'token_type',
            'capability',
            'commitment',
            'cashtoken_nft_details',
            'block',
            'is_cashtoken'
        )
    return utxos_values


def _get_ct_utxos(query, is_cashtoken_nft=None, show_address_index=False, confirmed=None):
    return _get_token_utxos(
        query,
        is_cashtoken=True,
        is_cashtoken_nft=is_cashtoken_nft,
        show_address_index=show_address_index,
        confirmed=confirmed,
    )


def _get_bch_utxos(query, show_address_index=False, confirmed=None):
    # Exclude dust amounts as they're likely to be SLP transactions
    # TODO: Needs another more sure way to exclude SLP transactions
    # dust = 546 / (10 ** 8)
    # query = query & Q(amount__gt=dust) & Q(token__name='bch')
    
    # NOTE: removed dust filter here since amount for BCH txns are always 0 now
    query = query & Q(token__name='bch')
    qs = Transaction.objects.filter(query)
    
    if isinstance(confirmed, bool):
        qs = qs.filter(blockheight__isnull=not confirmed)

    if show_address_index:
        utxos_values = qs.all().annotate(
            vout=F('index'),
            block=F('blockheight__number'),
            wallet_index=F('address__wallet_index'),
            address_path=F('address__address_path')
        ).values(
            'txid',
            'vout',
            'value',
            'block',
            'wallet_index',
            'address_path'
        )
    else:
        utxos_values = qs.all().annotate(
            vout=F('index'),
            block=F('blockheight__number'),
        ).values(
            'txid',
            'vout',
            'value',
            'block'
        )
    return utxos_values


class UTXO(APIView):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(name="baton", type=openapi.TYPE_BOOLEAN, in_=openapi.IN_QUERY, required=False),
            openapi.Parameter(name="is_cashtoken", type=openapi.TYPE_BOOLEAN, in_=openapi.IN_QUERY, default=False),
            openapi.Parameter(name="is_cashtoken_nft", type=openapi.TYPE_BOOLEAN, in_=openapi.IN_QUERY, required=False),
            openapi.Parameter(name="confirmed", type=openapi.TYPE_BOOLEAN, in_=openapi.IN_QUERY, required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        slpaddress = kwargs.get('slpaddress', '')
        bchaddress = kwargs.get('bchaddress', '')
        tokenaddress = kwargs.get('tokenaddress', '')
        tokenid = kwargs.get('tokenid', '')
        tokenid_or_category = kwargs.get('tokenid_or_category', '')
        category = kwargs.get('category', '')
        wallet_hash = kwargs.get('wallethash', '')
        baton = parse_boolean_query_param(request.query_params.get('baton', ''))
        is_cashtoken_nft = parse_boolean_query_param(request.query_params.get('is_cashtoken_nft', ''))
        is_cashtoken = parse_boolean_query_param(request.query_params.get('is_cashtoken', ''))
        confirmed = parse_boolean_query_param(request.query_params.get('confirmed', ''))

        if wallet_hash and confirmed:
            rescan_utxos(wallet_hash, full=True, bch_only=True)

        data = { 'valid': False }
        qs = None

        is_token_addr = is_token_address(tokenaddress)
        
        if is_bch_address(bchaddress):
            data['address'] = bchaddress
            query = Q(address__address=data['address']) & Q(spent=False)
            utxos_values = _get_bch_utxos(query, confirmed=confirmed)
        
        if is_slp_address(slpaddress) or is_token_addr:
            data['address'] = slpaddress
            if is_token_addr:
                data['address'] = bch_address_converter(tokenaddress, to_token_addr=False)

            if tokenid or category:
                query = Q(address__address=data['address']) & Q(spent=False)

                if is_token_addr:
                    if is_cashtoken_nft:
                        query = query & Q(cashtoken_nft__category=category)

                        if baton:
                            query = query & Q(
                                cashtoken_nft__capability=CashNonFungibleToken.Capability.MINTING
                            )
                        else:
                            if baton is not None:
                                query = query & (
                                    Q(cashtoken_nft__capability=CashNonFungibleToken.Capability.MUTABLE) |
                                    Q(cashtoken_nft__capability=CashNonFungibleToken.Capability.NONE)
                                )
                    else:
                        query = query & Q(cashtoken_ft__category=category)
                else:
                    query = query & Q(token__tokenid=tokenid)
            else:
                query = Q(address__address=data['address']) & Q(spent=False)
                if is_token_addr:
                    query = query & Q(token__tokenid=settings.WT_DEFAULT_CASHTOKEN_ID)

                    if is_cashtoken_nft:
                        query = query & Q(cashtoken_nft__isnull=False)

                        if baton:
                            query = query & Q(cashtoken_nft__capability=CashNonFungibleToken.Capability.MINTING)
                        else:
                            if baton is not None:
                                query = query & (
                                    Q(cashtoken_nft__capability=CashNonFungibleToken.Capability.MUTABLE) |
                                    Q(cashtoken_nft__capability=CashNonFungibleToken.Capability.NONE)
                                )
                    else:
                        if is_cashtoken_nft is not None:
                            query = query & Q(cashtoken_ft__isnull=False)

            if is_token_addr:
                utxos_values = _get_ct_utxos(query, is_cashtoken_nft=is_cashtoken_nft, confirmed=confirmed)
            else:
                utxos_values = _get_token_utxos(query, minting_baton=baton, confirmed=confirmed)

        if wallet_hash:
            wallet = Wallet.objects.get(wallet_hash=wallet_hash)
            data['wallet'] = wallet_hash

            if wallet.wallet_type == 'slp':
                if tokenid_or_category:
                    query = Q(wallet=wallet) & Q(spent=False) & Q(token__tokenid=tokenid_or_category)
                else:
                    query = Q(wallet=wallet) & Q(spent=False)

                utxos_values = _get_token_utxos(query, show_address_index=True, minting_baton=baton, confirmed=confirmed)

            elif wallet.wallet_type == 'bch':
                query = Q(wallet=wallet) & Q(spent=False)

                if is_cashtoken or tokenid_or_category:
                    query = query & Q(token__tokenid=settings.WT_DEFAULT_CASHTOKEN_ID)

                    if is_cashtoken_nft:
                        if tokenid_or_category:
                            query = query & Q(cashtoken_nft__category=tokenid_or_category)
                        else:
                            query = query & Q(cashtoken_nft__isnull=False)

                        if baton:
                            query = query & Q(cashtoken_nft__capability=CashNonFungibleToken.Capability.MINTING)
                        else:
                            if baton is not None:
                                query = query & (
                                    Q(cashtoken_nft__capability=CashNonFungibleToken.Capability.MUTABLE) |
                                    Q(cashtoken_nft__capability=CashNonFungibleToken.Capability.NONE)
                                )
                    else:
                        if tokenid_or_category:
                            query = query & Q(cashtoken_ft__category=tokenid_or_category)
                        else:
                            if is_cashtoken_nft is not None:
                                query = query & Q(cashtoken_ft__isnull=False)

                    utxos_values = _get_ct_utxos(query, is_cashtoken_nft=is_cashtoken_nft, show_address_index=True, confirmed=confirmed)
                else:
                    utxos_values = _get_bch_utxos(query, show_address_index=True, confirmed=confirmed)
                

        if baton is not None:
            data['minting_baton'] = baton

        data['utxos'] = list(utxos_values)
        data['valid'] = True  
        return Response(data=data, status=status.HTTP_200_OK)


class ScanUtxos(APIView):
    throttle_classes = [ScanUtxoThrottle]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(name="background", type=openapi.TYPE_BOOLEAN, in_=openapi.IN_QUERY, default=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        wallet_hash = kwargs.get('wallethash', '')
        background = request.query_params.get("background", None)
        if isinstance(background, str) and background.lower() == "false":
            background = False

        try:
            wallet = Wallet.objects.get(wallet_hash=wallet_hash)
        except Wallet.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if background:
            task = rescan_utxos.delay(wallet.wallet_hash, full=True)
            return Response({ "task_id": task.id }, status = status.HTTP_202_ACCEPTED)

        rescan_utxos(wallet.wallet_hash, full=True)
        return Response(data={'success': True}, status=status.HTTP_200_OK)
