import sys
import time
import ctypes
from ctypes import wintypes
import datetime
import pygame
import os

#region Init

# --- Windows API ---
user32 = ctypes.windll.user32
SetWindowPos = user32.SetWindowPos
GetCursorPos = user32.GetCursorPos
GetWindowRect = user32.GetWindowRect

SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004

# --- globalne do przeciągania ---
dragging = False
drag_offset = (0, 0)

def get_mouse_screen_pos():
    pt = ctypes.wintypes.POINT()
    GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def move_window_to(hwnd, x, y):
    SetWindowPos(hwnd, None, int(x), int(y), 0, 0, SWP_NOSIZE | SWP_NOZORDER)


# Inicjalizacja Pygame
WINDOW_WIDTH, WINDOW_HEIGHT = 600,600
BOX1_WIDTH, BOX1_HEIGHT = 600, 250
BOX2_WIDTH, BOX2_HEIGHT = 560, 210

pygame.init()
pygame.display.set_caption("Timer")
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.NOFRAME)

# kolor przezroczysty (BGR w Windows)
#transparent_rgb = (0,0,0) # czarne tło
transparent_rgb = (255, 0, 255)  # magenta
transparent_bgr = (transparent_rgb[2] << 16) | (transparent_rgb[1] << 8) | transparent_rgb[0]

#Windows API
hwnd = pygame.display.get_wm_info()["window"]

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
LWA_COLORKEY = 0x1

style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)
ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, ctypes.c_uint(transparent_bgr), 0, LWA_COLORKEY)


#endregion
switch_box = pygame.Rect(55, 420, 40, 90)

def get_sprite_path(filename):
    base_path = os.path.dirname(__file__)
    sprite_folder = os.path.join(base_path, "Sprites")
    if not os.path.exists(sprite_folder):
        raise FileNotFoundError(f"Folder 'sprites' nie istnieje w {base_path}")
    return os.path.join(sprite_folder, filename)

def admin_control(events):
    global counting, user_input_digits, input_time, output_time, timer, switch_box,mx, my
    for event in events:
        if event.type == pygame.KEYDOWN:
            # pauza / start
            if event.key == pygame.K_p:
                counting = not counting
                return

            # obsługa wpisywania czasu
            if event.key == pygame.K_BACKSPACE and user_input_digits:
                user_input_digits.pop()
            elif pygame.K_0 <= event.key <= pygame.K_9:
                if len(user_input_digits) < 6:  # maks 6 cyfr
                    user_input_digits.append(event.key - pygame.K_0)
            elif event.key == pygame.K_RETURN:  # Enter = start
                if timer:
                    s = ''.join(map(str, user_input_digits)).rjust(6, '0')
                    hours = int(s[-6:-4])
                    minutes = int(s[-4:-2])
                    seconds = int(s[-2:])
                    seconds = max(0, min(seconds, 59))
                    minutes = max(0, min(minutes, 59))
                    input_time = hours * 3600 + minutes * 60 + seconds
                    output_time = input_time
                    counting = True
                    user_input_digits.clear()
                else:
                    s = ''.join(map(str, user_input_digits)).rjust(4, '0')
                    target_h = int(s[-4:-2])
                    target_m = int(s[-2:])
                    target_h = max(0, min(target_h, 23))
                    target_m = max(0, min(target_m, 59))

                    now = datetime.datetime.now()
                    target = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
                    if target <= now:
                        target += datetime.timedelta(days=1)  # jeśli godzina już minęła

                    delta = target - now
                    input_time = int(delta.total_seconds())
                    output_time = input_time
                    counting = True
                    user_input_digits.clear()


        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                if switch_box.collidepoint(mx, my):
                    timer = not timer
                    user_input_digits.clear()

                    print("Switch toggled:", "Timer" if timer else "Clock")

# stworzenie surface
box1_surface = pygame.Surface((BOX1_WIDTH - 10, BOX1_HEIGHT - 10), pygame.SRCALPHA).convert_alpha()
box1_ramka = pygame.Surface((BOX1_WIDTH, BOX1_HEIGHT), pygame.SRCALPHA).convert_alpha()
box2_surface = pygame.Surface((BOX2_WIDTH -10, BOX2_HEIGHT - 10), pygame.SRCALPHA).convert_alpha()
box2_ramka = pygame.Surface((BOX2_WIDTH, BOX2_HEIGHT), pygame.SRCALPHA).convert_alpha()

Blue = pygame.Color("#304ec7")
Light_Blue = pygame.Color("#6dbff2")
Black = pygame.Color("#000000")
Purple = pygame.Color("#a781cf")
font_big = pygame.font.Font(None, 180)
font_medium = pygame.font.Font(None, 80)

