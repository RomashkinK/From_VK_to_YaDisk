from urllib.parse import urlencode

"""Код для получения токена VK"""

APP_iD = '51820438'
BASE_URL = 'https://oauth.vk.com/authorize'
params ={
    'client_id': APP_iD,
    'redirect_uri': 'https://oauth.vk.com/blank.html',
    'display': 'page',
    'scope': 'status,photos',
    'response_type': 'token'
}

print(BASE_URL + '?' + urlencode(params))

