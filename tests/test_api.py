import requests, time

url = "https://overpass-api.de/api/interpreter"

# Centro aproximado de Santiago (Plaza de Armas)
lat, lon = -33.4372, -70.6506
radius = 15000  # 15 km

query = f"""
[out:json][timeout:25];
(
  node["amenity"="hospital"](around:{radius},{lat},{lon});
  node["healthcare"="hospital"](around:{radius},{lat},{lon});
  way["amenity"="hospital"](around:{radius},{lat},{lon});
);
out center;
"""

headers = {"User-Agent": "EFT-SCY1101-ProyectoUniversitario/1.0 (contacto: tu_correo@duoc.cl)"}

start = time.time()
resp = requests.get(url, params={"data": query}, headers=headers)
elapsed = time.time() - start

print("Status code:", resp.status_code)
print("Tiempo:", round(elapsed, 2), "s")
if resp.status_code == 200:
    elems = resp.json().get("elements", [])
    print("N° de elementos:", len(elems))
    for e in elems[:5]:
        print(e.get("tags", {}).get("name", "sin nombre"))