from rest_framework import generics, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema  # ✅ Swagger 추가
from drf_yasg import openapi  # ✅ Swagger 문서 필드 설정
from main.models.category import Category
from main.serializers.category import CategorySerializer

class CategoryListView(generics.ListCreateAPIView):
    """
    ✅ 모든 카테고리 조회 (GET /categories/)
    ✅ 새로운 카테고리 추가 (POST /categories/)
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @swagger_auto_schema(
        operation_summary="모든 카테고리 조회",
        operation_description="등록된 모든 카테고리를 조회합니다.",
        responses={200: CategorySerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="새로운 카테고리 추가",
        operation_description="새로운 카테고리를 추가합니다. (최대 30글자 제한)",
        request_body=CategorySerializer,
        responses={
            201: CategorySerializer,
            400: "잘못된 요청 (30글자 초과 시 오류)"
        }
    )
    def create(self, request, *args, **kwargs):
        """ ✅ 새로운 카테고리 추가 (30글자 제한) """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework import generics, status
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from main.models.category import Category
from main.serializers.category import CategorySerializer
from drf_yasg.utils import swagger_auto_schema  # ✅ Swagger 추가
from drf_yasg import openapi  # ✅ Swagger 문서 필드 설정

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    ✅ 특정 카테고리 조회 (GET /categories/<id>/)
    ✅ 특정 카테고리 수정 (PATCH /categories/<id>/)
    ✅ 특정 카테고리 삭제 (DELETE /categories/<id>/, 단 '게시판' 삭제 불가)
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @swagger_auto_schema(
        operation_summary="특정 카테고리 조회",
        operation_description="카테고리 ID를 입력하면 해당 카테고리를 조회합니다.",
        responses={200: CategorySerializer, 404: "카테고리를 찾을 수 없습니다."}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="특정 카테고리 수정 (PUT 사용 금지)",
        operation_description="카테고리명을 수정합니다. (최대 30글자 제한) \n\n **PUT 요청은 허용되지 않습니다.**",
        request_body=CategorySerializer,
        responses={
            200: CategorySerializer,
            400: "잘못된 요청 (30글자 초과 시 오류)"
        }
    )
    def patch(self, request, *args, **kwargs):
        """ ✅ 카테고리 수정 (30글자 제한) """
        partial = kwargs.pop('partial', True)  # ✅ PUT을 막고 PATCH만 허용
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        auto_schema=None  # ✅ Swagger에서 PUT을 숨김
    )
    def put(self, request, *args, **kwargs):
        """ ❌ PUT 요청 비활성화 (Swagger 문서에서도 안 보이게 설정) """
        return Response({"error": "PUT 요청은 허용되지 않습니다. PATCH 요청을 사용하세요."},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @swagger_auto_schema(
        operation_summary="특정 카테고리 삭제",
        operation_description="카테고리를 삭제합니다. 단, '게시판' 카테고리는 삭제할 수 없습니다.",
        responses={204: "카테고리가 삭제되었습니다.", 403: "⚠️ '게시판' 카테고리는 삭제할 수 없습니다."}
    )
    def delete(self, request, *args, **kwargs):
        """ ✅ 특정 카테고리 삭제 (단, '게시판' 삭제 불가) """
        instance = self.get_object()
        if instance.name == "게시판":
            return Response({"error": "⚠️ '게시판' 카테고리는 삭제할 수 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        self.perform_destroy(instance)
        return Response({"message": "카테고리가 삭제되었습니다."}, status=status.HTTP_204_NO_CONTENT)
