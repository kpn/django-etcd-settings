import django
from django.conf import global_settings, settings

settings.configure(
    # Minimal django settings
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'unittest.sqlite',
            'TEST_NAME': ':memory:',
        },
    },
    MIDDLEWARE_CLASSES=global_settings.MIDDLEWARE_CLASSES,
    ROOT_URLCONF=None,
    INSTALLED_APPS=['etcd_settings'],
    DJES_DEV_PARAMS=None,
    DJES_REQUEST_GETTER=None,
    DJES_ENV='dev',
    DJES_ETCD_DETAILS=None,
    DJES_WSGI_FILE=None
    # DJES_ETCD_DETAILS=dict(host='localhost', port=4000, protocol='http',
    #                        prefix='/config/my-django-app')
)
if hasattr(django, 'setup'):
    django.setup()
