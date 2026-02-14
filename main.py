import pygame
import random
import os
import sys
import threading
import traceback
from PIL import Image
import db_manager as db
import bot_main

# --- КОНСТАНТЫ ---
HEAD, TORSO, LEGS = "ГОЛОВА", "КОРПУС", "НОГИ"
ZONES = [HEAD, TORSO, LEGS]

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def draw_status_box(screen, text, font, center_x, y, padding=15):
    if not text: return
    text_surf = font.render(text, True, (255, 255, 255))
    w, h = text_surf.get_width() + padding * 4, text_surf.get_height() + padding * 2
    x = center_x - w // 2
    overlay = pygame.Surface((w, h), pygame.SRCALPHA); pygame.draw.rect(overlay, (20, 20, 20, 180), (0, 0, w, h), border_radius=12)
    screen.blit(overlay, (x, y))
    pygame.draw.rect(screen, (200, 200, 200), (x, y, w, h), 1, border_radius=12)
    pygame.draw.rect(screen, (180, 150, 0), (x + 3, y + 3, w - 6, h - 6), 2, border_radius=9)
    screen.blit(text_surf, (center_x - text_surf.get_width() // 2, y + padding))

class Weapon:
    def __init__(self, name, bonus_damage, bonus_crit_chance, bonus_сrit_damage):
        self.name = name; self.bonus_damage = bonus_damage
        self.bonus_crit_chance = bonus_crit_chance; self.bonus_сrit_damage = bonus_сrit_damage

class Player:
    def __init__(self, name, hp, damage, armor, crit_chance, сrit_damage, weapon, side, static_img, attack_gif):
        self.name = name; self.max_hp = hp; self.side = side
        self.damage = damage + weapon.bonus_damage; self.armor = armor
        self.crit_chance = crit_chance + weapon.bonus_crit_chance
        self.сrit_damage = сrit_damage + weapon.bonus_сrit_damage
        self.static_image_orig = pygame.image.load(resource_path(static_img)).convert_alpha()
        self.attack_frames_orig = self._load_gif_frames(resource_path(attack_gif))
        self.state = "IDLE"; self.current_frame = 0; self.animation_speed = 0.17; self.image = None
        self.reset_stats()

    def reset_stats(self):
        self.hp = self.max_hp; self.total_damage_dealt = 0; self.crit_count = 0; self.current_choice = None
        self.hits_by_zone = {HEAD: 0, TORSO: 0, LEGS: 0}; self.blocks_by_zone = {HEAD: 0, TORSO: 0, LEGS: 0}

    def _load_gif_frames(self, path):
        pil_gif = Image.open(path); frames = []
        for i in range(pil_gif.n_frames):
            pil_gif.seek(i); frame = pil_gif.convert("RGBA")
            pygame_surface = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode)
            frames.append(pygame_surface)
        return frames

    def resize(self, screen_w, screen_h):
        target_h = int(screen_h * 0.55)
        w_ratio = self.static_image_orig.get_width() / self.static_image_orig.get_height()
        self.static_image = pygame.transform.smoothscale(self.static_image_orig, (int(target_h * w_ratio), target_h))
        self.attack_frames = [pygame.transform.smoothscale(f, (int(target_h * (f.get_width()/f.get_height())), target_h)) for f in self.attack_frames_orig]
        self.image = self.static_image if self.state == "IDLE" else self.attack_frames[min(int(self.current_frame), len(self.attack_frames)-1)]
        self.rect = self.image.get_rect()
        x_pos = int(screen_w * 0.38) if self.side == 'left' else int(screen_w * 0.62)
        self.rect.midbottom = (x_pos, int(screen_h * 0.9))

    def update(self):
        if self.state == "ATTACK":
            self.current_frame += self.animation_speed
            if self.current_frame >= len(self.attack_frames):
                self.state = "IDLE"; self.current_frame = 0; self.image = self.static_image; return True 
            else: self.image = self.attack_frames[int(self.current_frame)]
        return False

    def draw_char(self, screen):
        if self.image: screen.blit(self.image, self.rect)

    def draw_ui(self, screen, font, screen_w, screen_h, is_attacker, ui_bg, img_atk, img_def):
        bar_w, bar_h, margin_y = int(screen_w * 0.23), int(screen_h * 0.028), int(screen_h * 0.11)
        slab_w, slab_h = ui_bg.get_size()
        slab_x = int(screen_w * 0.1) if self.side == 'left' else int(screen_w * 0.9 - slab_w)
        screen.blit(ui_bg, (slab_x, margin_y - int(slab_h * 0.4)))
        x = slab_x + (slab_w - bar_w) // 2
        name_s = font.render(self.name, True, (240, 240, 240)); screen.blit(name_s, (x if self.side == 'left' else x + bar_w - name_s.get_width(), margin_y - name_s.get_height() - 4))
        pygame.draw.rect(screen, (30, 30, 30), (x, margin_y, bar_w, bar_h), border_radius=6)
        fill_w = int(bar_w * (max(0, self.hp) / self.max_hp))
        if fill_w > 0: pygame.draw.rect(screen, (46, 204, 113) if self.hp > 30 else (231, 76, 60), (x if self.side == 'left' else x + (bar_w - fill_w), margin_y, fill_w, bar_h), border_radius=6)
        pygame.draw.rect(screen, (200, 200, 200), (x, margin_y, bar_w, bar_h), 2, border_radius=6)
        status_text = "ГОТОВ!" if self.current_choice else "ВЫБИРАЕТ..."
        st_surf = font.render(status_text, True, (46, 204, 113) if self.current_choice else (255, 255, 255))
        screen.blit(st_surf, (x if self.side == 'left' else x + bar_w - st_surf.get_width(), margin_y + bar_h + 5))
        icon = img_atk if is_attacker else img_def
        icon_x = x + bar_w + 10 if self.side == 'left' else x - icon.get_width() - 10
        screen.blit(icon, (icon_x, margin_y + (bar_h // 2) - (icon.get_height() // 2)))

    def perform_attack(self, enemy, atk_z, def_z):
        self.state = "ATTACK"; self.current_frame = 0
        if atk_z == def_z: enemy.blocks_by_zone[def_z] += 1; return f"ЗАБЛОКИРОВАНО! ({atk_z})"
        is_crit = random.random() <= self.crit_chance; dmg = round(max(0, self.damage * (self.сrit_damage if is_crit else 1) - enemy.armor), 1)
        self.total_damage_dealt = round(self.total_damage_dealt + dmg, 1); self.hits_by_zone[atk_z] += 1
        if is_crit: self.crit_count += 1
        enemy.hp -= dmg; return f"{'КРИТ! ' if is_crit else ''}ПОПАДАНИЕ! ({atk_z}) -{dmg} HP"

class GameButton:
    def __init__(self, x, y, w, h, zone, side):
        self.rect = pygame.Rect(x, y, w, h); self.zone = zone; self.is_hovered = False
    def draw(self, screen, font, is_selected, role_text, active):
        if not active: return 
        bg = (180, 150, 0) if is_selected else ((100, 100, 100) if self.is_hovered else (40, 40, 40))
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2, border_radius=8)
        txt = font.render(f"{role_text}: {self.zone}", True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=self.rect.center))
    def check_click(self, pos): return self.rect.collidepoint(pos)

# --- ИНИЦИАЛИЗАЦИЯ ---
pygame.init()
db.init_db()
monitor_info = pygame.display.Info()
FULL_W, FULL_H = monitor_info.current_w, monitor_info.current_h
WINDOW_W, WINDOW_H = 1280, 720
is_fullscreen = True
SCREEN_WIDTH, SCREEN_HEIGHT = FULL_W, FULL_H
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.DOUBLEBUF)
clock = pygame.time.Clock()

p1 = Player("Игрок 1", 100, 15, 3, 0.3, 2.0, Weapon("Клеймор", 10, 0.1, 1.1), 'left', "images/p1_static.png", "images/p1_attack.gif")
p2 = Player("Игрок 2", 100, 10, 5, 0.35, 1.9, Weapon("Стилет", 7, 0.4, 0.4), 'right', "images/p2_static.png", "images/p2_attack.gif")
threading.Thread(target=bot_main.run_bot, daemon=True).start()

game_state = "MENU"; session_id = "000000"
background = None; splash_bg = None; ui_bg = None; font_ui = None; font_btn = None
img_attack = None; img_protect = None; img_ng_btn = None; img_back_btn = None
ng_btn_rect = None; back_btn_rect = None; connect_btn_rect = None
p1_buttons = []; p2_buttons = []; combat_log = ""; attacker = p1; defender = p2
ng_offset_y = 0; back_offset_y = 0

def update_res():
    global background, splash_bg, ui_bg, font_ui, font_btn, img_attack, img_protect, img_ng_btn, img_back_btn, ng_btn_rect, back_btn_rect, connect_btn_rect, p1_buttons, p2_buttons, SCREEN_WIDTH, SCREEN_HEIGHT
    background = pygame.transform.scale(pygame.image.load(resource_path("images/back.png")).convert(), (SCREEN_WIDTH, SCREEN_HEIGHT))
    splash_bg = pygame.transform.scale(pygame.image.load(resource_path("images/splash.png")).convert(), (SCREEN_WIDTH, SCREEN_HEIGHT))
    ng_orig = pygame.image.load(resource_path("images/ng_buttom.png")).convert_alpha()
    btn_w, btn_h = int(SCREEN_WIDTH * 0.25), int(int(SCREEN_WIDTH * 0.25) * (ng_orig.get_height()/ng_orig.get_width()))
    img_ng_btn = pygame.transform.smoothscale(ng_orig, (btn_w, btn_h))
    ng_btn_rect = img_ng_btn.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))
    connect_btn_rect = img_ng_btn.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 0.75))
    back_orig = pygame.image.load(resource_path("images/back_to_menu.png")).convert_alpha()
    b_w = int(SCREEN_WIDTH*0.18); img_back_btn = pygame.transform.smoothscale(back_orig, (b_w, int(b_w * (back_orig.get_height()/back_orig.get_width()))))
    back_btn_rect = img_back_btn.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 0.88))
    ui_slab_orig = pygame.image.load(resource_path("images/hp_name_texture.png")).convert_alpha()
    s_w = int(SCREEN_WIDTH * 0.32); slab_h = int(s_w * (ui_slab_orig.get_height()/ui_slab_orig.get_width())); ui_bg = pygame.transform.smoothscale(ui_slab_orig, (s_w, slab_h))
    img_attack = pygame.transform.smoothscale(pygame.image.load(resource_path("images/attack_state.png")).convert_alpha(), (int(slab_h*0.7), int(slab_h*0.7)))
    img_protect = pygame.transform.smoothscale(pygame.image.load(resource_path("images/protect_status.png")).convert_alpha(), (int(slab_h*0.7), int(slab_h*0.7)))
    font_ui, font_btn = pygame.font.SysFont("Arial", int(SCREEN_HEIGHT*0.035), bold=True), pygame.font.SysFont("Arial", int(SCREEN_HEIGHT*0.025), bold=True)
    p1.resize(SCREEN_WIDTH, SCREEN_HEIGHT); p2.resize(SCREEN_WIDTH, SCREEN_HEIGHT)
    btn_w, btn_h, side, start = int(SCREEN_WIDTH*0.18), int(SCREEN_HEIGHT*0.06), int(SCREEN_WIDTH*0.08), int(SCREEN_HEIGHT*0.40)
    p1_buttons = [GameButton(side, start+i*int(SCREEN_HEIGHT*0.08), btn_w, btn_h, z, 'left') for i, z in enumerate(ZONES)]
    p2_buttons = [GameButton(SCREEN_WIDTH-btn_w-side, start+i*int(SCREEN_HEIGHT*0.08), btn_w, btn_h, z, 'right') for i, z in enumerate(ZONES)]

