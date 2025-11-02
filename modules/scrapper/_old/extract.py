from datetime import datetime
from modules.scrapper.usgs.usgs_extract import query_usgs_data, download_usgs_data
from modules.scrapper.isc.isc_extract import query_isc_data, download_isc_data
from modules.scrapper.igp.igp_extract import query_igp_data, download_igp_data

from libs.config.config_logger import get_logger

logger = get_logger()


def extract_yearly_data(query_params, start_year, end_year, catalog_name, query_func, save_func, seismic_catalog_path):
    for year in range(start_year, end_year + 1):
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        # Actualizar los parámetros de la consulta con las fechas
        query_params["start_date"] = start_date
        query_params["end_date"] = end_date

        try:
            # Ejecutar la consulta
            if catalog_name == "usgs":
                data = query_func(
                    query_params["min_lat"], query_params["max_lat"],
                    query_params["min_lon"], query_params["max_lon"],
                    query_params["start_date"], query_params["end_date"]
                )
                csv_file = f"{seismic_catalog_path}/raw/{catalog_name}/{catalog_name}_{year}.csv"
                save_func(data, csv_file)

            elif catalog_name == "isc":
                isc_url = query_func(
                    query_params["min_lat"], query_params["max_lat"],
                    query_params["min_lon"], query_params["max_lon"],
                    query_params["start_date"], query_params["end_date"]
                )
                csv_file = f"{seismic_catalog_path}/raw/{catalog_name}/{catalog_name}_{year}.csv"
                save_func(isc_url, csv_file)

            elif catalog_name == "igp":
                data = query_func(year)
                csv_file = f"{seismic_catalog_path}/raw/{catalog_name}/{catalog_name}_{year}.csv"
                save_func(data, csv_file)

            logger.info(f"Archivo CSV guardado en: {csv_file}")

        except Exception as e:
            logger.error(
                f"Error procesando datos para {catalog_name} en el anho {year}: {e}")
            continue  # Continuar con el siguiente año


def extract(min_lat, max_lat, min_lon, max_lon, start_year, seismic_catalog_path):

    # Definir los límites espaciales
    query_params = {
        "min_lat": min_lat,
        "max_lat": max_lat,
        "min_lon": min_lon,
        "max_lon": max_lon,
    }

    # Rango de años para la consulta
    end_year = datetime.today().year

    # Procesar datos anuales para USGS
    extract_yearly_data(
        query_params, start_year, end_year,
        catalog_name="usgs",
        query_func=query_usgs_data,
        save_func=download_usgs_data,
        seismic_catalog_path=seismic_catalog_path
    )

    # Procesar datos anuales para ISC
    extract_yearly_data(
        query_params, start_year, end_year,
        catalog_name="isc",
        query_func=query_isc_data,
        save_func=download_isc_data,
        seismic_catalog_path=seismic_catalog_path
    )

    # Procesar datos anuales para IGP
    extract_yearly_data(
        query_params, start_year, end_year,
        catalog_name="igp",
        query_func=query_igp_data,
        save_func=download_igp_data,
        seismic_catalog_path=seismic_catalog_path
    )
