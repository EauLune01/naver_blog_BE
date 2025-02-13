import re
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

        # 아이디 유효성 검사 (5~20자, 영문 소문자, 숫자, 특수문자(-, _))
        #username_regex = r'^[a-z0-9_-]{5,20}$'
        #if not re.match(username_regex, data['id']):
            #errors["id"] = "아이디는 5~20자, 영문 소문자, 숫자, 특수문자(_), (-)만 사용할 수 있습니다."

        # ID 중복 검사
        if User.objects.filter(id=data['id']).exists():
            errors["id"] = "아이디가 중복되었습니다. 다시 입력해주세요."

        #비밀번호 확인 검사
        if data['password'] != data['password_confirm']:
            errors["password"] = "비밀번호가 다릅니다. 다시 입력해주세요"

        # 비밀번호 유효성 검사 (영어 대소문자, 숫자, 특수문자 혼합, 8자리 이상)
        #password_regex = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>])[A-Za-z\d!@#$%^&*(),.?":{}|<>]{8,}$'
        #if not re.match(password_regex, data['password']):
            #errors["password"] = "비밀번호는 영어 대소문자, 숫자, 특수문자를 혼합하여 8자리 이상이어야 합니다."

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')  # password_confirm 필드는 저장하지 않음
        validated_data['password'] = make_password(validated_data['password'])  # 비밀번호 해싱
        user = User.objects.create(**validated_data)
        return user
