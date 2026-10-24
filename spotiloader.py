from selenium import webdriver
from bs4 import BeautifulSoup
import time, tqdm, os, requests
from pathlib import Path
from selenium.webdriver.common.by import By
from yt_dlp import YoutubeDL
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC

# Папка для скачивания
DOWNLOAD_FOLDER = Path('d:/users/rigl3/Документы/Плайлист/Скачано из саунклауда 2')
DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

EXT = 'mp3'
EXTP = '.' + EXT
# Опции для сохранения
OP = {
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': EXT,
        'preferredquality': '192',
    }],
    'outtmpl': os.path.join(DOWNLOAD_FOLDER, "%(Name)s - %(Artists)s.%(ext)s"),
    'ffmpeg_location': 'C:/Users/rigl3/AppData/Local/ffmpeg-9.0.2-essentials_build/bin',
    'quiet': True
}

INVALID_SYMBOLS = r'\/:*?"<>|'

def get_playlist_tracks(playlist_url):
    # Настройка браузера
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in background
    driver = webdriver.Chrome(options=options)

    try:
        # 1. Переход на страницу с формой
        driver.get("https://spotidown.app") # замените на свой URL
        # time.sleep(10)
        # 2. Нахождение полей ввода (по ID, Name, XPath и т.д.)
        url_input = driver.find_element(By.NAME, "url")
        # 3. Ввод данных в поля
        url_input.send_keys(playlist_url)

        # 4. Отправка формы (нажатие Enter или клик по кнопке Submit)
        url_input.send_keys(Keys.RETURN)
        # Альтернативно можно найти кнопку и кликнуть:
        # submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        # submit_button.click()

        time.sleep(5)  # Дождитесь загрузки ответа

    finally:
        html = driver.page_source
        driver.quit()
    # Парсинг HTML
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
        f.close()
    soup = BeautifulSoup(html, "lxml")
    # какие файлы уже закончены
    tracks = []
    ready = []
    for f in DOWNLOAD_FOLDER.glob("*"):
        if f.suffix != EXTP:
            os.remove(f)
            continue
        ready.append(f.stem.split(' - ')[:2])
    ready = dict(ready)

    # Поиск элементов по структуре сайта
    found = soup.find('div', id='playlist-songs')

    name, artist, imgsource = '', '', ''
    # Получение данных трека из HTML
    for track in found:
        for el in track.find_all('div', class_='spotidown-middle center'):
            try: name = el.find('a', class_='hover-underline').text
            except: name = ''
            try: artist = el.find('span').text
            except: artist = ''
        for el in track.find_all('div', class_='spotidown-left left track-preview-artwork'):
            try: imgsource = el.find('img').get('src')
            except: imgsource = ''

        # if name not in ready:
        tracks.append({'Artists': artist, 'Name': name, 'ImageSource': imgsource})
    
    return tracks


def change_audio_tags(path, *args):         # args: 0 - Название, 1 - Исполнители, 2 - Альбом, 3 - Ссылка на иконку
    try:
        audio_id3 = ID3(path)
    except Exception:
        # Если тегов нет, создаем новые
        audio_id3 = ID3()
    try:
        r = requests.get(args[3])          # Картинка
        if r.status_code < 400:
            cover_data = r.content
        # if image_path.suffix == '.png':
        mime_type = 'image/jpeg'
        # else:
        #     mime_type = 'image/jpeg'
        audio_id3["APIC"] = APIC(encoding=3,                            # Картинка
                            mime=mime_type, type=3,
                            desc='Front cover', data=cover_data)
    except FileNotFoundError: raise FileNotFoundError('а где картинка')

    for i, attribute in enumerate(['TIT2', 'TPE1', 'TALB']):            # Название, Исполнитель, Альбом
        class_att = globals().get(attribute)
        try: audio_id3[attribute] = class_att(encoding=3, text=args[i])     
        except: raise ValueError('да что это блять')

    audio_id3.save(path)

playlist_url = input('Введите ссылку на плейлист из Spotify: ')
tracks = get_playlist_tracks(playlist_url)

for i, track in enumerate(tracks.copy()):
    options = OP.copy()
    for s in INVALID_SYMBOLS:           # Очистка от неверных символов
        track_c = {k : v.replace(s, '&') for k, v in track.items()}
    options['outtmpl'] = OP['outtmpl'] % (track_c | {'ext' : '%(ext)s'})
    track_path = options['outtmpl'] % {'ext' : EXT}

    with YoutubeDL(options) as ydl:
        try:
            zapros = f"ytsearch1:{track_c['Name']} - {track_c['Artists']}"          # для поиска через ютуб
            # if track['Artists'] == 'УННВ':
            #     zapros += " оригинал"
            ydl.download([zapros])
            # установка тегов
            change_audio_tags(track_path, track['Name'], track['Artists'], '', track['ImageSource'])
            print("Трек успешно найден и скачан!")
        except:
            print(f"Не удалось скачать трек {track['Name']} - {track['Artists']}")
        if (i + 1) % 5 or i == 1 or (i + 1) == len(tracks):
            print(f"Прогресс {i+1}/{len(tracks)}")

# КУЛЬТУРНАЯ ПРОГРАММА, ДЖАЗОВАЯ, ЯМА, ВСЕЛЕНСКИЙ ГРУЗ, *3 КИТА, ВЭЛКОМ ТУ РОССИЯНИЯ, ВСЕ БУДЕТ ХОРОШО, все что нам надо, александр, кто же будет читать для улиц, познания, пока тлеет, пословица, скандал, трупак, черная тишина
