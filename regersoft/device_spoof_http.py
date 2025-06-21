import requests
from config import HTTP_ROOT_SERVER

def spoof_device_profile():
    url = f"{HTTP_ROOT_SERVER}/spoof/device_profile"
    resp = requests.post(url)
    resp.raise_for_status()
    return resp.json()

def set_proxy(proxy):
    url = f"{HTTP_ROOT_SERVER}/spoof/proxy"
    data = {"proxy": proxy}
    resp = requests.post(url, json=data)
    resp.raise_for_status()
    return resp.json()

def clear_gsf():
    url = f"{HTTP_ROOT_SERVER}/clear_gsf"
    resp = requests.post(url)
    resp.raise_for_status()
    return resp.json()

def start_appium():
    url = f"{HTTP_ROOT_SERVER}/start_appium"
    resp = requests.post(url)
    resp.raise_for_status()
    return resp.json()

def get_device_info():
    url = f"{HTTP_ROOT_SERVER}/device_info"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()