running = True
timer = True # True = Timer | False - Clock
clock = pygame.time.Clock()
letters = False

input_time = 0
output_time = 0
countdown = 0
second_counter = 0
line = pygame.image.load(get_sprite_path("YellowLine.png"))
zigzag = pygame.image.load(get_sprite_path("PurpleZigzag.png"))
move = 0
move2 = 0
move_speed = 1
side = 1
side_switch_time = 0
user_input_digits = []

def timer_logic():
    global second_counter,countdown,output_time, letters, numbers_dict
    now = time.time()
    if output_time == 0:
        if letters:
            timer_offset = pygame.Vector2(30, 400)
            time_digits = "00:00"
            x_offset = 0
            for char in time_digits:
                if char == ":":
                    screen.blit(numbers_dict[char], timer_offset + (x_offset, 0))
                    x_offset += 60
                    continue
                digit = int(char)
                if digit in numbers_dict:
                    screen.blit(numbers_dict[digit], timer_offset + (x_offset, 0))
                x_offset += 60  # odstęp między cyframi
        else:
            time_string = "00:00"
            timer_offset = [120, 400]
            title_text = font_big.render(time_string, True, Blue)
            screen.blit(title_text, timer_offset)
        return

    if now >= second_counter + 1:
        second_counter = now
        countdown +=1
        output_time -= 1

    hour = output_time//3600
    minute =  (output_time % 3600) // 60
    second = output_time%60
    if letters:
        timer_offset = pygame.Vector2(30, 400)

        if hour > 0:
            time_digits = f"{hour:02}:{minute:02}:{second:02}"
        else:
            time_digits = f"{minute:02}:{second:02}"

        x_offset = 0
        for char in time_digits:
            if char == ":":
                screen.blit(numbers_dict[char], timer_offset + (x_offset, 0))
                x_offset += 60
                continue
            digit = int(char)
            if digit in numbers_dict:
                screen.blit(numbers_dict[digit], timer_offset + (x_offset, 0))
            x_offset += 60  # odstęp między cyframi
    else:
        if hour > 0:
            timer_offset = [30,400]
            time_string = f"{hour:02}:{minute:02}:{second:02}"
        else:
            time_string = f"{minute:02}:{second:02}"
            timer_offset = [120, 400]
        title_text = font_big.render(time_string, True, Blue)
        screen.blit(title_text, timer_offset)

def add_effects():
    global move,move2,move_speed,side_switch_time,side
    move += move_speed * side
    move2 +=( move_speed -0.1 ) * -side
    if move >= 100:
        move -= 100
    if move2 >= 100:
        move2 -= 100

    if time.time() > side_switch_time + 10:
        side_switch_time = time.time()
        side = side *-1

    line_count = BOX1_WIDTH//30
    for i in range(line_count):
        x = move + i * 100 - 250
        rect = pygame.Rect([x,0,300,60])
        box1_surface.blit(line,rect)

    line_count2 = BOX2_WIDTH // 40
    for i in range(line_count2):
        x = move2 + i * 100 - 250
        rect = pygame.Rect([x,0,300,60])
        box2_surface.blit(zigzag,rect)

def timer_input_screen():
    global user_input_digits

    # tworzymy string z cyfr
    s = ''.join(map(str, user_input_digits)).rjust(6, '0')
    hour = int(s[-6:-4])
    minute = int(s[-4:-2])
    second = int(s[-2:])

    input_box1 = pygame.Rect(140, 50, 80, 60)
    frame1 = pygame.Rect(135, 45, 90, 70)
    input_box2 = pygame.Rect(260, 50, 80, 60)
    frame2 = pygame.Rect(255, 45, 90, 70)
    input_box3 = pygame.Rect(380, 50, 80, 60)
    frame3 = pygame.Rect(375, 45, 90, 70)

    hour_text = font_medium.render(f"{hour:02}", True, Black)
    minute_text = font_medium.render(f"{minute:02}", True, Black)
    second_text = font_medium.render(f"{second:02}", True, Black)
    colon_text = font_medium.render(":", True, Black)

    pygame.draw.rect(box2_surface, Black, frame1, border_radius=10)
    pygame.draw.rect(box2_surface, Black, frame2, border_radius=10)
    pygame.draw.rect(box2_surface, Black, frame3, border_radius=10)
    pygame.draw.rect(box2_surface, Purple, input_box1, border_radius=10)
    pygame.draw.rect(box2_surface, Purple, input_box2, border_radius=10)
    pygame.draw.rect(box2_surface, Purple, input_box3, border_radius=10)

    box2_surface.blit(hour_text, [149, 55])
    box2_surface.blit(colon_text, [230, 55])
    box2_surface.blit(minute_text, [269, 55])
    box2_surface.blit(colon_text, [350, 55])
    box2_surface.blit(second_text, [389, 55])

    info_text = pygame.font.Font(None, 40).render("Enter duration (Enter = Start)", True, Black)
    box2_surface.blit(info_text, [90, 150])

