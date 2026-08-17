from typing import Any, Optional

from django import template

register = template.Library()


@register.filter
def get_item(dictionary: dict, key: Any) -> Optional[Any]:
    """Accede a un valor de un diccionario por su clave desde una plantilla."""
    return dictionary.get(key)