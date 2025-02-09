import requests


def sync_request(method, url, headers, json, params, data, timeout):
    response = requests.request(
        method.upper(),
        url,
        headers=headers,
        json=json,
        params=params,
        data=data,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
