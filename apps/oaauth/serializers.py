from rest_framework import serializers,exceptions
from .models import OAUser, UserStatusChoices,OADepartment


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True,error_messages={"required":"请输入邮箱！"})
    password = serializers.CharField(max_length=20, min_length=6)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = OAUser.objects.filter(email=email).first()
            if not user:
                raise serializers.ValidationError('不存在该邮箱')
            if not user.check_password(password):
                raise serializers.ValidationError('密码错误')
            if user.status == UserStatusChoices.UNACTIVE:
                raise serializers.ValidationError('账户未激活')
            if user.status == UserStatusChoices.LOCKED:
                raise serializers.ValidationError('账户被锁定')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('请传入邮箱和密码')
        return attrs

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OADepartment
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer()
    class Meta:
        model = OAUser
        # fields = '__all__'
        exclude = ('password', 'groups', 'user_permissions')

class ResetPwdSerializer(serializers.Serializer):
    oldpwd = serializers.CharField(min_length=6,max_length=20)
    pwd1 = serializers.CharField(min_length=6,max_length=20)
    pwd2 = serializers.CharField(min_length=6,max_length=20)

    def validate(self, attrs):
        oldpwd = attrs.get('oldpwd')
        pwd1 = attrs.get('pwd1')
        pwd2 = attrs.get('pwd2')

        user = self.context['request'].user
        if not user.check_password(oldpwd):
            raise exceptions.ValidationError("旧密码错误")
        if pwd1 != pwd2:
            raise exceptions.ValidationError("两个新密码不一致")
        return attrs

