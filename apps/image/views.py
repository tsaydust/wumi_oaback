from rest_framework.views import APIView
from .serializers import UploadedImageSerializer
from rest_framework.response import Response
from shortuuid import uuid
import os
from django.conf import settings


class UploadImageView(APIView):
    def post(self, request):
        serializer = UploadedImageSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data.get('image')
            filename = uuid() + os.path.splitext(file.name)[1]
            path = settings.MEDIA_ROOT / filename
            try:
                with open(path, 'wb') as fp:
                    for chunk in file.chunks():
                        fp.write(chunk)
            except Exception:
                return Response({
                    "errno": 1,
                    "message": "图片保存失败"
                })
            file_url = '/media/' + filename
            return Response({
                "errno": 0,
                "data": {
                    "url": file_url,
                    "alt": "",
                    "href": file_url
                }
            })

        else:
            print(serializer.errors)
            return Response({
                "errno": 1,  # 只要不等于 0 就行
                "message": list(serializer.errors.values())[0][0]
            })
