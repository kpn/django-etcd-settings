from distutils.core import setup
setup(
    name='etcd_settings',
    packages=['etcd_settings'],
    version='0.0',
    description='A dynamic settings management solution for django using ETCD',
    author='Enrique Paz',
    author_email='enrique.pazperez@kpn.com',
    url='https://stash.kpnnl.local/projects/DE/repos/django-etcd-settings',
    download_url='',  # FIXME Add a publicly accessible URL here
    keywords=['django', 'etcd', 'config', 'settings'],
    classifiers=[],
    install_requires=[
        'python-etcd>=0.4.1',
        'Django>=1.7.5',
        'python-dateutil>=2.2'
    ],
    test_requires=[
        'mock==1.3.0',
        'bpython>=0.14.0'
    ]
)
