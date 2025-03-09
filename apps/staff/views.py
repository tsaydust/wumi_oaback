from django.shortcuts import render
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from apps.oaauth.models import OADepartment, UserStatusChoices
from apps.oaauth.serializers import DepartmentSerializer
from .serializers import AddStaffSerializer, ActiveStaffSerializer, StaffUploadSerializer
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from util import aeser
from django.urls import reverse
from oaback.celery import debug_task
from .tasks import send_mail_task
from django.views import View
from django.http.response import JsonResponse
from urllib import parse
from rest_framework import generics
from rest_framework import exceptions
from apps.oaauth.serializers import UserSerializer
from .paginations import StaffListPagination
from rest_framework import viewsets
from rest_framework import mixins
from datetime import datetime
import json
import pandas as pd
from django.http.response import HttpResponse
from django.db import transaction



OAUser = get_user_model()

aes = aeser.AESCipher(settings.SECRET_KEY)


def send_active_email(request, email):
    token = aes.encrypt(email)
    # /staff/active?token=xxx
    active_path = reverse("staff:active_staff") + "?" + parse.urlencode({"token": token})
    # http://127.0.0.1:8000/staff/active?token=xxx
    active_url = request.build_absolute_uri(active_path)
    # 发送一个链接，让用户点击这个链接后，跳转到激活的页面，才能激活。
    # 为了区分用户，在发送链接邮件中，该链接中应该要包含这个用户的邮箱
    # 针对邮箱要进行加密：AES
    # http://localhost:8000/staff/active?token=4dFLaXTbbzciZKGm0LIafmhOuuW11S+7kEtqdUSeFf4=
    message = f"请点击以下链接激活账号：{active_url}"
    subject = f'账号激活',
    # send_mail(subject, recipient_list=[email], message=message, from_email=settings.DEFAULT_FROM_EMAIL)
    send_mail_task.delay(email, subject, message)


class DepartmentListView(ListAPIView):
    queryset = OADepartment.objects.all()
    serializer_class = DepartmentSerializer


# 激活员工的过程：
# 1. 用户访问激活的链接的时候，会返回一个含有表单的页面，视图中可以获取到token，为了在用户提交表单的时候，post函数中能知道这个token
# 我们可以在返回页面之前，先把token存储在cookie中
# 2. 校验用户上传的邮箱和密码是否正确，并且解密token中的邮箱，与用户提交的邮箱进行对比，如果都相同，那么就是激活成功
class ActiveStaffView(View):
    def get(self, request):
        # 获取token，并把token存储到cookie中，方便下次用户传过来
        # http://127.0.0.1:8000/staff/active?token=6AkzQXz+uIIlV/+I6gXMitowszWkiiDIj9J/XBfctIY=
        token = request.GET.get('token')
        response = render(request, 'active.html')
        response.set_cookie('token', token)
        return response

    def post(self, request):
        # 从cookie中获取token
        try:
            token = request.COOKIES.get('token')
            email = aes.decrypt(token)
            serializer = ActiveStaffSerializer(data=request.POST)
            if serializer.is_valid():
                form_email = serializer.validated_data.get('email')
                user = serializer.validated_data.get('user')
                if email != form_email:
                    return JsonResponse({"code": 400, "message": "邮箱错误！"})
                user.status = UserStatusChoices.ACTIVED
                user.save()
                return JsonResponse({"code": 200, "message": ""})
            else:
                detail = list(serializer.errors.values())[0][0]
                return JsonResponse({"code": 400, "message": detail})
        except Exception as e:
            print(e)
            return JsonResponse({"code": 400, "message": "token错误！"})


