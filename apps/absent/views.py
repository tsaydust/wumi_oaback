from django.shortcuts import render
from rest_framework import viewsets, mixins
from .models import AbsentType, Absent, AbsentStatusChoices
from .serializers import AbsentSerializer, AbsentTypeSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from .utils import get_responder
from  apps.oaauth.serializers import UserSerializer

class AbsentViewSet(mixins.CreateModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.DestroyModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = Absent.objects.all()
    serializer_class = AbsentSerializer

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        who = request.query_params.get('who')
        if who and who == 'sub':
            result = queryset.filter(responder=request.user)
        else:
            result = queryset.filter(requester=request.user)
        #result代表符合要求的数据
        page = self.paginate_queryset(result)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            #get_paginated_response除了返回序列化的数据，还会返回总数居多少上一页url
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(result, many=True)
        return Response(data=serializer.data)


class AbsentTypeView(APIView):
    def get(self, request):
        types = AbsentType.objects.all()
        serializer = AbsentTypeSerializer(types, many=True)
        return Response(data=serializer.data)

class ResponderView(APIView):
    def get(self, request):
        user = request.user
        responder = get_responder(request)
        serializer = UserSerializer(responder)
        return Response(data=serializer.data)