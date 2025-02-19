from rest_framework import serializers
from ..models.neighbor import Neighbor
from ..models.profile import Profile

class NeighborSerializer(serializers.ModelSerializer):
    """
    서로이웃 신청 + 서로이웃 목록 반환을 동시에 처리하는 Serializer
    """
    from_user = serializers.StringRelatedField(read_only=True)  # 신청한 사용자 (문자열)
    to_user = serializers.StringRelatedField(read_only=True)  # 신청 대상 사용자 (문자열)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    request_message = serializers.CharField(required=False, allow_blank=True)

    # 서로이웃 목록을 반환할 때 추가할 필드
    from_urlname = serializers.CharField(source="from_user.profile.urlname", read_only=True)  # 신청한 사용자의 URL 이름
    to_urlname = serializers.CharField(source="to_user.profile.urlname", read_only=True)  # 신청 대상 사용자의 URL 이름
    urlname = serializers.CharField(source="to_user.profile.urlname", read_only=True)  # urlname 추가
    username = serializers.CharField(source="to_user.profile.username", read_only=True)  # username 추가
    from_user_pic = serializers.SerializerMethodField()  # 신청한 사용자의 프로필 사진 URL
    to_user_pic = serializers.SerializerMethodField()  # 신청 대상 사용자의 프로필 사진 URL

    class Meta:
        model = Neighbor
        fields = [
            'id', 'from_user', 'to_user', 'from_urlname', 'to_urlname',
            'urlname', 'username', 'status', 'request_message',
            'created_at', 'from_user_pic', 'to_user_pic'
        ]
        read_only_fields = ['id', 'created_at']

    def get_from_user_pic(self, obj):
        """
        신청한 사용자의 프로필 사진 URL 반환
        """
        profile = obj.from_user.profile if obj.from_user.profile else None
        return profile.user_pic.url if profile and profile.user_pic else None

    def get_to_user_pic(self, obj):
        """
        신청 대상 사용자의 프로필 사진 URL 반환
        """
        profile = obj.to_user.profile if obj.to_user.profile else None
        return profile.user_pic.url if profile and profile.user_pic else None

    def validate(self, data):
        """
        유효성 검사: 자기 자신에게 신청 불가, 중복 신청 방지
        """
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context가 필요합니다.")

        from_user = request.user
        to_urlname = self.initial_data.get("to_urlname")  # 클라이언트에서 `to_urlname`을 입력받음

        try:
            to_user = Profile.objects.get(urlname=to_urlname).user
        except Profile.DoesNotExist:
            raise serializers.ValidationError("해당 URL 이름을 가진 사용자를 찾을 수 없습니다.")

        # 자기 자신에게 신청 불가
        if from_user == to_user:
            raise serializers.ValidationError("자기 자신에게 서로이웃 신청할 수 없습니다.")

        # 기존 신청 확인 (중복 신청 방지)
        if Neighbor.objects.filter(from_user=from_user, to_user=to_user, status='pending').exists():
            raise serializers.ValidationError("이미 보낸 서로이웃 요청이 있습니다.")

        if Neighbor.objects.filter(from_user=from_user, to_user=to_user, status='accepted').exists():
            raise serializers.ValidationError("이미 서로이웃 관계입니다.")

        return data

    def create(self, validated_data):
        """
        서로이웃 신청을 생성 (기본값: `pending`)
        """
        request = self.context.get("request")
        from_user = request.user
        to_urlname = self.initial_data.get("to_urlname")
        to_user = Profile.objects.get(urlname=to_urlname).user  # `Profile`에서 `User` 가져오기
        request_message = validated_data.get("request_message", "")

        neighbor_request = Neighbor.objects.create(from_user=from_user, to_user=to_user, request_message=request_message, status="pending")
        return neighbor_request

    def update(self, instance, validated_data):
        """
        서로이웃 요청을 `accepted`로 변경하면 Profile 관계에도 반영
        """
        instance.status = validated_data.get("status", instance.status)
        instance.save()

        if instance.status == "accepted":
            from_profile, _ = Profile.objects.get_or_create(user=instance.from_user)
            to_profile, _ = Profile.objects.get_or_create(user=instance.to_user)

            # 중복 추가 방지
            if not from_profile.neighbors.filter(id=to_profile.id).exists():
                from_profile.neighbors.add(to_profile)
                to_profile.neighbors.add(from_profile)

        return instance

