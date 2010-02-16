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

Known Issues
 * Many to Many fields don't automatically record changes. Adjustments have been made in the admin model to compensate for this. However, changes done outside the admin that are not adjusted may exhibit a delayed recording. (Django Ticket #5390)
 * Files are not preserved, just their path.
 * (Django 1.0 only) The FullHistory field does not work as expected with Non-abstract model inheritence, primarly for objects the have inherited another's FullHistory field (Django Ticket #9546)
 * FullHistory truncates microseconds for DateTimeFields
 * DateTimeFields are deserialized as strings
 * Model proxies is inefficient, likely to create duplicate history entries. Will be fixed.

Notes
 * Records for models that use Non-abstract inheritence are stored seperately per table. This has to do with the current implementation of serialization in Django. Also parent tables are capable of being independently modified of their inherited children.
 * Fullhistory for Non-abstract Model inheritence is slightly less performant as it follows the parental field.
 * QuerySet methods delete() and update() do not trigger signals and thus are outside of fullhistory
 * FullHistory Admin functionality is limited in Django 1.0


