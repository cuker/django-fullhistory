To install:

sudo setup.py install

*add fullhistory middleware

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'fullhistory.fullhistory.FullHistoryMiddleware',
)

* add fullhistory to installed apps:

INSTALLED_APPS = (
    'fullhistory',
)

* In your models.py, select the models you want to have fullhistory:

from fullhistory import register_model
register_model(SKU)
register_model(Order)
register_model(OrderItem)