def draw_stats_screen():
    global back_offset_y
    screen.blit(splash_bg, (0, 0))
    panel_w, panel_h = int(SCREEN_WIDTH * 0.7), int(SCREEN_HEIGHT * 0.65)
    p_x, p_y = (SCREEN_WIDTH - panel_w) // 2, (SCREEN_HEIGHT - panel_h) // 2 - 20
    overlay = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA); pygame.draw.rect(overlay, (0, 0, 0, 220), overlay.get_rect(), border_radius=20); screen.blit(overlay, (p_x, p_y))
    pygame.draw.rect(screen, (180, 150, 0), (p_x, p_y, panel_w, panel_h), 3, border_radius=20)
    winner = p1 if p1.hp > 0 else p2
    title = font_ui.render(f"ИТОГИ БОЯ. ПОБЕДИТЕЛЬ: {winner.name.upper()}", True, (255, 215, 0)); screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, p_y + 30))
    st_f = pygame.font.SysFont("Arial", int(SCREEN_HEIGHT * 0.028), bold=True)
    rows = ["УРОН", "КРИТЫ", "ЛЮБИМАЯ ЗОНА", "ЛУЧШАЯ ЗАЩИТА"]
    col_w, row_h, hy = panel_w // 3, (panel_h - 100) // 5, p_y + 100
    p1h, p2h = st_f.render(p1.name.upper(), True, (255, 255, 255)), st_f.render(p2.name.upper(), True, (255, 255, 255))
    screen.blit(p1h, (p_x + col_w + (col_w - p1h.get_width())//2, hy)); screen.blit(p2h, (p_x + 2*col_w + (col_w - p2h.get_width())//2, hy))
    pygame.draw.line(screen, (180, 150, 0), (p_x + 20, hy + 40), (p_x + panel_w - 20, hy + 40), 2)
    def get_z(d): return max(d, key=d.get) if sum(d.values()) > 0 else "—"
    for i, label in enumerate(rows):
        y = hy + 70 + i * row_h; screen.blit(st_f.render(label, True, (180, 150, 0)), (p_x + 30, y))
        v1, v2 = (str(p1.total_damage_dealt), str(p2.total_damage_dealt)) if i==0 else (str(p1.crit_count), str(p2.crit_count)) if i==1 else (get_z(p1.hits_by_zone), get_z(p2.hits_by_zone)) if i==2 else (get_z(p1.blocks_by_zone), get_z(p2.blocks_by_zone))
        s1, s2 = st_f.render(v1, True, (255, 255, 255)), st_f.render(v2, True, (255, 255, 255))
        screen.blit(s1, (p_x + col_w + (col_w - s1.get_width())//2, y)); screen.blit(s2, (p_x + 2*col_w + (col_w - s2.get_width())//2, y))
    t_off = -10 if back_btn_rect.collidepoint(pygame.mouse.get_pos()) else 0; back_offset_y += (t_off - back_offset_y) * 0.15; screen.blit(img_back_btn, (back_btn_rect.x, back_btn_rect.y + back_offset_y))

update_res()
running = True; is_animating = False

while running:
    try:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                is_fullscreen = not is_fullscreen
                SCREEN_WIDTH, SCREEN_HEIGHT = (FULL_W, FULL_H) if is_fullscreen else (WINDOW_W, WINDOW_H)
                screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN if is_fullscreen else pygame.RESIZABLE)
                update_res()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_state == "MENU" and ng_btn_rect.move(0, ng_offset_y).collidepoint(event.pos):
                    session_id = str(random.randint(100000, 999999)); db.create_session(session_id, 'left'); game_state = "CONNECT"
                elif game_state == "CONNECT" and connect_btn_rect.collidepoint(event.pos):
                    p1.reset_stats(); p2.reset_stats(); combat_log = "БИТВА НАЧИНАЕТСЯ!"; game_state = "GAME"
                elif game_state == "GAME" and not is_animating:
                    for b in p1_buttons:
                        if b.check_click(event.pos) and not p1.current_choice: db.set_choice(session_id, 1, b.zone)
                    for b in p2_buttons:
                        if b.check_click(event.pos) and not p2.current_choice: db.set_choice(session_id, 2, b.zone)
                elif game_state == "STATS" and back_btn_rect.move(0, back_offset_y).collidepoint(event.pos): game_state = "MENU"

        if game_state == "MENU":
            screen.blit(splash_bg, (0, 0)); target = -10 if ng_btn_rect.collidepoint(mouse_pos) else 0; ng_offset_y += (target - ng_offset_y) * 0.15; screen.blit(img_ng_btn, (ng_btn_rect.x, ng_btn_rect.y + ng_offset_y))
        elif game_state == "CONNECT":
            screen.blit(splash_bg, (0, 0)); draw_status_box(screen, f"КОД ДЛЯ БОТА: {session_id}", font_ui, SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100); draw_status_box(screen, "ПОДКЛЮЧИТЕСЬ К БОТУ И НАЖМИТЕ ДАЛЕЕ", font_btn, SCREEN_WIDTH//2, SCREEN_HEIGHT//2); screen.blit(img_ng_btn, connect_btn_rect); ds = font_btn.render("ДАЛЕЕ", True, (255,255,255)); screen.blit(ds, ds.get_rect(center=connect_btn_rect.center))
        elif game_state == "GAME":
            data = db.get_session_data(session_id)
            if data: p1.current_choice, p2.current_choice = data['p1_choice'], data['p2_choice']
            if p1.current_choice and p2.current_choice and not is_animating: combat_log = attacker.perform_attack(defender, p1.current_choice if attacker == p1 else p2.current_choice, p2.current_choice if attacker == p1 else p1.current_choice); is_animating = True
            if p1.update() or p2.update(): is_animating = False; attacker, defender = defender, attacker; db.clear_choices(session_id, attacker.side)
            screen.blit(background, (0, 0))
            if defender == p1: p1.draw_char(screen); p2.draw_char(screen)
            else: p2.draw_char(screen); p1.draw_char(screen)
            p1.draw_ui(screen, font_ui, SCREEN_WIDTH, SCREEN_HEIGHT, (attacker == p1), ui_bg, img_attack, img_protect); p2.draw_ui(screen, font_ui, SCREEN_WIDTH, SCREEN_HEIGHT, (attacker == p2), ui_bg, img_attack, img_protect)
            for b in p1_buttons: b.is_hovered = b.check_click(mouse_pos); b.draw(screen, font_btn, p1.current_choice == b.zone, "АТАКА" if attacker == p1 else "ЗАЩИТА", not p1.current_choice)
            for b in p2_buttons: b.is_hovered = b.check_click(mouse_pos); b.draw(screen, font_btn, p2.current_choice == b.zone, "АТАКА" if attacker == p2 else "ЗАЩИТА", not p2.current_choice)
            if p1.hp > 0 and p2.hp > 0: draw_status_box(screen, combat_log, font_ui, SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.28))
            elif not is_animating: game_state = "STATS"
            screen.blit(pygame.font.SysFont("Arial", 20).render(f"CODE: {session_id}", True, (200,200,200)), (20, SCREEN_HEIGHT - 40))
        elif game_state == "STATS": draw_stats_screen()

        pygame.display.flip(); clock.tick(60)
    except Exception:
        print(traceback.format_exc()); running = False

pygame.quit()