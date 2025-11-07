# gta_full.py - Mini GTA completo (Pygame)
# Requisitos: Python 3.8+, pygame
# Coloca opcionalmente sprites/sonidos en ./assets/ con nombres indicados.

import pygame
import os
import sys
import math
import random
import json
import time
from pathlib import Path
from collections import deque

# ------------------ Inicialización segura ------------------
pygame.init()
try:
    pygame.font.init()
except:
    pass
try:
    pygame.mixer.init()
except:
    pass

# ------------------ Rutas y carga segura ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

def safe_load_image(name, size=None, fallback_color=(255,255,255)):
    path = os.path.join(ASSETS_DIR, name)
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            if size:
                img = pygame.transform.smoothscale(img, size)
            return img
        except Exception as e:
            print(f"Warning: failed loading image {name}: {e}")
    # fallback surface
    if size is None: size = (40,40)
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill(fallback_color)
    return surf

def safe_load_sound(name):
    path = os.path.join(ASSETS_DIR, name)
    if os.path.exists(path):
        try:
            return pygame.mixer.Sound(path)
        except Exception as e:
            print(f"Warning: failed loading sound {name}: {e}")
    return None

# ------------------ Configuración de ventana / mapa ------------------
WIDTH, HEIGHT = 1280, 720
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mini GTA — Full")
CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 20)
BIG = pygame.font.SysFont(None, 28)

MAP_W, MAP_H = 3500, 2700

# ------------------ Sprites / sonidos (opcionales) ------------------
PLAYER_IMG = safe_load_image("player.png", (44,44), (240,240,240))
CAR_IMG = safe_load_image("car.png", (72,44), (130,130,220))
POLICE_IMG = safe_load_image("police.png", (48,48), (220,80,80))
BULLET_IMG = safe_load_image("bullet.png", (8,8), (255,220,80))
BUILDING_IMG = safe_load_image("building.png", (120,120), (110,110,110))

SND_SHOOT = safe_load_sound("shoot.wav")
SND_ENTER = safe_load_sound("enter.wav")
SND_WANTED = safe_load_sound("wanted.wav")
SND_ENGINE = safe_load_sound("engine.wav")

# ------------------ Colores y parámetros ------------------
GRASS = (34,120,40)
ROAD = (84,84,84)
BUILDING_COL = (36,34,34)
PLAYER_COLOR = (30,150,220)
CAR_COLOR = (200,50,50)
POLICE_COLOR = (40,120,220)
WHITE = (255,255,255)
BLACK = (0,0,0)
BULLET_COLOR = (255,220,80)

# Gameplay params
NUM_CARS = 45
NUM_NPCS = 90
NUM_POLICE_PEOPLE = 18
NUM_POLICE_CARS = 8
MAX_WANTED = 5

# ------------------ Utilidades ------------------
def clamp(v,a,b): return max(a, min(v, b))
def distance(a,b): return math.hypot(a[0]-b[0], a[1]-b[1])

