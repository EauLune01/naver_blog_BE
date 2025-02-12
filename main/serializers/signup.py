from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

User = get_user_model()

class SignupSerializer(serializers.ModelSerializer):
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'password', 'password_confirm']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, data):
        """ID 중복 여부 및 비밀번호 확인 검증"""
        errors = {}

        # ID 중복 검사
        if User.objects.filter(id=data['id']).exists():
            errors["id"] = "아이디가 중복되었습니다. 다시 입력해주세요"

        # 비밀번호 확인 검사
        if data['password'] != data['password_confirm']:
            errors["password"] = "비밀번호가 다릅니다. 다시 입력해주세요"

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')  # password_confirm 필드는 저장하지 않음
        validated_data['password'] = make_password(validated_data['password'])  # 비밀번호 해싱
        user = User.objects.create(**validated_data)
        return user


