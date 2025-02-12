from django.db import models
from django.conf import settings
from main.models.profile import Profile  # Profile 모델 import

class Neighbor(models.Model):
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_neighbor_requests'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_neighbor_requests'
    )
    request_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '신청중'),
            ('accepted', '수락됨'),
            ('rejected', '거절됨')
        ],
        default='pending'
    )

    class Meta:
        unique_together = ('from_user', 'to_user')  # ✅ 중복 신청 방지

    def save(self, *args, **kwargs):
        """
        ✅ 서로이웃 요청이 `accepted`로 변경되면 Profile의 neighbors 관계에 반영.
        ✅ 서로이웃 요청이 `rejected`면 신청 내역을 자동으로 삭제.
        """
        super().save(*args, **kwargs)

        if self.status == 'accepted':
            # ✅ Profile이 없는 경우 자동 생성
            from_profile, _ = Profile.objects.get_or_create(user=self.from_user)
            to_profile, _ = Profile.objects.get_or_create(user=self.to_user)

            # ✅ 중복 추가 방지
            if not from_profile.neighbors.filter(id=to_profile.id).exists():
                from_profile.neighbors.add(to_profile)
                to_profile.neighbors.add(from_profile)

        elif self.status == 'rejected':  # ✅ 거절된 요청 자동 삭제
            self.delete()

    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.status})"