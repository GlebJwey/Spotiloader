from selenium import webdriver
from bs4 import BeautifulSoup
import time, os, requests, eyed3, warnings
from pathlib import Path
from selenium.webdriver.common.by import By
from yt_dlp import YoutubeDL, utils
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

warnings.filterwarnings('ignore')

# Папка для скачивания
DOWNLOAD_FOLDER = Path("<Ваша папка для скачивания>")
DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

FFMPEG_LOCATION = "<Путь к FFMPEG>"

TXT_FILENAME = "exceptions_sp"

EXT  = 'mp3'
EXTP = '.' + EXT
# Опции для сохранения
OP = {
    'cookies': os.path.join(os.getcwd(), 'cookies.txt'),
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': EXT,
        'preferredquality': '192',
    }],
    'outtmpl': os.path.join(DOWNLOAD_FOLDER, "%(Name)s - %(Artists)s.%(ext)s"),
    'ffmpeg_location': FFMPEG_LOCATION,
    'quiet': True, 'no_warnings': True, 'ignoreerrors': True
}

INVALID_SYMBOLS = r'\/:*?"<>|'

EXCEPTS_N = []        # Сюда добавьте исключения среди плейлиста (названия)
EXCEPTS_A = []        # Сюда добавьте исключения среди плейлиста (исполнители)

HARD_EXCEPT = False          # Маркер для жесткой фильтрации исполнителей по исключениям

tracks = []        # Плейлист
ready  = []        # Уже существующие треки
skip   = []        # Не удалось скачать

def get_playlist_tracks(playlist_url):
    """Получение данных треков из плейлиста Spotify путём веб-скрапинга и парсинга HTML-страницы"""
    # Настройка браузера
    global tracks, ready, skip
    print('Парсинг страницы HTML...')
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Запуск на фоне
    driver = webdriver.Chrome(options=options)

    try:
        # 1. Переход на страницу с формой
        driver.get("https://spotidown.app") # замените на свой URL

        # 2. Нахождение полей ввода (по ID, Name, XPath и т.д.)
        url_input = driver.find_element(By.NAME, "url")
        # 3. Ввод данных в поля
        url_input.send_keys(playlist_url)

        # 4. Отправка формы (нажатие Enter или клик по кнопке Submit)
        url_input.send_keys(Keys.RETURN)
        time.sleep(5)  # Дождитесь загрузки ответа

    finally:
        html = driver.page_source
        driver.quit()
    # Парсинг HTML
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
        f.close()

    print('Получение данных треков из HTML страницы...')
    soup = BeautifulSoup(html, "lxml")

    # какие файлы уже закончены
    for f in DOWNLOAD_FOLDER.glob("*"):
        if f.suffix != EXTP:
            os.remove(f)
            continue
        ready.append(f.stem.split(' - ')[:2])
    ready = dict(ready)
    
    # Поиск элементов по структуре сайта
    found = soup.find('div', id='playlist-songs')

    name, artist, imgsource = '', '', ''
    exist_temp = []
    exA = None
    # Получение данных треков из HTML
    for track in found:
        for el in track.find_all('div', class_='spotidown-middle center'):
            try: name = el.find('a', class_='hover-underline').text         # Название
            except: name = ''           
            try: artist = el.find('span').text          # Исполнители
            except: artist = ''
        # Скип пустых значений
        if name == '' and artist == '':
            continue
        # Получение иконки трека
        for el in track.find_all('div', class_='spotidown-left left track-preview-artwork'):
            try: imgsource = el.find('img').get('src')
            except: imgsource = ''
        # Проверка на наличие исключений
        if HARD_EXCEPT:
            exist_temp = []
            for a in EXCEPTS_A:
                exist_temp.append(a.lower() in artist.lower())
            exA = any(exist_temp)
        else:
            exA = artist.lower() in list(map(str.lower, EXCEPTS_A))
        if name not in ready and artist not in ready and name.lower() not in list(map(str.lower, EXCEPTS_N)) and not exA:
            tracks.append({'Artists': artist, 'Name': name, 'ImageSource': imgsource})
    
    return tracks


def change_audio_tags(path, *args):
    """Устанавливает теги для трека (название, исполнители, альбом и ссылка на иконку)"""
    audiofile = eyed3.load(path)
    if (audiofile.tag == None):
        audiofile.initTag()
    try:
        r = requests.get(args[3])          # Картинка
        if r.status_code < 400:

            mime_type = 'image/png'

            audiofile.tag.images.set(3, r.content, mime_type)
    except FileNotFoundError: raise FileNotFoundError('а где картинка')

    try: audiofile.tag.title = args[0]          # Название
    except: None
    try: audiofile.tag.artist = args[1]         # Исполнители
    except: None
    try: audiofile.tag.album = args[2]          # Альбом
    except: None

    audiofile.tag.save(version=eyed3.id3.ID3_V2_3)

playlist_url = input('Введите ссылку на плейлист из Spotify: ')
tracks = get_playlist_tracks(playlist_url)

for i, track in enumerate(tracks):
    options = OP.copy()
    track_c = track.copy()

    for s in INVALID_SYMBOLS:           # Очистка от неверных символов
        track_c = {k : v.replace(s, '&') for k, v in track_c.items()}

    options['outtmpl'] = OP['outtmpl'] % (track_c | {'ext' : '%(ext)s'})
    track_path = options['outtmpl'] % {'ext' : EXT}

    with YoutubeDL(options) as ydl:
        att = 0
        print(f"\nСкачивание трека {track['Name']} - {track['Artists']}")

        while not os.path.exists(track_path) and att != 5:
            print(f'Попытка {att+1}')
            try:
                zapros = f"ytsearch1:{track_c['Name']} - {track_c['Artists']}"          # для поиска через ютуб
                ydl.download([zapros])
                if not os.path.exists(track_path):
                    raise FileExistsError
                
            except:
                print('\033[31m{}\033[0m'.format(f"Не удалось скачать трек {track['Name']} - {track['Artists']}"))
                att += 1

        if att < 5:
            # Установка тегов
            change_audio_tags(track_path, track['Name'], track['Artists'], '', track['ImageSource'])
            print('\033[32mТрек успешно найден и скачан!\033[0m')
        else:
            skip.append(track)
        if (i + 1) % 5 or i == 1 or (i + 1) == len(tracks):
            print(f"Прогресс {i+1}/{len(tracks)}")

    # Формирование файла exceptions_sp.txt с неудачными скачиваниями и исключениями
    with open(f"{TXT_FILENAME}.txt", 'w', encoding='utf-8') as f:
        f.write(f'Установите {len(skip)} треков самостоятельно: ')
        for t in skip:
            f.write(f"\n\t• {t['Name']} - {t['Artists']}")
        excepts_len = len(EXCEPTS_N) + len(EXCEPTS_A)
        if excepts_len > 0:
            f.write(f'\n\n{excepts_len} исключений, добавленными вами: ')
            if EXCEPTS_N:
                f.write(f'\n\t└ {len(EXCEPTS_N)} названий треков: ')
                for t in EXCEPTS_N:
                    f.write(f"\n\t\t• {t}")
            if EXCEPTS_A:
                f.write(f'\n\t└ {len(EXCEPTS_A)} исполнителей: ')
                for t in EXCEPTS_A:
                    f.write(f"\n\t\t• {t}")
            