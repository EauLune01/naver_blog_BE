from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from main.models.category import Category
from main.models.customuser import CustomUser
from ..serializers.signup import SignupSerializer


class SignupView(APIView):
    permission_classes = []  # 인증 없이 접근 가능

    @swagger_auto_schema(
        operation_summary="회원가입",
        operation_description="새로운 사용자를 생성합니다.",
        request_body=SignupSerializer,
        responses={
            201: openapi.Response(description="회원가입 성공", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={"message": openapi.Schema(type=openapi.TYPE_STRING)}
            )),
            400: openapi.Response(description="회원가입 실패", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={"message": openapi.Schema(type=openapi.TYPE_STRING)}
            )),
        }
    )
    def post(self, request):
        # ✅ 로그인된 사용자는 회원가입 불가능
        if request.user.is_authenticated:
            return Response({"message": "로그인된 상태에서는 회원가입이 불가능합니다."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # ✅ 사용자별로 개별적인 '게시판' 카테고리 생성
            Category.objects.get_or_create(name="게시판", user=user)

            return Response({"message": "회원가입이 완료되었습니다."}, status=status.HTTP_201_CREATED)

        return Response({"message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


