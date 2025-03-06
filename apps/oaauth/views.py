from rest_framework import status
from .serializers import LoginSerializer, UserSerializer, ResetPwdSerializer
from datetime import datetime
from .authentications import generate_jwt
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data.get('user')
            user.last_login = datetime.now()
            user.save()
            token = generate_jwt(user)
            return Response({'token': token, 'user': UserSerializer(user).data})
        else:
            # print(serializer.errors)
            # 字典的value是个dict_value对象需转化成list才能取下标x
            # print(list(serializer.errors.values())[0][0])
            detail = list(serializer.errors.values())[0][0]
            # drf在返回非200的时候，错误参数是detail
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)


# class AuthenticatedRequiredView:
#     permission_classes = [IsAuthenticated]


class ResetPwdView(APIView):
    # request：是DRF封装的，rest_framework.request.Request
    # 这个对象是针对django的HttpRequest对象进行了封装
    # permission_classes = [IsAuthenticated]
    def post(self, request):
        # print(request)
        # print(request.user)
        serializer = ResetPwdSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            pwd1 = serializer.validated_data.get('pwd1')
            request.user.set_password(pwd1)
            request.user.save()
            return Response()
        else:
            print(serializer.errors)
            detail = list(serializer.errors.values())[0][0]
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
