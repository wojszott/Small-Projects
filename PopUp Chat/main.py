import os
import random, threading, asyncio, time, queue
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

#region setup

def get_base_path():
    if hasattr(sys, '_MEIPASS'):
        # Jeśli uruchomione jako EXE, używamy ścieżki pliku wykonywalnego
        return os.path.dirname(sys.executable)
    # Jeśli uruchomione jako skrypt .py
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

CACHE_DIR = os.path.join(BASE_PATH, "emotes_cache")
SPRITES_DIR = os.path.join(BASE_PATH, "sprites")
CONFIG_FILE = os.path.join(BASE_PATH, "config.txt")

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

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

bot = None

class TwitchBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token="oauth:" + token,
            initial_channels=[initial_channels],
            prefix=prefix,
        )

    async def event_ready(self):
        print(f'✅ Połączono jako: {self.nick}')

    async def event_message(self, message):
        if message.echo:
            return

        # Zamiast rysować, wrzucamy dane do kolejki
        data = {
            "user_id": message.author.name,
            "name": message.author.display_name,
            "content": message.content,
            "color": message.author.color,
            "emotes": message.tags.get('emotes')
        }
        msg_queue.put(data)

        print(f"Odebrano: {message.content}")
        # To jest wymagane, by bot działał poprawnie!
        await self.handle_commands(message)


def run_bot():
    global bot
    # Ustawienie SelectorEventLoop naprawia niektóre błędy WinError na Windows
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = TwitchBot()
    try:
        loop.run_until_complete(bot.start())
    except KeyboardInterrupt:
        loop.run_until_complete(bot.close())
    finally:
        loop.close()


# Uruchomienie bota w tle
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

pygame.init()
screen_width = 1200
screen_height = 400
screen = pygame.display.set_mode((screen_width, screen_height), pygame.NOFRAME)
TRANS_COLOR = (255, 0, 128)
fwn = pygame.display.get_caption()[0] # Pobieramy uchwyt okna
hwnd = pygame.display.get_wm_info()["window"]

# Ustawiamy styl okna na warstwowe
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
    win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)

# Ustawiamy kolor TRANS_COLOR jako przeźroczysty (0,0,0, LWA_COLORKEY)
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*TRANS_COLOR), 0, win32con.LWA_COLORKEY)

# Opcjonalnie: Ustawienie okna "Zawsze na wierzchu" (Always on Top)
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
pygame.display.set_caption("Twitch chat")
#endregion
small_font = pygame.font.SysFont("consolas", 16)
big_font = pygame.font.SysFont("consolas", 16, bold=True)

msg_queue = queue.Queue()
active_messages = []
emote_cache = {}

class Popup:
    def __init__(self, data):
        self.TTL = 15
        self.pos_X = random.randint(10,890)
        self.name = data["name"]
        self.user_id = data["user_id"]
        self.color = data["color"]
        self.message = parse_message(data["content"], data["emotes"])
        self.pos_Y = 450
        self.background_color = (random.randint(60, 166), random.randint(102, 230), random.randint(0, 70))


class AnimatedEmote:
    def __init__(self, img_payload):
        self.frames = []
        self.delays = []
        self.total_duration = 0  # Sumaryczny czas animacji w ms

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

def get_emote_path(emote_id, extension="webp"):
    return os.path.join(CACHE_DIR, f"{emote_id}.{extension}")


def load_7tv_emotes(channel_id):
    global emotes_7tv
    url = URLS['7tv_user'].format(channel=channel_id)

    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200: return

        data = response.json()
        emotes = data.get('emote_set', {}).get('emotes', [])

        for e in emotes:
            name = e['name']
            emote_id = e['id']
            file_path = get_emote_path(emote_id)

            # SPRAWDZAMY CZY PLIK ISTNIEJE NA DYSKU
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    img_data = f.read()
            else:
                # JEŚLI NIE MA, POBIERAMY I ZAPISUJEMY
                img_url = f"https:{e['data']['host']['url']}/1x.webp"
                img_data = requests.get(img_url, timeout=5).content
                with open(file_path, "wb") as f:
                    f.write(img_data)

            # Zamiana danych (z dysku lub sieci) na obiekt Pygame
            with Image.open(io.BytesIO(img_data)) as img:
                if getattr(img, "is_animated", False):
                    emotes_7tv[name] = AnimatedEmote(img_data)
                else:
                    surf = pygame.image.load(io.BytesIO(img_data)).convert_alpha()
                    emotes_7tv[name] = surf

    except Exception as ex:
        print(f"Błąd cache: {ex}")

