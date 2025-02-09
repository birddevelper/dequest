import requests


def sync_request(method, url, headers, data, params, timeout):
    response = requests.request(
        method.upper(),
        url,
        headers=headers,
        json=data,
        params=params,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
