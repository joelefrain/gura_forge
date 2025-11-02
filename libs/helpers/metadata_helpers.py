import pandas as pd

from tabulate import tabulate


def style_output(result):
    """Aplica formato tabulado y lo muestra directamente."""
    if isinstance(result, pd.DataFrame):
        formatted_result = tabulate(
            result, headers="keys", tablefmt="pretty", showindex=False
        )
    else:
        formatted_result = str(result)
    print(formatted_result)


def style_metadata_property(func):
    """Decorador para aplicar estilo automáticamente a propiedades."""

    def wrapper(self):
        result = func(self)
        return style_output(result)

    return property(wrapper)


def valid_attr(obj):
    """Devuelve una lista de atributos válidos basados en las propiedades definidas en la clase."""
    return [
        attr
        for attr in dir(obj)
        if isinstance(getattr(obj.__class__, attr, None), property)
    ]


def style_metadata(func):
    """Decorador general para funciones que devuelven DataFrames o resultados simples."""

    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        return style_output(result)

    return wrapper


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
