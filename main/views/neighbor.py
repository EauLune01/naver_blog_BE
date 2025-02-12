from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.generics import DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from ..models.neighbor import Neighbor
from ..models.profile import Profile
from ..serializers.neighbor import NeighborSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import models
from django.db.models import Q


class NeighborView(APIView):
    """
    ✅ 서로이웃 신청 (POST)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="서로이웃 신청(urlname) (버튼 방식)",
        operation_description="특정 사용자의 프로필에서 서로이웃 추가 버튼을 누르면 해당 사용자를 대상으로 신청을 보냅니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "request_message": openapi.Schema(type=openapi.TYPE_STRING, description="서로이웃 신청 메시지", example="친하게 지내고 싶어요!")
            },
            required=["request_message"]
        ),
        responses={
            201: openapi.Response(
                description="서로이웃 신청 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "neighbor_request": openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: openapi.Response(description="잘못된 요청"),
        },
    )
    def post(self, request, to_urlname):
        """
        ✅ 서로이웃 신청 (POST /api/neighbors/{to_urlname}/)
        """
        from_user = request.user
        to_user_profile = get_object_or_404(Profile, urlname=to_urlname)
        to_user = to_user_profile.user

        # ✅ 자기 자신에게 신청 불가
        if from_user == to_user:
            return Response({"message": "자기 자신에게 서로이웃 신청할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ 기존 신청 확인 (중복 신청 방지)
        if Neighbor.objects.filter(from_user=from_user, to_user=to_user, status='pending').exists():
            return Response({"message": "이미 보낸 서로이웃 요청이 있습니다."}, status=status.HTTP_400_BAD_REQUEST)

        if Neighbor.objects.filter(from_user=from_user, to_user=to_user, status='accepted').exists():
            return Response({"message": "이미 서로이웃 관계입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ 요청 메시지 처리
        request_message = request.data.get("request_message", "").strip()

        # ✅ 서로이웃 신청 생성
        neighbor_request = Neighbor.objects.create(
            from_user=from_user,
            to_user=to_user,
            request_message=request_message,
            status="pending"
        )

        return Response({
            "message": "서로이웃 신청이 완료되었습니다.",
            "neighbor_request": NeighborSerializer(neighbor_request).data
        }, status=status.HTTP_201_CREATED)



class NeighborRequestListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NeighborSerializer

    @swagger_auto_schema(
        operation_summary="받은 서로이웃 요청 목록 조회",
        operation_description="현재 로그인한 사용자가 받은 서로이웃 요청 목록을 조회합니다.",
        responses={
            200: openapi.Response(
                description="서로이웃 요청 목록 반환",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "requests": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "from_username": openapi.Schema(type=openapi.TYPE_STRING,
                                                                    description="요청 보낸 사용자 닉네임"),
                                    "from_user_pic": openapi.Schema(type=openapi.TYPE_STRING, format="url",
                                                                    description="요청 보낸 사용자 프로필 사진"),
                                    "request_message": openapi.Schema(type=openapi.TYPE_STRING,
                                                                       description="서로이웃 신청 메시지")
                                }
                            )
                        )
                    }
                )
            ),
            200: openapi.Response(description="받은 서로이웃 요청이 없습니다."),
        }
    )
    def list(self, request, *args, **kwargs):
        """
        ✅ 받은 서로이웃 요청이 없는 경우 적절한 메시지를 반환
        """
        queryset = self.get_queryset()

        if not queryset.exists():
            return Response({"message": "받은 서로이웃 요청이 없습니다.", "requests": []}, status=200)

        request_list = [
            {
                "from_username": neighbor.from_user.profile.username,  # ✅ 사용자에게 username을 보여줌
                "from_urlname": neighbor.from_user.profile.urlname,  # ✅ 내부 처리용 urlname
                "from_user_pic": neighbor.from_user.profile.user_pic.url if neighbor.from_user.profile.user_pic else None,
                "request_message": neighbor.request_message  # ✅ 신청 메시지 추가
            }
            for neighbor in queryset
        ]

        return Response({"requests": request_list}, status=200)

    def get_queryset(self):
        """
        ✅ 자신에게 서로이웃 요청을 보낸 사람들(QuerySet) 반환
        """
        user = self.request.user
        return Neighbor.objects.filter(to_user=user, status="pending").select_related("from_user__profile")

class NeighborAcceptView(APIView):
    """
    ✅ 서로이웃 요청 수락 (PUT /api/neighbors/accept/{neighbor_id}/)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="서로이웃 요청 수락",
        operation_description="받은 서로이웃 신청을 수락합니다.",
        responses={
            200: openapi.Response(description="서로이웃 요청 수락됨"),
            400: openapi.Response(description="이미 수락된 요청"),
            404: openapi.Response(description="요청을 찾을 수 없음"),
        }
    )
    def put(self, request, from_urlname):
        """
        ✅ 서로이웃 요청을 보낸 사용자의 URL 이름 (`from_urlname`)을 기반으로 수락
        """
        to_user = request.user  # 현재 로그인한 사용자
        from_user_profile = get_object_or_404(Profile, urlname=from_urlname)
        from_user = from_user_profile.user

        # ✅ 서로이웃 요청 찾기
        neighbor_request = get_object_or_404(
            Neighbor, from_user=from_user, to_user=to_user, status="pending"
        )

        if neighbor_request.status == "accepted":
            return Response({"message": "이미 서로이웃 상태입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ 서로이웃 요청 수락
        neighbor_request.status = "accepted"
        neighbor_request.save()

        return Response({"message": "서로이웃 요청이 수락되었습니다."}, status=status.HTTP_200_OK)


class NeighborRejectView(APIView):
    """
    ✅ 서로이웃 요청 거절 (DELETE /api/neighbors/reject/{from_user_id}/)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="서로이웃 요청 거절",
        operation_description="서로이웃 요청을 보낸 사용자의 ID로 조회하여 거절합니다.",
        responses={
            200: openapi.Response(description="서로이웃 요청 거절됨"),
            400: openapi.Response(description="이미 수락된 요청"),
            404: openapi.Response(description="요청을 찾을 수 없음"),
        }
    )
    def delete(self, request, from_urlname):
        """
        ✅ 서로이웃 요청을 보낸 사용자의 `urlname`을 기반으로 거절
        """
        to_user = request.user  # 현재 로그인한 사용자
        from_user_profile = get_object_or_404(Profile, urlname=from_urlname)
        from_user = from_user_profile.user

        # ✅ 서로이웃 요청 찾기
        neighbor_request = get_object_or_404(
            Neighbor, from_user=from_user, to_user=to_user, status="pending"
        )

        if neighbor_request.status == "accepted":
            return Response({"message": "이미 수락된 요청은 거절할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ 서로이웃 요청 거절 (삭제)
        neighbor_request.delete()

        return Response({"message": "서로이웃 요청이 거절되었습니다."}, status=status.HTTP_200_OK)


class PublicNeighborListView(APIView):
    """
    ✅ 서로이웃 목록 조회 (GET /api/neighbors/{urlname}/)
    - 프로필이 존재하지 않으면 404 반환.
    - 프로필 소유자가 서로이웃 목록을 비공개로 설정한 경우 "비공개입니다" 반환.
    """
    permission_classes = []

    @swagger_auto_schema(
        operation_summary="타인의 서로이웃 목록 조회",
        operation_description="특정 사용자의 서로이웃 목록을 `urlname`으로 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                'urlname', openapi.IN_PATH, description="조회할 사용자의 URL 이름",
                type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="서로이웃 목록 반환",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "urlname": openapi.Schema(type=openapi.TYPE_STRING, description="사용자의 URL 이름"),
                        "neighbors": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "urlname": openapi.Schema(type=openapi.TYPE_STRING, description="서로이웃 사용자의 URL 이름"),
                                    "user_pic": openapi.Schema(type=openapi.TYPE_STRING, format="url", description="프로필 이미지 URL"),
                                }
                            )
                        )
                    }
                )
            ),
            403: openapi.Response(description="비공개입니다."),
            404: openapi.Response(description="사용자를 찾을 수 없음"),
        }
    )
    def get(self, request, urlname):
        profile = get_object_or_404(Profile, urlname=urlname)

        # ✅ 서로이웃 목록이 비공개인 경우
        if not profile.neighbor_visibility:
            return Response({"message": "비공개입니다."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ `Neighbor` 모델을 사용하여 서로이웃 관계 조회
        neighbors = Neighbor.objects.filter(
            Q(from_user=profile.user) | Q(to_user=profile.user),
            status="accepted"
        ).select_related("from_user__profile", "to_user__profile")

        neighbor_list = [
            {
                "urlname": (neighbor.to_user.profile if neighbor.from_user == profile.user else neighbor.from_user.profile).urlname,
                "user_pic": (neighbor.to_user.profile if neighbor.from_user == profile.user else neighbor.from_user.profile).user_pic.url if (neighbor.to_user.profile if neighbor.from_user == profile.user else neighbor.from_user.profile).user_pic else None
            }
            for neighbor in neighbors
        ]

        return Response({
            "urlname": profile.urlname,
            "neighbors": neighbor_list
        }, status=status.HTTP_200_OK)


class MyNeighborListView(ListAPIView):
    """
    ✅ 로그인한 사용자의 서로이웃 목록 조회
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내 서로이웃 목록 조회",
        operation_description="로그인한 사용자의 서로이웃 목록을 조회합니다.",
        responses={
            200: openapi.Response(
                description="서로이웃 목록 반환",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "neighbors": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "urlname": openapi.Schema(type=openapi.TYPE_STRING, description="서로이웃 사용자의 URL 이름"),
                                    "username": openapi.Schema(type=openapi.TYPE_STRING, description="서로이웃 사용자의 닉네임"),
                                    "user_pic": openapi.Schema(type=openapi.TYPE_STRING, format="url", description="프로필 이미지 URL"),
                                }
                            )
                        ),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="서로이웃이 없는 경우의 메시지")
                    }
                )
            ),
            404: openapi.Response(description="사용자를 찾을 수 없음"),
        }
    )
    def get(self, request):
        """
        ✅ 로그인한 사용자의 서로이웃 목록을 조회합니다.
        """
        profile = get_object_or_404(Profile, user=request.user)

        # ✅ `Neighbor` 모델을 사용하여 서로이웃 관계 조회
        neighbors = Neighbor.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user),
            status="accepted"
        ).select_related("from_user__profile", "to_user__profile")

        neighbor_list = []
        for neighbor in neighbors:
            if neighbor.from_user == request.user:
                neighbor_profile = neighbor.to_user.profile  # ✅ `to_user`의 Profile 가져오기
            else:
                neighbor_profile = neighbor.from_user.profile  # ✅ `from_user`의 Profile 가져오기

            neighbor_list.append({
                "urlname": neighbor_profile.urlname,  # ✅ 반환 값에 `urlname` 포함
                "username": neighbor_profile.username,  # ✅ 사용자가 볼 수 있도록 `username` 포함
                "user_pic": neighbor_profile.user_pic.url if neighbor_profile.user_pic else None
            })

        response_data = {"neighbors": neighbor_list}
        if not neighbor_list:
            response_data["message"] = "서로이웃이 없습니다."

        return Response(response_data, status=status.HTTP_200_OK)