# ------------------ Cámara ------------------
class Camera:
    def __init__(self,w,h):
        self.x = 0; self.y = 0; self.w=w; self.h=h
    def update(self, target):
        if hasattr(target,'x') and hasattr(target,'y'):
            tx,ty = target.x, target.y
        else:
            tx,ty = target
        self.x = int(clamp(tx - WIDTH//2, 0, MAP_W - WIDTH))
        self.y = int(clamp(ty - HEIGHT//2, 0, MAP_H - HEIGHT))
    def to_screen(self, pos):
        return pos[0]-self.x, pos[1]-self.y

camera = Camera(WIDTH, HEIGHT)

# ------------------ Mundo (roads + buildings con hitboxes) ------------------
class World:
    def __init__(self):
        self.roads = []
        # grid roads
        for y in range(200, MAP_H, 400):
            self.roads.append(pygame.Rect(0,y,MAP_W,100))
        for x in range(200, MAP_W, 400):
            self.roads.append(pygame.Rect(x,0,100,MAP_H))
        # buildings random but not on roads center
        self.buildings = []
        for _ in range(160):
            bw = random.randint(80,220); bh = random.randint(80,220)
            bx = random.randint(0, MAP_W - bw)
            by = random.randint(0, MAP_H - bh)
            rect = pygame.Rect(bx,by,bw,bh)
            # avoid big overlap with roads - simple check
            ok = True
            for r in self.roads:
                if rect.colliderect(r.inflate(30,30)):
                    ok = False; break
            if ok:
                self.buildings.append(rect)
        # add some large blocks
        for cx in range(800, 2400, 700):
            self.buildings.append(pygame.Rect(cx, 600, 300, 400))
    def draw(self, surf, cam):
        surf.fill(GRASS)
        for r in self.roads:
            sx,sy = cam.to_screen((r.x, r.y))
            pygame.draw.rect(surf, ROAD, (sx, sy, r.w, r.h))
        # buildings
        for b in self.buildings:
            sx,sy = cam.to_screen((b.x,b.y))
            # draw image tiled if available small; else rect
            try:
                surf.blit(pygame.transform.smoothscale(BUILDING_IMG, (b.w, b.h)), (sx,sy))
            except:
                pygame.draw.rect(surf, BUILDING_COL, (sx,sy,b.w,b.h))
    def collides_building(self, rect):
        for b in self.buildings:
            if rect.colliderect(b):
                return True
        return False

# ------------------ Player ------------------
class Player:
    def __init__(self,x,y):
        self.x = x; self.y = y
        self.w = 36; self.h = 44
        self.angle = 0
        self.speed = 3.8
        self.in_vehicle = None
        self.health = 100
        self.weapon = 0
        self.ammo = [80,12]  # pistol, shotgun
        self.fire_cooldown = 0
        self.money = 0
        # image rect
        self.image = PLAYER_IMG
        self.rect = pygame.Rect(self.x - self.w//2, self.y - self.h//2, self.w, self.h)
    def update(self, keys, dt):
        if self.in_vehicle:
            return
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if dx or dy:
            l = math.hypot(dx,dy) or 1
            nx = self.x + dx/l * self.speed
            ny = self.y + dy/l * self.speed
            new_rect = pygame.Rect(nx - self.w//2, ny - self.h//2, self.w, self.h)
            if not GAME.world.collides_building(new_rect):
                self.x = nx; self.y = ny
        # clamp
        self.x = clamp(self.x, 5, MAP_W-5); self.y = clamp(self.y, 5, MAP_H-5)
        self.rect.topleft = (self.x - self.w//2, self.y - self.h//2)
    def draw(self, surf, cam):
        sx,sy = cam.to_screen((self.x - self.w//2, self.y - self.h//2))
        try:
            surf.blit(self.image, (sx,sy))
        except:
            pygame.draw.rect(surf, PLAYER_COLOR, (sx,sy,self.w,self.h))
    def enter_exit_vehicle(self):
        if self.in_vehicle:
            v = self.in_vehicle
            v.driver = None
            self.in_vehicle = None
            # place player next to car
            self.x = v.x + math.cos(v.angle)*(v.w + 8)
            self.y = v.y + math.sin(v.angle)*(v.h + 8)
            self.rect.topleft = (self.x - self.w//2, self.y - self.h//2)
            if SND_ENTER: SND_ENTER.play()
            GAME.message("Exited vehicle")
            return
        # try to enter nearby non-police car
        for v in GAME.vehicles:
            if not v.is_police and distance((self.x,self.y),(v.x,v.y)) < 48 and v.driver is None:
                v.driver = self
                self.in_vehicle = v
                if SND_ENTER: SND_ENTER.play()
                GAME.message("Entered vehicle")
                return
        GAME.message("No vehicle nearby or vehicle is police")

# ------------------ Vehicle ------------------
class Vehicle:
    def __init__(self,x,y,color=CAR_COLOR,is_police=False):
        self.x=x; self.y=y
        self.w=56; self.h=36
        self.angle=0
        self.speed=0
        self.max_speed=5 if not is_police else 6.2
        self.accel=0.2; self.brake=0.3; self.turn_speed=3.5
        self.color=color
        self.driver=None
        self.is_police=is_police
        self.health=100
        self.image = CAR_IMG
    def update(self, dt, player=None, wanted=0):
        if self.driver:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]:
                self.speed = clamp(self.speed + self.accel, -self.max_speed/2, self.max_speed)
            elif keys[pygame.K_s]:
                self.speed = clamp(self.speed - self.brake, -self.max_speed/2, self.max_speed)
            else:
                self.speed *= 0.96
                if abs(self.speed) < 0.01: self.speed = 0
            if keys[pygame.K_a]:
                self.angle -= self.turn_speed * (self.speed / max(0.1,self.max_speed)) * dt * 60
            if keys[pygame.K_d]:
                self.angle += self.turn_speed * (self.speed / max(0.1,self.max_speed)) * dt * 60
        else:
            # AI
            if self.is_police and wanted>0 and player:
                dx = player.x - self.x; dy = player.y - self.y
                ang = math.atan2(dy, dx)
                diff = ((ang - self.angle + math.pi) % (2*math.pi)) - math.pi
                self.angle += clamp(diff, -0.05, 0.05)
                self.speed = clamp(self.speed + 0.06, -self.max_speed/2, self.max_speed)
            else:
                # idle drift
                if random.random() < 0.002: self.angle += random.uniform(-0.4,0.4)
                self.speed *= 0.995
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        # collision with buildings: simple push back
        rect = pygame.Rect(self.x - self.w/2, self.y - self.h/2, self.w, self.h)
        if GAME.world.collides_building(rect):
            # push back
            self.x -= math.cos(self.angle) * self.speed * 2
            self.y -= math.sin(self.angle) * self.speed * 2
            self.speed = 0
        self.x = clamp(self.x, 0, MAP_W); self.y = clamp(self.y, 0, MAP_H)
    def draw(self, surf, cam):
        sx,sy = cam.to_screen((self.x - self.w/2, self.y - self.h/2))
        try:
            rotated = pygame.transform.rotate(self.image, -math.degrees(self.angle))
            r = rotated.get_rect(center=(sx + self.w/2, sy + self.h/2))
            surf.blit(rotated, r.topleft)
        except:
            s = pygame.Surface((self.w,self.h), pygame.SRCALPHA)
            pygame.draw.rect(s, self.color, (0,0,self.w,self.h))
            surf.blit(s, (sx,sy))

# ------------------ NPC (peatones / policía a pie) ------------------
class NPC:
    def __init__(self,x,y,police=False):
        self.x=x; self.y=y
        self.w=14; self.h=18
        self.police = police
        self.alive = True
        self.vx=random.uniform(-1.2,1.2); self.vy=random.uniform(-1.2,1.2)
        self.speed = 1.2 if not police else 1.6
    def update(self, dt, player=None, wanted=0):
        if not self.alive: return
        if self.police and wanted>0 and player:
            dx = player.x - self.x; dy = player.y - self.y
            d = math.hypot(dx,dy) or 1
            self.vx = (dx/d) * 1.6 * (1 + wanted*0.1); self.vy = (dy/d) * 1.6 * (1 + wanted*0.1)
        else:
            if random.random() < 0.02:
                self.vx = random.uniform(-1.2,1.2); self.vy = random.uniform(-1.2,1.2)
        nx = self.x + self.vx * self.speed
        ny = self.y + self.vy * self.speed
        rect = pygame.Rect(nx - self.w/2, ny - self.h/2, self.w, self.h)
        if not GAME.world.collides_building(rect):
            self.x = clamp(nx, 5, MAP_W-5); self.y = clamp(ny, 5, MAP_H-5)
    def draw(self, surf, cam):
        if not self.alive: return
        sx,sy = cam.to_screen((self.x - self.w/2, self.y - self.h/2))
        color = POLICE_COLOR if self.police else (200,180,80)
        pygame.draw.rect(surf, color, (sx,sy,self.w,self.h))

# ------------------ Bullet ------------------
class Bullet:
    def __init__(self,x,y,angle,owner,speed=14,life=120,damage=30):
        self.x=x; self.y=y
        self.vx=math.cos(angle)*speed; self.vy=math.sin(angle)*speed
        self.life=life; self.owner=owner; self.damage=damage
        self.image = BULLET_IMG
    def update(self, dt):
        self.x += self.vx; self.y += self.vy; self.life -= 1
    def draw(self, surf, cam):
        sx,sy = cam.to_screen((self.x - 4, self.y - 4))
        try:
            surf.blit(self.image, (sx,sy))
        except:
            pygame.draw.circle(surf, BULLET_COLOR, (int(sx+4), int(sy+4)), 3)

# ------------------ Mission ------------------
class Mission:
    def __init__(self):
        self.active = False; self.target = None; self.target_pos = None; self.reward = 0
    def start_steal(self):
        candidates = [v for v in GAME.vehicles if not v.is_police and v.driver is None]
        if not candidates: return
        car = random.choice(candidates)
        self.active = True; self.target = car
        self.target_pos = (random.randint(200, MAP_W-200), random.randint(200, MAP_H-200))
        self.reward = 200 + random.randint(0,400)
        GAME.message("Mission: steal the car and deliver")
    def update(self, dt):
        if not self.active or not self.target: return
        if GAME.player.in_vehicle == self.target and distance((GAME.player.x,GAME.player.y), self.target_pos) < 50:
            GAME.player.money += self.reward
            self.active = False; self.target = None
            GAME.message(f"Mission complete! ${self.reward}")

# ------------------ Game ------------------
class Game:
    def __init__(self):
        self.world = World()
        self.player = Player(MAP_W//2, MAP_H//2)
        self.vehicles = []
        for _ in range(NUM_CARS):
            x=random.randint(50,MAP_W-50); y=random.randint(50,MAP_H-50)
            self.vehicles.append(Vehicle(x,y))
        for _ in range(NUM_POLICE_CARS):
            x=random.randint(50,MAP_W-50); y=random.randint(50,MAP_H-50)
            self.vehicles.append(Vehicle(x,y,color=POLICE_COLOR,is_police=True))
        self.npcs = []
        for _ in range(NUM_NPCS):
            x=random.randint(20,MAP_W-20); y=random.randint(20,MAP_H-20); self.npcs.append(NPC(x,y, police=False))
        for _ in range(NUM_POLICE_PEOPLE):
            x=random.randint(20,MAP_W-20); y=random.randint(20,MAP_H-20); self.npcs.append(NPC(x,y, police=True))
        self.bullets = []
        self.wanted = 0
        self.minimap = True
        self.mission = Mission()
        self.message_queue = deque()
        self.last_reinforce = time.time()
        self.time = 0.0
    def message(self, txt, ttl=3.0):
        self.message_queue.appendleft([txt, ttl])
    def save(self, filename="savegame.json"):
        data = {'player': {'x':self.player.x,'y':self.player.y,'health':self.player.health,'money':self.player.money,'ammo':self.player.ammo,'weapon':self.player.weapon}, 'wanted': self.wanted}
        try:
            with open(filename,'w') as f: json.dump(data,f)
            self.message("Game saved")
        except Exception as e:
            self.message(f"Save failed: {e}")
    def load(self, filename="savegame.json"):
        if not os.path.exists(filename): self.message("No save file"); return
        try:
            with open(filename,'r') as f: data=json.load(f)
            p=data.get('player',{})
            self.player.x = p.get('x', self.player.x); self.player.y = p.get('y', self.player.y)
            self.player.health = p.get('health', self.player.health); self.player.money = p.get('money', self.player.money)
            self.player.ammo = p.get('ammo', self.player.ammo); self.player.weapon = p.get('weapon', self.player.weapon)
            self.wanted = data.get('wanted', self.wanted)
            self.message("Game loaded")
        except Exception as e:
            self.message(f"Load failed: {e}")
    def fire(self):
        if self.player.fire_cooldown > 0: return
        w = self.player.weapon
        if self.player.ammo[w] <= 0:
            self.message("No ammo")
            return
        mx,my = pygame.mouse.get_pos()
        world_mouse = (mx + camera.x, my + camera.y)
        ang = math.atan2(world_mouse[1] - self.player.y, world_mouse[0] - self.player.x)
        if w == 0:
            b = Bullet(self.player.x + math.cos(ang)*24, self.player.y + math.sin(ang)*24, ang, 'player', speed=18, life=120, damage=35)
            self.bullets.append(b); self.player.ammo[w] -= 1; self.player.fire_cooldown = 0.18
        else:
            for _ in range(6):
                spread = random.uniform(-0.35,0.35); a = ang + spread
                b = Bullet(self.player.x + math.cos(a)*24, self.player.y + math.sin(a)*24, a, 'player', speed=15, life=80, damage=18)
                self.bullets.append(b)
            self.player.ammo[w] -= 1; self.player.fire_cooldown = 0.9
        if SND_SHOOT: SND_SHOOT.play()
        self.wanted = clamp(self.wanted + 1, 0, MAX_WANTED)
        if SND_WANTED: SND_WANTED.play()
    def try_enter_exit(self):
        self.player.enter_exit_vehicle()
    def update(self, dt):
        keys = pygame.key.get_pressed()
        mx,my = pygame.mouse.get_pos()
        world_mouse = (mx + camera.x, my + camera.y)
        self.time += dt
        # player aim angle
        self.player.angle = math.atan2(world_mouse[1] - self.player.y, world_mouse[0] - self.player.x)
        # update
        if self.player.in_vehicle:
            # vehicle controlled
            self.player.in_vehicle.update(dt, player=self.player, wanted=self.wanted)
            self.player.x, self.player.y = self.player.in_vehicle.x, self.player.in_vehicle.y
        else:
            self.player.update(keys, dt)
        # vehicles
        for v in list(self.vehicles):
            if v != self.player.in_vehicle:
                v.update(dt, player=self.player, wanted=self.wanted)
        # npcs
        for n in self.npcs:
            n.update(dt, player=self.player, wanted=self.wanted)
        # bullets
        for b in list(self.bullets):
            b.update(dt)
            if b.life <= 0 or b.x < 0 or b.x > MAP_W or b.y < 0 or b.y > MAP_H:
                try: self.bullets.remove(b)
                except: pass; continue
            # hit NPCs
            for npc in self.npcs:
                if npc.alive and abs(b.x - npc.x) < 12 and abs(b.y - npc.y) < 12:
                    npc.alive = False
                    try: self.bullets.remove(b)
                    except: pass
                    if not npc.police: self.wanted = clamp(self.wanted + 1, 0, MAX_WANTED)
                    break
            # hit vehicles
            for v in self.vehicles:
                if abs(b.x - v.x) < max(v.w,v.h)/2 + 8 and abs(b.y - v.y) < max(v.w,v.h)/2 + 8:
                    v.health -= b.damage
                    try: self.bullets.remove(b)
                    except: pass
                    if v.driver and isinstance(v.driver, Player):
                        v.driver.health -= b.damage * 0.6
                    break
        # police reinforcements based on wanted
        if self.wanted > 0 and time.time() - self.last_reinforce > max(3, 12 - self.wanted*2):
            side = random.choice(['top','bottom','left','right'])
            if side=='top': x=random.randint(50,MAP_W-50); y=10
            elif side=='bottom': x=random.randint(50,MAP_W-50); y=MAP_H-10
            elif side=='left': x=10; y=random.randint(50,MAP_H-50)
            else: x=MAP_W-10; y=random.randint(50,MAP_H-50)
            pc = Vehicle(x,y,color=POLICE_COLOR,is_police=True); self.vehicles.append(pc)
            self.last_reinforce = time.time(); self.message("Police reinforcement arrived")
        # wanted decay slowly
        if self.wanted > 0 and int(self.time) % 6 == 0:
            self.wanted = clamp(self.wanted - 0.0008, 0, MAX_WANTED)
        # mission
        self.mission.update(dt)
        # camera
        target = self.player.in_vehicle if self.player.in_vehicle else self.player
        camera.update(target)
        # messages TTL
        if self.message_queue:
            for i in range(len(self.message_queue)-1, -1, -1):
                item = self.message_queue[i]
                item[1] -= dt
                if item[1] <= 0:
                    try: self.message_queue.pop()
                    except: pass
    def draw_hud(self, surf):
        # health
        pygame.draw.rect(surf, (0,0,0), (14, HEIGHT-44, 272, 34))
        pygame.draw.rect(surf, (200,0,0), (18, HEIGHT-40, clamp(self.player.health,0,100)/100*264, 26))
        surf.blit(FONT.render(f'HP: {int(self.player.health)}', True, WHITE), (20, HEIGHT-40))
        # ammo and money
        surf.blit(FONT.render(f'Ammo: {self.player.ammo[self.player.weapon]}', True, WHITE), (20, 10))
        surf.blit(FONT.render(f'Money: ${self.player.money}', True, WHITE), (20, 30))
        # wanted (stars)
        for i in range(int(self.wanted)):
            pygame.draw.polygon(surf, (255,215,0), [(WIDTH-20 - i*30, 14), (WIDTH-8 - i*30, 30), (WIDTH-32 - i*30, 30)])
        # mission
        if self.mission.active:
            surf.blit(FONT.render('Mission active - deliver car', True, WHITE), (WIDTH//2 - 120, 10))
    def draw_minimap(self, surf):
        if not self.minimap: return
        mw,mh = 220,140; sx=WIDTH-mw-12; sy=HEIGHT-mh-12
        mini = pygame.Surface((mw,mh)); mini.fill((20,80,30))
        for r in self.world.roads:
            rx = int(r.x / MAP_W * mw); ry = int(r.y / MAP_H * mh); rw = int(max(2, r.w / MAP_W * mw)); rh = int(max(2, r.h / MAP_H * mh))
            pygame.draw.rect(mini, ROAD, (rx,ry,rw,rh))
        for v in self.vehicles:
            vx = int(v.x / MAP_W * mw); vy = int(v.y / MAP_H * mh); color = POLICE_COLOR if v.is_police else CAR_COLOR
            pygame.draw.circle(mini, color, (vx, vy), 2)
        px = int(self.player.x / MAP_W * mw); py = int(self.player.y / MAP_H * mh); pygame.draw.circle(mini, PLAYER_COLOR, (px, py), 3)
        surf.blit(mini, (sx, sy))
    def draw(self, surf):
        self.world.draw(surf, camera)
        for v in self.vehicles: v.draw(surf, camera)
        for n in self.npcs: n.draw(surf, camera)
        for b in self.bullets: b.draw(surf, camera)
        if self.player.in_vehicle: self.player.in_vehicle.draw(surf, camera)
        else: self.player.draw(surf, camera)
        self.draw_hud(surf)
        self.draw_minimap(surf)
        # messages
        if self.message_queue:
            msg,ttl = self.message_queue[0]
            surf.blit(BIG.render(msg, True, WHITE), (WIDTH//2 - 260, HEIGHT-72))

# ------------------ Inicializar juego ------------------
GAME = Game()
GAME.message("Welcome! Q: mission | E enter | K save | L load", 4.0)

# ------------------ Loop principal ------------------
mouse_held=False; hold_timer=0
running=True
while running:
    dt = CLOCK.tick(60) / 1000.0
    GAME.player.fire_cooldown = max(0, GAME.player.fire_cooldown - dt)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running=False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running=False
            elif event.key == pygame.K_r: GAME = Game(); GAME.message("Reset game",2.0)
            elif event.key == pygame.K_e: GAME.try_enter_exit()
            elif event.key == pygame.K_1: GAME.player.weapon = 0
            elif event.key == pygame.K_2: GAME.player.weapon = 1
            elif event.key == pygame.K_m: GAME.minimap = not GAME.minimap
            elif event.key == pygame.K_k: GAME.save()
            elif event.key == pygame.K_l: GAME.load()
            elif event.key == pygame.K_q and not GAME.mission.active: GAME.mission.start_steal()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_held=True; GAME.fire()
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                mouse_held=False
    if mouse_held:
        hold_timer += dt
        if GAME.player.weapon == 0 and hold_timer > 0.14:
            GAME.fire(); hold_timer=0
    else:
        hold_timer = 0
    GAME.update(dt)
    GAME.draw(SCREEN)
    pygame.display.flip()

pygame.quit()
sys.exit()
a