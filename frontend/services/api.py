import requests

def request(base_url, path, token, method="GET", **kwargs):
    response = requests.request(method, base_url.rstrip("/") + "/api" + path,
        headers={"Authorization": f"Bearer {token}"}, timeout=300, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text or "Backend returned an invalid response"}
    if not response.ok:
        detail = payload.get("detail", "Backend request failed")
        if isinstance(detail, str):
            # Keep older backend response wording aligned with the current UI brand.
            detail = detail.replace("ResearchIQ", "MedNext").replace("Research IQ", "MedNext")
        raise RuntimeError(detail)
    return payload
