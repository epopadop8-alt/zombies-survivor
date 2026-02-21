import pygame
import random
import math
import os

# 1. Initialize Pygame
pygame.init()

# --- Constants ---
WIDTH, HEIGHT = 800, 600
WHITE, BLACK, RED = (255, 255, 255), (0, 0, 0), (255, 0, 0)
GREEN, BLUE, YELLOW = (0, 200, 0), (0, 200, 255), (255, 255, 0)
GOLD, GRAY, DARK_GRAY = (255, 215, 0), (100, 100, 100), (40, 40, 40)
DARK_GRASS, ORANGE = (34, 139, 34), (255, 69, 0)

# 2. Setup Screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Zombie Survival: Sprint & Stamina")

# 3. Image Fallbacks
def load_img(name, size, color):
    try:
        img = pygame.image.load(name).convert_alpha()
        return pygame.transform.scale(img, size)
    except:
        surf = pygame.Surface(size)
        surf.fill(color)
        pygame.draw.rect(surf, WHITE, surf.get_rect(), 2)
        return surf

ZOMBIE_IMAGE = load_img("zombie_img.png", (40, 50), GREEN)
PLAYER_IMAGE = load_img("player_img.png", (30, 42), BLUE) 
BOSS_IMAGE = load_img("zombie_img.png", (100, 120), RED)

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
large_font = pygame.font.SysFont(None, 72)

# --- Save/Load Records ---
def load_records():
    records = {"Easy": 1, "Medium": 1, "Hard": 1}
    if os.path.exists("highscore.txt"):
        with open("highscore.txt", "r") as f:
            for line in f:
                if ":" in line:
                    diff, lvl = line.strip().split(":")
                    if diff in records: records[diff] = int(lvl)
    return records

def save_record(diff, lvl):
    recs = load_records()
    if lvl > recs[diff]:
        recs[diff] = lvl
        with open("highscore.txt", "w") as f:
            for d, l in recs.items(): f.write(f"{d}:{l}\n")

# --- Global Stats ---
player_max_health, player_health = 3, 3
ammo_capacity, total_money = 12, 0 
current_level = 1
difficulty = "Medium"
records = load_records()
player_speed = 5
sprint_speed = 8
max_stamina = 100
current_stamina = 100
reload_speed_modifier = 1200 
last_hit_time = 0
invincibility_duration = 1000 

# Inventory
current_gun = "Pistol"
owned_guns = ["Pistol"]
grenades_count, turrets_owned, mines_count, nukes_count = 2, 0, 0, 0
has_dog = False

# --- Classes ---
class Bullet:
    def __init__(self, x, y, tx, ty, color=YELLOW):
        self.pos = [x, y]
        angle = math.atan2(ty - y, tx - x)
        self.dx, self.dy = math.cos(angle) * 14, math.sin(angle) * 14
        self.color = color
    def move(self):
        self.pos[0] += self.dx; self.pos[1] += self.dy
    def draw(self, s):
        pygame.draw.circle(s, self.color, (int(self.pos[0]), int(self.pos[1])), 5)

class Zombie:
    def __init__(self, x, y, speed, hp, is_boss=False):
        self.pos = [x, y]
        self.speed, self.health, self.max_health = speed, hp, hp
        self.is_boss = is_boss
        self.w, self.h = (100, 120) if is_boss else (40, 50)
    def move(self, px, py, safe_rect):
        current_speed = self.speed * 0.15 if safe_rect.colliderect(pygame.Rect(self.pos[0], self.pos[1], self.w, self.h)) else self.speed
        dist = math.hypot(px - self.pos[0], py - self.pos[1])
        if dist > 0:
            self.pos[0] += ((px - self.pos[0]) / dist) * current_speed
            self.pos[1] += ((py - self.pos[1]) / dist) * current_speed
    def draw(self, s):
        img = BOSS_IMAGE if self.is_boss else ZOMBIE_IMAGE
        s.blit(img, (self.pos[0], self.pos[1]))
        if not self.is_boss and self.max_health > 1:
            pygame.draw.rect(s, RED, (self.pos[0], self.pos[1]-10, 40, 5))
            pygame.draw.rect(s, GREEN, (self.pos[0], self.pos[1]-10, 40 * (self.health/self.max_health), 5))

