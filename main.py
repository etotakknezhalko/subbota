import pygame
import random
import os
import sys
from PIL import Image  # Используем Pillow для корректного чтения кадров GIF

# --- КОНСТАНТЫ ЗОН ---
# Эти константы используются как ключи для логики атаки/защиты и для текстов на кнопках
HEAD = "ГОЛОВА"
TORSO = "КОРПУС"
LEGS = "НОГИ"
ZONES = [HEAD, TORSO, LEGS]

# --- СИСТЕМНЫЕ ФУНКЦИИ ---

def resource_path(relative_path):
    """
    Функция для работы с путями внутри EXE-файла.
    PyInstaller при запуске --onefile распаковывает файлы во временную папку _MEIPASS.
    Эта функция определяет, откуда брать ресурсы: из папки с кодом или из временной папки.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ИНТЕРФЕЙСА ---

def draw_status_box(screen, text, font, center_x, y, padding=15):
    """
    Рисует стилизованное информационное окно (лог боя или имя победителя).
    Включает в себя полупрозрачный фон, золотую рамку и декоративные уголки.
    """
    if not text: return
    
    # Рендерим текст и вычисляем размеры окна на основе длины текста
    text_surf = font.render(text, True, (255, 255, 255))
    w, h = text_surf.get_width() + padding * 4, text_surf.get_height() + padding * 2
    x = center_x - w // 2

    # Создаем поверхность с поддержкой прозрачности (SRCALPHA)
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(overlay, (20, 20, 20, 180), (0, 0, w, h), border_radius=12)
    screen.blit(overlay, (x, y))
    
    # Рисуем контуры рамки (светло-серый и золотой слои)
    pygame.draw.rect(screen, (200, 200, 200), (x, y, w, h), 1, border_radius=12)
    pygame.draw.rect(screen, (180, 150, 0), (x + 3, y + 3, w - 6, h - 6), 2, border_radius=9)
    
    # Рисуем декоративные уголки (L-образные линии)
    corner_size = 10
    for cx, cy in [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]:
        dx = corner_size if cx == x else -corner_size
        dy = corner_size if cy == y else -corner_size
        pygame.draw.line(screen, (255, 215, 0), (cx, cy), (cx + dx, cy), 3)
        pygame.draw.line(screen, (255, 215, 0), (cx, cy), (cx, cy + dy), 3)
        
    # Выводим сам текст по центру окна
    screen.blit(text_surf, (center_x - text_surf.get_width() // 2, y + padding))

# --- КЛАССЫ ИГРОВОЙ ЛОГИКИ ---

class Weapon:
    """Хранит бонусы характеристик оружия"""
    def __init__(self, name, bonus_damage, bonus_crit_chance, bonus_сrit_damage):
        self.name = name
        self.bonus_damage = bonus_damage
        self.bonus_crit_chance = bonus_crit_chance
        self.bonus_сrit_damage = bonus_сrit_damage

class Player:
    """
    Основной класс игрока. Управляет характеристиками, анимациями, 
    отрисовкой персонажа и накоплением статистики боя.
    """
    def __init__(self, name, hp, damage, armor, crit_chance, сrit_damage, weapon, side, static_img, attack_gif):
        self.name = name
        self.max_hp = hp
        # Итоговые статы учитывают базовые значения + бонусы оружия
        self.damage = damage + weapon.bonus_damage
        self.armor = armor
        self.crit_chance = crit_chance + weapon.bonus_crit_chance
        self.сrit_damage = сrit_damage + weapon.bonus_сrit_damage
        self.side = side  # 'left' или 'right' для позиционирования
        
        # Загрузка графики (используем resource_path для EXE)
        self.static_image_orig = pygame.image.load(resource_path(static_img)).convert_alpha()
        self.attack_frames_orig = self._load_gif_frames(resource_path(attack_gif))
        
        self.state = "IDLE"      # IDLE (покой) или ATTACK (удар)
        self.current_frame = 0    # Индекс текущего кадра анимации
        self.animation_speed = 0.17
        
        self.reset_stats()  # Инициализация HP и счетчиков

    def reset_stats(self):
        """Сбрасывает HP и все показатели статистики перед новым боем"""
        self.hp = self.max_hp
        self.total_damage_dealt = 0
        self.crit_count = 0
        self.current_choice = None  # Выбранная зона для текущего хода
        self.hits_by_zone = {HEAD: 0, TORSO: 0, LEGS: 0}
        self.blocks_by_zone = {HEAD: 0, TORSO: 0, LEGS: 0}

    def _load_gif_frames(self, path):
        """Разбивает GIF файл на список поверхностей Pygame"""
        pil_gif = Image.open(path)
        frames = []
        for i in range(pil_gif.n_frames):
            pil_gif.seek(i)
            frame = pil_gif.convert("RGBA")
            pygame_surface = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode)
            frames.append(pygame_surface)
        return frames

    def _scale_img(self, img, target_h):
        """Масштабирует картинку под высоту экрана с сохранением пропорций"""
        w, h = img.get_size()
        ratio = target_h / h
        return pygame.transform.smoothscale(img, (int(w * ratio), target_h))

    def resize(self, screen_w, screen_h):
        """Пересчитывает размеры спрайтов и позиции персонажа при изменении окна"""
        target_h = int(screen_h * 0.55)  # Рост персонажа - 55% от высоты экрана
        self.static_image = self._scale_img(self.static_image_orig, target_h)
        self.attack_frames = [self._scale_img(f, target_h) for f in self.attack_frames_orig]
        
        # Обновляем текущую картинку в зависимости от состояния
        self.image = self.static_image if self.state == "IDLE" else self.attack_frames[min(int(self.current_frame), len(self.attack_frames)-1)]
        self.rect = self.image.get_rect()
        
        # Расстановка по горизонтали: 38% для левого, 62% для правого
        if self.side == 'left': self.rect.midbottom = (int(screen_w * 0.38), int(screen_h * 0.9))
        else: self.rect.midbottom = (int(screen_w * 0.62), int(screen_h * 0.9))

    def update(self):
        """Проигрывает анимацию удара. Возвращает True, когда анимация закончилась"""
        if self.state == "ATTACK":
            self.current_frame += self.animation_speed
            if self.current_frame >= len(self.attack_frames):
                self.state = "IDLE"
                self.current_frame = 0
                self.image = self.static_image
                return True 
            else:
                self.image = self.attack_frames[int(self.current_frame)]
        return False

    def draw_char(self, screen):
        """Рисует персонажа на экране"""
        if self.image: screen.blit(self.image, self.rect)

    def draw_ui(self, screen, font, screen_w, screen_h, is_attacker, ui_bg, img_atk, img_def):
        """Отрисовывает интерфейс: каменную плиту, имя, HP-бар и иконку статуса (меч/щит)"""
        bar_w, bar_h = int(screen_w * 0.23), int(screen_h * 0.028)
        margin_y = int(screen_h * 0.11) # Отступ сверху
        
        # Отрисовка подложки (каменной плиты)
        slab_w, slab_h = ui_bg.get_size()
        slab_x = int(screen_w * 0.1) if self.side == 'left' else int(screen_w * 0.9 - slab_w)
        slab_y = margin_y - int(slab_h * 0.4) 
        screen.blit(ui_bg, (slab_x, slab_y))
        
        # Координаты для элементов внутри плиты
        x = slab_x + (slab_w - bar_w) // 2
        
        # Имя персонажа
        name_surf = font.render(self.name, True, (240, 240, 240))
        name_x = x if self.side == 'left' else x + bar_w - name_surf.get_width()
        screen.blit(name_surf, (name_x, margin_y - name_surf.get_height() - 4))
        
        # Полоска здоровья (Фон и Заполнение с закруглением)
        radius = 6 
        pygame.draw.rect(screen, (30, 30, 30), (x, margin_y, bar_w, bar_h), border_radius=radius)
        fill_w = int(bar_w * (max(0, self.hp) / self.max_hp))
        color = (46, 204, 113) if self.hp > 30 else (231, 76, 60)
        
        if fill_w > radius * 2: 
            if self.side == 'left': pygame.draw.rect(screen, color, (x, margin_y, fill_w, bar_h), border_radius=radius)
            else: pygame.draw.rect(screen, color, (x + (bar_w - fill_w), margin_y, fill_w, bar_h), border_radius=radius)
        elif fill_w > 0: 
            draw_x = x if self.side == 'left' else x + (bar_w - fill_w)
            pygame.draw.rect(screen, color, (draw_x, margin_y, fill_w, bar_h))

        # Обводка полоски
        pygame.draw.rect(screen, (200, 200, 200), (x, margin_y, bar_w, bar_h), 2, border_radius=radius)
        
        # Иконка Меча (Атака) или Щита (Защита)
        icon = img_atk if is_attacker else img_def
        icon_x = x + bar_w + 10 if self.side == 'left' else x - icon.get_width() - 10
        icon_y = margin_y + (bar_h // 2) - (icon.get_height() // 2)
        screen.blit(icon, (icon_x, icon_y))

    def perform_attack(self, enemy, attack_zone, defense_zone):
        """
        Логика расчета урона.
        Сравнивает зону атаки и зону защиты. Если совпали - урон 0.
        Если не совпали - расчет урона с учетом крита и брони.
        """
        self.state = "ATTACK"
        self.current_frame = 0
        
        if attack_zone == defense_zone:
            # Успешный блок противника
            enemy.blocks_by_zone[defense_zone] += 1
            return f"ЗАБЛОКИРОВАНО! ({attack_zone})"
        
        # Расчет критического удара
        roll = random.random()
        is_crit = roll <= self.crit_chance
        dmg_multiplier = self.сrit_damage if is_crit else 1
        damage = round(max(0, self.damage * dmg_multiplier - enemy.armor), 1)
        
        # Запись статистики для итогового экрана
        self.total_damage_dealt = round(self.total_damage_dealt + damage, 1)
        if is_crit: self.crit_count += 1
        self.hits_by_zone[attack_zone] += 1
        
        enemy.hp -= damage
        return f"{'КРИТ! ' if is_crit else ''}ПОПАДАНИЕ! ({attack_zone}) -{damage} HP"

# --- КЛАСС КНОПКИ БОЯ ---

class GameButton:
    """Интерактивная кнопка для выбора зоны удара/защиты"""
    def __init__(self, x, y, w, h, zone, side):
        self.rect = pygame.Rect(x, y, w, h)
        self.zone = zone
        self.side = side 
        self.is_hovered = False

    def draw(self, screen, font, is_selected, role_text):
        # Выбор цвета: золотой если нажата, серый если наведен курсор, темно-серый обычный
        bg = (180, 150, 0) if is_selected else ((100, 100, 100) if self.is_hovered else (40, 40, 40))
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2, border_radius=8)
        
        # Текст на кнопке (например: "АТАКА: ГОЛОВА")
        text_surf = font.render(f"{role_text}: {self.zone}", True, (255, 255, 255))
        screen.blit(text_surf, text_surf.get_rect(center=self.rect.center))

    def check_click(self, pos):
        """Проверяет, попадает ли координата клика в прямоугольник кнопки"""
        return self.rect.collidepoint(pos)

# --- ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ ---

pygame.init()
monitor = pygame.display.Info()
FULL_W, FULL_H = monitor.current_w, monitor.current_h
WINDOW_W, WINDOW_H = 1280, 720

is_fullscreen = True
SCREEN_WIDTH, SCREEN_HEIGHT = FULL_W, FULL_H
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Subota RPG")
clock = pygame.time.Clock()

# Создание оружия и игроков
p1 = Player("Игрок 1", 100, 15, 3, 0.3, 2.0, Weapon("Меч", 5, 0.1, 1.0), 'left', "images/p1_static.png", "images/p1_attack.gif")
p2 = Player("Игрок 2", 100, 10, 5, 0.35, 1.9, Weapon("Нож", 3, 0.3, 0.8), 'right', "images/p2_static.png", "images/p2_attack.gif")

# Глобальные переменные для ресурсов
background = None; splash_bg = None; font_ui = None; font_btn = None; ui_bg = None
img_attack = None; img_protect = None; img_ng_btn = None; img_back_btn = None
ng_btn_rect = None; back_btn_rect = None
p1_buttons = []; p2_buttons = []; combat_log = "БИТВА НАЧИНАЕТСЯ!"
attacker = p1; defender = p2

# Состояния игры
game_state = "MENU" # MENU, GAME, STATS
ng_offset_y = 0     # Смещение для анимации кнопки меню
back_offset_y = 0

def update_res():
    """
    Загружает и масштабирует все графические ресурсы при запуске или изменении разрешения.
    Использует resource_path для совместимости с EXE.
    """
    global background, splash_bg, font_ui, font_btn, p1_buttons, p2_buttons, ui_bg, img_attack, img_protect, img_ng_btn, img_back_btn, ng_btn_rect, back_btn_rect, SCREEN_WIDTH, SCREEN_HEIGHT
    
    # Фоны
    background = pygame.transform.scale(pygame.image.load(resource_path("images/back.png")).convert(), (SCREEN_WIDTH, SCREEN_HEIGHT))
    splash_bg = pygame.transform.scale(pygame.image.load(resource_path("images/splash.png")).convert(), (SCREEN_WIDTH, SCREEN_HEIGHT))
    
    # Кнопка главного меню
    ng_orig = pygame.image.load(resource_path("images/ng_buttom.png")).convert_alpha()
    btn_w = int(SCREEN_WIDTH * 0.25)
    btn_h = int(btn_w * (ng_orig.get_height() / ng_orig.get_width()))
    img_ng_btn = pygame.transform.smoothscale(ng_orig, (btn_w, btn_h))
    ng_btn_rect = img_ng_btn.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))
    
    # Кнопка возврата в меню
    back_orig = pygame.image.load(resource_path("images/back_to_menu.png")).convert_alpha()
    back_w = int(SCREEN_WIDTH * 0.18)
    back_h = int(back_w * (back_orig.get_height() / back_orig.get_width()))
    img_back_btn = pygame.transform.smoothscale(back_orig, (back_w, back_h))
    back_btn_rect = img_back_btn.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 0.88))
    
    # Текстуры UI боя
    ui_slab_orig = pygame.image.load(resource_path("images/hp_name_texture.png")).convert_alpha()
    slab_w = int(SCREEN_WIDTH * 0.32)
    slab_h = int(slab_w * (ui_slab_orig.get_height() / ui_slab_orig.get_width()))
    ui_bg = pygame.transform.smoothscale(ui_slab_orig, (slab_w, slab_h))
    
    icon_h = int(slab_h * 0.7)
    img_attack = pygame.transform.smoothscale(pygame.image.load(resource_path("images/attack_state.png")).convert_alpha(), (int(icon_h), int(icon_h)))
    img_protect = pygame.transform.smoothscale(pygame.image.load(resource_path("images/protect_status.png")).convert_alpha(), (int(icon_h), int(icon_h)))
    
    # Шрифты
    font_ui = pygame.font.SysFont("Arial", int(SCREEN_HEIGHT * 0.035), bold=True)
    font_btn = pygame.font.SysFont("Arial", int(SCREEN_HEIGHT * 0.025), bold=True)
    
    # Пересчет позиций игроков и кнопок зон
    p1.resize(SCREEN_WIDTH, SCREEN_HEIGHT); p2.resize(SCREEN_WIDTH, SCREEN_HEIGHT)
    b_w, b_h, side, start = int(SCREEN_WIDTH * 0.18), int(SCREEN_HEIGHT * 0.06), int(SCREEN_WIDTH * 0.08), int(SCREEN_HEIGHT * 0.40)
    p1_buttons = [GameButton(side, start + i*int(SCREEN_HEIGHT*0.08), b_w, b_h, z, 'left') for i, z in enumerate(ZONES)]
    p2_buttons = [GameButton(SCREEN_WIDTH - b_w - side, start + i*int(SCREEN_HEIGHT*0.08), b_w, b_h, z, 'right') for i, z in enumerate(ZONES)]

def draw_stats_screen():
    """Отрисовка финального экрана статистики в виде таблицы"""
    global back_offset_y
    screen.blit(splash_bg, (0, 0))
    
    # Полупрозрачная панель таблицы
    panel_w, panel_h = int(SCREEN_WIDTH * 0.7), int(SCREEN_HEIGHT * 0.65)
    panel_x, panel_y = (SCREEN_WIDTH - panel_w) // 2, (SCREEN_HEIGHT - panel_h) // 2 - 20
    overlay = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(overlay, (0, 0, 0, 220), overlay.get_rect(), border_radius=20)
    screen.blit(overlay, (panel_x, panel_y))
    pygame.draw.rect(screen, (180, 150, 0), (panel_x, panel_y, panel_w, panel_h), 3, border_radius=20)

    # Имя победителя сверху
    winner = p1 if p1.hp > 0 else p2
    title = font_ui.render(f"ИТОГИ БОЯ. ПОБЕДИТЕЛЬ: {winner.name.upper()}", True, (255, 215, 0))
    screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, panel_y + 30))

    # Сетка таблицы
    stats_font = pygame.font.SysFont("Arial", int(SCREEN_HEIGHT * 0.028), bold=True)
    rows_labels = ["УРОН", "КРИТЫ", "ЛЮБИМАЯ ЗОНА", "ЛУЧШАЯ ЗАЩИТА"]
    def get_max_z(d): return max(d, key=d.get) if sum(d.values()) > 0 else "—"
    
    col_w, row_h, header_y = panel_w // 3, (panel_h - 100) // 5, panel_y + 100
    p1_head, p2_head = stats_font.render(p1.name.upper(), True, (255, 255, 255)), stats_font.render(p2.name.upper(), True, (255, 255, 255))
    screen.blit(p1_head, (panel_x + col_w + (col_w - p1_head.get_width())//2, header_y))
    screen.blit(p2_head, (panel_x + 2*col_w + (col_w - p2_head.get_width())//2, header_y))

    # Рисуем линии сетки
    pygame.draw.line(screen, (80, 80, 80), (panel_x + col_w, header_y - 10), (panel_x + col_w, panel_y + panel_h - 20), 2)
    pygame.draw.line(screen, (80, 80, 80), (panel_x + 2*col_w, header_y - 10), (panel_x + 2*col_w, panel_y + panel_h - 20), 2)
    pygame.draw.line(screen, (180, 150, 0), (panel_x + 20, header_y + 40), (panel_x + panel_w - 20, header_y + 40), 2)

    # Отрисовка строк с данными
    for i, label in enumerate(rows_labels):
        y = header_y + 70 + i * row_h
        screen.blit(stats_font.render(label, True, (180, 150, 0)), (panel_x + 30, y))
        
        # Получаем данные на основе текущей строки
        if i == 0: v1, v2 = str(p1.total_damage_dealt), str(p2.total_damage_dealt)
        elif i == 1: v1, v2 = str(p1.crit_count), str(p2.crit_count)
        elif i == 2: v1, v2 = get_max_z(p1.hits_by_zone), get_max_z(p2.hits_by_zone)
        else: v1, v2 = get_max_z(p1.blocks_by_zone), get_max_z(p2.blocks_by_zone)
        
        s1, s2 = stats_font.render(v1, True, (255, 255, 255)), stats_font.render(v2, True, (255, 255, 255))
        screen.blit(s1, (panel_x + col_w + (col_w - s1.get_width())//2, y))
        screen.blit(s2, (panel_x + 2*col_w + (col_w - s2.get_width())//2, y))
        
        if i < len(rows_labels) - 1:
            pygame.draw.line(screen, (50, 50, 50), (panel_x + 20, y + 45), (panel_x + panel_w - 20, y + 45), 1)

    # Анимация и отрисовка кнопки "В МЕНЮ"
    t_offset = -10 if back_btn_rect.collidepoint(pygame.mouse.get_pos()) else 0
    back_offset_y += (t_offset - back_offset_y) * 0.15
    screen.blit(img_back_btn, (back_btn_rect.x, back_btn_rect.y + back_offset_y))

# Первичная загрузка
update_res()

is_animating = False; running = True

# --- ИГРОВОЙ ЦИКЛ ---

while running:
    mouse_pos = pygame.mouse.get_pos()
    
    # 1. ОБРАБОТКА СОБЫТИЙ
    for event in pygame.event.get():
        if event.type == pygame.QUIT: 
            running = False
            
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            # Переключение полноэкранного режима
            is_fullscreen = not is_fullscreen
            W, H = (FULL_W, FULL_H) if is_fullscreen else (WINDOW_W, WINDOW_H)
            screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN if is_fullscreen else pygame.RESIZABLE)
            SCREEN_WIDTH, SCREEN_HEIGHT = W, H
            update_res()
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == "MENU":
                # Учитываем смещение анимации при проверке клика
                if ng_btn_rect.move(0, ng_offset_y).collidepoint(event.pos): 
                    p1.reset_stats(); p2.reset_stats(); combat_log = "БИТВА НАЧИНАЕТСЯ!"; game_state = "GAME"
            
            elif game_state == "GAME" and not is_animating:
                # Клик по кнопкам выбора зон для обоих игроков
                if p1.hp > 0 and p2.hp > 0:
                    for b in p1_buttons:
                        if b.check_click(event.pos): p1.current_choice = b.zone
                    for b in p2_buttons:
                        if b.check_click(event.pos): p2.current_choice = b.zone
                    
                    # Если оба сделали выбор - запускаем ход
                    if p1.current_choice and p2.current_choice:
                        combat_log = attacker.perform_attack(defender, attacker.current_choice, defender.current_choice)
                        is_animating = True
            
            elif game_state == "STATS":
                if back_btn_rect.move(0, back_offset_y).collidepoint(event.pos): 
                    game_state = "MENU"

        if event.type == pygame.VIDEORESIZE and not is_fullscreen: 
            SCREEN_WIDTH, SCREEN_HEIGHT = event.w, event.h; update_res()

    # 2. ЛОГИКА И ОБНОВЛЕНИЕ СОСТОЯНИЙ
    
    if game_state == "MENU":
        screen.blit(splash_bg, (0, 0))
        # Плавная анимация подъема кнопки при наведении
        target_offset = -10 if ng_btn_rect.collidepoint(mouse_pos) else 0
        ng_offset_y += (target_offset - ng_offset_y) * 0.15
        screen.blit(img_ng_btn, (ng_btn_rect.x, ng_btn_rect.y + ng_offset_y))
        
    elif game_state == "GAME":
        # Обновление кадров гифок
        if p1.update() or p2.update(): 
            is_animating = False
            p1.current_choice = None; p2.current_choice = None
            attacker, defender = defender, attacker # Смена ролей (кто атакует, кто защищается)
            
        # Отрисовка фона и персонажей (атакующий рисуется поверх защищающегося)
        screen.blit(background, (0, 0))
        if defender == p1: p1.draw_char(screen); p2.draw_char(screen)
        else: p2.draw_char(screen); p1.draw_char(screen)
        
        # Отрисовка UI
        p1.draw_ui(screen, font_ui, SCREEN_WIDTH, SCREEN_HEIGHT, (attacker == p1), ui_bg, img_attack, img_protect)
        p2.draw_ui(screen, font_ui, SCREEN_WIDTH, SCREEN_HEIGHT, (attacker == p2), ui_bg, img_attack, img_protect)
        
        # Отрисовка кнопок выбора зон
        for b in p1_buttons: 
            b.is_hovered = b.check_click(mouse_pos)
            b.draw(screen, font_btn, p1.current_choice == b.zone, "АТАКА" if attacker == p1 else "ЗАЩИТА")
        for b in p2_buttons: 
            b.is_hovered = b.check_click(mouse_pos)
            b.draw(screen, font_btn, p2.current_choice == b.zone, "АТАКА" if attacker == p2 else "ЗАЩИТА")
            
        # Лог боя или переход к статистике
        if p1.hp > 0 and p2.hp > 0: 
            draw_status_box(screen, combat_log, font_ui, SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.28))
        elif not is_animating: 
            game_state = "STATS"

    elif game_state == "STATS":
        draw_stats_screen()

    # 3. ОБНОВЛЕНИЕ ЭКРАНА
    pygame.display.flip()
    clock.tick(60) # Лимит 60 кадров в секунду

pygame.quit()