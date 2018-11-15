import requests


def wkt(epsg):
    url = f"http://epsg.io/?q={epsg}&format=json"
    resp = requests.get(url)
    data = resp.json()
    return data["results"][0]["wkt"]
