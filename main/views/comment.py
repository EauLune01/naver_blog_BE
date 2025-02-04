import re
from rest_framework import generics,status
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

User = get_user_model()  # Django 기본 User 모델 가져오기


class CommentListView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(
        operation_summary="댓글 목록 조회",
        operation_description="게시글의 댓글 및 대댓글을 조회합니다. 비밀 댓글은 작성자 또는 게시글 작성자만 볼 수 있습니다.",
        responses={
            200: openapi.Response(description="조회 성공", schema=CommentSerializer(many=True)),
            403: openapi.Response(description="조회 권한이 없습니다.")
        }
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # ✅ 조회할 수 없는 경우 403 반환
        if not queryset.exists():
            return Response({"error": "이 게시글의 댓글을 조회할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        self.queryset = queryset
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        """
        ✅ 특정 댓글 조회 (비밀 댓글 및 'mutual' 게시글 제한)
        """
        post_id = self.kwargs.get('post_id')
        user = self.request.user

        # ✅ Swagger 요청이면 빈 QuerySet 반환
        if getattr(self, 'swagger_fake_view', False):
            return Comment.objects.none()

        post = get_object_or_404(Post, id=post_id)

        # ✅ '나만 보기' 게시글이면 작성자 본인만 댓글 조회 가능
        if post.visibility == 'me' and (not user.is_authenticated or post.author.profile != user.profile):
            return Comment.objects.none()

        # ✅ '서로 이웃 공개' 게시글이면 서로 이웃만 댓글 조회 가능
        if post.visibility == 'mutual' and not post.author.profile.neighbors.filter(id=user.profile.id).exists():
            return Comment.objects.none()

        return Comment.objects.filter(post_id=post_id)


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
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
        post_id = self.kwargs.get('post_id')
        user = self.request.user  # ✅ NameError 해결 (user 추가)

        if post_id is None:
            raise Http404("post_id가 없습니다.")  # ✅ post_id가 없으면 404 에러 반환

        # ✅ Swagger 요청이면 빈 QuerySet 반환
        if getattr(self, 'swagger_fake_view', False):
            return Comment.objects.none()

        post = get_object_or_404(Post, id=post_id)

        # ✅ '나만 보기' 게시글이면 작성자 본인만 조회 가능
        if post.visibility == 'me' and (not user.is_authenticated or post.author.profile != user.profile):
            return Comment.objects.none()

        # ✅ '서로 이웃 공개' 게시글이면 서로 이웃만 댓글 조회 가능
        if post.visibility == 'mutual':
            if not user.is_authenticated:
                return Comment.objects.none()
            if not post.author.profile.neighbors.filter(id=user.profile.id).exists():
                return Comment.objects.none()

        return Comment.objects.filter(post_id=post_id)

    @swagger_auto_schema(
        operation_summary="댓글 수정 (PATCH)",
        operation_description="특정 댓글을 수정합니다. (작성자만 가능)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'content': openapi.Schema(type=openapi.TYPE_STRING, description='수정할 댓글 내용')},
            required=['content']
        ),
        responses={
            200: openapi.Response(description="수정 성공", schema=CommentSerializer()),
            403: openapi.Response(description="수정 권한이 없습니다."),
            404: openapi.Response(description="댓글을 찾을 수 없습니다."),
        }
    )
    def patch(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, id=self.kwargs['pk'], post_id=self.kwargs['post_id'])
        user = request.user  # ✅ user 변수 추가

        if comment.post.visibility == 'me' and comment.post.author.profile != user.profile:
            raise ValidationError("이 게시글에는 작성자 본인만 댓글을 작성할 수 있습니다.")

        if comment.post.visibility == 'mutual' and not comment.post.author.profile.neighbors.filter(
                id=user.profile.id).exists():
            raise ValidationError("서로 이웃만 이 게시글에 댓글을 작성할 수 있습니다.")

        if user.profile != comment.author:
            return Response({"error": "수정할 권한이 없습니다."}, status=403)

        return super().patch(request, *args, **kwargs)

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
        comment = get_object_or_404(Comment, id=self.kwargs['pk'], post_id=self.kwargs['post_id'])
        user = request.user  # ✅ user 변수 추가

        if comment.post.visibility == 'me' and comment.post.author.profile != user.profile:
            return Response({"error": "이 게시글의 댓글을 삭제할 권한이 없습니다."}, status=403)

        if comment.post.visibility == 'mutual' and not comment.post.author.profile.neighbors.filter(
                id=user.profile.id).exists():
            return Response({"error": "서로 이웃만 이 게시글의 댓글을 삭제할 수 있습니다."}, status=403)

        if user.profile != comment.author and user.profile != comment.post.author.profile:
            return Response({"error": "삭제할 권한이 없습니다."}, status=403)

        if comment.is_parent:
            comment.content = "삭제된 댓글입니다."
            comment.is_private = False
            comment.save()
        else:
            comment.delete()

        return Response({"message": "댓글이 삭제되었습니다."}, status=204)