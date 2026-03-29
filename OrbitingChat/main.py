import json
import math
import os
import threading, asyncio, time
import configparser
import sys

import pygame
from twitchio.ext import commands
import win32api
import win32con
import win32gui
import io
import urllib.request
from PIL import Image, ImageSequence
import requests
import multiprocessing

#region setup

def get_base_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

CACHE_DIR = os.path.join(BASE_PATH, "emotes_cache")
CACHE_DIR2 = os.path.join(BASE_PATH, "emotes_cache2")
SPRITES_DIR = os.path.join(BASE_PATH, "sprites")
INDEX_FILE = os.path.join(BASE_PATH, "INDEX.txt")
CONFIG_FILE = os.path.join(BASE_PATH, "config.txt")

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
if not os.path.exists(CACHE_DIR2):
    os.makedirs(CACHE_DIR2)

config = configparser.ConfigParser()
if os.path.exists(CONFIG_FILE):
    config.read(CONFIG_FILE, encoding='utf-8')
else:
    print(f"Nie znaleziono pliku: {CONFIG_FILE}")

token = config['GameSettings']['token'].strip()
initial_channels = config['GameSettings']['initial_channels'].strip()
prefix = config['GameSettings']['prefix'].strip()
bot_id = config['GameSettings']['bot_id'].strip()
URLS = {
    "twitch": config['Endpoints']['twitch_emote'],
    "7tv_user": config['Endpoints']['seven_tv_user'],
    "7tv_emote": config['Endpoints']['seven_tv_emote']
}

class TwitchBot(commands.Bot):
    def __init__(self, queue_front, queue_back, urls):
        self.q_front = queue_front
        self.q_back =queue_back
        self.count = 0
        super().__init__(
            token="oauth:" + token,
            initial_channels=[initial_channels],
            prefix=prefix,
        )
        self.urls = urls

    async def event_ready(self):
        print(f'Połączono jako: {self.nick}')

    async def event_message(self, message):
        if message.echo:
            return

        emotes_raw = message.tags.get('emotes', {})
        emote_ids = []
        if len(emotes_raw) > 0:
            emotes_raw = emotes_raw.split()
            data = emotes_raw.pop()
            data = data.split("/")
            for dat in data:
                emote_id, space = dat.split(":")
                emote_ids.append(emote_id)

            for eid in emote_ids:
                path = os.path.join(CACHE_DIR, f"{eid}.bin")
                if not os.path.exists(path):
                    try:
                        url = self.urls['twitch'].format(eid=eid)
                        with urllib.request.urlopen(url) as response:
                            with open(path, "wb") as f:
                                f.write(response.read())
                    except:
                        pass

        # Zamiast rysować, wrzucamy dane do kolejki
        data = {
            "user_id": message.author.name,
            "name": message.author.display_name,
            "content": message.content,
            "color": message.author.color,
            "emotes": message.tags.get('emotes'),
            "start_time": time.time(),
            "delay": self.count
        }
        self.count += 8
        if self.count == 100: self.count = 0

        self.q_front.put(data)
        self.q_back.put(data)

        print(f"Odebrano: {message.content}")
        await self.handle_commands(message)


def run_bot(q_front, q_back, urls):
    # Ustawienie SelectorEventLoop naprawia niektóre błędy WinError na Windows
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = TwitchBot(q_front, q_back, urls)
    try:
        loop.run_until_complete(bot.start())
    except KeyboardInterrupt:
        loop.run_until_complete(bot.close())
    finally:
        loop.run_until_complete(bot.close())
        loop.close()

class AnimatedEmote:
    def __init__(self, img_payload):
        self.frames = []
        self.delays = []
        self.total_duration = 0

        pil_img = Image.open(io.BytesIO(img_payload))

        for frame in ImageSequence.Iterator(pil_img):
            # Konwersja na Pygame
            frame_rgba = frame.convert("RGBA")
            pygame_surface = pygame.image.fromstring(
                frame_rgba.tobytes(), frame_rgba.size, "RGBA"
            )

            # Pobieramy czas trwania klatki (standardowo 100ms jeśli brak danych)
            duration = frame.info.get('duration', 100)
            if duration == 0: duration = 100  # Zabezpieczenie przed błędnymi plikami

            self.frames.append(pygame_surface)
            self.delays.append(duration)
            self.total_duration += duration

    def get_frame(self):
        if not self.frames:
            return None

        # 1. Pobieramy aktualny czas w milisekundach
        # % self.total_duration sprawia, że animacja zapętla się idealnie
        current_time_ms = int(time.time() * 1000) % self.total_duration

        # 2. Sprawdzamy, która klatka odpowiada temu momentowi
        accumulated_time = 0
        for i, delay in enumerate(self.delays):
            accumulated_time += delay
            if current_time_ms < accumulated_time:
                return self.frames[i]

        return self.frames[0]

