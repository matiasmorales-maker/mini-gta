# gta_full_v5.py - Mini GTA completo (Pygame)
# NOVEDADES: Estilo visual Retro (GTA 2) (v7)
# Requisitos: Python 3.8+, pygame

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
pygame.display.set_caption("Mini GTA — Full V7 (Estilo GTA 2)")
CLOCK = pygame.time.Clock()
# FONT para un aspecto más grueso y legible
FONT = pygame.font.SysFont("Courier New", 20, bold=True)
BIG = pygame.font.SysFont("Courier New", 28, bold=True)

MAP_W, MAP_H = 4000, 3000 
CITY_BLOCK_SIZE = 500 

# ------------------ Sprites / sonidos (opcionales) ------------------
# Colores predeterminados para fallback (más oscuros para el nuevo estilo)
PLAYER_IMG = safe_load_image("player.png", (44,44), (200,200,200)) # Gris claro
CAR_IMG = safe_load_image("car.png", (72,44), (80,80,180)) # Azul oscuro
POLICE_IMG = safe_load_image("police.png", (72,44), (180,60,60)) # Rojo ladrillo
BULLET_IMG = safe_load_image("bullet.png", (8,8), (255,160,0)) # Naranja brillante
EXPLOSION_IMG = safe_load_image("explosion.png", (64,64), (255,165,0))

SND_SHOOT = safe_load_sound("shoot.wav")
SND_RELOAD = safe_load_sound("reload.wav") 
SND_ENTER = safe_load_sound("enter.wav")
SND_WANTED = safe_load_sound("wanted.wav")
SND_ENGINE = safe_load_sound("engine.wav")
SND_EXPLOSION = safe_load_sound("explosion.wav")
SND_HEAL = safe_load_sound("heal.wav") 

# ------------------ Colores y parámetros (Estilo GTA 2) ------------------
GRASS = (18, 55, 20)      # Pasto muy oscuro
ROAD = (30, 30, 30)       # Asfalto casi negro
PAVEMENT_COL = (60, 60, 60) # Aceras de hormigón oscuro
WHITE = (255,255,255)
BLACK = (0,0,0)

# Colores de HUD estilo neón/retro
HUD_TEXT_COLOR = (255, 255, 50) # Amarillo neón
HUD_WANTED_COLOR = (255, 50, 50) # Rojo intenso
HUD_MONEY_COLOR = (50, 255, 50) # Verde brillante
WINDOW_LIGHT = (255, 230, 150) # Luz cálida para ventanas
POLICE_COLOR = (200, 50, 50) # Color uniforme para policía

# Paleta de colores de edificios variados 
BUILDING_PALETTE = [
    (50, 50, 50),      # Gris oscuro (Hormigón)
    (100, 100, 100),   # Gris medio
    (120, 80, 50),     # Marrón oscuro (Ladrillo)
    (50, 70, 90),      # Azul petróleo (Acero/Vidrio oscuro)
    (160, 160, 160)    # Blanco sucio
]

# Gameplay params
NUM_CARS = 60
NUM_NPCS = 120
NUM_POLICE_PEOPLE = 25
NUM_POLICE_CARS = 12
MAX_WANTED = 5

