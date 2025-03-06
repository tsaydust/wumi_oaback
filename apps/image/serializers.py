from rest_framework import serializers
from django.core.validators import FileExtensionValidator


class UploadedImageSerializer(serializers.Serializer):
    # ImageField会检测是否为图片
    image = serializers.ImageField(
        validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg', 'gif'])],
        error_messages={'require': '请上传图片！', 'invalid_image': '请上传正确格式的图片'}
    )

    def validate_image(self, value):
        max_size = 0.5 * 1024 * 1024
        size = value.size
        if size > max_size:
            raise serializers.ValidationError('图片最大不能超过0.5mb')
        return value