class OrbitingMessage:
    def __init__(self, data):
        self.TTL =  (time.time() - data['start_time']) + 80
        self.name = data["name"]
        self.user_id = data["user_id"]
        self.color = data["color"]
        self.message = parse_message(data["content"], data["emotes"])
        self.radius_x = 500  # Szerokość elipsy
        self.radius_y = 100   # "Płaskość" elipsy
        self.speed = -0.1     # Radiany na sekundę
        self.angle = (time.time() - data['start_time']) * self.speed
        self.delay =  data["delay"]

    def get_pos(self, screen_w, screen_h):
        # rzutowanie 3D na 2D
        x = screen_w // 2 + math.cos(self.angle) * self.radius_x
        y = screen_h // 2 + math.sin(self.angle) * self.radius_y
        # Z decyduje, czy wiadomość jest z przodu (sin > 0), czy z tyłu (sin < 0)
        z = math.sin(self.angle)
        return x, y, z

def get_emote_path(emote_id, extension="webp", default=True):
    if default:
        return os.path.join(CACHE_DIR, f"{emote_id}.{extension}")
    else:
        return os.path.join(CACHE_DIR2, f"{emote_id}.{extension}")

def load_7tv_emotes(channel_id, urls):
    url = urls['7tv_user'].format(channel=channel_id)

    index_data = {}
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        except:
            index_data = {}

    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200: return

        data = response.json()
        emotes = data.get('emote_set', {}).get('emotes', [])

        for e in emotes:
            emote_id = e['id']
            name = e['name']
            index_data[name] = emote_id

            file_path = get_emote_path(emote_id, default=False)

            if not os.path.exists(file_path):
                img_url = f"https:{e['data']['host']['url']}/1x.webp"
                img_data = requests.get(img_url, timeout=5).content
                with open(file_path, "wb") as f:
                    f.write(img_data)

        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=4)

    except Exception as ex:
        print(f"Błąd cache: {ex}")

def get_render_obj(obj):
    if isinstance(obj, AnimatedEmote):
        return obj.get_frame()
    return obj

def draw_msg(screen,msg, small_font, local_cache, sign_img,title_img, emote_dict):
    name_text = small_font.render(msg.name, True, msg.color)
    text_surf = pygame.Surface((270, 200), pygame.SRCALPHA)

    base_X = 10
    base_Y = 15
    for part in msg.message:
        if "emotes" not in part:
            part = part.split()
            for word in part:
                if word in emote_dict:
                    obj = get_emote_from_disk(emote_dict[word], local_cache, default=False)
                    img = get_render_obj(obj)
                    emote_w = img.get_width()

                    if base_X + emote_w + 4 > 270:
                        base_X = 10
                        base_Y += 30

                    text_surf.blit(img, (base_X - 4, base_Y - 6))
                    base_X += emote_w + 4
                else:
                    word += " "
                    text_w, text_h = small_font.size(word)
                    if base_X + text_w > 270:
                        base_X = 10
                        base_Y += 30
                    text = small_font.render(word, True, "#474747")
                    text_surf.blit(text, (base_X, base_Y))
                    base_X += text_w
        else:
            obj = get_emote_from_disk(part, local_cache)
            if isinstance(obj, AnimatedEmote):
                img = obj.get_frame()
            else:
                img = obj
            if base_X + 30 > 270:
                base_X = 10
                base_Y += 30
            text_surf.blit(img, (base_X - 4, base_Y - 6))
            base_X += 30

    msg_surf = pygame.Surface((300, 300), pygame.SRCALPHA)
    sign_height = max(50, base_Y + 28)
    sign_width = 280
    if base_Y < 20:
        sign_width = min(280, max(160, base_X))
    sign_img = pygame.transform.smoothscale(sign_img, (sign_width, sign_height))
    text_w, text_h = small_font.size(msg.name.strip())
    title = pygame.transform.scale(title_img, (text_w + 4, 18))
    msg_surf.blit(sign_img, (0, 10))
    msg_surf.blit(text_surf,(0,15))
    msg_surf.blit(title, (6, 6))
    msg_surf.blit(name_text, (10, 10))
    x,y,z = msg.get_pos(1200,600)
    screen.blit(msg_surf,(x, y))

def get_emotes_index():
    index_data = {}

    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            print(f"Wczytano {len(index_data)} emotek z indeksu lokalnego.")
        except Exception as e:
            print(f"Błąd czytania pliku indeksu: {e}")
            index_data = {}

    return index_data

def get_emote_from_disk(emote_id, local_cache, default = True):

    if default:
        path = os.path.join(CACHE_DIR, f"{emote_id}.bin")
        if emote_id in local_cache:
            return local_cache[emote_id]
    else:
        path = os.path.join(CACHE_DIR2, f"{emote_id}.webp")
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()

        with Image.open(io.BytesIO(data)) as img:
            if getattr(img, "is_animated", False):
                obj = AnimatedEmote(data)
            else:
                obj = pygame.image.load(io.BytesIO(data)).convert_alpha()

        local_cache[emote_id] = obj
        return obj
    print("No Index")
    return None

