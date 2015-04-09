#!/usr/bin/env python
import os
import sys

from django.conf import settings
from django.core.management import execute_from_command_line


DATABASE_ENGINE = os.environ.get('DATABASE_ENGINE', None)

if DATABASE_ENGINE:
    DATABASES = {
        'default': {
            'ENGINE': DATABASE_ENGINE,
            'NAME': 'modelcluster',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        }
    }


if not settings.configured:
    settings.configure(
        DATABASES=DATABASES,
        INSTALLED_APPS=[
            'modelcluster',

            'django.contrib.contenttypes',
            'taggit',

            'tests',
        ],
        MIDDLEWARE_CLASSES = (
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ),
        USE_TZ=True,
        TIME_ZONE='America/Chicago',
    )


def runtests():
    argv = sys.argv[:1] + ['test'] + sys.argv[1:]
    execute_from_command_line(argv)


if __name__ == '__main__':
    runtests()

