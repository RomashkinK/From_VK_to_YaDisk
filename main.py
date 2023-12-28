import requests
import json
import configparser
import datetime
from tqdm import tqdm
from pprint import pprint


# Для начала работы необходимо заполнить данные в settings.ini

def get_token_id(file_name):
    """Функция возвращает токен и id пользователя для работы с VK и Яндекс.Диском, хранящихся в settings.ini"""
    config = configparser.ConfigParser()
    config.read(file_name)
    vk_token = config["vk"]["access_token"]
    vk_user_id = config["vk"]["vk_id"]
    ya_token = config["ya_disk"]["ya_disk_token"]
    return [vk_token, vk_user_id, ya_token]


def find_max_dpi(dict_in_search):
    """Функция возвращает ссылку на фотографию максимального размера и её размер"""
    max_dpi = 0
    need_elem = 0
    for j in range(len(dict_in_search)):
        file_dpi = dict_in_search[j].get("width") * dict_in_search[j].get("height")
        if file_dpi > max_dpi:
            max_dpi = file_dpi
            need_elem = j
    return dict_in_search[need_elem].get("url"), dict_in_search[need_elem].get("type")


def time_convert(time_unix):
    """Функция переводит дату загрузки фотографии в привычный формат"""
    time_bc = datetime.datetime.fromtimestamp(time_unix)
    str_time = time_bc.strftime("date of upload %d-%m-%Y")
    return str_time


class VKRequest:

    API_BASE_URL = 'https://api.vk.com/method/'

    def __init__(self, access_token, user_id):
        """Метод для получения основных параметров для запроса к VK API"""
        self.token = get_token_id("settings.ini")[0] 
        self.user_id = get_token_id("settings.ini")[1]
        self.json_list, self.sorted_dict = self.sort_required_dict_for_upload_and_json()

    def common_params(self):
        """Метод возвращает основные параметры для запроса к VK API"""
        return {
            'access_token': self.token,
            'v': '5.131',
        }
    
    def get_photos_info(self):
        """Метод возвращает информацию о всех фотографиях профиля"""
        url = f'{self.API_BASE_URL}photos.get'
        params = {
            'owner_id': self.user_id,
            'album_id': "profile",
            'photo_sizes': 1,
            'extended': 1,
            "rev": 1
        }
        photos_info = requests.get(url, params={**self.common_params(), **params}).json()["response"]
        return photos_info["count"], photos_info["items"]
    
    def get_required_dict(self):
        """Метод возвращает словарь с необходимой информацией о фотографиях профиля"""
        photo_count, photo_items = self.get_photos_info()
        result_dict = {}
        for i in range(photo_count):
            likes_count = photo_items[i]["likes"]["count"]
            url_download, picture_size = find_max_dpi(photo_items[i]["sizes"])
            time_correction = time_convert(photo_items[i]["date"])
            new_value = result_dict.get(likes_count,[])
            new_value.append({"likes_count": likes_count,
                              "add_name": time_correction,
                              "photo_url": url_download,
                              "size": picture_size})
            result_dict[likes_count] = new_value
        return result_dict
    
    def sort_required_dict_for_upload_and_json(self):
        """Метод сортирует словарь для загрузки на Яндекс.Диск и формирует JSON"""
        json_list = []
        sorted_dict = {}
        photo_dict = self.get_required_dict()
        counter = 0
        for a in photo_dict.keys():
            for b in photo_dict[a]:
                if len(photo_dict[a]) == 1:
                    file_name = f'{b["likes_count"]}.jpeg'
                else:
                    file_name = f'{b["likes_count"]} {b["add_name"]}.jpeg'
                json_list.append({
                    "file_name": file_name,
                    "size": b["size"],
                })
                if b["likes_count"] == 0:
                    sorted_dict[file_name] = photo_dict[a][counter]["photo_url"]
                    counter += 1
                else:
                    sorted_dict[file_name] = photo_dict[a][0]["photo_url"]
        return json_list, sorted_dict
    

class YaDiskUploader:

    def __init__(self, token, folder_name, num):
        """Метод для получения основных параметров для выгрузки на Яндекс.Диск"""
        self.token = get_token_id("settings.ini")[2]
        self.headers = {"Authorization": self.token}
        self.url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        self.added_files_num = num
        self.folder_name = self.create_folder(folder_name)

    def create_folder(self, folder_name):
        """Метод для создания папки на Яндекс.Диске"""
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {"path": folder_name}
        if requests.get(url, headers=self.headers, params=params).status_code !=200:
            requests.put(url, headers=self.headers, params=params)
            print (f'Папка {folder_name} создана')
        else:
            print(f'Папка {folder_name} уже существует. Измените название папки')
        return folder_name
    
    def link_to_folder(self, folder_name):
        """Метод для получения ссылки на папку на Яндекс.Диске"""
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {"path": folder_name}
        response = requests.get(url, headers=self.headers, params=params).json()["_embedded"]["items"]
        link_to_folder = []
        for i in response:
            link_to_folder.append(i["name"])
        return link_to_folder
    
    def upload_files(self, dict_files):
        """Метод для загрузки на Яндекс.Диск"""
        files_in_folder = self.link_to_folder(self.folder_name)
        copy_counter = 0
        for key, i in zip(dict_files.keys(), tqdm(range(self.added_files_num))):
            if copy_counter < self.added_files_num:
                if key not in files_in_folder:
                    params = {"path": f"{self.folder_name}/{key}",
                              "url": dict_files[key],
                              "overwrite": "false"
                              }
                    requests.post(self.url, headers=self.headers, params=params)
                    copy_counter += 1
                else:
                    print(f'Файл {key} уже существует')
            else:
                break
        print (f'\nВ папку "{self.folder_name}" загружено {copy_counter} файлов.')


if __name__ == '__main__':
    vk = VKRequest(get_token_id("settings.ini")[0], get_token_id("settings.ini")[1])

    with open ('vk_profile_photos.json', 'w', encoding='utf-8') as file:
        json.dump(vk.json_list, file, indent=4, ensure_ascii=False)

    ya = YaDiskUploader(get_token_id("settings.ini")[2], "Photos from VK", 5)
    ya.upload_files(vk.sorted_dict)