def parse_message(content, emotes_raw):
    if not emotes_raw:
        return [content]

    # 1. Tworzymy listę wszystkich wystąpień emotek
    segments = []
    emotes_raw = emotes_raw.split()
    data = emotes_raw.pop()
    data = data.split("/")
    for dat in data:
        emote_id, space = dat.split(":")
        if "-" in space:
            spaces = space.split(",")
            for s in spaces:
                start, end = s.split("-")
                segments.append({'id': emote_id, 'start': int(start), 'end': int(end)})
        else:
            start, end = space.split("-")
            segments.append({'id': emote_id, 'start': int(start), 'end': int(end)})

    # 2. Sortujemy je według kolejności w tekście
    segments.sort(key=lambda x: x['start'])

    # 3. Dzielimy tekst na kawałki
    parsed_result = []
    last_idx = 0
    for seg in segments:
        # Dodaj tekst przed emotką
        if seg['start'] > last_idx:
            parsed_result.append(content[last_idx:seg['start']])

        # Dodaj ID emotki
        parsed_result.append(seg['id'])
        last_idx = seg['end'] + 1

    # Dodaj resztę tekstu po ostatniej emotce
    if last_idx < len(content):
        parsed_result.append(content[last_idx:])

    return parsed_result

def run_overlay(layer_type, shared_queue, custom_emote_dict):
    pygame.init()
    screen = pygame.display.set_mode((1600, 600), pygame.NOFRAME)
    small_font = pygame.font.SysFont("consolas", 16)
    sign_img = pygame.image.load(get_sprite_path("Sign.png")).convert_alpha()
    title_img = pygame.image.load(get_sprite_path("Title.png")).convert_alpha()

    try:
        pygame.display.set_icon(sign_img)
    except:
        pass

    # --- Magia Windows (Przezroczystość) ---
    hwnd = pygame.display.get_wm_info()["window"]
    TRANS_COLOR = (255, 0, 128)
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                           win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*TRANS_COLOR), 0, win32con.LWA_COLORKEY)

    # Ustawienie warstwy
    if layer_type == "FRONT":
        # Zawsze na wierzchu
        pygame.display.set_caption("TwitchChat_Front")
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002)
    else:
        # Normalne okno (będzie pod postacią, jeśli postać jest Topmost)
        pygame.display.set_caption("TwitchChat_Back")
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002)

    clock = pygame.time.Clock()
    local_messages = []
    running = True
    local_cache = {}

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 1. Pobierz nowe wiadomości z procesora bota
        try:
            while not shared_queue.empty():
                msg_data = shared_queue.get()
                local_messages.append(OrbitingMessage(msg_data))
        except:
            pass

        screen.fill(TRANS_COLOR)

        # 2. Aktualizuj i Rysuj
        for m in local_messages[::-1]:
            if m.delay > 0:
                m.delay += -dt
                continue
            m.angle += m.speed * dt
            m.TTL += -dt
            if m.TTL < 0:
                local_messages.remove(m)
            x,y,z = m.get_pos(1600, 600)

            # KLUCZ: Filtrowanie warstwy
            if layer_type == "FRONT" and z > -0.08:
                draw_msg(screen, m, small_font, local_cache, sign_img, title_img, custom_emote_dict)
            elif layer_type == "BACK" and z < 0.08:
                draw_msg(screen, m, small_font, local_cache, sign_img, title_img, custom_emote_dict)

        pygame.display.flip()
    pygame.quit()

def get_sprite_path(filename):
    return os.path.join(SPRITES_DIR, filename)

if __name__ == '__main__':
    # Kolejka dostępna dla wszystkich procesów
    multiprocessing.freeze_support()
    queue_front = multiprocessing.Queue()
    queue_back = multiprocessing.Queue()
    threading.Thread(target=load_7tv_emotes, args=(bot_id,URLS), daemon=True).start()
    custom_emote_dict = get_emotes_index()

    # Proces bota
    p_bot = multiprocessing.Process(target=run_bot, args=(queue_front,queue_back, URLS))

    # Proces okna przedniego
    p_front = multiprocessing.Process(target=run_overlay, args=("FRONT", queue_front, custom_emote_dict))

    # Proces okna tylnego
    p_back = multiprocessing.Process(target=run_overlay, args=("BACK", queue_back, custom_emote_dict))

    p_bot.start()
    p_front.start()
    p_back.start()

    try:
        # Pętla monitorująca: dopóki oba okna żyją, główny program czeka
        while p_front.is_alive() and p_back.is_alive():
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("Zamykanie przez użytkownika (Ctrl+C)...")
    finally:
        # Sprzątanie: jeśli jedno okno padło, ubijamy wszystko inne
        print("Sprzątanie procesów...")
        for p in [p_bot, p_front, p_back]:
            if p.is_alive():
                p.terminate()  # Brutalne ale skuteczne zatrzymanie
                p.join()  # Upewnienie się, że zasoby zostały zwolnione
        print("Program zamknięty.")