class MyNeighborDeleteView(DestroyAPIView):
    """
    ✅ 로그인한 사용자의 특정 서로이웃 삭제
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내 서로이웃 삭제",
        operation_description="로그인한 사용자가 특정 서로이웃을 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                "neighbor_urlname",
                openapi.IN_PATH,
                description="삭제할 서로이웃의 URL 이름",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="서로이웃 삭제 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="삭제 완료 메시지")
                    }
                )
            ),
            404: openapi.Response(
                description="서로이웃 관계가 존재하지 않음",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="에러 메시지")
                    }
                )
            ),
        }
    )
    def delete(self, request, neighbor_urlname):
        """
        ✅ 로그인한 사용자의 서로이웃 관계를 삭제합니다.
        """
        profile = get_object_or_404(Profile, user=request.user)
        neighbor_profile = get_object_or_404(Profile, urlname=neighbor_urlname)

        # ✅ 서로이웃 관계 확인
        neighbor_relation = Neighbor.objects.filter(
            Q(from_user=request.user, to_user=neighbor_profile.user) |
            Q(from_user=neighbor_profile.user, to_user=request.user),
            status="accepted"
        ).first()

        if not neighbor_relation:
            return Response({"message": "서로이웃 관계가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        # ✅ 서로이웃 관계 삭제
        neighbor_relation.delete()

        return Response({"message": "서로이웃 관계가 삭제되었습니다."}, status=status.HTTP_200_OK)