from selenium import webdriver
from bs4 import BeautifulSoup
import time, tqdm, os, requests, warnings
from pathlib import Path
from selenium.webdriver.common.by import By
from yt_dlp import YoutubeDL

warnings.filterwarnings('ignore')

# Папка для скачивания
DOWNLOAD_FOLDER = Path('d:/users/rigl3/Документы/Плайлист/Скачано из саунклауда 2')
DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

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
    'ffmpeg_location': 'C:/Users/rigl3/AppData/Local/ffmpeg-9.0.2-essentials_build/bin',
    'quiet': True, 'no_warnings': True, 'ignoreerrors': True
}

INVALID_SYMBOLS = r'\/:*?"<>|'

EXCEPTS_N = []        # Сюда добавьте исключения среди плейлиста (названия)
EXCEPTS_A = []        # Сюда добавьте исключения среди плейлиста (исполнители)

HARD_EXCEPT = True          # Маркер для жесткой фильтрации исполнителей по исключениям

tracks =  []        # Плейлист
ready  =  []        # Уже существующие треки
skip   =  []        # Не удалось скачать

def get_playlist_tracks(playlist_url):
    """Получение данных треков из плейлиста Soundcloud путём веб-скрапинга и парсинга HTML-страницы"""
    # Настройка браузера
    global tracks, ready, skip
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Запуск на фоне
    driver = webdriver.Chrome(options=options)
    driver.get(playlist_url)
    time.sleep(5)  # Дождитесь загрузки ответа

    # Прокрутка, чтобы загрузить все треки
    driver.get(playlist_url)
    
    scroll_pause_time = 2.0             # Время ожидания для загрузки элементов
    # Максимальный размер страницы
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Прокрутка до самого низа
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)

        # Вычисление новой высоты страницы и сравнение со старой
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            # Триггер достижения конца страницы
            print("Достигнут конец страницы.")
            break
        
        last_height = new_height

    # Парсинг HTML
    html = driver.page_source
    driver.quit()

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
    found = soup.find('ul', class_='trackList__list sc-clearfix sc-list-nostyle')

    name, artist = '', ''
    exist_temp = []
    exA = None
    # Получение данных треков из HTML
    for track in found:
        try: name = track.find('a', class_='trackItem__trackTitle sc-link-primary').text.lower()
        except: name = ''           # Название
        try: artist = track.find('a', class_='trackItem__username sc-link-light sc-link-secondary sc-mr-0.5x').text.lower()
        except: artist = ''         # Исполнители
        # Скип пустых значений
        if name == '' and artist == '':
            continue

        if artist in name:
            name -= artist
        # Проверка на наличие исключений
        if HARD_EXCEPT:
            exist_temp = []
            for a in EXCEPTS_A:
                exist_temp.append(a.lower() in artist.lower())
            exA = any(exist_temp)
        else:
            exA = artist.lower() in list(map(str.lower, EXCEPTS_A))
        if name not in ready and artist not in ready and name.lower() not in list(map(str.lower, EXCEPTS_N)) and artist.lower() not in list(map(str.lower, EXCEPTS_A)) and not exA:
            tracks.append({'Artists': artist, 'Name': name})
    
    return tracks

playlist_url = input('Введите ссылку на плейлист из SoundCloud: ')
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
            print('\033[32mТрек успешно найден и скачан!\033[0m')
        else:
            skip.append(track)
        if (i + 1) % 5 or i == 1 or (i + 1) == len(tracks):
            print(f"Прогресс {i+1}/{len(tracks)}")

    # Формирование файла exceptions_sc.txt с неудачными скачиваниями и исключениями
    with open('exceptions_sc.txt', 'w', encoding='utf-8') as f:
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
