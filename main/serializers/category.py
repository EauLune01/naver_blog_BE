from rest_framework import serializers
from main.models.category import Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

    def validate_name(self, value):
        """ ✅ 카테고리명이 30글자를 초과하면 오류 발생 """
        if len(value) > 30:
            raise serializers.ValidationError("카테고리명은 최대 30글자까지만 입력할 수 있습니다.")
        return value
