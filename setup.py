#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pkgversion import list_requirements, pep440_version
from setuptools import setup, find_packages

setup(
    name='django-etcd-settings',
    version=pep440_version(),
    description="A dynamic settings management solution for django using ETCD",
    long_description=open('README.md').read(),
    author="Enrique Paz",
    author_email='quiquepaz@gmail.com',
    url='https://stash.kpnnl.local/DE/django-etcd-settings',
    install_requires=list_requirements('requirements/requirements-base.txt'),
    packages=find_packages(exclude=['etcd_settings.tests*']),
    tests_require=['tox'],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
