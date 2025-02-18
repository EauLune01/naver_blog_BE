import re
from rest_framework import generics, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from main.models.comment import Comment
from main.models.post import Post
from main.serializers.comment import CommentSerializer
from main.models.profile import Profile  # ✅ Profile 모델 임포트
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from django.http import Http404

class CommentListView(ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(
        operation_summary="댓글 목록 조회",
        operation_description="게시글의 댓글 및 대댓글을 조회합니다. 비밀 댓글은 작성자 또는 게시글 작성자만 볼 수 있습니다.",
        responses={
            200: openapi.Response(description="조회 성공", schema=CommentSerializer(many=True)),
            403: openapi.Response(description="조회 권한이 없습니다."),
            404: openapi.Response(description="게시글을 찾을 수 없습니다."),
        }
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # 게시글이 없는 경우 404 반환
        if queryset is None:
            return Response({"error": "게시글을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 🔥 `context={'request': request}` 추가!
        serializer = self.serializer_class(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        """
        ✅ 특정 댓글 조회 (비밀 댓글 및 'mutual' 게시글 제한)
        """
        if getattr(self, 'swagger_fake_view', False):
            return Comment.objects.none()

        post_id = self.kwargs.get('post_id')
        if post_id is None:
            return Comment.objects.none()

        post = Post.objects.filter(id=post_id).first()
        if not post:
            return Comment.objects.none()

        user = self.request.user

        # ✅ '나만 보기' 게시물 → 작성자 본인만 조회 가능
        if post.visibility == 'me' and (not user.is_authenticated or post.user != user):
            return Comment.objects.none()

        # ✅ '서로 이웃 공개' 게시물 → 서로 이웃만 조회 가능
        if post.visibility == 'mutual' and not post.user.profile.neighbors.filter(id=user.profile.id).exists():
            return Comment.objects.none()

        # ✅ 댓글과 대댓글을 계층적으로 가져오기
        comments = Comment.objects.filter(post_id=post_id, parent__isnull=True).prefetch_related('replies')

        return comments

    @swagger_auto_schema(
        operation_summary="댓글 생성",
        operation_description="게시글에 댓글을 작성합니다. '서로 이웃 공개' 게시물에는 서로 이웃만 댓글을 달 수 있으며, '나만 보기' 게시물에는 작성자 본인만 댓글을 달 수 있습니다.",
        request_body=CommentSerializer,
        responses={
            201: openapi.Response(description="댓글 작성 성공", schema=CommentSerializer()),
            400: openapi.Response(description="잘못된 요청"),
            403: openapi.Response(description="댓글 작성 권한이 없습니다."),
            404: openapi.Response(description="게시글을 찾을 수 없습니다."),
        }
    )
    def post(self, request, *args, **kwargs):
        """
        ✅ 댓글 작성 (전체 공개 or 서로 이웃 or '나만 보기' 제한 적용)
        """
        post_id = self.kwargs.get('post_id')
        if not post_id:
            return Response({"error": "post_id가 없습니다."}, status=400)

        post = Post.objects.filter(id=post_id).first()
        if not post:
            return Response({"error": "게시글을 찾을 수 없습니다."}, status=404)

        user = request.user

        # ✅ '나만 보기' 게시물 → 작성자 본인만 댓글 가능
        if post.visibility == 'me' and post.user != user:
            return Response({"error": "이 게시글에는 작성자 본인만 댓글을 작성할 수 있습니다."}, status=403)

        # ✅ '서로 이웃 공개' 게시물 → 서로 이웃인지 체크
        if post.visibility == 'mutual' and not post.user.profile.neighbors.filter(id=user.profile.id).exists():
            return Response({"error": "서로 이웃 관계인 사용자만 댓글을 작성할 수 있습니다."}, status=403)

        # ✅ 댓글 저장
        is_private = request.data.get('is_private', False)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(post=post, is_private=is_private)  # ✅ user.profile 대신 create()에서 처리
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

class CommentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


    @swagger_auto_schema(
        operation_summary="댓글 상세 조회",
        operation_description="특정 댓글을 조회합니다. 비밀 댓글은 작성자 또는 게시글 작성자만 볼 수 있습니다.",
        responses={
            200: openapi.Response(description="조회 성공", schema=CommentSerializer()),
            403: openapi.Response(description="조회 권한이 없습니다."),
            404: openapi.Response(description="댓글을 찾을 수 없습니다."),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        """
        ✅ 특정 댓글 조회 (비밀 댓글 및 'mutual' 게시글 제한)
        """
        if getattr(self, 'swagger_fake_view', False):
            return Comment.objects.none()

        post_id = self.kwargs.get('post_id')
        if post_id is None:
            return Comment.objects.none()

        post = Post.objects.filter(id=post_id).first()
        if not post:
            return Comment.objects.none()

        user = self.request.user
        if post.visibility == 'me' and (not user.is_authenticated or post.user.profile != user.profile):
            return Comment.objects.none()

        if post.visibility == 'mutual' and not post.user.profile.neighbors.filter(id=user.profile.id).exists():
            return Comment.objects.none()

        return Comment.objects.filter(post_id=post_id)

    # ✅ 공통으로 사용할 `request_body` 정의
    comment_update_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "content": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="댓글 내용",
                example="이 댓글을 수정합니다."
            ),
            "is_private": openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                description="비밀 댓글 여부 (True: 비공개, False: 공개)",
                example=False
            ),
        },
        required=["content"],  # ✅ content는 필수 입력값
    )

    # ✅ PUT 요청용: content 필수
    comment_update_schema_put = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "content": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="댓글 내용",
                example="이 댓글을 수정합니다."
            ),
            "is_private": openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                description="비밀 댓글 여부 (True: 비공개, False: 공개)",
                example=False
            ),
        },
        required=["content"],  # ✅ PUT에서는 content 필수
    )

    # ✅ PATCH 요청용: content 필수 아님
    comment_update_schema_patch = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "content": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="댓글 내용",
                example="이 댓글을 수정합니다."
            ),
            "is_private": openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                description="비밀 댓글 여부 (True: 비공개, False: 공개)",
                example=False
            ),
        }
    )

    # ✅ PUT (전체 수정)
    @swagger_auto_schema(
        operation_summary="댓글 수정 (전체 업데이트, PUT)",
        operation_description="특정 댓글을 전체 수정합니다. 댓글 작성자만 수정 가능합니다.",
        request_body=comment_update_schema_put,
        responses={
            200: openapi.Response(description="수정 성공", schema=CommentSerializer()),
            403: openapi.Response(description="수정 권한이 없습니다."),
            404: openapi.Response(description="댓글을 찾을 수 없습니다."),
        }
    )
    def put(self, request, *args, **kwargs):
        post_id = self.kwargs.get('post_id')
        comment = get_object_or_404(Comment, id=self.kwargs['pk'], post_id=post_id)
        user = request.user

        if user.profile != comment.author:
            return Response({"error": "수정할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ `content`와 `is_private`만 받아서 업데이트하도록 `data` 필터링
        data = request.data.copy()
        allowed_fields = {"content", "is_private"}
        data = {key: value for key, value in data.items() if key in allowed_fields}

        serializer = CommentSerializer(comment, data=data, partial=False, context={'request': request})  # ✅ context 추가
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    # ✅ PATCH (부분 수정)
    @swagger_auto_schema(
        operation_summary="댓글 수정 (부분 업데이트, PATCH)",
        operation_description="특정 댓글을 일부 수정합니다. 댓글 작성자만 수정 가능합니다.",
        request_body=comment_update_schema_patch,  # ✅ content 필수 X
        responses={
            200: openapi.Response(description="수정 성공", schema=CommentSerializer()),
            403: openapi.Response(description="수정 권한이 없습니다."),
            404: openapi.Response(description="댓글을 찾을 수 없습니다."),
        }
    )
    def patch(self, request, *args, **kwargs):
        post_id = self.kwargs.get('post_id')
        comment = get_object_or_404(Comment, id=self.kwargs['pk'], post_id=post_id)
        user = request.user

        if user.profile != comment.author:
            return Response({"error": "수정할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ `content`와 `is_private`만 받아서 업데이트하도록 `data` 필터링
        data = request.data.copy()
        allowed_fields = {"content", "is_private"}
        data = {key: value for key, value in data.items() if key in allowed_fields}

        serializer = CommentSerializer(comment, data=data, partial=True, context={'request': request})  # ✅ context 추가
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="댓글 삭제",
        operation_description="특정 댓글을 삭제합니다. (댓글 작성자 또는 게시글 작성자만 가능)",
        responses={
            204: openapi.Response(description="댓글 삭제 성공"),
            403: openapi.Response(description="삭제 권한이 없습니다."),
            404: openapi.Response(description="댓글을 찾을 수 없습니다."),
        }
    )
    def delete(self, request, *args, **kwargs):
        """
        ✅ 댓글 삭제 (댓글 작성자 또는 게시글 작성자만 가능)
        """
        post_id = self.kwargs.get('post_id')
        if post_id is None:
            return Response({"error": "post_id가 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        comment = get_object_or_404(Comment, id=self.kwargs['pk'], post_id=post_id)
        user = request.user

        # ✅ 댓글 작성자 또는 게시글 작성자만 삭제 가능
        if user.profile != comment.author and user.profile != comment.post.user.profile:
            return Response({"error": "삭제할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        if comment.is_parent:
            comment.content = "삭제된 댓글입니다."
            comment.is_private = False
            comment.save()
        else:
            comment.delete()

        return Response({"message": "댓글이 삭제되었습니다."}, status=status.HTTP_204_NO_CONTENT)