def clock_input_screen():
    global user_input_digits

    # tworzymy string z cyfr
    s = ''.join(map(str, user_input_digits)).rjust(4, '0')
    hour = int(s[-4:-2])
    minute = int(s[-2:])

    input_box1 = pygame.Rect(170, 50, 80, 60)
    frame1 = pygame.Rect(165, 45, 90, 70)
    input_box2 = pygame.Rect(290, 50, 80, 60)
    frame2 = pygame.Rect(285, 45, 90, 70)

    pygame.draw.rect(box2_surface, Black, frame1, border_radius=10)
    pygame.draw.rect(box2_surface, Black, frame2, border_radius=10)
    pygame.draw.rect(box2_surface, Purple, input_box1, border_radius=10)
    pygame.draw.rect(box2_surface, Purple, input_box2, border_radius=10)

    hour_text = font_medium.render(f"{hour:02}", True, Black)
    minute_text = font_medium.render(f"{minute:02}", True, Black)
    colon_text = font_medium.render(":", True, Black)

    box2_surface.blit(hour_text, [179, 55])
    box2_surface.blit(colon_text, [260, 55])
    box2_surface.blit(minute_text, [299, 55])

    info_text = pygame.font.Font(None, 40).render("Enter finish time (Enter = Start)", True, Black)
    box2_surface.blit(info_text, [90, 150])

def draw_switch():
    global timer, switch_box
    clock_text = pygame.font.Font(None, 40).render("Clock", True, Black)
    box2_surface.blit(clock_text, [10, 20])
    timer_text = pygame.font.Font(None, 40).render("Timer", True, Black)
    box2_surface.blit(timer_text, [10, 120])

    frame = pygame.Rect(25, 45, 40, 80)
    pygame.draw.rect(box2_surface, Black, frame, border_radius=20)

    pygame.draw.rect(box2_surface, Purple, pygame.Rect(30, 50, 30, 70), border_radius=20)

    if timer:
        switch_y = 90
    else:
        switch_y = 50
    switch = pygame.Rect(30, switch_y, 30, 30)
    pygame.draw.rect(box2_surface, Light_Blue, switch, border_radius=20)


def check_letters():
    global letters, numbers_dict
    number_list = ["0.png","1.png","2.png","3.png","4.png","5.png","6.png","7.png","8.png","9.png"]
    try:
        for i in range(len(number_list)):
            number = number_list[i]
            print(i)
            num = pygame.image.load(get_sprite_path(f"Numbers/{number}"))
            num = pygame.transform.scale(num, (80,80))
            numbers_dict[i] = num
        num = pygame.image.load(get_sprite_path(f"Numbers/colon.png"))
        num = pygame.transform.scale(num, (80, 80))
        numbers_dict[":"] = num
        print("Files loaded")
        letters = True
    except Exception as e:
        print("Error:", e)
        return

numbers_dict = {}
counting = False
check_letters()

while running:
    events =  pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # rozpocznij przeciąganie
                rect = ctypes.wintypes.RECT()
                GetWindowRect(hwnd, ctypes.byref(rect))
                mx, my = get_mouse_screen_pos()
                drag_offset = (mx - rect.left, my - rect.top)
                dragging = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                dragging = False

        elif event.type == pygame.MOUSEMOTION and dragging:
            mx, my = get_mouse_screen_pos()
            new_x = mx - drag_offset[0]
            new_y = my - drag_offset[1]
            move_window_to(hwnd, new_x, new_y)

    admin_control(events)
    screen.fill(transparent_rgb)

    if counting:
        timer_logic()
    else:
        box1_surface.fill(Blue)
        box2_surface.fill(Light_Blue)
        box1_ramka.fill(Black)
        box2_ramka.fill(Black)
        add_effects()
        draw_switch()
        if timer:
            timer_input_screen()
        else:
            clock_input_screen()
        box2_ramka.blit(box2_surface, [5, 5])
        box1_surface.blit(box2_ramka, [20, 20])
        box1_ramka.blit(box1_surface, [5, 5])
        screen.blit(box1_ramka, [0, 350])

    pygame.display.flip()
    pygame.display.update()
    clock.tick(60)

pygame.quit()
sys.exit()