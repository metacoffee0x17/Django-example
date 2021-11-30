from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .models import VideoPost
from functools import reduce
from django.db.models import Q
import operator
import json


# Create your views here.

def filter_by_tag(request):
  tag = request.GET.get('tag', None)
  count = int(request.GET.get('count', None))
  queryset = VideoPost.objects.all().order_by('-published_date')
  tag = json.loads(tag)
  if tag[0] != 'All':
    queryset = VideoPost.objects.filter(reduce(operator.or_, (Q(tag__contains=x) for x in tag))).order_by('-published_date')
  result = [{'link': x.embedded_link, 'title': x.title, 'id': x.id} for x in queryset]
  data = {'videos': json.dumps(result[:count])}
  return JsonResponse(data)
def get_content_by_id(request):
  id = request.GET.get('id', None)
  queryset = VideoPost.objects.get(pk=id)
  data = {'title': queryset.title, 'link': queryset.embedded_link, 'description': queryset.description}
  return JsonResponse(data)