class Dog:
    def __init__(self, x, y):
        self.pos = [x, y]
    def update(self, px, py, zombies):
        target = [px - 40, py + 20]
        if zombies:
            nearest = min(zombies, key=lambda z: math.hypot(z.pos[0]-self.pos[0], z.pos[1]-self.pos[1]))
            if math.hypot(nearest.pos[0]-self.pos[0], nearest.pos[1]-self.pos[1]) < 200:
                target = [nearest.pos[0], nearest.pos[1]]
        dist = math.hypot(target[0] - self.pos[0], target[1] - self.pos[1])
        if dist > 5:
            self.pos[0] += ((target[0]-self.pos[0])/dist) * 6
            self.pos[1] += ((target[1]-self.pos[1])/dist) * 6
    def draw(self, s):
        pygame.draw.rect(s, (139, 69, 19), (self.pos[0], self.pos[1], 22, 16))
        pygame.draw.rect(s, BLACK, (self.pos[0]+15, self.pos[1]+4, 4, 4))

class Explosion:
    def __init__(self, x, y, radius=150):
        self.x, self.y, self.radius, self.max_radius, self.alive = x, y, 10, radius, True
    def update(self):
        self.radius += 12
        if self.radius > self.max_radius: self.alive = False
    def draw(self, s):
        pygame.draw.circle(s, ORANGE, (self.x, self.y), self.radius, 6)

class Mine:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x-10, y-10, 20, 20)
    def draw(self, s):
        pygame.draw.rect(s, DARK_GRAY, self.rect)
        pygame.draw.circle(s, RED, self.rect.center, 5)

class Turret:
    def __init__(self, x, y):
        self.pos = [x, y]
        self.rect = pygame.Rect(x-15, y-15, 30, 30)
        self.last_shot = 0
    def update(self, zombies, bullets, now):
        if now - self.last_shot > 500 and zombies:
            target = min(zombies, key=lambda z: math.hypot(z.pos[0]-self.pos[0], z.pos[1]-self.pos[1]))
            bullets.append(Bullet(self.pos[0], self.pos[1], target.pos[0]+20, target.pos[1]+25, color=BLUE))
            self.last_shot = now
    def draw(self, s):
        pygame.draw.rect(s, GRAY, self.rect)
        pygame.draw.rect(s, BLACK, (self.pos[0]-5, self.pos[1]-5, 10, 10))

