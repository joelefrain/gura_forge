import os
import math
from config.config import KM_TO_GEODESIC_GRADES


def is_file(path):
    """Verifica si una ruta es un archivo. Si no existe, lo crea."""
    if os.path.isfile(path):
        return True
    elif not os.path.exists(path):  # Si la ruta no existe, crea el archivo
        with open(path, "w") as f:
            pass
        return True
    return False


def is_dir(path):
    """Verifica si una ruta es un directorio. Si no existe, lo crea."""
    if os.path.isdir(path):
        return True
    elif not os.path.exists(path):  # Si la ruta no existe, crea el directorio
        os.makedirs(path)
        return True
    return False


def crop_image(image_path):
    from PIL import Image

    # Abrir la imagen
    img = Image.open(image_path)

    # Convertir a formato RGBA (si no lo está)
    img = img.convert("RGBA")

    # Obtener los píxeles de la imagen
    pixdata = img.load()

    # Obtener el tamaño de la imagen
    ancho, alto = img.size

    # Determinar los límites del área no blanca
    left, top, right, bottom = ancho, alto, 0, 0
    for y in range(alto):
        for x in range(ancho):
            r, g, b, a = pixdata[x, y]
            if (r, g, b) != (255, 255, 255):  # Si el píxel no es blanco
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    # Recortar la imagen
    cropped_img = img.crop((left, top, right + 1, bottom + 1))

    # Guardar la imagen recortada
    cropped_img.save(image_path)


def create_circle(center, radius, num_points=100):
    """
    Crea un círculo como una aproximación con num_points vértices.
    """

    from shapely.geometry import Point
    from shapely.geometry import Polygon

    lon, lat = center
    points = [
        (
            lon
            + (radius / KM_TO_GEODESIC_GRADES) * math.cos(2 * math.pi * i / num_points),
            lat
            + (radius / KM_TO_GEODESIC_GRADES) * math.sin(2 * math.pi * i / num_points),
        )
        for i in range(num_points)
    ]
    return Polygon(points)


def calc_extent(latitude, longitude, side_length=400):
    """
    Calcula los límites de un área rectangular en grados basado en un mapa cuadrado de lado dado en kilómetros.

    Args:
        latitude (float): Latitud central en grados.
        longitude (float): Longitud central en grados.
        side_length (float): Lado del cuadrado del mapa en kilómetros. Por defecto, 400 km.

    Returns:
        list: Extensión [min_longitude, max_longitude, min_latitude, max_latitude].
    """
    # 1 grado de latitud ≈ 111 km
    lat_per_degree = KM_TO_GEODESIC_GRADES  # km
    lon_per_degree = KM_TO_GEODESIC_GRADES * math.cos(math.radians(latitude))  # km

    # Calcular la mitad del lado en kilómetros
    half_side_km = side_length / 2

    # Calcular los límites en grados
    min_longitude = longitude - (half_side_km / lon_per_degree)
    max_longitude = longitude + (half_side_km / lon_per_degree)
    min_latitude = latitude - (half_side_km / lat_per_degree)
    max_latitude = latitude + (half_side_km / lat_per_degree)

    # Retornar el array 'extent'
    return [min_longitude, max_longitude, min_latitude, max_latitude]
