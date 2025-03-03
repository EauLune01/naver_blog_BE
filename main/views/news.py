from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from main.serializers import NewsSerializer
from main.models.comment import Comment
from main.models.heart import Heart

class MyNewsListView(ListAPIView):
    """
    내 소식 API (내 게시글에 달린 댓글, 좋아요 / 내 댓글에 달린 대댓글)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NewsSerializer

    @swagger_auto_schema(
        operation_summary="내 소식 조회",
        operation_description="내 게시물에 달린 댓글, 좋아요 및 내 댓글에 달린 대댓글을 최신순으로 조회",
        responses={200: NewsSerializer(many=True)}
    )
    def get_queryset(self):
        user = self.request.user
        profile = user.profile  # ✅ Profile 객체 가져오기

        # ✅ 내가 작성한 게시글에 달린 댓글 (post__user → 내가 작성한 게시글)
        post_comment_news = list(Comment.objects.filter(
            post__user=user, is_read=False
        ).exclude(author=profile)  # ✅ 내가 쓴 댓글은 제외
        .select_related('post', 'author')
        .order_by('-created_at'))

        # ✅ 내가 작성한 게시글에 달린 좋아요 (post__user → 내가 작성한 게시글)
        post_like_news = list(Heart.objects.filter(
            post__user=user, is_read=False
        ).exclude(user=profile.user)  # ✅ 내가 누른 좋아요는 제외, profile.user로 수정
        .select_related('post', 'user')
        .order_by('-created_at'))

        # ✅ 내가 작성한 댓글에 달린 대댓글 (parent__author → 내가 쓴 댓글에 대한 대댓글)
        comment_reply_news = list(Comment.objects.filter(
            parent__author=profile, is_read=False
        ).exclude(author=profile)  # ✅ 내가 작성한 대댓글은 제외
        .select_related('post', 'author')
        .order_by('-created_at'))

        # ✅ 최신순으로 정렬하고 최대 5개만 반환
        combined_news = sorted(
            post_comment_news + post_like_news + comment_reply_news,
            key=lambda obj: obj.created_at,
            reverse=True
        )[:5]

        return combined_news

