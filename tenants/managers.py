import threading

from django.db import models

_thread_locals = threading.local()


def set_current_entreprise(entreprise):
    _thread_locals.entreprise = entreprise


def get_current_entreprise():
    return getattr(_thread_locals, 'entreprise', None)


def clear_current_entreprise():
    _thread_locals.entreprise = None


class TenantManager(models.Manager):
    """Filtre automatiquement sur l'entreprise courante (thread-local).

    Sans entreprise courante (management commands, migrations, superuser
    non rattaché), le queryset reste non filtré.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        entreprise = get_current_entreprise()
        if entreprise is not None:
            qs = qs.filter(entreprise=entreprise)
        return qs

    def create(self, **kwargs):
        if 'entreprise' not in kwargs:
            entreprise = get_current_entreprise()
            if entreprise is not None:
                kwargs['entreprise'] = entreprise
        return super().create(**kwargs)

    def get_or_create(self, defaults=None, **kwargs):
        # Django route get_or_create()/update_or_create() vers le create()
        # du QuerySet (pas celui, surcharge ci-dessus, du Manager) : sans ce
        # rappel explicite, l'entreprise courante ne serait pas injectee et
        # l'insertion echouerait (entreprise_id NOT NULL) des qu'un appelant
        # omet 'entreprise' en comptant sur ce filet de securite.
        if 'entreprise' not in kwargs:
            entreprise = get_current_entreprise()
            if entreprise is not None:
                kwargs['entreprise'] = entreprise
        return super().get_or_create(defaults=defaults, **kwargs)

    def update_or_create(self, defaults=None, **kwargs):
        if 'entreprise' not in kwargs:
            entreprise = get_current_entreprise()
            if entreprise is not None:
                kwargs['entreprise'] = entreprise
        return super().update_or_create(defaults=defaults, **kwargs)
