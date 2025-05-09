from lib.tools.styles import style_metadata


def valid_attr(obj):
    """Devuelve una lista de atributos válidos basados en las propiedades definidas en la clase."""
    return [attr for attr in dir(obj) if isinstance(getattr(obj.__class__, attr, None), property)]


@style_metadata
def get_info(obj, value):
    """Devuelve información solicitada según el valor especificado."""
    valid_attributes = valid_attr(obj)
    if value in valid_attributes:
        return getattr(obj, value)
    else:
        raise ValueError(
            f"Atributo no válido: '{value}'. Debe ser uno de los siguientes: {', '.join(valid_attributes)}."
        )
