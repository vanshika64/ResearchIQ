import requests

def request(base_url, path, token, method="GET", **kwargs):
    response = requests.request(method, base_url.rstrip("/") + "/api" + path,
        headers={"Authorization": f"Bearer {token}"}, timeout=300, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text or "Backend returned an invalid response"}
    if not response.ok:
        raise RuntimeError(payload.get("detail", "Backend request failed"))
    return payload
