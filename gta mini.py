# GTA Mini — Versión extendida completa en Pygame
import pygame
import sys
import math
import random
from collections import deque
import json
from pathlib import Path

# --- Inicialización ---
pygame.init()
pygame.font.init()
pygame.mixer.init()

W, H = 960, 640
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("GTA Mini — Extended")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 20)
BIGFONT = pygame.font.SysFont(None, 28)

MAP_W, MAP_H = 3000, 3000

# Colores
GRASS = (34, 120, 40)
ROAD = (80, 80, 80)
BUILDING = (40, 36, 36)
PLAYER_COLOR = (10, 200, 120)
CAR_COLOR = (200, 50, 50)
POLICE_COLOR = (40, 120, 220)
NPC_COLOR = (200, 180, 80)
BULLET_COLOR = (255, 240, 120)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Assets
ASSETS = Path("assets")
ASSETS.mkdir(exist_ok=True)

def try_load_sound(name):
    path = ASSETS / name
    if path.exists():
        try:
            return pygame.mixer.Sound(str(path))
        except Exception:
            return None
    return None

SND_SHOOT = try_load_sound("shoot.wav")
SND_ENTER = try_load_sound("enter.wav")
SND_WANTED = try_load_sound("wanted.wav")

# --- Funciones auxiliares ---
def clamp(v, a, b):
    return max(a, min(b, v))

def distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