# put /staff/staff/<uid>
class StaffViewSet(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin
):
    queryset = OAUser.objects.all()
    pagination_class = StaffListPagination

    def get_serializer_class(self):
        if self.request.method in ['GET', 'PUT']:
            return UserSerializer
        else:
            return AddStaffSerializer

    # 获取员工列表
    def get_queryset(self):
        department_id = self.request.query_params.get('department_id')
        realname = self.request.query_params.get('realname')
        date_joined = self.request.query_params.getlist('date_joined[]')

        queryset = self.queryset
        # 返回员工列表逻辑：
        # 1. 如果是董事会的，那么返回所有员工
        # 2. 如果不是董事会的，但是是部门的leader，那么就返回部门的员工
        # 3. 如果不是董事会的，也不是部门leader，那么就抛出403 Forbidden错误
        user = self.request.user
        if user.department.name != '董事会':
            if user.uid != user.department.leader.uid:
                raise exceptions.PermissionDenied()
            else:
                queryset = queryset.filter(department_id=user.department_id)
        else:
            # 董事会中，根据部门id进行过滤
            if department_id:
                queryset = queryset.filter(department_id=department_id)

        if realname:
            queryset = queryset.filter(realname__icontains=realname)
        if date_joined:
            # ['2024-10-01', '2024-10-10']
            try:
                start_date = datetime.strptime(date_joined[0], "%Y-%m-%d")
                end_date = datetime.strptime(date_joined[1], "%Y-%m-%d")
                queryset = queryset.filter(date_joined__range=(start_date, end_date))
            except Exception:
                pass
        return queryset.order_by("-date_joined").all()

    # 新增员工
    def create(self, request, *args, **kwargs):
        # 如果用的是视图集，那么视图集会自动把request放到context中
        # 如果是直接继承自APIView，那么就需要手动将request对象传给serializer.context中
        serializer = AddStaffSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            realname = serializer.validated_data['realname']
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            # 1. 保存用户数据
            user = OAUser.objects.create_user(email=email, realname=realname, password=password)
            department = request.user.department
            user.department = department
            user.save()

            # 2. 发送激活邮件 I/O：网络请求、文件读写
            send_active_email(request, email)

            return Response()
        else:
            return Response(data={'detail': list(serializer.errors.values())[0][0]}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)




class StaffDownloadView(APIView):
    def get(self, request):
        # /staff/download?pks=[x,y]
        # ['x','y'] -> json格式的字符串
        pks = request.query_params.get('pks')
        try:
            pks = json.loads(pks)
        except Exception:
            return Response({"detail": "员工参数错误！"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            current_user = request.user
            queryset = OAUser.objects
            if current_user.department.name != '董事会':
                if current_user.department.leader_id != current_user.uid:
                    return Response({'detail': "没有权限下载！"}, status=status.HTTP_403_FORBIDDEN)
                else:
                    # 如果是部门的leader，那么就先过滤为本部门的员工
                    queryset = queryset.filter(department_id=current_user.department_id)
            queryset = queryset.filter(pk__in=pks)
            result = queryset.values("realname", "email", "department__name", 'date_joined', 'status')
            staff_df = pd.DataFrame(list(result))
            staff_df = staff_df.rename(
                columns={"realname": "姓名", "email": '邮箱', 'department__name': '部门', "date_joined": '入职日期',
                         'status': '状态'})
            response = HttpResponse(content_type='application/xlsx')
            response['Content-Disposition'] = "attachment; filename=员工信息.xlsx"
            # 把staff_df写入到Response中
            with pd.ExcelWriter(response) as writer:
                staff_df.to_excel(writer, sheet_name='员工信息')
            return response
        except Exception as e:
            print(e)
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StaffUploadView(APIView):
    def post(self, request):
        serializer = StaffUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data.get('file')
            current_user = request.user
            if current_user.department.name != '董事会' or current_user.department.leader_id != current_user.uid:
                return Response({"detail": "您没有权限访问！"}, status=status.HTTP_403_FORBIDDEN)

            staff_df = pd.read_excel(file)
            users = []
            for index, row in staff_df.iterrows():
                # 获取部门
                if current_user.department.name != '董事会':
                    department = current_user.department
                else:
                    try:
                        department = OADepartment.objects.filter(name=row['部门']).first()
                        if not department:
                            return Response({"detail": f"{row['部门']}不存在！"}, status=status.HTTP_400_BAD_REQUEST)
                    except Exception as e:
                        return Response({"detail": "部门列不存在！"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    email = row['邮箱']
                    realname = row['姓名']
                    password = "111111"
                    user = OAUser(email=email, realname=realname, department=department, status=UserStatusChoices.UNACTIVE)
                    user.set_password(password)
                    users.append(user)
                except Exception:
                    return Response({"detail": "请检查文件中邮箱、姓名、部门名称！"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                # 原子操作（事务）
                with transaction.atomic():
                    # 统一把数据添加到数据库中
                    OAUser.objects.bulk_create(users)
            except Exception:
                return Response({"detail": "员工数据添加错误！"}, status=status.HTTP_400_BAD_REQUEST)

            # 异步给每个新增的员工发送邮件
            for user in users:
                send_active_email(request, user.email)
            return Response()
        else:
            detail = list(serializer.errors.values())[0][0]
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

class TestCeleryView(APIView):
    def get(self, request):
        # 用celery异步执行debug_task这个任务
        debug_task.delay()
        return Response({"detail": "成功！"})