# Definición de armas con capacidades de munición máxima y cargador
WEAPONS_DATA = {
    0: {"name": "PISTOL", "mag_size": 15, "max_ammo": 150, "damage": 35, "cooldown": 0.18},
    1: {"name": "SHOTGUN", "mag_size": 6, "max_ammo": 30, "damage": 18, "cooldown": 0.9}
}

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
        self.buildings = []
        self.pavements = [] 
        self.generate_city_grid()

    def generate_city_grid(self):
        road_width = 100
        pavement_width = 15 
        
        # 1. Crear la rejilla de carreteras y aceras
        for i in range(0, MAP_W // CITY_BLOCK_SIZE):
            x = i * CITY_BLOCK_SIZE + road_width / 2
            # Carretera Vertical
            self.roads.append(pygame.Rect(x - road_width / 2, 0, road_width, MAP_H))
            # Aceras Verticales
            self.pavements.append(pygame.Rect(x - road_width / 2, 0, pavement_width, MAP_H))
            self.pavements.append(pygame.Rect(x + road_width / 2 - pavement_width, 0, pavement_width, MAP_H))

        for j in range(0, MAP_H // CITY_BLOCK_SIZE):
            y = j * CITY_BLOCK_SIZE + road_width / 2
            # Carretera Horizontal
            self.roads.append(pygame.Rect(0, y - road_width / 2, MAP_W, road_width))
            # Aceras Horizontales
            self.pavements.append(pygame.Rect(0, y - road_width / 2, MAP_W, pavement_width))
            self.pavements.append(pygame.Rect(0, y + road_width / 2 - pavement_width, MAP_W, pavement_width))

        # 2. Generar edificios dentro de las manzanas (sin solaparse con aceras)
        building_margin = 10 
        
        for i in range(MAP_W // CITY_BLOCK_SIZE):
            for j in range(MAP_H // CITY_BLOCK_SIZE):
                
                block_x = i * CITY_BLOCK_SIZE + road_width
                block_y = j * CITY_BLOCK_SIZE + road_width
                block_w = CITY_BLOCK_SIZE - road_width
                block_h = CITY_BLOCK_SIZE - road_width
                
                current_x = block_x + building_margin
                current_y = block_y + building_margin
                max_x = block_x + block_w - building_margin
                max_y = block_y + block_h - building_margin
                
                while current_y < max_y:
                    current_x = block_x + building_margin
                    while current_x < max_x:
                        
                        # VARIACIÓN DE ESTRUCTURAS (más GTA 2: muy variadas)
                        r = random.random()
                        if r < 0.3: # Rascacielos/Torre (delgado y mediano-grande)
                            bw = random.randint(30, 80)
                            bh = random.randint(30, 80)
                            b_type = 'office'
                        elif r < 0.6: # Almacén/Comercial (largo y bajo)
                            bw = random.randint(80, 150)
                            bh = random.randint(40, 80)
                            b_type = 'shop'
                        else: # Estándar/Residencial
                            bw = random.randint(50, 120)
                            bh = random.randint(50, 120)
                            b_type = 'residence'
                        
                        bw = min(bw, max_x - current_x)
                        bh = min(bh, max_y - current_y)
                        
                        if bw >= 20 and bh >= 20: 
                            rect = pygame.Rect(current_x, current_y, bw, bh)
                            color = random.choice(BUILDING_PALETTE)
                            self.buildings.append({'rect': rect, 'color': color, 'type': b_type})
                            current_x += bw + building_margin
                        else:
                            break 
                    current_y += random.randint(30, 80) + building_margin 
                    
                    if current_y > max_y and current_y < max_y + 40: 
                        current_y = max_y

    def draw(self, surf, cam):
        surf.fill(GRASS)
        
        # 1. Draw Roads
        for r in self.roads:
            sx,sy = cam.to_screen((r.x, r.y))
            pygame.draw.rect(surf, ROAD, (sx, sy, r.w, r.h))
            
            # Detalle de Carreteras (líneas amarillas)
            if r.w > r.h: # Horizontal
                center_y = sy + r.h / 2
                # Dibuja la línea central discontinua
                start_x = (cam.x % 60) - 60 
                for i in range(int(WIDTH / 60) + 2):
                    line_x = 0 + i * 60 - start_x
                    if sx < line_x < sx + r.w:
                         pygame.draw.rect(surf, (255, 160, 0), (line_x, center_y - 2, 30, 4)) # Naranja retro
            else: # Vertical
                center_x = sx + r.w / 2
                start_y = (cam.y % 60) - 60 
                for i in range(int(HEIGHT / 60) + 2):
                    line_y = 0 + i * 60 - start_y
                    if sy < line_y < sy + r.h:
                        pygame.draw.rect(surf, (255, 160, 0), (center_x - 2, line_y, 4, 30))
        
        # 2. Draw Pavements (Aceras)
        for p in self.pavements:
            sx,sy = cam.to_screen((p.x, p.y))
            pygame.draw.rect(surf, PAVEMENT_COL, (sx, sy, p.w, p.h))
            # Borde negro/oscuro para definir
            pygame.draw.rect(surf, BLACK, (sx, sy, p.w, p.h), 1)

        # 3. Draw Buildings (Estructuras Variadas con Efecto 3D)
        shadow_depth = 4 # Profundidad de la sombra
        
        for b_data in self.buildings:
            b = b_data['rect']
            sx,sy = cam.to_screen((b.x,b.y))
            
            color = b_data['color']
            darker_color = tuple(max(0, c - 20) for c in color)
            lighter_color = tuple(min(255, c + 20) for c in color)

            # 3.1 Dibujar la Sombra (efecto 3D)
            pygame.draw.rect(surf, darker_color, (sx + shadow_depth, sy + shadow_depth, b.w, b.h))
            
            # 3.2 Dibujar el Cuerpo Principal
            pygame.draw.rect(surf, color, (sx,sy,b.w,b.h))
            
            # 3.3 Detalle de Fachada/Ventanas
            window_color = WINDOW_LIGHT
            
            if b_data['type'] == 'office':
                # Patrón de rejilla (ventanas de oficina)
                window_size = 6; gap = 6
                for wx in range(gap, b.w - gap, window_size + gap):
                    for wy in range(gap, b.h - gap, window_size + gap):
                        w_sx = sx + wx; w_sy = sy + wy
                        pygame.draw.rect(surf, window_color, (w_sx, w_sy, window_size, window_size))
            
            elif b_data['type'] == 'shop':
                # Fachada de tienda (una ventana grande)
                pygame.draw.rect(surf, (150, 20, 20), (sx, sy, b.w, 8)) # Toldo/Techo rojo
                pygame.draw.rect(surf, (50, 50, 50), (sx + 5, sy + 10, b.w - 10, b.h - 15)) # Ventana (oscura)
                
            else: # residence
                # Patrón de ventanas pequeño y espaciado (residencial)
                window_size = 4; gap = 12
                for wx in range(gap, b.w - gap, window_size + gap):
                    for wy in range(gap, b.h - gap, window_size + gap):
                        w_sx = sx + wx; w_sy = sy + wy
                        pygame.draw.rect(surf, window_color, (w_sx, w_sy, window_size, window_size))

            # 3.4 Borde superior para efecto de luz
            pygame.draw.rect(surf, lighter_color, (sx, sy, b.w, 1))
            pygame.draw.rect(surf, lighter_color, (sx, sy, 1, b.h))
            
            # 3.5 Borde negro final
            pygame.draw.rect(surf, BLACK, (sx,sy,b.w,b.h), 1)
                
    def collides_building(self, rect):
        for b_data in self.buildings:
            # Colisiona con el área del edificio, ignorando el efecto 3D
            if rect.colliderect(b_data['rect']):
                return True
        return False

# ------------------ Player ------------------
class Player:
    # (Player class remains mostly the same, only adjusted weapon names and colors)
    def __init__(self,x,y):
        self.x = x; self.y = y
        self.w = 36; self.h = 44
        self.angle = 0
        self.speed = 3.8
        self.in_vehicle = None
        self.health = 100
        self.weapon = 0
        
        self.ammo_in_mag = [WEAPONS_DATA[0]["mag_size"], 0]
        self.ammo_total = [WEAPONS_DATA[0]["max_ammo"], WEAPONS_DATA[1]["max_ammo"]]
        
        self.fire_cooldown = 0
        self.reload_timer = 0 
        self.money = 1000 
        self.alive = True
        self.image = PLAYER_IMG
        self.rect = pygame.Rect(self.x - self.w//2, self.y - self.h//2, self.w, self.h)
        
    def get_current_weapon_data(self):
        return WEAPONS_DATA[self.weapon]
    
    def update(self, keys, dt):
        if not self.alive: return
        
        if self.reload_timer > 0:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.complete_reload()
            return 
        
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
                
        self.x = clamp(self.x, 5, MAP_W-5); self.y = clamp(self.y, 5, MAP_H-5)
        self.rect.topleft = (self.x - self.w//2, self.y - self.h//2)

    def start_reload(self):
        if not self.alive or self.in_vehicle: return
        if self.reload_timer > 0:
            GAME.message("Already reloading.")
            return

        w_data = self.get_current_weapon_data()
        w = self.weapon
        mag = self.ammo_in_mag[w]
        total = self.ammo_total[w]
        mag_size = w_data["mag_size"]
        
        if mag == mag_size:
            GAME.message("Magazine is full")
            return
        if total == 0:
            GAME.message("No reserve ammo")
            return
            
        needed = mag_size - mag
        transfer = min(needed, total)
        
        if transfer > 0:
            self.reload_timer = 2.0
            GAME.message("RELOADING...", 2.1)
            if SND_RELOAD: SND_RELOAD.play()
        else:
            GAME.message("Cannot reload")
            
    def complete_reload(self):
        w_data = self.get_current_weapon_data()
        w = self.weapon
        mag = self.ammo_in_mag[w]
        total = self.ammo_total[w]
        mag_size = w_data["mag_size"]
        
        needed = mag_size - mag
        transfer = min(needed, total)
        
        self.ammo_in_mag[w] += transfer
        self.ammo_total[w] -= transfer
        GAME.message("Reload complete!", 1.5)

    def heal(self):
        if not self.alive or self.in_vehicle:
            GAME.message("Cannot heal right now.")
            return
        if self.health == 100:
            GAME.message("Health is already full.")
            return
        if self.money < 100:
            GAME.message("Need $100 for a medkit.")
            return
            
        self.money -= 100
        self.health = min(100, self.health + 50)
        GAME.message("Healed 50 HP for $100.", 2.0)
        if SND_HEAL: SND_HEAL.play()
        if self.health <= 0:
            self.alive = False
            GAME.message("WASTED. Press [L] to reload last save, or ESC to quit.", 5.0)

    def draw(self, surf, cam):
        if not self.alive: return
        sx,sy = cam.to_screen((self.x - self.w//2, self.y - self.h//2))
        try:
            rotated = pygame.transform.rotate(self.image, -math.degrees(self.angle))
            r = rotated.get_rect(center=(sx + self.w/2, sy + self.h/2))
            surf.blit(rotated, r.topleft)
        except:
            # Fallback a un círculo simple con color de alto contraste
            pygame.draw.circle(surf, HUD_TEXT_COLOR, (int(sx+self.w/2), int(sy+self.h/2)), int(self.w/2))
    
    def enter_exit_vehicle(self):
        if not self.alive: return
        if self.reload_timer > 0:
            GAME.message("Cannot enter/exit while reloading.")
            return

        if self.in_vehicle:
            v = self.in_vehicle
            v.driver = None
            self.in_vehicle = None
            self.x = v.x + math.cos(v.angle)*(v.w + 8)
            self.y = v.y + math.sin(v.angle)*(v.h + 8)
            self.rect.topleft = (self.x - self.w//2, self.y - self.h//2)
            if SND_ENTER: SND_ENTER.play()
            GAME.message("EXITED VEHICLE")
            return
        for v in GAME.vehicles:
            if not v.is_police and distance((self.x,self.y),(v.x,v.y)) < 60 and v.driver is None and v.health > 0 and not v.is_exploding:
                v.driver = self
                self.in_vehicle = v
                if SND_ENTER: SND_ENTER.play()
                GAME.message("ENTERED VEHICLE")
                return
        GAME.message("NO VEHICLE NEARBY")
        
    def switch_weapon(self):
        if not self.alive or self.in_vehicle: return
        self.weapon = (self.weapon + 1) % len(WEAPONS_DATA)
        self.reload_timer = 0 
        GAME.message(f"WEAPON: {self.get_current_weapon_data()['name']}")

# ------------------ Vehicle ------------------
class Vehicle:
    # (Vehicle class remains the same)
    def __init__(self,x,y,color=CAR_IMG.get_at((1,1)),is_police=False):
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
        self.image = CAR_IMG if not is_police else POLICE_IMG
        self.is_exploding = False 
        self.explosion_timer = 0
    
    def damage(self, amount):
        if self.health > 0:
            self.health = max(0, self.health - amount)
            if self.health <= 0 and not self.is_exploding:
                self.is_exploding = True
                self.explosion_timer = 1.0 
                GAME.message("VEHICLE DESTROYED")
                if SND_EXPLOSION: SND_EXPLOSION.play()
                if self.driver and isinstance(self.driver, Player):
                    self.driver.in_vehicle = None
                    self.driver.x = self.x; self.driver.y = self.y
                    self.driver.health -= 20 
                    GAME.message("EJECTED! DAMAGE TAKEN")
                    self.driver = None
                elif self.driver and self.is_police:
                    self.driver = None

    def update(self, dt, player=None, wanted=0):
        if self.health <= 0:
            if self.is_exploding:
                self.explosion_timer -= dt
                if self.explosion_timer <= 0:
                    GAME.particles.add_explosion(self.x, self.y, 80, (255,100,0))
                    if player and player.alive and distance((self.x,self.y), (player.x,player.y)) < 150:
                         player.health = max(0, player.health - 50)
                         GAME.message("EXPLOSION DAMAGE!")
                    for npc in GAME.npcs:
                         if npc.alive and distance((self.x,self.y), (npc.x,npc.y)) < 150:
                             npc.damage(50)
                    self.is_exploding = False
            return 

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
            if self.is_police and wanted>0 and player and player.alive and distance((self.x,self.y), (player.x,player.y)) < 800:
                dx = player.x - self.x; dy = player.y - self.y
                d = math.hypot(dx,dy) or 1
                ang = math.atan2(dy, dx)
                diff = ((ang - self.angle + math.pi) % (2*math.pi)) - math.pi
                self.angle += clamp(diff, -0.05, 0.05)
                self.speed = clamp(self.speed + 0.06, -self.max_speed/2, self.max_speed)
            else:
                if random.random() < 0.002: self.angle += random.uniform(-0.4,0.4)
                self.speed *= 0.995
        
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        
        rect = pygame.Rect(self.x - self.w/2, self.y - self.h/2, self.w, self.h)
        if GAME.world.collides_building(rect):
            self.x -= math.cos(self.angle) * self.speed * 2
            self.y -= math.sin(self.angle) * self.speed * 2
            self.speed = 0
            if abs(self.speed) > 2.0:
                 self.damage(5)

        self.x = clamp(self.x, 0, MAP_W); self.y = clamp(self.y, 0, MAP_H)

    def draw(self, surf, cam):
        sx,sy = cam.to_screen((self.x - self.w/2, self.y - self.h/2))
        
        current_image = self.image
        if self.health < 50:
            damage_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            alpha = 200 - self.health * 2 
            damage_surf.fill((255, 0, 0, clamp(alpha, 0, 200))) 
            
            temp_img = current_image.copy()
            temp_img.blit(damage_surf, (0, 0))
            current_image = temp_img

        if self.health > 0:
            try:
                rotated = pygame.transform.rotate(current_image, -math.degrees(self.angle))
                r = rotated.get_rect(center=(sx + self.w/2, sy + self.h/2))
                surf.blit(rotated, r.topleft)
            except:
                s = pygame.Surface((self.w,self.h), pygame.SRCALPHA)
                pygame.draw.rect(s, self.color, (0,0,self.w,self.h))
                surf.blit(s, (sx,sy))
        
        if self.is_exploding:
            explosion_scale = 1.0 + (1.0 - self.explosion_timer) * 2
            exp_w = int(EXPLOSION_IMG.get_width() * explosion_scale)
            exp_h = int(EXPLOSION_IMG.get_height() * explosion_scale)
            exp_img = pygame.transform.scale(EXPLOSION_IMG, (exp_w, exp_h))
            
            exp_sx = int(sx + self.w/2 - exp_w/2)
            exp_sy = int(sy + self.h/2 - exp_h/2)
            surf.blit(exp_img, (exp_sx, exp_sy))
            
            
# ------------------ NPC (peatones / policía a pie) ------------------
class NPC:
    def __init__(self,x,y,police=False):
        self.x=x; self.y=y
        self.w=14; self.h=18
        self.police = police
        self.alive = True
        self.health = 100
        self.vx=random.uniform(-1.2,1.2); self.vy=random.uniform(-1.2,1.2)
        self.speed = 1.2 if not police else 1.6
    
    def damage(self, amount):
        if self.health > 0:
            self.health = max(0, self.health - amount)
            if self.health <= 0:
                self.alive = False
                if not self.police: 
                    GAME.player.money += 15
                    GAME.wanted = clamp(GAME.wanted + 0.02, 0, MAX_WANTED) 
                    if SND_WANTED: SND_WANTED.play()

    def update(self, dt, player=None, wanted=0):
        if not self.alive: return
        if self.police and wanted>0 and player and player.alive:
            dx = player.x - self.x; dy = player.y - self.y
            d = math.hypot(dx,dy) or 1
            self.vx = (dx/d) * self.speed * (1 + wanted*0.1); self.vy = (dy/d) * self.speed * (1 + wanted*0.1)
            if distance((self.x, self.y), (player.x, player.y)) < 30 and player.in_vehicle is None:
                player.health = max(0, player.health - 0.5)
        else:
            if random.random() < 0.02:
                self.vx = random.uniform(-1.2,1.2); self.vy = random.uniform(-1.2,1.2)
        nx = self.x + self.vx * self.speed
        ny = self.y + self.vy * self.speed
        rect = pygame.Rect(nx - self.w/2, ny - self.h/2, self.w, self.h)
        if not GAME.world.collides_building(rect):
            self.x = clamp(nx, 5, MAP_W-5); self.y = clamp(ny, 5, MAP_H-5)
        else:
            self.vx = -self.vx; self.vy = -self.vy
            
    def draw(self, surf, cam):
        if not self.alive: return
        sx,sy = cam.to_screen((self.x - self.w/2, self.y - self.h/2))
        color = POLICE_COLOR if self.police else (255, 255, 50) # Peatones amarillos neón
        pygame.draw.rect(surf, color, (sx,sy,self.w,self.h))
        # Simple health bar for police
        if self.police and self.health < 100:
             bar_w = int(self.w * (self.health / 100))
             pygame.draw.rect(surf, (200,50,50), (sx, sy - 5, self.w, 3))
             pygame.draw.rect(surf, (50,200,50), (sx, sy - 5, bar_w, 3))

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
            pygame.draw.circle(surf, BULLET_IMG.get_at((1,1)), (int(sx+4), int(sy+4)), 3)

# ------------------ Partículas (para explosiones/golpes) ------------------
class Particle:
    def __init__(self, x, y, color, size, lifetime, vx, vy):
        self.x, self.y = x, y
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.vx, self.vy = vx, vy

    def update(self, dt):
        self.x += self.vx; self.y += self.vy; self.lifetime -= dt
        self.size = max(0, self.size - 0.1 * dt)

    def draw(self, surf, cam):
        sx, sy = cam.to_screen((self.x, self.y))
        pygame.draw.circle(surf, self.color, (int(sx), int(sy)), int(self.size))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add_explosion(self, x, y, count, color):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 8)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            p = Particle(x, y, color, random.uniform(3, 8), random.uniform(0.5, 1.5), vx, vy)
            self.particles.append(p)

    def update(self, dt):
        self.particles = [p for p in self.particles if p.lifetime > 0 and p.size > 0]
        for p in self.particles:
            p.update(dt)

    def draw(self, surf, cam):
        for p in self.particles:
            p.draw(surf, cam)

# ------------------ Mission ------------------
class Mission:
    def __init__(self):
        self.active = False; self.target = None; self.target_pos = None; self.reward = 0
    def start_steal(self):
        candidates = [v for v in GAME.vehicles if not v.is_police and v.driver is None and v.health > 0]
        if not candidates: return
        car = random.choice(candidates)
        self.active = True; self.target = car
        self.target_pos = (random.randint(200, MAP_W-200), random.randint(200, MAP_H-200))
        self.reward = 200 + random.randint(0,400)
        GAME.message("MISSION: STEAL CAR AND DELIVER")
    def update(self, dt):
        if not self.active or not self.target: return
        if self.target.health <= 0:
            GAME.message("MISSION FAILED: TARGET DESTROYED")
            self.active = False; self.target = None
            return
        
        if GAME.player.in_vehicle == self.target and distance((GAME.player.x,GAME.player.y), self.target_pos) < 50:
            GAME.player.money += self.reward
            self.active = False; self.target = None
            GAME.message(f"MISSION COMPLETE! ${self.reward}")

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
            self.vehicles.append(Vehicle(x,y,is_police=True))
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
        self.particles = ParticleSystem()
        
    def message(self, txt, ttl=3.0):
        self.message_queue.appendleft([txt, ttl])
    
    def save(self, filename="savegame.json"):
        # (Save/Load methods remain the same)
        data = {
            'player': {
                'x':self.player.x,'y':self.player.y,'health':self.player.health,
                'money':self.player.money,'weapon':self.player.weapon,
                'ammo_in_mag': self.player.ammo_in_mag, 
                'ammo_total': self.player.ammo_total
            }, 
            'wanted': self.wanted
        }
        try:
            with open(filename,'w') as f: json.dump(data,f)
            self.message("GAME SAVED")
        except Exception as e:
            self.message(f"SAVE FAILED: {e}")
            
    def load(self, filename="savegame.json"):
        if not os.path.exists(filename): self.message("NO SAVE FILE"); return
        try:
            with open(filename,'r') as f: data=json.load(f)
            p=data.get('player',{})
            self.player.x = p.get('x', self.player.x); self.player.y = p.get('y', self.player.y)
            self.player.health = p.get('health', self.player.health); self.player.money = p.get('money', self.player.money)
            self.player.weapon = p.get('weapon', self.player.weapon)
            self.player.ammo_in_mag = p.get('ammo_in_mag', self.player.ammo_in_mag)
            self.player.ammo_total = p.get('ammo_total', self.player.ammo_total)
            self.player.alive = self.player.health > 0
            self.player.in_vehicle = None 
            
            self.wanted = data.get('wanted', self.wanted)
            self.message("GAME LOADED")
        except Exception as e:
            self.message(f"LOAD FAILED: {e}")
    
    def fire(self):
        if not self.player.alive or self.player.in_vehicle: return
        if self.player.fire_cooldown > 0 or self.player.reload_timer > 0: return
        
        w = self.player.weapon
        w_data = WEAPONS_DATA[w]
        
        if self.player.ammo_in_mag[w] <= 0:
            self.message("OUT OF AMMO. PRESS R TO RELOAD.")
            return
            
        mx,my = pygame.mouse.get_pos()
        world_mouse = (mx + camera.x, my + camera.y)
        ang = math.atan2(world_mouse[1] - self.player.y, world_mouse[0] - self.player.x)
        
        if w == 0: # Pistol
            b = Bullet(self.player.x + math.cos(ang)*24, self.player.y + math.sin(ang)*24, ang, 'player', speed=18, life=120, damage=w_data["damage"])
            self.bullets.append(b); self.player.ammo_in_mag[w] -= 1; self.player.fire_cooldown = w_data["cooldown"]
        else: # Shotgun
            for _ in range(6):
                spread = random.uniform(-0.35,0.35); a = ang + spread
                b = Bullet(self.player.x + math.cos(a)*24, self.player.y + math.sin(a)*24, a, 'player', speed=15, life=80, damage=w_data["damage"])
                self.bullets.append(b)
            self.player.ammo_in_mag[w] -= 1; self.player.fire_cooldown = w_data["cooldown"]
        
        self.particles.add_explosion(self.player.x + math.cos(ang)*24, self.player.y + math.sin(ang)*24, 2, (100,100,100))
            
        if SND_SHOOT: SND_SHOOT.play()
        self.wanted = clamp(self.wanted + 0.02, 0, MAX_WANTED) 
        if SND_WANTED and self.wanted > 0.95 and self.wanted < 1.05: SND_WANTED.play()
        
    def try_enter_exit(self):
        self.player.enter_exit_vehicle()

    def update(self, dt):
        keys = pygame.key.get_pressed()
        mx,my = pygame.mouse.get_pos()
        world_mouse = (mx + camera.x, my + camera.y)
        
        self.time += dt * 0.5 

        if self.player.alive:
            self.player.fire_cooldown = max(0, self.player.fire_cooldown - dt)
            if self.player.reload_timer <= 0:
                self.player.angle = math.atan2(world_mouse[1] - self.player.y, world_mouse[0] - self.player.x)
            
            if self.player.in_vehicle:
                self.player.in_vehicle.update(dt, player=self.player, wanted=self.wanted)
                self.player.x, self.player.y = self.player.in_vehicle.x, self.player.in_vehicle.y
            else:
                self.player.update(keys, dt)
        
        self.vehicles = [v for v in self.vehicles if v.health > 0 or v.is_exploding]

        for v in self.vehicles:
            v.update(dt, player=self.player, wanted=self.wanted)
        for n in self.npcs:
            n.update(dt, player=self.player, wanted=self.wanted)
        
        self.npcs = [n for n in self.npcs if n.alive]
        
        for b in list(self.bullets):
            b.update(dt)
            if b.life <= 0 or b.x < 0 or b.x > MAP_W or b.y < 0 or b.y > MAP_H:
                try: self.bullets.remove(b)
                except: pass; continue
            
            hit = False
            for npc in self.npcs:
                if npc.alive and abs(b.x - npc.x) < 12 and abs(b.y - npc.y) < 12:
                    npc.damage(b.damage)
                    hit = True; break
            
            if not hit:
                for v in self.vehicles:
                    if v.health > 0 and abs(b.x - v.x) < max(v.w,v.h)/2 + 8 and abs(b.y - v.y) < max(v.w,v.h)/2 + 8:
                        v.damage(b.damage)
                        hit = True; break
            
            if hit:
                self.particles.add_explosion(b.x, b.y, 5, (200, 200, 200))
                try: self.bullets.remove(b)
                except: pass

        if self.wanted > 0 and self.player.in_vehicle is None and not any(n.police for n in self.npcs):
            self.wanted = max(0, self.wanted - dt * 0.1) 
            
        if self.wanted >= 1 and time.time() - self.last_reinforce > 30 / self.wanted:
            px,py = self.player.x, self.player.y
            sx,sy = px + random.uniform(500,1000) * random.choice([-1,1]), py + random.uniform(500,1000) * random.choice([-1,1])
            self.vehicles.append(Vehicle(sx, sy, is_police=True))
            self.npcs.append(NPC(sx+10, sy+10, police=True))
            self.last_reinforce = time.time()
            self.message("POLICE REINFORCEMENTS ARRIVED")
        
        self.message_queue = deque([[txt, ttl - dt] for txt, ttl in self.message_queue if ttl > 0])
        self.mission.update(dt)
        self.particles.update(dt)
        
        cam_target = self.player.in_vehicle if self.player.in_vehicle else self.player
        camera.update(cam_target)


    def draw(self, surf):
        self.world.draw(surf, camera)

        if self.mission.active and self.mission.target_pos:
            sx, sy = camera.to_screen(self.mission.target_pos)
            # Objetivo de misión como un círculo amarillo neón parpadeante
            pulse_radius = 25 + math.sin(self.time * 10) * 5
            pygame.draw.circle(surf, HUD_TEXT_COLOR, (int(sx), int(sy)), int(pulse_radius), 5)


        for n in self.npcs:
            n.draw(surf, camera)
            
        for v in self.vehicles:
            v.draw(surf, camera)

        if self.player.in_vehicle is None:
            self.player.draw(surf, camera)
            
        for b in self.bullets:
            b.draw(surf, camera)

        self.particles.draw(surf, camera)
        
        # Oscurecimiento (se mantiene el efecto para ambientación)
        day_time = (self.time % 24)
        darkness = 0
        if 18 <= day_time <= 24: darkness = int(180 * (day_time - 18) / 6) # Menos oscuro para contraste
        elif 0 <= day_time <= 6: darkness = int(180 * (6 - day_time) / 6)
        
        darkness = clamp(darkness, 0, 180) 
        
        if darkness > 0:
            dark_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dark_overlay.fill((0, 0, 0, darkness))
            surf.blit(dark_overlay, (0, 0))

        self.draw_hud(surf)
        
        if self.minimap:
            self.draw_minimap(surf)

    def draw_hud(self, surf):
        # Fondo para el HUD (barra negra)
        pygame.draw.rect(surf, BLACK, (0, 0, WIDTH, 70))
        pygame.draw.line(surf, (30,30,30), (0, 70), (WIDTH, 70), 2)
        
        # 1. Health Bar (Izquierda)
        health_color = HUD_WANTED_COLOR if self.player.health < 30 else HUD_MONEY_COLOR
        health_txt = BIG.render("ARMOR", True, HUD_TEXT_COLOR)
        surf.blit(health_txt, (10, 5))
        
        # Barra de vida
        bar_w = 150
        pygame.draw.rect(surf, BLACK, (10, 35, bar_w, 25))
        pygame.draw.rect(surf, health_color, (12, 37, (bar_w-4) * (self.player.health / 100), 21))
        pygame.draw.rect(surf, HUD_TEXT_COLOR, (10, 35, bar_w, 25), 2)
        
        # 2. Money & Wanted Level (Derecha)
        
        # Nivel de Búsqueda (Estrellas)
        wanted_text = "WANTED LEVEL: " + ("*" * int(self.wanted))
        wanted_txt = BIG.render(wanted_text, True, HUD_WANTED_COLOR)
        surf.blit(wanted_txt, (WIDTH - wanted_txt.get_width() - 10, 5))

        # Dinero
        money_txt = BIG.render(f"CREDIT: ${self.player.money:,.0f}", True, HUD_MONEY_COLOR)
        surf.blit(money_txt, (WIDTH - money_txt.get_width() - 10, 35))

        # 3. Weapon Info (Centro)
        w = self.player.weapon
        w_data = WEAPONS_DATA[w]
        
        ammo_in_mag = self.player.ammo_in_mag[w]
        ammo_total = self.player.ammo_total[w]
        
        weapon_text = w_data['name']
        ammo_text = f"{ammo_in_mag} / {ammo_total}"

        weapon_surf = BIG.render(weapon_text, True, HUD_TEXT_COLOR)
        ammo_surf = BIG.render(ammo_text, True, HUD_TEXT_COLOR)
        
        center_x = WIDTH // 2
        surf.blit(weapon_surf, (center_x - weapon_surf.get_width() // 2, 5))
        surf.blit(ammo_surf, (center_x - ammo_surf.get_width() // 2, 35))

        if self.player.reload_timer > 0:
            reload_txt = BIG.render("RELOADING", True, (255, 100, 0))
            surf.blit(reload_txt, (center_x - reload_txt.get_width() // 2, 60))
        
        # 4. Messages (Parte inferior central)
        for i, (txt, ttl) in enumerate(self.message_queue):
            msg_surf = FONT.render(txt, True, HUD_TEXT_COLOR)
            x_pos = WIDTH // 2 - msg_surf.get_width() // 2
            y_pos = HEIGHT - 30 - i * 25
            surf.blit(msg_surf, (x_pos, y_pos))

    def draw_minimap(self, surf):
        map_size = 180; map_x = WIDTH - map_size - 10; map_y = HEIGHT - map_size - 10
        ratio = map_size / MAP_W
        
        map_surf = pygame.Surface((map_size, map_size))
        map_surf.fill(BLACK) # Fondo negro para el minimapa (estilo radar)
        
        # Roads (líneas grises muy delgadas)
        for r in self.world.roads:
            rx,ry,rw,rh = r.x * ratio, r.y * ratio, r.w * ratio, r.h * ratio
            pygame.draw.rect(map_surf, (50, 50, 50), (rx, ry, rw, rh))
            
        # Buildings (ligeramente más claros)
        for b_data in self.world.buildings:
            b = b_data['rect']
            bx,by,bw,bh = b.x * ratio, b.y * ratio, b.w * ratio, b.h * ratio
            color = tuple(min(255, c + 30) for c in b_data['color'])
            pygame.draw.rect(map_surf, color, (bx, by, bw, bh))


        # Player (punto brillante)
        px, py = self.player.x * ratio, self.player.y * ratio
        pygame.draw.circle(map_surf, HUD_MONEY_COLOR, (int(px), int(py)), 3)
        
        # NPCs (police in red)
        for n in self.npcs:
            nx, ny = n.x * ratio, n.y * ratio
            color = HUD_WANTED_COLOR if n.police else HUD_TEXT_COLOR
            pygame.draw.circle(map_surf, color, (int(nx), int(ny)), 2)
            
        # Vehicles (puntos)
        for v in self.vehicles:
            vx, vy = v.x * ratio, v.y * ratio
            color = (0, 0, 255) if v.is_police else (255, 50, 50)
            if v.driver == self.player: color = HUD_MONEY_COLOR 
            pygame.draw.rect(map_surf, color, (int(vx-2), int(vy-2), 4, 4))
            
        # Target (green pulse)
        if self.mission.active and self.mission.target_pos:
            tx, ty = self.mission.target_pos[0] * ratio, self.mission.target_pos[1] * ratio
            pulse_radius = 5 + math.sin(self.time * 10) * 2
            pygame.draw.circle(map_surf, HUD_MONEY_COLOR, (int(tx), int(ty)), int(pulse_radius), 1)

        # Draw map onto screen with a thick border (GTA 2 style)
        pygame.draw.rect(surf, HUD_TEXT_COLOR, (map_x - 5, map_y - 5, map_size + 10, map_size + 10), 3)
        surf.blit(map_surf, (map_x, map_y))


# ------------------ Main Loop ------------------
def handle_input():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                GAME.fire()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                GAME.try_enter_exit()
            elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                GAME.save()
            elif event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                GAME.load()
            elif event.key == pygame.K_m:
                GAME.minimap = not GAME.minimap
            elif event.key == pygame.K_ESCAPE:
                return False
            elif event.key == pygame.K_p:
                GAME.mission.start_steal()
            elif event.key == pygame.K_r: # R for Reload
                GAME.player.start_reload()
            elif event.key == pygame.K_t: # T for Treatment/Heal
                GAME.player.heal()
            elif event.key == pygame.K_q: # Q for Switch Weapon
                GAME.player.switch_weapon()
            elif event.key == pygame.K_l and not GAME.player.alive:
                GAME.load() 
                if not GAME.player.alive: 
                    GAME.__init__()
                    GAME.player.x = MAP_W//2; GAME.player.y = MAP_H//2
                    GAME.player.health = 100
                    GAME.player.alive = True
                
    return True

GAME = Game()
RUNNING = True
while RUNNING:
    DT = CLOCK.tick(60) / 1000.0 
    
    RUNNING = handle_input()
    
    if RUNNING:
        GAME.update(DT)
        GAME.draw(SCREEN)
        
        pygame.display.flip()

pygame.quit()
sys.exit()