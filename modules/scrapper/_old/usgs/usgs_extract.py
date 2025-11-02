import csv
import requests

from libs.config.config_logger import get_logger

logger = get_logger()

def query_usgs_data(min_lat, max_lat, min_lon, max_lon, start_date, end_date, min_depth=None, max_depth=None, min_magnitude=None, max_magnitude=None, eventtype=None):
    try:
        # Construcción de la URL de consulta
        url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        params = {
            "format": "geojson",
            "minlatitude": min_lat,
            "maxlatitude": max_lat,
            "minlongitude": min_lon,
            "maxlongitude": max_lon,
            "starttime": start_date,
            "endtime": end_date,
        }
        
        if eventtype is not None:
            params["eventtype"] = "earthquake"
        if min_depth is not None:
            params["mindepth"] = min_depth
        if max_depth is not None:
            params["maxdepth"] = max_depth
        if min_magnitude is not None:
            params["minmagnitude"] = min_magnitude
        if max_magnitude is not None:
            params["maxmagnitude"] = max_magnitude

        response = requests.get(url, params=params)
        response.raise_for_status()  # Verifica si hubo un error en la solicitud HTTP
        data = response.json()
        return data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al realizar la solicitud: {e}")
        return None

def download_usgs_data(data, output_file):
    if data is None:
        logger.warning("No hay datos disponibles para guardar en CSV.")
        return

    # Definir los nombres de las columnas del CSV según las propiedades especificadas
    fieldnames = [
        "alert", "cdi", "code", "depth", "depthError", "detail", "dmin", 
        "felt", "gap", "horizontalError", "id", "ids", "latitude", 
        "locationSource", "longitude", "mag", "magError", "magNst", 
        "magSource", "magType", "mmi", "net", "nst", "place", "rms", 
        "sig", "sources", "status", "time", "tsunami", "type", "types", 
        "tz", "updated", "url"
    ]
    
    try:
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for feature in data["features"]:
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {}).get("coordinates", [])

                row = { 
                    "alert": properties.get("alert", ""),
                    "cdi": properties.get("cdi", ""),
                    "code": properties.get("code", ""),
                    "depth": geometry[2] if len(geometry) > 2 else "",
                    "depthError": properties.get("depthError", ""),
                    "detail": properties.get("detail", ""),
                    "dmin": properties.get("dmin", ""),
                    "felt": properties.get("felt", ""),
                    "gap": properties.get("gap", ""),
                    "horizontalError": properties.get("horizontalError", ""),
                    "id": properties.get("id", ""),
                    "ids": properties.get("ids", ""),
                    "latitude": geometry[1] if len(geometry) > 1 else "",
                    "locationSource": properties.get("locationSource", ""),
                    "longitude": geometry[0] if len(geometry) > 0 else "",
                    "mag": properties.get("mag", ""),
                    "magError": properties.get("magError", ""),
                    "magNst": properties.get("magNst", ""),
                    "magSource": properties.get("magSource", ""),
                    "magType": properties.get("magType", ""),
                    "mmi": properties.get("mmi", ""),
                    "net": properties.get("net", ""),
                    "nst": properties.get("nst", ""),
                    "place": properties.get("place", ""),
                    "rms": properties.get("rms", ""),
                    "sig": properties.get("sig", ""),
                    "sources": properties.get("sources", ""),
                    "status": properties.get("status", ""),
                    "time": properties.get("time", 0),
                    "tsunami": properties.get("tsunami", ""),
                    "type": properties.get("type", ""),
                    "types": properties.get("types", ""),
                    "tz": properties.get("tz", ""),
                    "updated": properties.get("updated", 0),
                    "url": properties.get("url", "")
                }
                writer.writerow(row)
    
    except IOError as e:
        logger.error(f"Error al escribir el archivo CSV: {e}")
