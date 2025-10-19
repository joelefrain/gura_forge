import os
import json
import pyproj

import pandas as pd
import geopandas as gpd

from shapely.ops import transform
from shapely.geometry import Point


class FaultIdentifier:
    base_path = os.path.dirname(os.path.abspath(__file__))
    json_source = "data/data.json"

    def __init__(self, shapefile, author=None, map_name=None, rev_date=None):
        """
        Inicializar con la ruta del shapefile y cargarlo en un GeoDataFrame.

        Parameters:
            shapefile (str): Ruta del archivo shapefile.
            author (str): Autor de los datos (opcional).
            map_name (str): Nombre del mapa (opcional).
            rev_date (str): Fecha de revisión de los datos (opcional).
        """
        self.map_gdf = gpd.read_file(shapefile)

        # Asegurarse que el CRS sea WGS 84
        if self.map_gdf.crs != "EPSG:4326":
            self.map_gdf = self.map_gdf.to_crs(epsg=4326)

        # Definir sistemas de coordenadas
        self.wgs84 = pyproj.CRS("EPSG:4326")  # Coordenadas geográficas
        self.local_crs = pyproj.CRS("EPSG:3857")  # Coordenadas proyectadas en metros

        # Crear transformaciones
        self.project_to_meters = pyproj.Transformer.from_crs(
            self.wgs84, self.local_crs, always_xy=True
        ).transform
        self.project_to_wgs84 = pyproj.Transformer.from_crs(
            self.local_crs, self.wgs84, always_xy=True
        ).transform

        # Metadatos
        self.author = author
        self.map_name = map_name
        self.rev_date = rev_date

        # Coordenadas y radio
        self._circle_params = None

    @classmethod
    def known_shp(cls, key, json_data=None):
        """
        Inicializar una instancia de FaultIdentifier a partir de un JSON.

        Parameters:
            key (str): Clave para acceder a los datos en el JSON.
            json_data (dict): Diccionario con los datos necesarios para la inicialización (opcional).

        Returns:
            FaultIdentifier: Instancia inicializada de la clase.
        """
        # Construir ruta del archivo de datos JSON
        json_path = os.path.join(cls.base_path, cls.json_source)

        # Si no se pasa json_data, cargarlo desde la fuente
        if json_data is None:
            with open(json_path, "r", encoding="utf-8") as file:
                json_data = json.load(file)

        # Extraer los valores del JSON usando la clave
        data = json_data[key]

        # Construir ruta del archivo de datos SHP
        shp_path = os.path.join(cls.base_path, data.get("shapefile"))

        # Inicializar la clase con los valores del JSON
        return cls(
            shapefile=shp_path,
            author=data.get("author"),
            map_name=data.get("map_name"),
            rev_date=data.get("rev_date"),
        )

    def create_circle(self, longitude, latitude, radius, resolution=100):
        """Crear un polígono circular con un centro y un radio en kilómetros."""
        # Guardar los parámetros del círculo
        self._circle_params = (longitude, latitude, radius)

        # Crear el punto central en la proyección original
        center = Point(longitude, latitude)
        center_m = transform(self.project_to_meters, center)

        # Crear el círculo en la proyección métrica
        circle_m = center_m.buffer(
            radius * 1000, resolution=resolution
        )  # Radio de km a metros
        circle_wgs84 = transform(self.project_to_wgs84, circle_m)

        return circle_wgs84

    def within(self, longitude, latitude, radius):
        """Encuentra geometrías que intersectan un círculo en el GeoDataFrame."""
        circle = self.create_circle(longitude, latitude, radius)

        # Filtrar geometrías que intersectan con el círculo
        faults_in = self.map_gdf[self.map_gdf.geometry.intersects(circle)]
        return faults_in if not faults_in.empty else gpd.GeoDataFrame()

    def get_faults(self, faults_gdf, name_id, agg_dict):
        """
        Resumen de fallas basado en el nombre, con agregación personalizada.

        Parameters:
            faults_gdf (GeoDataFrame): GeoDataFrame de fallas.
            name_id (str): Nombre de la columna para agrupar.
            agg_dict (dict): Diccionario donde las claves son los nombres de las columnas a agregar y
                             los valores son las funciones de agregación a aplicar (p. ej., 'sum', 'first').

        Returns:
            pandas.DataFrame: DataFrame con las columnas agregadas y las funciones aplicadas.
        """
        if not isinstance(agg_dict, dict):
            raise ValueError("El argumento agg_dict debe ser un diccionario.")

        # Realizar la agrupación y aplicar el diccionario de agregación
        faults_df = faults_gdf.groupby(name_id, as_index=False).agg(agg_dict)
        return faults_df

    @property
    def circle_params(self):
        """Devuelve un DataFrame con las columnas 'longitude', 'latitude' y 'radius' del círculo si ha sido definido."""
        if self._circle_params is not None:
            df = pd.DataFrame(
                [self._circle_params], columns=["Longitude", "Latitude", "Radius"]
            )
            return df
        else:
            raise AttributeError("El círculo no ha sido creado aún.")

    @property
    def columns_shp(self):
        """Devuelve un DataFrame con las columnas del GeoDataFrame y sus tipos de datos."""
        return pd.DataFrame(
            {"Column Name": self.map_gdf.columns, "Data Type": self.map_gdf.dtypes}
        )

    @property
    def metadata(self):
        """Devuelve un DataFrame con los metadatos."""
        return pd.DataFrame(
            {
                "Field": ["Author", "Map Name", "Revision Date", "CRS"],
                "Value": [
                    self.author or "No disponible",
                    self.map_name or "No disponible",
                    self.rev_date or "No disponible",
                    self.map_gdf.crs.to_string(),
                ],
            }
        )
