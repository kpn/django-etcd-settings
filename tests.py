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
        ENV='dev',
        REQUEST_GETTER_MODULE=None,
        ETCD_CONFIG_PREFIX='/config/my-django-app',
        # ETCD_DETAILS=dict(host='localhost', port=4000, protocol='http')
        ETCD_DETAILS=None
    )
    if hasattr(django, 'setup'):
        django.setup()

    try:
        from django.test.runner import DiscoverRunner as Runner
    except ImportError:
        from django.test.simple import DjangoTestSuiteRunner as Runner

    test_runner = Runner(verbosity=1)
    return test_runner.run_tests(['etcd_settings'])


def main():
    failures = run_tests()
    sys.exit(failures)

if __name__ == '__main__':
    main()
