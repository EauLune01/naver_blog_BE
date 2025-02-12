from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


# CustomUserManager: 사용자 계정을 생성시 필요한 메서드를 포함하는 사용자 정의 매니저 클래스
class CustomUserManager(BaseUserManager):
    #일반 사용자 생성
    def create_user(self, id, password=None, **extra_fields):
        if not id:
            raise ValueError("The ID field must be set")
        if not password:
            raise ValueError("The password field must be set")

        user = self.model(id=id, **extra_fields)
        user.set_password(password) #비밀번호를 해싱
        user.save(using=self._db) #DB에 저장
        return user

    #관리자 계정 생성
    def create_superuser(self, id, password=None, **extra_fields):
        #강제로 관리자, 슈퍼유저 권한 부여
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        #create_user 메서드를 호출해 슈퍼유저 생성
        return self.create_user(id, password, **extra_fields)


# CustomUser 모델 정의:  장고의 기본 사용자 모델을 확장(AbstractUser 상속)해 새로운 사용자 모델을 정의
class CustomUser(AbstractUser):
    username = None  # username 필드 제거
    id = models.CharField(max_length=50, unique=True, primary_key=True)  # 고유 ID 필드 추가
    #pw는 이미 abstractuser 상속받아서 필요없음

    # 필요 없는 필드 제거
    first_name = None
    last_name = None

    email = None
    #CustomUser.objects.create_user()/create_superuser()와 같은 방법으로 매니저를 호출하여 사용자를 생성
    objects = CustomUserManager()

    #id 필드를 기준으로 사용자를 찾고, 사용자가 입력한 id와 password가 데이터베이스에 저장된 값과 일치할 때 로그인
    USERNAME_FIELD = 'id'  # 로그인에 사용할 필드
    REQUIRED_FIELDS = []  # 슈퍼유저를 생성할 때 추가로 요구되는 필드: 현재는 비워둠

    #CustomUser 객체를 문자열로 변환할 때, 해당 객체의 id 값을 반환
    def __str__(self):
        return self.id
