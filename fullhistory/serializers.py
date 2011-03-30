from django.core.serializers.python import Serializer as BaseSerializer, Deserializer
from django.utils.encoding import smart_unicode

class Serializer(BaseSerializer):
    def handle_fk_field(self, obj, field):
        self._current[field.name] = smart_unicode(field._get_val_from_obj(obj), strings_only=True)
