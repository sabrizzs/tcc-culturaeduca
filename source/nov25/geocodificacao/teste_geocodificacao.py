import requests, time

STRUCT_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "Samantha-Geocoder/1.0 (samantha@email.com)"}

def geocode_structured(
    street=None, house_number=None, city=None, state=None, postcode=None,
    country="Brasil", countrycodes="br", language="pt-BR", throttle_s=1
):
    # Nominatim aceita parâmetros estruturados:
    # street, city, county, state, country, postalcode
    # Dica: combine número + logradouro em 'street'
    street_full = street
    if house_number and street:
        street_full = f"{house_number} {street}"

    params = {
        "street": street_full,
        "city": city,
        "state": state,
        "country": country,
        "postalcode": postcode,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 1,
        "countrycodes": countrycodes,
        "accept-language": language,
    }
    # Remover None
    params = {k: v for k, v in params.items() if v}

    r = requests.get(STRUCT_URL, params=params, headers=HEADERS, timeout=30)
    if r.status_code == 429:
        wait = int(r.headers.get("Retry-After", "2"))
        time.sleep(wait)
        r = requests.get(STRUCT_URL, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    time.sleep(throttle_s)
    if not data:
        return None
    hit = data[0]
    return {
        "lat": float(hit["lat"]),
        "lon": float(hit["lon"]),
        "display_name": hit.get("display_name"),
        "address": hit.get("address", {}),
        "importance": hit.get("importance"),
    }

# Exemplo:
res2 = geocode_structured(
    street="Av. Paulista", house_number="1578",
    city="São Paulo", state="SP", postcode=None
)
print(res2)
