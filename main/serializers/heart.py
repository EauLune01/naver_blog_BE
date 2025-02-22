from rest_framework import serializers
from main.models.heart import Heart

class HeartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Heart
        fields = ['id', 'user', 'post','created_at']
        read_only_fields = ['id', 'user', 'post','created_at']
