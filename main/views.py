from django.http import HttpResponse

def home(request):
    return HttpResponse("Здравствуйте, daszv мир!")