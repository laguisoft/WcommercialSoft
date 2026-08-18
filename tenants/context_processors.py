def current_entreprise(request):
    return {'current_entreprise': getattr(request, 'entreprise', None)}
