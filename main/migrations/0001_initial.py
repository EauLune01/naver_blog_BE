# Generated by Django 5.1 on 2025-02-23 09:17

import django.db.models.deletion
import django.utils.timezone
import main.models.post
import main.models.profile
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False, unique=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='카테고리명')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categories', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(choices=[('주제 선택 안 함', '주제 선택 안 함'), ('문학·책', '문학·책'), ('영화', '영화'), ('미술·디자인', '미술·디자인'), ('공연·전시', '공연·전시'), ('음악', '음악'), ('드라마', '드라마'), ('스타·연예인', '스타·연예인'), ('만화·애니', '만화·애니'), ('방송', '방송'), ('일상·생각', '일상·생각'), ('육아·결혼', '육아·결혼'), ('반려동물', '반려동물'), ('좋은글·이미지', '좋은글·이미지'), ('패션·미용', '패션·미용'), ('인테리어/DIY', '인테리어/DIY'), ('요리·레시피', '요리·레시피'), ('상품리뷰', '상품리뷰'), ('원예/재배', '원예/재배'), ('게임', '게임'), ('스포츠', '스포츠'), ('사진', '사진'), ('자동차', '자동차'), ('취미', '취미'), ('국내여행', '국내여행'), ('세계여행', '세계여행'), ('맛집', '맛집'), ('IT/컴퓨터', 'IT/컴퓨터'), ('사회/정치', '사회/정치'), ('건강/의학', '건강/의학'), ('비즈니스/경제', '비즈니스/경제'), ('어학/외국어', '어학/외국어'), ('교육/학문', '교육/학문')], default='주제 선택 안 함', max_length=50)),
                ('keyword', models.CharField(choices=[('default', '주제 선택 안 함'), ('엔터테인먼트/예술', '엔터테인먼트/예술'), ('생활/노하우/쇼핑', '생활/노하우/쇼핑'), ('취미/여가/여행', '취미/여가/여행'), ('지식/동향', '지식/동향')], default='default', max_length=50)),
                ('title', models.CharField(max_length=100)),
                ('content', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('draft', '임시 저장'), ('published', '발행')], default='draft', max_length=10)),
                ('visibility', models.CharField(choices=[('everyone', '전체 공개'), ('mutual', '서로 이웃만 공개'), ('me', '나만 보기')], default='everyone', max_length=10)),
                ('like_count', models.PositiveIntegerField(default=0)),
                ('comment_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_read', models.BooleanField(default=False)),
                ('category', models.ForeignKey(default=1, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='posts', to='main.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PostImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to=main.models.post.image_upload_path)),
                ('caption', models.CharField(blank=True, max_length=255, null=True)),
                ('is_representative', models.BooleanField(default=False)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='main.post')),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('blog_name', models.CharField(max_length=20)),
                ('blog_pic', models.ImageField(blank=True, default='default/blog_default.jpg', null=True, upload_to=main.models.profile.blog_pic_upload_path)),
                ('username', models.CharField(default='Unnamed', max_length=15)),
                ('user_pic', models.ImageField(blank=True, default='default/user_default.jpg', null=True, upload_to=main.models.profile.user_pic_upload_path)),
                ('intro', models.CharField(blank=True, help_text='간단한 자기소개를 입력해주세요 (최대 100자)', max_length=100, null=True)),
                ('urlname', models.CharField(max_length=30, unique=True)),
                ('urlname_edit_count', models.PositiveIntegerField(default=0, help_text='urlname 변경 횟수 (0: 변경 가능, 1: 변경 불가)')),
                ('neighbor_visibility', models.BooleanField(default=True, help_text='서로이웃 목록을 공개할지 여부')),
                ('neighbors', models.ManyToManyField(blank=True, to='main.profile')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author_name', models.CharField(max_length=15)),
                ('content', models.TextField()),
                ('is_parent', models.BooleanField(default=True)),
                ('is_private', models.BooleanField(default=False)),
                ('is_post_author', models.BooleanField(default=False)),
                ('like_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_read', models.BooleanField(default=False)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='main.comment')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='main.post')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.profile')),
            ],
            options={
                'verbose_name': 'Comment',
                'verbose_name_plural': 'Comments',
            },
        ),
        migrations.CreateModel(
            name='CommentHeart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_read', models.BooleanField(default=False)),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hearts', to='main.comment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('comment', 'user')},
            },
        ),
        migrations.CreateModel(
            name='Neighbor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('pending', '신청중'), ('accepted', '수락됨'), ('rejected', '거절됨')], default='pending', max_length=20)),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_neighbor_requests', to=settings.AUTH_USER_MODEL)),
                ('to_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_neighbor_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('from_user', 'to_user')},
            },
        ),
        migrations.CreateModel(
            name='Heart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_read', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hearts', to='main.post')),
            ],
            options={
                'unique_together': {('post', 'user')},
            },
        ),
    ]
