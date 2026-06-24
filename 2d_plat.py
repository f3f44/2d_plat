import time
init_start = time.perf_counter()

import pygame, math, copy, json, colorama, psutil, platform, os, io, tempfile
import assets.modules.myzip as lvl
import tkinter as tk
from tkinter import filedialog

f3_static = [
    f"OS: {platform.system()} {platform.release()}",
]

w, h = 800, 600
fps = 100
tps = 100
ttd = 1/tps
frame = 0
tick = 0
accumulator = 0
last_time = init_start+1-1
alpha = 0

colorama.init()
pygame.init()
pygame.mixer.init()
screen_final = pygame.display.set_mode((w, h), pygame.RESIZABLE)
screen = pygame.Surface((w//3, h//3), pygame.SRCALPHA)
clock = pygame.time.Clock()
Vec2 = pygame.math.Vector2
os.system('cls')

level = {}
sprites = {
    '__ERROR__': r'assets\sprites\debug\ERROR.png',
    '__jump_pad__': r'assets\sprites\jump_pad.png',
    '__player_default_skin__': r'assets\sprites\player_skins\Player_default.png',
    '__logo__': r'assets\sprites\logo.png',
    '__bg_logo__': r'assets\sprites\logo.png',
    '__text_logo__': r'assets\sprites\text_logo.png',
}
sounds = {}

level_archive = lvl.decode_to_dict(r'.\levels\test.lvl')
level_data = json.loads(level_archive['structure.json'])
level_config = json.loads(level_archive['config.json'])
for j, i in level_archive['sprite'].items():
    sprites[j] = i
for j, i in level_archive['sound'].items():
    sounds[j] = i
os.system('cls')
#os.system('pause')

for j, i in sprites.items():
    try:
        sprites[j] = pygame.image.load(i).convert_alpha()
        print(f'Sprite {j} loaded from path ({i})')
    except Exception:
        try:
            sprites[j] = pygame.image.load(io.BytesIO(i)).convert_alpha()
            print(f'Sprite {j} loaded from archive')
        except Exception:
            print(f'\033[38;2;255;0;0mERROR>>>Sprite {i} (known as {j}) does not exist!\033[0m')
            sprites[j] = sprites['__ERROR__']

for j, i in sounds.items():
    try:
        if not (isinstance(i, str) and os.path.exists(i)):
            raise ValueError
        sounds[j] = pygame.mixer.Sound(i)
        print(f'Sound {j} loaded from path ({i})')
    except Exception:
        try:
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_file.write(i)
                temp_file_path = temp_file.name
            sounds[j] = pygame.mixer.Sound(temp_file_path)
            print(f'Sound {j} loaded from archive')
        except Exception:
            print(f'\033[38;2;255;0;0mERROR>>>Sound {i} (known as {j}) does not exist!\033[0m')

_current_process = psutil.Process()

def get_ram_usage():
    ram_used_bytes = _current_process.memory_info().rss
    ram_used_mb = round(ram_used_bytes / (1024**2), 1)
    ram_total_bytes = psutil.virtual_memory().total
    ram_total_gb = round(ram_total_bytes / (1024**3))
    return ram_used_mb, ram_total_gb

def gen_id(l=32):
    r = ''
    a = fr'QWERTYUIOP{"{}"}ASDFGHJKL:"|ZXCVBNM<>?qwertyuiop[]asdfghjkl;{"'"}\zxcvbnm,./'
    for i in range(l):
        r += a[random.randint(0, len(a)-1)]
    return r

class Camera:
    def __init__(self):
        self.pos = Vec2(0, 0)
        self.phpos = Vec2(0, 0)
    def update(self, target):
        if isinstance(target, tuple):
            self.phpos -= (self.phpos-target)/10
            return
        r = pygame.Rect(target.pos.x-10, target.pos.y+10, 20, 20)
        if r.collidepoint((self.pos.x, self.pos.y)):
            return
        self.phpos.x -= (self.phpos.x-target.rect.centerx-(target.vel.x/target.max_speed*400))/5
        self.phpos.y -= (self.phpos.y-target.rect.centery-(target.vel.y/target.max_speed*0))/5
        ss = screen.get_size()
        self.pos = self.phpos+(-ss[0]//2, -ss[1]//2)
camera = Camera()

class Solid:
    def __init__(self, rect, beh, name=''):
        self.rect = pygame.Rect(rect)
        self.beh = beh
        self.delta_x = 0
        self.delta_y = 0
        self.hp = 100
        self.name = name
    def update(self):
        self.delta_x = 0
        self.delta_y = 0
        beh = self.beh
        if not beh:
            return
        if beh['type'] == 'sine':
            old_x = self.rect.x
            old_y = self.rect.y
            self.rect.x = int(round(math.sin((2 * math.pi * (tick/100)) / beh['speed'] + beh['time offset']) * beh['amplitude'][0] + beh['center'][0]))
            self.rect.y = int(round(math.sin((2 * math.pi * (tick/100)) / beh['speed'] + beh['time offset']) * beh['amplitude'][1] + beh['center'][1]))
            self.delta_x = self.rect.x - old_x
            self.delta_y = self.rect.y - old_y
    def draw(self):
        pygame.draw.rect(screen, (255, 255, 255), (self.rect.x-camera.pos.x, self.rect.y-camera.pos.y, self.rect.width, self.rect.height))

class Visual:
    def __init__(self, sprite, pos, rot, size, follow):
        self.pos = Vec2(pos)
        self.spr = sprites[sprite]
        r = self.spr.get_rect()
        hs = size*(r.height/r.width)
        self.spr = pygame.transform.scale(self.spr, [size, hs])
        self.spr = pygame.transform.rotate(self.spr, rot)
        self.follow = Vec2(follow)
    def draw(self):
        r = self.spr.get_rect()
        screen_x = int(self.pos.x - (camera.pos.x * self.follow.x))
        screen_y = int(self.pos.y - (camera.pos.y * self.follow.y))
        r.topleft = (screen_x, screen_y)
        s = screen.get_rect()
        if r.colliderect(s):
            screen.blit(self.spr, r.topleft, special_flags=pygame.BLEND_ALPHA_SDL2)

class Pad:
    def __init__(self, pos, Type='jump', direction=(0, 0), hidden=False):
        self.pos = Vec2(pos)
        self.spr_pos=(0, 0)
        self.type = Type
        self.vec = Vec2(direction)
        self.hid = hidden
        if self.type == 'jump':
            s = sprites['__jump_pad__']
            angle = self.vec.as_polar()[1]-90
            self.spr = pygame.transform.rotate(s, -angle-180)
            basebox = (Vec2(-14, 1), Vec2(14, 1), Vec2(14, -2), Vec2(-14, -2))
            self.hitbox = (basebox[0].rotate(angle)+self.pos, basebox[1].rotate(angle)+self.pos, basebox[2].rotate(angle)+self.pos, basebox[3].rotate(angle)+self.pos)
            hitbox_x = (self.hitbox[0].x, self.hitbox[1].x, self.hitbox[2].x, self.hitbox[3].x)
            hitbox_y = (self.hitbox[0].y, self.hitbox[1].y, self.hitbox[2].y, self.hitbox[3].y)
            self.checkbox = pygame.Rect(min(hitbox_x), min(hitbox_y), max(hitbox_x)-min(hitbox_x), max(hitbox_y)-min(hitbox_y))
            self.spr_pos = Vec2(self.spr.get_rect(center=self.pos).topleft)
    def check_collision(self, rect):
        if not self.checkbox.colliderect(rect):
            return False
        for i in [(0, 1), (1, 2), (2, 3), (3, 0)]:
            if rect.clipline(self.hitbox[i[0]], self.hitbox[i[1]]):
                return True
        return False
    def draw(self):
        if self.hid:
            return
        screen.blit(self.spr, self.spr_pos-camera.pos, special_flags=pygame.BLEND_ALPHA_SDL2)

def limit_view(rad=200):
    res = []
    p_screen_x = player.rect.centerx - camera.pos.x
    p_screen_y = player.rect.centery - camera.pos.y
    player_screen = pygame.Vector2(p_screen_x, p_screen_y)
    for degree in range(0, 360, 2):
        angle = math.radians(degree)
        ray_dir = pygame.Vector2(math.cos(angle), math.sin(angle))
        closest_point = player_screen + ray_dir * rad
        min_dist = rad
        for s in level['solids']:
            s_left = s.rect.left - camera.pos.x
            s_right = s.rect.right - camera.pos.x
            s_top = s.rect.top - camera.pos.y
            s_bottom = s.rect.bottom - camera.pos.y
            lines = [
                ((s_left, s_top), (s_right, s_top)),
                ((s_right, s_top), (s_right, s_bottom)),
                ((s_right, s_bottom), (s_left, s_bottom)),
                ((s_left, s_top), (s_left, s_bottom))
            ]
            for p1, p2 in lines:
                x1, y1 = p1
                x2, y2 = p2
                x3, y3 = player_screen.x, player_screen.y
                x4, y4 = player_screen.x + ray_dir.x * rad, player_screen.y + ray_dir.y * rad
                den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
                if den == 0: 
                    continue
                t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
                u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
                if 0 <= t <= 1 and 0 <= u <= 1:
                    ix = x1 + t * (x2 - x1)
                    iy = y1 + t * (y2 - y1)
                    dist = math.hypot(ix - player_screen.x, iy - player_screen.y)
                    if dist < min_dist:
                        min_dist = dist
                        closest_point = pygame.Vector2(ix, iy)
        res.append(closest_point)
    res.sort(key=lambda p: math.atan2(p.y - player_screen.y, p.x - player_screen.x))
    return res

level['solids'] = [] 
for i in level_data['solids']:
    level['solids'].append(Solid(i['rect'], i['beh'], i.get('name', '')))
level['pads'] = []
for i in level_data['pads']:
    level['pads'].append(Pad(i['pos'], i.get('Type', 'jump'), i.get('direction', (0, 0)), i.get('hidden', False)))
level['sprites'] = []
for i in level_data['sprites']:
    level['sprites'].append(Visual(i['sprite'], i['pos'], i['rot'], i['size'], i['follow']))

controls = {
    'jump': pygame.K_SPACE,
    'left': pygame.K_a,
    'right': pygame.K_d,
    'run': pygame.K_LSHIFT,
}

class Player:
    def __init__(self, pos=(0, 0), skin=sprites['__player_default_skin__']):
        self.rect = pygame.Rect(pos[0], pos[1], 6, 14)
        self.pos = Vec2(pos[0], pos[1])
        self.vel = Vec2(0, 0)
        self.max_speed = 30
        self.sprites = []
        self.flip_sprites = []
        self.hp = 100
        if isinstance(skin, str):
            image = pygame.image.load(skin)
        else:
            image = skin
        a = image.get_rect()
        b = a.width/4
        c = a.height/4
        for y in range(4):
            for x in range(4):
                r = image.subsurface((x*b, y*c, b, c))
                self.sprites.append(r)
        for y in range(4):
            for x in range(4):
                r = image.subsurface((x*b, y*c, b, c))
                r = pygame.transform.flip(r, True, False)
                self.flip_sprites.append(r)
        self.ground = False
        self.direction = False
        self.cheats = []
        self.jpx = False
        self.run = False
        self.fall = 0
        self.cfall = 0
        self.stands_on = None
    def update(self):
        k = pygame.key.get_pressed()
        
        for i in level['pads']:
            if i.check_collision(self.rect):
                self.jp = True
                self.vel.x = copy.copy(i.vec.x)
                if i.vec.y != 0:
                    self.vel.y = copy.copy(i.vec.y)
                if self.vel.x != 0:
                    self.jpx = True
                break
        
        for event in event_buf:
            if event.type == pygame.KEYDOWN:
                if event.key == controls['jump'] and self.ground:
                    self.vel.y = -3
                if event.key == controls['run']:
                    self.run = 1
            if event.type == pygame.KEYUP:
                if event.key == controls['jump'] and self.vel.y < 0 and not self.jpx:
                    self.vel.y *= 0.5
                if event.key == controls['run']:
                    self.run = 0
        
        if self.ground:
            rect = self.rect.copy()
            rect.height += 4
            rect.y += 2
            for i in level['solids']:
                if rect.colliderect(i.rect):
                    self.pos.x += i.delta_x
                    self.pos.y += i.delta_y
        
        if not self.jpx and not self.run:
            if k[controls['right']] and self.vel.x+0.25 < self.max_speed:
                self.vel.x += 0.25
                self.direction = False
                
            if k[controls['left']] and self.vel.x-0.25 > -self.max_speed:
                self.vel.x -= 0.25
                self.direction = True
            
            self.vel.x *= 0.8
        elif not self.jpx:
            if k[controls['right']] and self.vel.x+0.25 < self.max_speed*10:
                self.vel.x += 0.25
                self.direction = False
                
            if k[controls['left']] and self.vel.x-0.25 > -self.max_speed*10:
                self.vel.x -= 0.25
                self.direction = True
            
            self.vel.x *= 0.8
        
        self.pos.x += self.vel.x
        self.rect.x = int(round(self.pos.x))
        
        self.vel.y += 0.1
        self.vel.y = min(max(self.vel.y, -self.max_speed), self.max_speed)
        self.pos.y += self.vel.y
        self.rect.y = int(round(self.pos.y))
        self.ground = False
        
        for i in level['solids']:
            if self.rect.colliderect(i.rect):
                over = (min(self.rect.right, i.rect.right) - max(self.rect.left, i.rect.left), min(self.rect.bottom, i.rect.bottom) - max(self.rect.top, i.rect.top))
                if over[0] < over[1]:
                    if self.rect.centerx < i.rect.centerx:
                        self.pos.x -= over[0]
                    else:
                        self.pos.x += over[0]
                    self.vel.x = 0
                else:
                    if self.rect.centery < i.rect.centery:
                        self.pos.y -= over[1]
                    else:
                        self.pos.y += over[1]
                    self.vel.y = 0
                self.rect.x = int(round(self.pos.x))
                self.rect.y = int(round(self.pos.y))
                self.jpx = False
        rect = self.rect.copy()
        rect.y += 1
        self.stands_on = None
        for i in level['solids']:
            if rect.colliderect(i.rect):
                self.ground = True
                self.stands_on = i.name
                break
        
        if self.pos.y > 300:
            self.pos = Vec2(0, 0)
            self.vel = Vec2(0, 0)
        
        self.fall = self.cfall-1+1
        if not self.ground:
            self.cfall += 1
        else:
            self.cfall = 0
        
    def draw(self):
        k = pygame.key.get_pressed()
        c = 0
        if self.ground:
            if round(self.vel.x) != 0:
                c = int((tick//10)%3+1)
        else:
            c = 5
        pos = self.sprites[c].get_rect(center=self.rect.center)
        if not self.direction:
            screen.blit(self.sprites[c], (pos[0]+1-camera.pos.x, pos[1]-1-camera.pos.y), special_flags=pygame.BLEND_ALPHA_SDL2)
        else:
            screen.blit(self.flip_sprites[c], (pos[0]-1-camera.pos.x, pos[1]-1-camera.pos.y), special_flags=pygame.BLEND_ALPHA_SDL2)
player = Player()

def select_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(
        title="Выберите файл скина",
        initialdir=os.getcwd(),
        filetypes=[
            ("Image files", "*.jpg *.png *.bmp"),
            ("All files", "*.*")
        ]
    )
    root.destroy()
    return file_path

globalz = globals()
menu = None

class Button:
    def __init__(self, rect, behFile='', menu=None):
        self.rect = pygame.Rect(rect)
        try:
            with open(behFile) as f:
                self.code = f.read().split('|')
        except Exception as e:
            print(f'\033[38;2;255;0;0mERROR>>>Button Behaivior File {behFile} does not exist!\033[0m')
            print(e)
        self.p = False
        self.menu = menu
    def update(self):
        global menu
        if menu!=self.menu:
            self.p = False
            return
        mpos = pygame.mouse.get_pos()
        m = pygame.mouse.get_pressed()
        if self.rect.collidepoint(mpos) and m[0]:
            if self.p:
                exec(self.code[2], globalz, {'self': self})
            else:
                exec(self.code[1], globalz, {'self': self})
        elif self.p:
            exec(self.code[3], globalz, {'self': self})
        exec(self.code[0], globalz, {'self': self})
        self.p = copy.copy(m[0])
    def draw(self, look=(255, 255, 255)):
        if isinstance(look, tuple):
            pygame.draw.rect(screen_final, look, self.rect)
        else:
            screen_final.blit(look, self.rect)

s = w, h

f3mts = 20
TAA = False
Text = pygame.font.SysFont('Consolas', f3mts)

f3_static_text = []
f3_dynamic_text = []
f3_dynamic = []
debug_menu = False
for i in f3_static:
    f3_static_text.append(Text.render(i, TAA, (255, 255, 255)))
f3_text = f3_static_text[:]
temps = pygame.Surface((w, h), pygame.SRCALPHA)

tick_counter = 0
real_tps = tps
last_f3_update = time.perf_counter()
event_buf = []

adv_f3 = False
show_fps = False

if level_config['background'][2]:
    bgrect = sprites[level_config['background'][0]].get_rect()
    bgh = bgrect.height/bgrect.width
    sprites[level_config['background'][0]] = pygame.transform.scale(sprites[level_config['background'][0]], ((800//3), (800//3)*bgh))
    bgrect = sprites[level_config['background'][0]].get_rect()
del bgh

sound_req = {}
for j, i in level_config['solids'].items():
    sound_req[i[0]] = f'player.stands_on == "{j}" and {i[1]}'

view = limit_view()

fog = screen.copy()
mask = pygame.Surface((w // 3, h // 3), pygame.SRCALPHA)

sr = pygame.Rect(0, 0, 800, 600)
sprites['__bg_logo__'] = pygame.transform.scale(sprites['__bg_logo__'], (64, 64))
rs = screen_final.get_size()
rs = (rs[0]+64, rs[1]+64)
bgscreen = pygame.Surface(rs)
for y in range(0, rs[1]+64, 64):
    for x in range(0, rs[0]+64, 64):
        bgscreen.blit(sprites['__bg_logo__'], (x, y))

pause = False
pausescr = pygame.Surface((w, h), pygame.SRCALPHA)
pygame.draw.rect(pausescr, (0, 0, 0, 64), (0, 0, w, h))
pause_text = [('Resume', r'assets\behFiles\buttons\resume.py')]
for j, i in enumerate(pause_text):
    t = Text.render(i[0], TAA, (255, 255, 255))
    r = t.get_rect()
    pause_menu = [(Button((25, 100+(f3mts*j), r.width, r.height), i[1], 'pause'), t)]
sprites['__text_logo__'] = pygame.transform.scale(sprites['__text_logo__'], (264, 40))
pausescr.blit(sprites['__text_logo__'], (25, 25))

pygame.display.set_caption('2d_plat beta testing v0.2.0')
pygame.display.set_icon(sprites['__logo__'])
init_time = time.perf_counter() - init_start
print(f"\033[38;2;{int(max(0, min(1, (init_time - 0.5) / 0.5)) * 255)};{int((1 - max(0, min(1, (init_time - 1.0) / 0.5))) * 255)};0mInited in: {round(init_time, 3)}s\033[0m")

run = True
while run:
    frame += 1
    st = time.perf_counter()
    dt = st - last_time
    last_time = st
    if not pause:
        accumulator += dt
    true_w, true_h = screen_final.get_size()
    
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F3:
                debug_menu = not debug_menu
            if debug_menu:
                if event.key == pygame.K_p:
                    adv_f3 = not adv_f3
                if event.key == pygame.K_f:
                    show_fps = not show_fps
            if event.key == pygame.K_ESCAPE:
                pause = not pause
                if pause:
                    menu = 'pause'
                else:
                    menu = None
        if event.type == pygame.VIDEORESIZE:
            sr = screen.get_rect()
            s = event.w, event.h
            sr.width, sr.height = (s[0], s[0]*0.75)
            sr.center = (s[0]//2, s[1]//2)
            if sr.height > s[1]:
                sr.width, sr.height = (s[1]/0.75, s[1])
                sr.center = (s[0]//2, s[1]//2)
            bgscreen = pygame.Surface((event.w+64, event.h+64))
            rs = (event.w+64, event.h+64)
            for y in range(0, rs[1]+64, 64):
                for x in range(0, rs[0]+64, 64):
                    bgscreen.blit(sprites['__bg_logo__'], (x, y))
            pausescr = pygame.Surface((event.w, event.h), pygame.SRCALPHA)
            pygame.draw.rect(pausescr, (0, 0, 0, 64), (0, 0, event.w, event.h))
            pausescr.blit(sprites['__text_logo__'], (25, 25))
        if not pause:
            event_buf.append(event)
    
    if menu != None:
        pygame.mouse.set_visible(True)
    else:
        pygame.mouse.set_visible(False)
        pygame.mouse.set_pos((s[0]//2, s[1]//2))
    
    while accumulator > ttd and not pause:
        tick += 1
        for i in level['solids']:
            i.update()
        player.update()
        camera.update(player)
        if level_config['darkness']:
            view = limit_view()
        for j, i in sound_req.items():
            if eval(i, {'player': player}):
                sounds[j].play()
        accumulator -= ttd
        tick_counter += 1
        event_buf = []
    
    screen_final.fill((0, 0, 0))
    screen_final.blit(bgscreen, ((frame//10)%64-64, (frame//10)%64-64))
    screen.fill((0, 0, 0, 0))
    
    for x in range(int((-camera.pos.x * level_config['background'][1][0]) % bgrect.width - bgrect.width), w // 3 + bgrect.width, bgrect.width):
        for y in range(int((-camera.pos.y * level_config['background'][1][1]) % bgrect.height - bgrect.height), h // 3 + bgrect.height, bgrect.height):
            screen.blit(sprites[level_config['background'][0]], (x, y))
    
    for i in level['solids']:
        i.draw()
    for i in level['sprites']:
        i.draw()
    player.draw()
    for i in level['pads']:
        i.draw()
    if level_config['darkness']:
        fog.fill((0, 0, 0, 0))
        mask.fill((0, 0, 0, 255))
        pygame.draw.polygon(mask, (0, 0, 0, 0), view)
        screen.blit(mask, (0, 0))
    
    scaled_screen = pygame.transform.scale(screen, (sr.width, sr.height))
    screen_final.blit(scaled_screen, (sr.x, sr.y))
    if pause:
        screen_final.blit(pausescr, (0, 0))
        for i in pause_menu:
            i[0].update()
            i[0].draw(i[1])
    
    if debug_menu and (st - last_f3_update >= 0.5):
        passed_time = st - last_f3_update
        real_tps = round(tick_counter / passed_time)
        tick_counter = 0
        last_f3_update = st
        f3_dynamic = []
        f3_dynamic_text = []
        f3_text = f3_static_text[:]
        ft = round(time.perf_counter() - st, 5)
        f3_dynamic.append(f'TPS: {real_tps} / {tps}')
        f3_dynamic.append(f'FPS: {round(clock.get_fps(), 1)}')
        
        r = get_ram_usage()
        f3_dynamic.append(f'RAM: {r[0]}mb/{r[1]}gb')
        if adv_f3:
            f3_dynamic.append(f'-----PLAYER-----')
            f3_dynamic.append(f'Pos: {player.rect.center}')
            f3_dynamic.append(f'Vel: {player.vel}')
            f3_dynamic.append(f'True Pos: {player.pos}')
            f3_dynamic.append(f'Grounded: {player.ground}')
            f3_dynamic.append(f'fall: {player.fall}')
        
        for i in f3_dynamic:
            f3_dynamic_text.append(Text.render(i, TAA, (255, 255, 255)))
        for i in f3_dynamic_text:
            f3_text.append(i)
            
        temps.fill((0, 0, 0, 0))
        for j, i in enumerate(f3_text):
            r = i.get_rect()
            pygame.draw.rect(temps, (0, 0, 0, 64), (0, f3mts * j, r.width, r.height))
            temps.blit(i, (0, f3mts * j))
    elif (st - last_f3_update >= 0.5) and show_fps:
        temps.fill((0, 0, 0, 0))
        m = Text.render(f'FPS: {round(clock.get_fps(), 1)}', TAA, (255, 255, 255))
        r = m.get_rect()
        pygame.draw.rect(temps, (0, 0, 0, 64), (0, 0, r.width, r.height))
        temps.blit(m, (0, 0))
    
    if debug_menu or show_fps:
        screen_final.blit(temps, (0, 0))
    pygame.display.flip()
    clock.tick()
print('bye!')
pygame.quit()