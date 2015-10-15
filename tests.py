import sys


def run_tests():
    import django
    from django.conf import settings, global_settings
    settings.configure(
        # Minimal django settings
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'TEST_NAME': ':memory:',
            },
        },
        MIDDLEWARE_CLASSES=global_settings.MIDDLEWARE_CLASSES,
        INSTALLED_APPS=['etcd_settings'],
        DJES_DEV_PARAMS=None,
        DJES_REQUEST_GETTER_MODULE=None,
        DJES_ENV='dev',
        DJES_ETCD_DETAILS=None
        # DJES_ETCD_DETAILS=dict(host='localhost', port=4000, protocol='http',
        #                        prefix='/config/my-django-app')
    )
    if hasattr(django, 'setup'):
        django.setup()

    try:
        from django.test.runner import DiscoverRunner as Runner
    except ImportError:
        from django.test.simple import DjangoTestSuiteRunner as Runner

    test_runner = Runner(verbosity=1)
    return test_runner.run_tests(['tests'])


def main():
    failures = run_tests()
    sys.exit(failures)

if __name__ == '__main__':
    main()
