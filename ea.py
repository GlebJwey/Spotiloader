from selenium import webdriver
from bs4 import BeautifulSoup
import time, tqdm, os, requests
from pathlib import Path
from selenium.webdriver.common.by import By
from yt_dlp import YoutubeDL

DOWNLOAD_FOLDER = Path('d:/users/rigl3/Документы/Плайлист/Скачано из саунклауда')
DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

OP = {
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': os.path.join(DOWNLOAD_FOLDER, "%(Name)s - %(Artists)s.%(ext)s"),
    'ffmpeg_location': 'C:/Users/rigl3/AppData/Local/ffmpeg-9.0.2-essentials_build/bin'
}

INVALID_SYMBOLS = r'\/:*?"<>|'

def get_playlist_tracks(playlist_url):
    # Настройка браузера
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in background
    driver = webdriver.Chrome(options=options)
    driver.get(playlist_url)
    time.sleep(10)  # Wait for page to load

    # Прокрутка, чтобы загрузить все треки
    # 1. Открываем целевой сайт
    driver.get(playlist_url)
    
    # Задаем время ожидания для загрузки элементов
    scroll_pause_time = 2.0 

    # 2. Получаем начальную высоту страницы
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # 3. Прокручиваем страницу до самого низа
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # 4. Ждем, пока загрузится новая порция контента
        time.sleep(scroll_pause_time)

        # 5. Вычисляем новую высоту страницы и сравниваем со старой
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            # Если высота не изменилась, значит, мы достигли конца страницы
            print("Достигнут конец страницы.")
            break
            
        last_height = new_height
        # print(block_elements = driver.find_elements(By.CLASS_NAME, "your-item-class"))
        # print(f"Загружено элементов: {len(block_elements)}")


    # r = requests.get(playlist_url)
    # Парсинг HTML
    html = driver.page_source
    driver.quit()
    # html = r.text
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
        f.close()
    soup = BeautifulSoup(html, "lxml")
    tracks = []
    ready = []
    for f in DOWNLOAD_FOLDER.glob("*"):
        ready.append(f.stem.split(' - ')[:1])
    print(ready)
    ready = dict(ready)
    # Поиск элементов по структуре Spotify
    for track in soup.find('ul', class_='trackList__list sc-clearfix sc-list-nostyle'):
        try: name = track.find('a', class_='trackItem__trackTitle sc-link-primary').text.lower()
        except: name = ''
        try: artist = track.find('a', class_='trackItem__username sc-link-light sc-link-secondary sc-mr-0.5x').text.lower()
        except: artist = ''
        for s in INVALID_SYMBOLS:
            name = name.replace(s, '&')
            artist = artist.replace(s, '&')
        if artist in name:
            name -= artist
        if name not in ready:
            tracks.append({'Artists': artist, 'Name': name})
    
    return tracks
# Использование

playlist_url = input('Введите ссылку на плейлист из SoundCloud: ')
tracks = get_playlist_tracks(playlist_url)

for i, track in enumerate(tracks):
    options = OP.copy()
    options['outtmpl'] = OP['outtmpl'] % (track | {'ext' : '%(ext)s'})
    print(options)
    with YoutubeDL(options) as ydl:
        try:
            zapros = f"ytsearch1:{track['Name']} - {track['Artists']}"
            if track['Artists'] == 'УННВ':
                zapros += " оригинал"
            ydl.download([zapros])
            print("Трек успешно найден и скачан!")
        except:
            print(f"Не удалось скачать трек {track['Name']} - {track['Artists']}")
        if (i + 1) % 5 or i == 1 or (i + 1) == len(tracks):
            print(f"Прогресс {i+1}/{len(tracks)}")

# КУЛЬТУРНАЯ ПРОГРАММА, ASCHE ZU ASCHE, ДЖАЗОВАЯ, ИЗ ГОВЯЖЬИХ ХВОСТОВ, ХМУРЫЙ ДЕНЬ, ЛЕТНИЙ ВЕЧЕР, ОСКАЛ, DERBY DAY, ШОФЕР-ДАЛЬНОБОЙЩИК, SONNE, ВСЕЛЕНСКИЙ ГРУЗ, 2012, УРАЛРЭП, ЗИМЫ НЕ БУДЕТ, БУДНИ, СКОРО, КЛАССИКА, *3 КИТА, ПОЕДИНОК С СОБОЙ, ВЭЛКОМ ТУ РОССИЯНИЯ
