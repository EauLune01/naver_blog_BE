from rest_framework import serializers

class PasswordUpdateSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context['user']

        if not user.check_password(data['current_password']):
            raise serializers.ValidationError({"current_password": "현재 비밀번호가 올바르지 않습니다."})

        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "새 비밀번호가 일치하지 않습니다."})

        if data['current_password'] == data['new_password']:
            raise serializers.ValidationError({"new_password": "현재 비밀번호와 동일한 비밀번호는 사용할 수 없습니다."})

        return data
