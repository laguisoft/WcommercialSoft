from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def compte_non_rattache(request):
    return render(request, 'tenants/compte_non_rattache.html')
