import requests

url = "https://www.igp.gob.pe/servicios/api-acelerometrica/ran/breadcrumbstations2"

# mismo JSON que muestra DevTools (30 bytes, sin espacios)
body = '{"datetime":"20250101_170829"}'

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.igp.gob.pe",
    "Referer": "https://www.igp.gob.pe/servicios/aceldat-peru/reportes-registros-acelerometricos?date=20250101_170829",
    # "Cookie": "...",  # opcional: solo si lo necesitas y lo copias de tu navegador
    # "User-Agent": "Mozilla/5.0 ..."  # opcional
}

response = requests.post(url, data=body, headers=headers)

print("Status code:", response.status_code)
print("Respuesta:")
print(response.text)
