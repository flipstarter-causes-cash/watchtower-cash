import pytz
from datetime import datetime
from django.utils import timezone
from rest_framework import serializers

from .utils.broadcast import broadcast_transaction
from .utils.totp import generate_pos_device_totp


class TimestampField(serializers.IntegerField):
    def to_representation(self, value):
        return datetime.timestamp(value)

    def to_internal_value(self, data):
        return datetime.fromtimestamp(data).replace(tzinfo=pytz.UTC)


class PosDeviceSerializer(serializers.Serializer):
    posid = serializers.IntegerField()
    wallet_hash = serializers.CharField()


class POSPaymentSerializer(serializers.Serializer):
    transaction = serializers.CharField()
    otp = serializers.CharField(required=False)
    payment_timestamp = TimestampField()
    pos_device = PosDeviceSerializer()

    def save(self):
        validated_data = self.validated_data
        otp = validated_data.get("otp", None)
        payment_timestamp = validated_data.get("payment_timestamp", timezone.now())
        pos_device_data = validated_data["pos_device"]
        wallet_hash = pos_device_data["wallet_hash"]
        posid = pos_device_data["posid"]

        response = {
            "success": False,
            "txid": "",
        }

        otp_timestamp = round(payment_timestamp.timestamp())
        response["otp_timestamp"] = otp_timestamp
        if otp is not None:
            if otp != generate_pos_device_totp(wallet_hash, posid, timestamp=otp_timestamp):
                raise serializers.ValidationError("Provided OTP does not match")
            response["otp_valid"] = True
        else:
            response["otp"] = generate_pos_device_totp(wallet_hash, posid, timestamp=otp_timestamp)

        broadcast_response = broadcast_transaction(validated_data["transaction"])
        if not broadcast_response["success"]:
            error_msg = "Failed to broadcast transaction"
            if "error" in broadcast_response and broadcast_response["error"]:
                error_msg = broadcast_response["error"]
            raise serializers.ValidationError(error_msg)

        response["success"] = True
        response["txid"] = broadcast_response["txid"]

        return response


class POSPaymentResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    txid = serializers.CharField()
    otp = serializers.CharField(required=False)
    otp_timestamp = serializers.IntegerField()
    otp_valid = serializers.CharField(required=False)
