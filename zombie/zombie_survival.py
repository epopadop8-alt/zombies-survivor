import pygame
import random
import math
import os

pygame.init()

# -------------------------
# SETTINGS
# -------------------------
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Zombie Survival")

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)

# -------------------------
# LOAD IMAGES
# -------------------------
player_img = pygame.image.load("assets/player.png").convert_alpha()
player_img = pygame.transform.scale(player_img, (40, 50))

zombie_img = pygame.image.load("assets/zombie.png").convert_alpha()
zombie_img = pygame.transform.scale(zombie_img, (40, 50))

background_img = pygame.image.load("assets/background.png").convert()
background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT))

# -------------------------
# PLAYER
# -------------------------
player_pos = [WIDTH//2, HEIGHT//2]
player_speed = 5
sprint_speed = 8
max_stamina = 100
stamina = 100
player_health = 5

# -------------------------
# GAME LISTS
# -------------------------
bullets = []
zombies = []

wave = 1
kills = 0
kill_goal = 5

# -------------------------
# CLASSES
# -------------------------
class Bullet:
    def __init__(self, x, y, tx, ty):
        self.pos = [x, y]
        angle = math.atan2(ty - y, tx - x)
        self.dx = math.cos(angle) * 12
        self.dy = math.sin(angle) * 12

    def move(self):
        self.pos[0] += self.dx
        self.pos[1] += self.dy

    def draw(self):
        pygame.draw.circle(screen, (255,255,0), (int(self.pos[0]), int(self.pos[1])), 5)

class Zombie:
    def __init__(self):
        side = random.choice(["top","bottom","left","right"])
        if side == "top":
            self.pos = [random.randint(0, WIDTH), -50]
        elif side == "bottom":
            self.pos = [random.randint(0, WIDTH), HEIGHT+50]
        elif side == "left":
            self.pos = [-50, random.randint(0, HEIGHT)]
        else:
            self.pos = [WIDTH+50, random.randint(0, HEIGHT)]

        self.speed = 1.5 + wave * 0.2
        self.health = 2

    def move(self):
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist != 0:
            self.pos[0] += (dx/dist) * self.speed
            self.pos[1] += (dy/dist) * self.speed

    def draw(self):
        screen.blit(zombie_img, self.pos)

# -------------------------
# MAIN LOOP
# -------------------------
running = True
last_spawn = 0
last_shot = 0

while running:
    clock.tick(60)
    screen.blit(background_img, (0,0))
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # -------------------------
    # MOVEMENT + SPRINT
    # -------------------------
    keys = pygame.key.get_pressed()
    speed = player_speed

    if keys[pygame.K_LSHIFT] and stamina > 0:
        speed = sprint_speed
        stamina -= 1
    else:
        if stamina < max_stamina:
            stamina += 0.5

    if keys[pygame.K_w]: player_pos[1] -= speed
    if keys[pygame.K_s]: player_pos[1] += speed
    if keys[pygame.K_a]: player_pos[0] -= speed
    if keys[pygame.K_d]: player_pos[0] += speed

    player_pos[0] = max(0, min(WIDTH-40, player_pos[0]))
    player_pos[1] = max(0, min(HEIGHT-50, player_pos[1]))

    # -------------------------
    # SHOOTING
    # -------------------------
    mouse = pygame.mouse.get_pressed()
    mx, my = pygame.mouse.get_pos()

    if mouse[0] and now - last_shot > 300:
        bullets.append(Bullet(player_pos[0]+20, player_pos[1]+25, mx, my))
        last_shot = now

    # -------------------------
    # SPAWN ZOMBIES
    # -------------------------
    if now - last_spawn > 1000 and kills < kill_goal:
        zombies.append(Zombie())
        last_spawn = now

    # -------------------------
    # UPDATE BULLETS
    # -------------------------
    for b in bullets[:]:
        b.move()
        b.draw()
        if b.pos[0] < 0 or b.pos[0] > WIDTH or b.pos[1] < 0 or b.pos[1] > HEIGHT:
            bullets.remove(b)

    # -------------------------
    # UPDATE ZOMBIES
    # -------------------------
    for z in zombies[:]:
        z.move()
        z.draw()

        # collision with player
        player_rect = pygame.Rect(player_pos[0], player_pos[1], 40, 50)
        zombie_rect = pygame.Rect(z.pos[0], z.pos[1], 40, 50)

        if player_rect.colliderect(zombie_rect):
            player_health -= 1
            zombies.remove(z)
            if player_health <= 0:
                running = False

        # bullet collision
        for b in bullets[:]:
            if zombie_rect.collidepoint(b.pos):
                z.health -= 1
                bullets.remove(b)
                if z.health <= 0:
                    zombies.remove(z)
                    kills += 1

    # -------------------------
    # WAVE CLEAR
    # -------------------------
    if kills >= kill_goal and len(zombies) == 0:
        wave += 1
        kills = 0
        kill_goal += 5

    # -------------------------
    # DRAW PLAYER
    # -------------------------
    screen.blit(player_img, player_pos)

    # -------------------------
    # HUD
    # -------------------------
    screen.blit(font.render(f"HP: {player_health}", True, (255,255,255)), (10,10))
    screen.blit(font.render(f"Wave: {wave}", True, (255,255,255)), (10,35))
    screen.blit(font.render(f"Stamina", True, (255,255,255)), (10,60))
    pygame.draw.rect(screen, (100,100,100), (10,85,100,10))
    pygame.draw.rect(screen, (0,200,255), (10,85,stamina,10))

    pygame.display.flip()

pygame.quit()
