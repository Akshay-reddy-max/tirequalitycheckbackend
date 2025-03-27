from rest_framework import serializers
from .models import TyreScan

class TyreScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TyreScan
        fields = '__all__'
