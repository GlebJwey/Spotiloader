import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.video.VideoClip import VideoClip
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token

INPUT_FILE = "text.txt"
OUTPUT_FILE = "pycharm_typing.mp4"
WIDTH, HEIGHT = 1920, 1080
FPS = 30
TYPING_SPEED_AVG = 0.02
BACKSPACE_SPEED = 0.12
ERROR_PROBABILITY = 0.0
BACKSPACE_PROBABILITY = 0.7

FONT_SIZE = 28
FONT_PATH = "C:/Windows/Fonts/consola.ttf"

BG_COLOR = (43, 43, 43)
GUTTER_BG = (49, 51, 53)
CURRENT_LINE_BG = (50, 50, 50)
LINE_NUM_COLOR = (96, 99, 102)
GUTTER_WIDTH = 80
PADDING_X = 15
PADDING_Y = 20
LINE_HEIGHT = int(FONT_SIZE * 1.3)

COLOR_MAP = {
    Token.Text: (169, 183, 198),
    Token.Keyword: (204, 120, 50),
    Token.Keyword.Namespace: (204, 120, 50),
    Token.Name.Builtin: (136, 136, 198),
    Token.Name.Function: (255, 198, 109),
    Token.Name.Class: (166, 226, 46),
    Token.Name.Decorator: (187, 181, 41),
    Token.String: (106, 135, 89),
    Token.String.Doc: (98, 151, 85),
    Token.Number: (104, 151, 187),
    Token.Operator: (169, 183, 198),
    Token.Punctuation: (169, 183, 198),
    Token.Comment: (128, 128, 128),
}


def get_token_color(token_type):
    while token_type is not None:
        if token_type in COLOR_MAP:
            return COLOR_MAP[token_type]
        token_type = token_type.parent
    return COLOR_MAP[Token.Text]


if not os.path.exists(INPUT_FILE):
    with open(INPUT_FILE, "w", encoding='utf-8') as f:
        f.write("print('Hello World')")


def generate_keystrokes(text):
    actions = []
    current_text = ""
    for char in text:
        if random.random() < ERROR_PROBABILITY and len(current_text) > 0 and char != "\n":
            wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz1234567890_=")
            current_text += wrong_char
            actions.append(('add', wrong_char, TYPING_SPEED_AVG * 1.5))
            if random.random() < BACKSPACE_PROBABILITY:
                actions.append(('backspace', 1, BACKSPACE_SPEED))
                current_text = current_text[:-1]
                current_text += char
                actions.append(('add', char, TYPING_SPEED_AVG))
        else:
            current_text += char
            actions.append(('add', char, TYPING_SPEED_AVG if char != " " else TYPING_SPEED_AVG * 0.5))
    return actions


with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    raw_code = f.read()

keystrokes = generate_keystrokes(raw_code)


def make_frame(t):
    elapsed_time = 0
    display_text = ""
    for action_type, value, delay in keystrokes:
        elapsed_time += delay
        if elapsed_time > t:
            break
        if action_type == 'add':
            display_text += value
        elif action_type == 'backspace':
            display_text = display_text[:-value]

    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except OSError:
        font = ImageFont.load_default()

    lines_list = display_text.split('\n')
    current_line_idx = len(lines_list) - 1

    # === ЛОГИКА СКРОЛЛИНГА ===
    scroll_offset_y = 0
    bottom_margin = LINE_HEIGHT * 2  # Оставляем 2 пустые строки снизу
    cursor_virtual_y = PADDING_Y + current_line_idx * LINE_HEIGHT

    if cursor_virtual_y > HEIGHT - bottom_margin:
        scroll_offset_y = cursor_virtual_y - (HEIGHT - bottom_margin)
    # ==========================

    highlight_y = PADDING_Y + current_line_idx * LINE_HEIGHT - scroll_offset_y
    draw.rectangle([GUTTER_WIDTH, highlight_y, WIDTH, highlight_y + LINE_HEIGHT], fill=CURRENT_LINE_BG)

    # Панель с номерами строк
    draw.rectangle([0, 0, GUTTER_WIDTH, HEIGHT], fill=GUTTER_BG)
    draw.line([(GUTTER_WIDTH, 0), (GUTTER_WIDTH, HEIGHT)], fill=(85, 85, 85), width=1)

    for i in range(current_line_idx + 1):
        num_y = PADDING_Y + i * LINE_HEIGHT - scroll_offset_y
        # Отрисовываем номер строки, только если он в пределах экрана
        if -LINE_HEIGHT < num_y < HEIGHT:
            line_num_str = str(i + 1)
            num_width = font.getlength(line_num_str)
            num_x = GUTTER_WIDTH - num_width - 15
            draw.text((num_x, num_y), line_num_str, font=font, fill=LINE_NUM_COLOR)

    tokens = list(lex(display_text, PythonLexer()))
    cursor_x = GUTTER_WIDTH + PADDING_X
    cursor_y = PADDING_Y - scroll_offset_y

    for token_type, token_value in tokens:
        color = get_token_color(token_type)
        parts = token_value.split('\n')
        for i, part in enumerate(parts):
            if part:
                # Отрисовываем текст (то, что ушло вверх за 0, Pillow просто не нарисует)
                draw.text((cursor_x, cursor_y), part, font=font, fill=color)
                cursor_x += font.getlength(part)
            if i < len(parts) - 1:
                cursor_x = GUTTER_WIDTH + PADDING_X
                cursor_y += LINE_HEIGHT

    if int(t * 2) % 2 == 0:
        draw.line([(cursor_x + 2, cursor_y + 2), (cursor_x + 2, cursor_y + LINE_HEIGHT - 2)], fill=(187, 187, 187),
                  width=2)

    return np.array(img)


total_duration = sum(delay for _, _, delay in keystrokes) + 3.0
video_clip = VideoClip(make_frame, duration=total_duration)
video_clip.write_videofile(
    OUTPUT_FILE,
    fps=FPS,
    codec='libx264',
    audio=False,
    ffmpeg_params=['-pix_fmt', 'yuv420p'])