# --- Functions ---
def reset_game_vars():
    global bullets, zombies, explosions, mines, turrets, SAFE_ZONE, player_health, dog, current_stamina
    global current_ammo, is_reloading, player_pos, last_spawn, level_kills, kill_goal, boss_spawned
    bullets, zombies, explosions, mines, turrets = [], [], [], [], []
    current_ammo = ammo_capacity
    player_health = player_max_health 
    current_stamina = max_stamina
    is_reloading, boss_spawned = False, False
    player_pos = [WIDTH // 2, HEIGHT // 2]
    last_spawn = pygame.time.get_ticks()
    level_kills = 0
    kill_goal = 1 if current_level % 5 == 0 else 5 + (current_level * 4)
    SAFE_ZONE = pygame.Rect(WIDTH//2 - 70, HEIGHT//2 - 70, 140, 140)
    dog = Dog(player_pos[0]-50, player_pos[1]) if has_dog else None

def draw_btn(txt, x, y, w, h, col, active=True):
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, col if active else DARK_GRAY, rect, border_radius=8)
    t_surf = font.render(txt, True, WHITE)
    screen.blit(t_surf, (x + (w - t_surf.get_width())//2, y + (h - t_surf.get_height())//2))
    return rect

# --- Main Game ---
game_state = "TITLE"
reset_game_vars()
last_shot = 0

running = True
while running:
    screen.fill(DARK_GRASS)
    mx, my = pygame.mouse.get_pos()
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        
        if game_state == "TITLE" and event.type == pygame.MOUSEBUTTONDOWN:
            if b_start.collidepoint(mx, my): game_state = "GAME"
            if b_shop_init.collidepoint(mx, my): game_state = "SHOP"
            if b_how_init.collidepoint(mx, my): game_state = "HOW"
            if b_easy.collidepoint(mx, my): difficulty = "Easy"
            if b_med.collidepoint(mx, my): difficulty = "Medium"
            if b_hard.collidepoint(mx, my): difficulty = "Hard"

        elif game_state == "GAME" and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_g and grenades_count > 0:
                explosions.append(Explosion(mx, my)); grenades_count -= 1
            if event.key == pygame.K_m and mines_count > 0:
                mines.append(Mine(player_pos[0]+15, player_pos[1]+20)); mines_count -= 1
            if event.key == pygame.K_t and turrets_owned > 0:
                turrets.append(Turret(player_pos[0], player_pos[1])); turrets_owned -= 1
            if event.key == pygame.K_n and nukes_count > 0:
                explosions.append(Explosion(WIDTH//2, HEIGHT//2, 800))
                zombies.clear(); level_kills = kill_goal; nukes_count -= 1

        elif game_state == "SHOP" and event.type == pygame.MOUSEBUTTONDOWN:
            if pygame.Rect(300, 540, 200, 45).collidepoint(mx, my): 
                current_level += 1; reset_game_vars(); game_state = "GAME"
            if pygame.Rect(50, 100, 300, 35).collidepoint(mx, my) and total_money >= 50:
                player_health = player_max_health; total_money -= 50
            if pygame.Rect(50, 140, 300, 35).collidepoint(mx, my) and total_money >= 200:
                player_max_health += 1; player_health += 1; total_money -= 200
            if pygame.Rect(50, 180, 300, 35).collidepoint(mx, my) and total_money >= 150:
                ammo_capacity += 4; total_money -= 150
            if pygame.Rect(50, 220, 300, 35).collidepoint(mx, my) and total_money >= 40:
                grenades_count += 1; total_money -= 40
            if pygame.Rect(50, 260, 300, 35).collidepoint(mx, my) and total_money >= 60:
                mines_count += 1; total_money -= 60
            if pygame.Rect(50, 300, 300, 35).collidepoint(mx, my) and total_money >= 250:
                turrets_owned += 1; total_money -= 250
            if pygame.Rect(50, 340, 300, 35).collidepoint(mx, my) and total_money >= 400 and not has_dog:
                has_dog = True; total_money -= 400
            if pygame.Rect(50, 380, 300, 35).collidepoint(mx, my) and total_money >= 800:
                nukes_count += 1; total_money -= 800
            if pygame.Rect(450, 100, 300, 35).collidepoint(mx, my) and total_money >= 150 and "Uzi" not in owned_guns:
                owned_guns.append("Uzi"); total_money -= 150
            if pygame.Rect(450, 140, 300, 35).collidepoint(mx, my) and total_money >= 200 and "Shotgun" not in owned_guns:
                owned_guns.append("Shotgun"); total_money -= 200
            for i, g in enumerate(["Pistol", "Uzi", "Shotgun"]):
                if pygame.Rect(450+(i*90), 200, 80, 35).collidepoint(mx, my) and g in owned_guns: current_gun = g

        elif game_state == "GAMEOVER" and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            save_record(difficulty, current_level); records = load_records()
            current_level, total_money, player_max_health = 1, 0, 3
            owned_guns, ammo_capacity, has_dog = ["Pistol"], 12, False
            grenades_count, turrets_owned, mines_count, nukes_count = 2, 0, 0, 0
            reset_game_vars(); game_state = "TITLE"

    if game_state == "GAME":
        pygame.draw.rect(screen, (0, 80, 200), SAFE_ZONE, 2)
        
        # Difficulty Scaling
        z_speed = (1.2 + (current_level * 0.1)) if difficulty == "Easy" else (2.2 + (current_level * 0.15)) if difficulty == "Medium" else (3.8 + (current_level * 0.2))
        m_mult = 1 if difficulty == "Easy" else 3 if difficulty == "Medium" else 6
        
        # Spawning
        if current_level % 5 != 0:
            if now - last_spawn > 1000 and level_kills < kill_goal:
                side = random.choice(["T", "B", "L", "R"])
                sx = random.randint(0, WIDTH) if side in ["T", "B"] else (-50 if side == "L" else WIDTH+50)
                sy = random.randint(0, HEIGHT) if side in ["L", "R"] else (-50 if side == "T" else HEIGHT+50)
                z_hp = random.choice([2, 3]) if current_level >= 3 and random.random() < 0.2 else 1
                zombies.append(Zombie(sx, sy, z_speed, z_hp)); last_spawn = now
        elif not boss_spawned:
            zombies.append(Zombie(WIDTH//2, -150, z_speed * 0.4, 25 + (current_level * 5), True)); boss_spawned = True

        # Boss UI
        if boss_spawned and zombies:
            for b in zombies:
                if b.is_boss:
                    pygame.draw.rect(screen, DARK_GRAY, (200, 20, 400, 20))
                    pygame.draw.rect(screen, RED, (200, 20, 400 * (b.health/b.max_health), 20))

        # Sprinting Logic
        k = pygame.key.get_pressed()
        is_sprinting = k[pygame.K_LSHIFT] and current_stamina > 0 and (k[pygame.K_w] or k[pygame.K_s] or k[pygame.K_a] or k[pygame.K_d])
        active_speed = sprint_speed if is_sprinting else player_speed
        
        if is_sprinting:
            current_stamina -= 0.8
        elif current_stamina < max_stamina:
            current_stamina += 0.4

        # Shooting & Reload Bar
        cooldown = 400 if current_gun == "Pistol" else 130 if current_gun == "Uzi" else 900
        if pygame.mouse.get_pressed()[0] and not is_reloading and now - last_shot > cooldown:
            if current_ammo > 0:
                if current_gun == "Shotgun":
                    for a in [-0.25, 0, 0.25]: bullets.append(Bullet(player_pos[0]+15, player_pos[1]+20, mx + math.sin(a)*100, my + math.cos(a)*100))
                else: bullets.append(Bullet(player_pos[0]+15, player_pos[1]+20, mx, my))
                current_ammo -= 1; last_shot = now
            else: is_reloading = True; reload_start = now

        if is_reloading:
            progress = (now - reload_start) / reload_speed_modifier
            pygame.draw.rect(screen, BLACK, (player_pos[0]-5, player_pos[1]-15, 40, 6))
            pygame.draw.rect(screen, YELLOW, (player_pos[0]-5, player_pos[1]-15, 40 * progress, 6))
            if progress >= 1: current_ammo = ammo_capacity; is_reloading = False

        # Input Movement
        if k[pygame.K_w] and player_pos[1] > 0: player_pos[1] -= active_speed
        if k[pygame.K_s] and player_pos[1] < HEIGHT-42: player_pos[1] += active_speed
        if k[pygame.K_a] and player_pos[0] > 0: player_pos[0] -= active_speed
        if k[pygame.K_d] and player_pos[0] < WIDTH-30: player_pos[0] += active_speed

        # Logic
        if has_dog: dog.update(player_pos[0], player_pos[1], zombies); dog.draw(screen)
        for t in turrets: t.update(zombies, bullets, now); t.draw(screen)
        for m in mines[:]:
            m.draw(screen)
            for z in zombies[:]:
                if m.rect.colliderect(pygame.Rect(z.pos[0], z.pos[1], z.w, z.h)):
                    explosions.append(Explosion(m.rect.centerx, m.rect.centery, 160)); mines.remove(m); break
        
        for e in explosions[:]:
            e.update(); e.draw(screen)
            for z in zombies[:]:
                if math.hypot(z.pos[0]-e.x, z.pos[1]-e.y) < e.radius:
                    z.health -= 5; (zombies.remove(z) if z.health <= 0 else None); level_kills += 1; total_money += m_mult
            if not e.alive: explosions.remove(e)

        for b in bullets[:]:
            b.move(); b.draw(screen)
            for z in zombies[:]:
                if pygame.Rect(z.pos[0], z.pos[1], z.w, z.h).collidepoint(b.pos):
                    z.health -= 1; (bullets.remove(b) if b in bullets else None)
                    if z.health <= 0: (zombies.remove(z) if z in zombies else None); total_money += m_mult; level_kills += 1

        for z in zombies[:]:
            z.move(player_pos[0], player_pos[1], SAFE_ZONE); z.draw(screen)
            if pygame.Rect(z.pos[0], z.pos[1], z.w, z.h).colliderect(pygame.Rect(player_pos[0], player_pos[1], 30, 42)):
                if now - last_hit_time > invincibility_duration:
                    player_health -= 1; last_hit_time = now
                    if player_health <= 0: game_state = "GAMEOVER"
                (zombies.remove(z) if not z.is_boss else None)

        if level_kills >= kill_goal and not zombies: game_state = "LEVEL_CLEAR"

        # Draw Player
        if now - last_hit_time > invincibility_duration or (now // 100 % 2 == 0):
            screen.blit(PLAYER_IMAGE, (player_pos[0], player_pos[1]))
        
        # HUD
        screen.blit(font.render(f"HP: {player_health}/{player_max_health} | Cash: ${total_money} | Lvl: {current_level}", True, WHITE), (10, 10))
        screen.blit(font.render(f"Ammo: {current_ammo} | G:{grenades_count} M:{mines_count} T:{turrets_owned} N:{nukes_count}", True, YELLOW), (10, 35))
        
        # Stamina Bar
        pygame.draw.rect(screen, GRAY, (10, 60, 100, 10))
        pygame.draw.rect(screen, BLUE, (10, 60, current_stamina, 10))

    elif game_state == "TITLE":
        screen.blit(large_font.render("ZOMBIE SURVIVAL", True, WHITE), (180, 50))
        b_easy = draw_btn(f"EASY - BEST: {records['Easy']}", 150, 140, 160, 40, (0,100,0) if difficulty=="Easy" else GRAY)
        b_med = draw_btn(f"MEDIUM - BEST: {records['Medium']}", 320, 140, 160, 40, (0,0,100) if difficulty=="Medium" else GRAY)
        b_hard = draw_btn(f"HARD - BEST: {records['Hard']}", 490, 140, 160, 40, (100,0,0) if difficulty=="Hard" else GRAY)
        b_start = draw_btn("START GAME", 300, 250, 200, 50, GREEN)
        b_shop_init = draw_btn("OPEN SHOP", 300, 320, 200, 50, BLUE)
        b_how_init = draw_btn("HOW TO PLAY", 300, 390, 200, 50, GRAY)

    elif game_state == "SHOP":
        screen.blit(large_font.render("TACTICAL SHOP", True, GOLD), (210, 20))
        screen.blit(font.render(f"Cash: ${total_money}", True, GREEN), (350, 75))
        draw_btn("Repair HP ($50)", 50, 100, 300, 35, (70,0,0))
        draw_btn("Upgrade Max HP ($200)", 50, 140, 300, 35, RED)
        draw_btn("Upgrade Max Ammo ($150)", 50, 180, 300, 35, YELLOW)
        draw_btn("Grenade x1 ($40)", 50, 220, 300, 35, ORANGE)
        draw_btn("Landmine x1 ($60)", 50, 260, 300, 35, DARK_GRAY)
        draw_btn("Turret x1 ($250)", 50, 300, 300, 35, GRAY)
        draw_btn("Buy Dog Companion ($400)", 50, 340, 300, 35, (139,69,19), not has_dog)
        draw_btn("NUKE x1 ($800)", 50, 380, 300, 35, RED)
        draw_btn("BUY UZI ($150)", 450, 100, 300, 35, BLUE, "Uzi" not in owned_guns)
        draw_btn("BUY SHOTGUN ($200)", 450, 140, 300, 35, BLUE, "Shotgun" not in owned_guns)
        for i, g in enumerate(["Pistol", "Uzi", "Shotgun"]):
            col = GREEN if current_gun == g else GRAY
            draw_btn(g, 450+(i*90), 200, 80, 35, col, g in owned_guns)
        draw_btn("START NEXT WAVE", 300, 540, 200, 45, GREEN)

    elif game_state == "LEVEL_CLEAR":
        screen.blit(large_font.render("WAVE CLEAR", True, GOLD), (240, 250))
        screen.blit(font.render("Press SPACE for Shop", True, WHITE), (310, 330))
        if pygame.key.get_pressed()[pygame.K_SPACE]: game_state = "SHOP"

    elif game_state == "GAMEOVER":
        screen.blit(large_font.render("YOU DIED", True, RED), (280, 250))
        screen.blit(font.render("Press SPACE for Menu", True, WHITE), (310, 330))
        if pygame.key.get_pressed()[pygame.K_SPACE]: 
            save_record(difficulty, current_level); reset_game_vars(); game_state = "TITLE"

    pygame.display.flip(); clock.tick(60)
pygame.quit()