def update_msg(msg, decrement):
    if decrement:
        msg.TTL += -1
    if msg.TTL < 0:
        active_messages.remove(msg)

    if msg.TTL > 12 and msg.pos_Y >= 180:
        msg.pos_Y += -0.3

    if msg.TTL < 3:
        msg.pos_Y += 0.3

def get_render_obj(obj):
    if isinstance(obj, AnimatedEmote):
        return obj.get_frame()
    return obj

def draw_msg(msg):
    global sign_img, title_img
    msg_surf = pygame.Surface((220, 140), pygame.SRCALPHA)
    msg_surf.blit(sign_img, (-30,-30))
    name_text = big_font.render(msg.name, True, msg.color)
    text_surf = pygame.Surface((220, 120), pygame.SRCALPHA)

    base_X = 10
    base_Y = 15
    for part in msg.message:
        if "emotes" not in part:
            part = part.split()
            for word in part:
                if word in emotes_7tv:
                    #7tv emotes
                    obj = emotes_7tv[word]
                    img = get_render_obj(obj)
                    emote_w = img.get_width()

                    if base_X + emote_w + 4 > 210:
                        base_X = 10
                        base_Y += 28

                    text_surf.blit(img, (base_X - 4, base_Y - 6))
                    base_X += emote_w + 4
                else:
                    word += " "
                    text_w, text_h = small_font.size(word)
                    if base_X + text_w > 210:
                        base_X = 10
                        base_Y += 28
                    text = small_font.render(word, True, ("#474747"))
                    text_surf.blit(text, (base_X, base_Y))
                    base_X += text_w
        else:
            #twitch emotes
            obj = get_emote(part)
            if isinstance(obj, AnimatedEmote):
                img = obj.get_frame()
            else:
                img = obj
            if base_X + 28 > 210:
                base_X = 10
                base_Y += 28
            text_surf.blit(img, (base_X - 4, base_Y - 6))
            base_X += 28

    msg_surf.blit(text_surf,(0,15))
    text_w, text_h = big_font.size(msg.name.strip())
    title = pygame.transform.scale(title_img, (text_w + 4, 18))
    msg_surf.blit(title, (6, 6))
    msg_surf.blit(name_text, (10, 10))
    screen.blit(msg_surf,(msg.pos_X, msg.pos_Y))

def get_emote(emote_id):
    if emote_id not in emote_cache:
        url = URLS['twitch'].format(eid=emote_id)
        with urllib.request.urlopen(url) as response:
            data = response.read()
            with Image.open(io.BytesIO(data)) as img:
                if getattr(img, "is_animated", False):
                    emote_cache[emote_id] = AnimatedEmote(data)
                else:
                    img_byte = io.BytesIO(data)
                    emote_cache[emote_id] = pygame.image.load(img_byte).convert_alpha()
    return emote_cache[emote_id]

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
        # Dodaj tekst przed emotką (jeśli jest)
        if seg['start'] > last_idx:
            parsed_result.append(content[last_idx:seg['start']])

        # Dodaj ID emotki
        parsed_result.append(seg['id'])
        last_idx = seg['end'] + 1

    # Dodaj resztę tekstu po ostatniej emotce
    if last_idx < len(content):
        parsed_result.append(content[last_idx:])

    return parsed_result

def get_sprite_path(filename):
    return os.path.join(SPRITES_DIR, filename)

clock = 0
running = True
emotes_7tv = {}
threading.Thread(target=load_7tv_emotes, args=(bot_id,), daemon=True).start()

try:
    sign_img = pygame.image.load(get_sprite_path("Sign.png")).convert_alpha()
    sign_img = pygame.transform.scale(sign_img, (280, 220))
    title_img = pygame.image.load(get_sprite_path("Title.png")).convert_alpha()
except pygame.error as e:
    print(f"Błąd ładowania grafiki: {e}")

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    try:
        while True:  # Pobierz wszystkie oczekujące wiadomości
            new_msg = msg_queue.get_nowait()
            active_messages.append(Popup(new_msg))

    except queue.Empty:
        pass

    screen.fill(TRANS_COLOR)
    decrement = False
    if time.time() > clock + 1:
        decrement = True
        clock = time.time()

    for msg in active_messages:
        update_msg(msg, decrement)
        draw_msg(msg)

    pygame.display.flip()

if bot:
    asyncio.run_coroutine_threadsafe(bot.close(), asyncio.get_event_loop())
pygame.quit()
sys.exit()