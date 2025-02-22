from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from main.models.post import Post
from main.models.heart import Heart
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from main.serializers.heart import HeartSerializer

User = get_user_model()  # ✅ Django의 사용자 모델 가져오기

class ToggleHeartView(generics.GenericAPIView):
    """ ✅ 하트 추가/삭제 (토글 기능) """
    permission_classes = [IsAuthenticated]
    serializer_class = HeartSerializer  # ✅ 기존 Serializer 사용

    @swagger_auto_schema(
        operation_summary="하트 추가/삭제",
        operation_description="게시글에 하트를 추가하거나 취소합니다.",
        responses={
            200: openapi.Response(description="하트 취소", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING, description="응답 메시지"),
                    "like_count": openapi.Schema(type=openapi.TYPE_INTEGER, description="현재 하트 개수")
                }
            )),
            201: openapi.Response(description="하트 추가", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING, description="응답 메시지"),
                    "like_count": openapi.Schema(type=openapi.TYPE_INTEGER, description="현재 하트 개수")
                }
            )),
        }
    )
    def post(self, request, post_id):
        if getattr(self, 'swagger_fake_view', False):
            return Response({"message": "Swagger 문서 생성 중"}, status=status.HTTP_200_OK)

        post = get_object_or_404(Post, id=post_id)
        user = request.user

        # ✅ '나만 보기' 게시글이면 하트 불가능
        if post.visibility == 'me':
            return Response({"error": "이 게시글에서는 좋아요를 누를 수 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ '서로 이웃 공개' 게시글이면 서로 이웃만 하트 가능 (is_mutual 대신 neighbors 사용)
        if post.visibility == 'mutual' and not post.user.profile.neighbors.filter(id=user.profile.id).exists():
            return Response({"error": "서로 이웃만 이 게시글에 좋아요를 누를 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ 현재 유저가 이미 하트를 눌렀는지 확인하고 최적화
        heart = Heart.objects.filter(post=post, user=user).first()

        if heart:
            heart.delete()
            post.like_count = max(0, post.like_count - 1)  # ✅ like_count 감소
            post.save()
            return Response({"message": "하트 취소", "like_count": post.like_count}, status=status.HTTP_200_OK)

        Heart.objects.create(post=post, user=user)
        post.like_count += 1
        post.save()

        return Response({"message": "하트 추가", "like_count": post.like_count}, status=status.HTTP_201_CREATED)


class PostHeartUsersView(generics.RetrieveAPIView):
    """ ✅ 특정 게시글을 좋아요한 유저 목록 반환 """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="게시글을 좋아요한 유저 목록 조회",
        operation_description="게시글을 좋아요한(하트를 누른) 유저 목록을 반환합니다.",
        responses={
            200: openapi.Response(description="유저 목록 반환", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "liked_users": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "username": openapi.Schema(type=openapi.TYPE_STRING, description="유저 이름"),
                                "urlname": openapi.Schema(type=openapi.TYPE_STRING, description="유저 URL 이름"),
                                "user_pic": openapi.Schema(type=openapi.TYPE_STRING, description="유저 프로필 사진 URL"),
                                "blog_name": openapi.Schema(type=openapi.TYPE_STRING, description="블로그 이름"),
                            }
                        ),
                        description="좋아요(하트)를 누른 유저 목록"
                    )
                }
            )),
        }
    )
    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        user = request.user

        # ✅ '나만 보기' 게시글이면 하트 유저 목록 조회 불가
        if post.visibility == 'me' and post.user != user:
            return Response({"error": "이 게시글의 좋아요 유저 목록을 조회할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ '서로 이웃 공개' 게시글이면 서로 이웃만 하트 목록 조회 가능
        if post.visibility == 'mutual' and not post.user.profile.neighbors.filter(id=user.profile.id).exists():
            return Response({"error": "서로 이웃만 이 게시글의 좋아요 유저 목록을 조회할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ Heart 테이블에서 해당 게시글을 좋아요한 유저 정보 가져오기
        hearts = Heart.objects.filter(post=post).select_related('user__profile')  # profile까지 join
        liked_users = [
            {
                "username": heart.user.profile.username,  # ✅ username 반환
                "urlname": heart.user.profile.urlname,  # ✅ urlname 반환
                "user_pic": heart.user.profile.user_pic.url, # user_pic 반환
                "blog_name": heart.user.profile.blog_name  # ✅ blog_name 추가
            }
            for heart in hearts
        ]

        return Response({"liked_users": liked_users}, status=status.HTTP_200_OK)




class PostHeartCountView(generics.RetrieveAPIView):
    """ ✅ 특정 게시글의 하트 개수 반환 """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="게시글 하트 개수 조회",
        operation_description="게시글의 총 좋아요(하트) 개수를 반환합니다.",
        responses={
            200: openapi.Response(description="하트 개수 반환", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "like_count": openapi.Schema(type=openapi.TYPE_INTEGER, description="현재 하트 개수")
                }
            )),
        }
    )
    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        user = request.user

        # ✅ '나만 보기' 게시글이면 하트 개수 조회 불가
        if post.visibility == 'me' and post.user != user:
            return Response({"error": "이 게시글의 하트 개수를 조회할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ '서로 이웃 공개' 게시글이면 서로 이웃만 하트 개수 조회 가능 (is_mutual 대신 neighbors 사용)
        if post.visibility == 'mutual' and not post.user.profile.neighbors.filter(id=user.profile.id).exists():
            return Response({"error": "서로 이웃만 이 게시글의 하트 개수를 조회할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)

        return Response({"like_count": post.like_count}, status=status.HTTP_200_OK)
