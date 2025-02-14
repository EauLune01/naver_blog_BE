from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from main.models.comment import Comment
from main.models.heart import Heart
from main.models.commentHeart import CommentHeart  # ✅ 댓글 좋아요 추가
from main.serializers.activity import ActivitySerializer

class MyActivityListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ActivitySerializer

    def get_queryset(self):
        return self.get_latest_unread_activity(self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_latest_unread_activity(request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @staticmethod
    def get_latest_unread_activity(user):
        profile = user.profile

        # ✅ 내가 좋아요 누른 게시글 (안 읽은 것만)
        liked_posts = list(Heart.objects.filter(user=user, post__isnull=False, is_read=False)
                           .select_related('post', 'user')
                           .order_by('-created_at'))

        # ✅ 내가 좋아요 누른 댓글 (안 읽은 것만)
        liked_comments = list(CommentHeart.objects.filter(user=user, comment__isnull=False, is_read=False)
                              .select_related('comment', 'user')
                              .order_by('-created_at'))

        # ✅ 내가 작성한 댓글 (안 읽은 것만)
        my_comments = list(Comment.objects.filter(
            author=profile, is_read=False, is_parent=True
        ).select_related('author').order_by('-created_at'))

        # ✅ 내가 작성한 대댓글 (안 읽은 것만)
        my_replies = list(Comment.objects.filter(
            author=profile, is_read=False, is_parent=False
        ).select_related('author').order_by('-created_at'))

        # ✅ 최신순 정렬 후 최대 5개 반환
        combined_activity = sorted(
            liked_posts + liked_comments + my_comments + my_replies,
            key=lambda obj: obj.created_at,
            reverse=True
        )[:5]

        return combined_activity
