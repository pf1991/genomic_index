from django.shortcuts import render
import requests
from django.conf import settings
import time

from django.http import Http404, HttpResponse, HttpResponseRedirect

def index(request):

    if request.POST:
        start = time.time()
        r = requests.get(settings.INDEX_URL + '?search=' + request.POST['term']).json()
        # print(r)
        data = {'result': r, 'term': request.POST['term'], 'time': time.time() - start}
        return render(request, 'search.html', data) 
    else:
	    return render(request, 'search.html')