# --- Clases ---
class Camera:
    def __init__(self, w, h):
        self.x = 0
        self.y = 0
        self.w = w
        self.h = h

    def update(self, target):
        tx = target.x if hasattr(target,'x') else target[0]
        ty = target.y if hasattr(target,'y') else target[1]
        self.x = int(clamp(tx - W//2, 0, MAP_W - W))
        self.y = int(clamp(ty - H//2, 0, MAP_H - H))

    def to_screen(self, pos):
        return pos[0]-self.x, pos[1]-self.y

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.w = 18
        self.h = 26
        self.angle = 0
        self.speed = 3.6
        self.in_vehicle = None
        self.health = 100
        self.weapon = 0
        self.ammo = [80, 12]  # Pistola, escopeta
        self.fire_cooldown = 0
        self.money = 0

    def update(self, keys, dt):
        if self.in_vehicle:
            return
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if dx or dy:
            l = math.hypot(dx, dy) or 1
            self.x += dx/l * self.speed
            self.y += dy/l * self.speed
        self.x = clamp(self.x, 5, MAP_W-5)
        self.y = clamp(self.y, 5, MAP_H-5)

    def draw(self, surf, cam):
        sx, sy = cam.to_screen((self.x, self.y))
        pygame.draw.rect(surf, PLAYER_COLOR, (sx-self.w/2, sy-self.h/2, self.w, self.h))
        gx = sx + math.cos(self.angle)*16
        gy = sy + math.sin(self.angle)*16
        pygame.draw.line(surf, (30,50,30),(sx,sy),(gx,gy),4)

class Vehicle:
    def __init__(self, x, y, color=CAR_COLOR, police=False):
        self.x = x
        self.y = y
        self.w = 28
        self.h = 50
        self.color = color
        self.speed = 0
        self.max_speed = 4 if not police else 5
        self.angle = 0
        self.driver = None
        self.police = police

    def update(self, player=None):
        if self.driver is None and self.police and player:
            # Movimiento simple: perseguir jugador
            dx = player.x - self.x
            dy = player.y - self.y
            self.angle = math.atan2(dy, dx)
            self.speed = self.max_speed
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.x = clamp(self.x, 0, MAP_W)
        self.y = clamp(self.y, 0, MAP_H)

    def draw(self, surf, cam):
        sx, sy = cam.to_screen((self.x, self.y))
        pygame.draw.rect(surf, self.color, (sx-self.w/2, sy-self.h/2, self.w, self.h))

class Bullet:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 10

    def update(self):
        self.x += math.cos(self.angle)*self.speed
        self.y += math.sin(self.angle)*self.speed

    def draw(self, surf, cam):
        sx, sy = cam.to_screen((self.x, self.y))
        pygame.draw.circle(surf, BULLET_COLOR, (int(sx), int(sy)), 4)

class Mission:
    def __init__(self):
        self.active = False
        self.target_vehicle = None
        self.delivery_point = (0,0)

    def start_steal_car(self, game):
        cars = [v for v in game.vehicles if not v.police and v.driver is None]
        if cars:
            self.target_vehicle = random.choice(cars)
            self.delivery_point = (random.randint(100, MAP_W-100), random.randint(100, MAP_H-100))
            self.active = True
            game.add_message("Mission: Steal the car and deliver it!")

class Game:
    def __init__(self):
        self.player = Player(W//2, H//2)
        self.vehicles = [Vehicle(random.randint(100, MAP_W-100), random.randint(100, MAP_H-100)) for _ in range(10)]
        self.vehicles += [Vehicle(random.randint(100, MAP_W-100), random.randint(100, MAP_H-100), color=POLICE_COLOR, police=True) for _ in range(3)]
        self.bullets = []
        self.camera = Camera(W,H)
        self.mission = Mission()
        self.message_queue = deque(maxlen=5)
        self.minimap = True
        self.time = 0

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.player.update(keys, dt)
        for v in self.vehicles:
            v.update(self.player)
        for b in self.bullets:
            b.update()
        self.camera.update(self.player)
        self.time += dt

    def draw(self, surf):
        surf.fill(GRASS)
        for v in self.vehicles:
            v.draw(surf, self.camera)
        for b in self.bullets:
            b.draw(surf, self.camera)
        self.player.draw(surf, self.camera)
        # HUD
        health_text = FONT.render(f"Health: {self.player.health}", True, WHITE)
        surf.blit(health_text, (8,8))
        if self.mission.active:
            mission_text = FONT.render("Mission Active!", True, WHITE)
            surf.blit(mission_text, (8,28))

    def fire_weapon(self):
        if self.player.fire_cooldown<=0 and self.player.ammo[self.player.weapon]>0:
            angle = self.player.angle
            b = Bullet(self.player.x + math.cos(angle)*20, self.player.y + math.sin(angle)*20, angle)
            self.bullets.append(b)
            self.player.ammo[self.player.weapon] -= 1
            self.player.fire_cooldown = 0.2
            if SND_SHOOT: SND_SHOOT.play()
            self.add_message("Bang!")

    def add_message(self, text):
        self.message_queue.appendleft(text)

    def queue_messages(self, surf):
        for i, msg in enumerate(self.message_queue):
            r = FONT.render(msg, True, WHITE)
            surf.blit(r, (8, 32 + i*20))

    def try_enter_vehicle(self):
        for v in self.vehicles:
            if distance((self.player.x,self.player.y),(v.x,v.y))<40 and not v.police:
                self.player.in_vehicle = v
                v.driver = self.player
                self.add_message("Entered vehicle!")
                if SND_ENTER: SND_ENTER.play()
                return

    def save(self):
        data = {
            'player': {'x': self.player.x, 'y': self.player.y, 'health': self.player.health, 'money': self.player.money}
        }
        with open("savegame.json", "w") as f:
            json.dump(data,f)
        self.add_message("Game saved.")

    def load(self):
        if not Path("savegame.json").exists():
            self.add_message("No save file found.")
            return
        with open("savegame.json","r") as f:
            data = json.load(f)
        self.player.x = data['player']['x']
        self.player.y = data['player']['y']
        self.player.health = data['player']['health']
        self.player.money = data['player']['money']
        self.add_message("Game loaded.")

# --- Instanciación del juego ---
game = Game()

# --- Loop principal ---
mouse_held = False
shoot_hold_timer = 0
running = True

while running:
    dt = clock.tick(60)/1000.0
    game.player.fire_cooldown = max(0, game.player.fire_cooldown - dt)

    for event in pygame.event.get():
        if event.type==pygame.QUIT: running=False
        elif event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE: running=False
            elif event.key==pygame.K_e: game.try_enter_vehicle()
            elif event.key==pygame.K_1: game.player.weapon=0
            elif event.key==pygame.K_2: game.player.weapon=1
            elif event.key==pygame.K_m: game.minimap = not game.minimap
            elif event.key==pygame.K_k: game.save()
            elif event.key==pygame.K_l: game.load()
            elif event.key==pygame.K_q and not game.mission.active: game.mission.start_steal_car(game)
        elif event.type==pygame.MOUSEBUTTONDOWN:
            if event.button==1:
                mouse_held=True
                game.fire_weapon()
        elif event.type==pygame.MOUSEBUTTONUP:
            if event.button==1: mouse_held=False

    if mouse_held:
        shoot_hold_timer += dt
        if game.player.weapon==0 and shoot_hold_timer>0.14:
            game.fire_weapon()
            shoot_hold_timer=0
    else:
        shoot_hold_timer=0

    game.update(dt)
    game.draw(screen)
    game.queue_messages(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
