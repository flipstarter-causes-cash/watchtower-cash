from rest_framework import serializers

from datetime import timedelta

from vouchers.models import *


class VaultSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Vault
        fields = '__all__'


class VoucherSerializer(serializers.ModelSerializer):
    capability = serializers.SerializerMethodField()

    class Meta:
        model = Voucher
        fields = (
            'id',
            'vault',
            'value',
            'minting_txid',
            'claim_txid',
            'category',
            'commitment',
            'capability',
            'claimed',
            'expired',
            'duration_days',
            'date_created',
            'date_claimed',
            'expiration_date',
        )

        read_only_fields = (
            'expiration_date',
            'id',
            'capability',
        )

    def get_capability(self, obj):
        return 'none'


class VoucherClaimCheckSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=100, required=True)  # vault token address
    voucher_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True
    )


class VoucherClaimCheckResponseSerializer(serializers.Serializer):
    proceed = serializers.BooleanField(default=False)
    voucher_id = serializers.JSONField()


class VoucherClaimedResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)


class VoucherClaimedSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=100, required=True)
    txid = serializers.CharField(max_length=100, required=True)
