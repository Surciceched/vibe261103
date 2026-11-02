"""제비우스 스타일 종스크롤 슈팅 게임 (pygame).

공중의 적은 자퍼(Z / Space)로, 지상의 적은 조준점이 가리키는 곳에
블래스터(X / Left Ctrl)를 떨어뜨려 파괴한다. 그래픽과 효과음은 모두
코드로 생성하므로 별도의 리소스 파일이 필요 없다.

실행: python shooting.py
"""

import array
import math
import random
import sys
from dataclasses import dataclass

import pygame

WIDTH = 480
HEIGHT = 640
FPS = 60

SCROLL_SPEED = 1.2
AREA_LENGTH = 4200  # 보스가 나타나기까지 스크롤되는 거리(픽셀)
BOSS_TIME_LIMIT = 45 * FPS
RETICLE_DISTANCE = 150
BOMB_FLIGHT_FRAMES = 24
BOMB_RADIUS = 22
START_LIVES = 3
FIRST_EXTEND = 20000
NEXT_EXTEND = 40000

WHITE = (240, 240, 245)
BLACK = (0, 0, 0)
SILVER = (190, 198, 210)
STEEL = (110, 120, 138)
DARK_STEEL = (58, 64, 78)
RED = (232, 70, 70)
ORANGE = (250, 160, 60)
YELLOW = (250, 225, 90)
CYAN = (100, 225, 240)
PINK = (255, 110, 190)
TEXT_SHADOW = (10, 12, 20)

TERRAIN_PALETTE = [
    (38, 82, 48),   # 숲
    (92, 80, 50),   # 사막
    (54, 74, 62),   # 습지
    (70, 66, 76),   # 황무지
]
PALETTE_SPAN = 5000
RIVER_COLOR = (38, 74, 112)
RIVER_EDGE = (66, 108, 140)
ROAD_COLOR = (120, 112, 96)


def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def distance(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def aimed_velocity(x, y, target_x, target_y, speed):
    d = distance(x, y, target_x, target_y) or 1
    return (target_x - x) / d * speed, (target_y - y) / d * speed


def river_x(world):
    return WIDTH * 0.5 + 130 * math.sin(world / 410) + 60 * math.sin(world / 157)


def river_half_width(world):
    return 34 + 10 * math.sin(world / 230)


def road_x(world):
    return WIDTH * 0.5 + 170 * math.sin(world / 530 + 2)


def terrain_color(world):
    position = world / PALETTE_SPAN
    index = int(position)
    return lerp_color(
        TERRAIN_PALETTE[index % len(TERRAIN_PALETTE)],
        TERRAIN_PALETTE[(index + 1) % len(TERRAIN_PALETTE)],
        position - index,
    )


class Terrain:
    """스크롤 위치에 맞춰 지형 조각을 절차적으로 생성하고 재사용한다."""

    CHUNK_HEIGHT = 256
    ROW_HEIGHT = 8

    def __init__(self):
        self.chunks = {}

    def _build_chunk(self, index):
        surface = pygame.Surface((WIDTH, self.CHUNK_HEIGHT)).convert()
        top_world = (index + 1) * self.CHUNK_HEIGHT

        for row in range(0, self.CHUNK_HEIGHT, self.ROW_HEIGHT):
            color = terrain_color(top_world - row)
            surface.fill(color, (0, row, WIDTH, self.ROW_HEIGHT))

        # 경계에 걸친 장식이 잘리지 않도록 위아래 조각의 장식도 함께 그린다.
        neighbors = (index - 1, index, index + 1)
        for source in neighbors:
            rng = random.Random(source * 7919 + 13)
            shift = (index - source) * self.CHUNK_HEIGHT
            for _ in range(14):
                x = rng.randrange(WIDTH)
                y = rng.randrange(self.CHUNK_HEIGHT) + shift
                base = terrain_color(top_world - y)
                patch = lerp_color(base, BLACK, 0.12)
                pygame.draw.ellipse(surface, patch, (x - 40, y - 16, 80, 32))

        road = [
            (road_x(top_world - y), y)
            for y in range(-8, self.CHUNK_HEIGHT + 9, 8)
        ]
        pygame.draw.lines(surface, ROAD_COLOR, False, road, 5)

        left, right = [], []
        for y in range(-8, self.CHUNK_HEIGHT + 9, 8):
            world = top_world - y
            center = river_x(world)
            half = river_half_width(world)
            left.append((center - half, y))
            right.append((center + half, y))
        pygame.draw.polygon(surface, RIVER_COLOR, left + right[::-1])
        pygame.draw.lines(surface, RIVER_EDGE, False, left, 3)
        pygame.draw.lines(surface, RIVER_EDGE, False, right, 3)

        for source in neighbors:
            rng = random.Random(source * 6271 + 29)
            shift = (index - source) * self.CHUNK_HEIGHT
            for _ in range(46):
                x = rng.randrange(WIDTH)
                y = rng.randrange(self.CHUNK_HEIGHT) + shift
                size = rng.randint(3, 6)
                world = top_world - y
                if abs(x - river_x(world)) < river_half_width(world) + 10:
                    continue
                if abs(x - road_x(world)) < 10:
                    continue
                base = terrain_color(world)
                pygame.draw.circle(surface, lerp_color(base, BLACK, 0.3), (x + 1, y + 2), size)
                pygame.draw.circle(surface, lerp_color(base, WHITE, 0.1), (x, y), size)
        return surface

    def draw(self, screen, scroll):
        first = int(scroll // self.CHUNK_HEIGHT)
        last = int((scroll + HEIGHT) // self.CHUNK_HEIGHT)
        for index in range(first, last + 1):
            if index not in self.chunks:
                self.chunks[index] = self._build_chunk(index)
            y = HEIGHT - ((index + 1) * self.CHUNK_HEIGHT - scroll)
            screen.blit(self.chunks[index], (0, round(y)))
        for index in [i for i in self.chunks if i < first]:
            del self.chunks[index]


class SoundBank:
    """효과음을 코드로 합성한다. 오디오 장치가 없으면 조용히 넘어간다."""

    def __init__(self):
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 256)
            rate, _, channels = pygame.mixer.get_init()
            self.sounds = {
                "shot": self._tone(rate, channels, 1400, 700, 50, 0.10),
                "bomb": self._tone(rate, channels, 900, 240, 160, 0.16),
                "boom": self._tone(rate, channels, 300, 60, 200, 0.22, noise=True),
                "hit": self._tone(rate, channels, 500, 300, 60, 0.15, noise=True),
                "bonus": self._tone(rate, channels, 600, 1500, 240, 0.2),
                "death": self._tone(rate, channels, 500, 40, 700, 0.3, noise=True),
            }
        except pygame.error:
            self.sounds = {}

    @staticmethod
    def _tone(rate, channels, start_hz, end_hz, ms, volume, noise=False):
        total = int(rate * ms / 1000)
        rng = random.Random(start_hz)
        samples = array.array("h")
        phase = 0.0
        for i in range(total):
            t = i / total
            phase += (start_hz + (end_hz - start_hz) * t) / rate
            wave = 1.0 if phase % 1 < 0.5 else -1.0
            if noise:
                wave = wave * 0.35 + rng.uniform(-1, 1) * 0.65
            value = int(wave * (1 - t) * volume * 32767)
            samples.extend([value] * channels)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, name):
        sound = self.sounds.get(name)
        if sound:
            sound.play()


@dataclass
class Controls:
    dx: float = 0
    dy: float = 0
    fire: bool = False
    bomb: bool = False


def read_controls():
    keys = pygame.key.get_pressed()
    dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
    dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
    return Controls(
        dx=dx,
        dy=dy,
        fire=keys[pygame.K_z] or keys[pygame.K_SPACE],
        bomb=keys[pygame.K_x] or keys[pygame.K_LCTRL],
    )


class Player:
    SPEED = 4.2
    FIRE_INTERVAL = 7
    BOMB_INTERVAL = 26
    HIT_RADIUS = 7
    MIN_Y = 220

    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT - 80
        self.fire_cooldown = 0
        self.bomb_cooldown = 0
        self.invulnerable = 150
        self.respawn_timer = 0

    @property
    def active(self):
        return self.respawn_timer == 0

    @property
    def reticle(self):
        return self.x, self.y - RETICLE_DISTANCE

    def respawn(self):
        self.x = WIDTH / 2
        self.y = HEIGHT - 80
        self.invulnerable = 150

    def update(self, game, controls):
        self.fire_cooldown = max(0, self.fire_cooldown - 1)
        self.bomb_cooldown = max(0, self.bomb_cooldown - 1)
        self.invulnerable = max(0, self.invulnerable - 1)

        if self.respawn_timer > 0:
            self.respawn_timer -= 1
            if self.respawn_timer == 0:
                self.respawn()
            return

        dx, dy = controls.dx, controls.dy
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        self.x = max(18, min(WIDTH - 18, self.x + dx * self.SPEED))
        self.y = max(self.MIN_Y, min(HEIGHT - 28, self.y + dy * self.SPEED))

        if controls.fire and self.fire_cooldown == 0:
            self.fire_cooldown = self.FIRE_INTERVAL
            game.shots.append(Shot(self.x - 8, self.y - 16))
            game.shots.append(Shot(self.x + 8, self.y - 16))
            game.sounds.play("shot")

        if controls.bomb and self.bomb_cooldown == 0:
            self.bomb_cooldown = self.BOMB_INTERVAL
            target_x, target_y = self.reticle
            game.bombs.append(Bomb(self.x, self.y, target_x, target_y))
            game.sounds.play("bomb")

    def draw(self, screen, frame):
        if not self.active:
            return
        if self.invulnerable and frame // 4 % 2:
            return
        x, y = self.x, self.y

        shadow = pygame.Surface((60, 60), pygame.SRCALPHA)
        points = [(30, 10), (46, 42), (30, 36), (14, 42)]
        pygame.draw.polygon(shadow, (0, 0, 0, 80), points)
        screen.blit(shadow, (x - 30 + 14, y - 30 + 20))

        pygame.draw.polygon(screen, STEEL, [(x, y - 8), (x + 22, y + 15), (x + 8, y + 12), (x - 8, y + 12), (x - 22, y + 15)])
        pygame.draw.polygon(screen, SILVER, [(x, y - 20), (x + 8, y + 2), (x + 6, y + 15), (x - 6, y + 15), (x - 8, y + 2)])
        pygame.draw.polygon(screen, CYAN, [(x, y - 11), (x + 4, y - 1), (x - 4, y - 1)])
        pygame.draw.circle(screen, ORANGE, (round(x - 3), round(y + 16)), 2 + frame // 3 % 2)
        pygame.draw.circle(screen, ORANGE, (round(x + 3), round(y + 16)), 2 + frame // 3 % 2)


class Shot:
    SPEED = 11

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alive = True

    def update(self):
        self.y -= self.SPEED
        if self.y < -20:
            self.alive = False

    def draw(self, screen):
        pygame.draw.line(screen, YELLOW, (self.x, self.y), (self.x, self.y + 10), 3)
        pygame.draw.line(screen, WHITE, (self.x, self.y), (self.x, self.y + 5), 1)


class Bomb:
    """조준점으로 날아가 지상에 떨어지는 블래스터 폭탄."""

    def __init__(self, x, y, target_x, target_y):
        self.start_x = x
        self.start_y = y
        self.target_x = target_x
        self.target_y = target_y      # 지형과 함께 스크롤되는 착탄 지점
        self.air_target_y = target_y  # 스크롤과 무관하게 떠 있는 보스용 착탄 지점
        self.frame = 0
        self.landed = False

    def update(self):
        self.target_y += SCROLL_SPEED
        self.frame += 1
        if self.frame >= BOMB_FLIGHT_FRAMES:
            self.landed = True

    def draw(self, screen):
        t = self.frame / BOMB_FLIGHT_FRAMES
        x = self.start_x + (self.target_x - self.start_x) * t
        y = self.start_y + (self.target_y - self.start_y) * t
        radius = max(2, round(6 * (1 - t) + 2))
        pygame.draw.circle(screen, DARK_STEEL, (round(x), round(y)), radius + 1)
        pygame.draw.circle(screen, ORANGE, (round(x), round(y)), radius)


class EnemyBullet:
    """적이 쏘는 스파리오 탄."""

    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if not (-20 < self.x < WIDTH + 20 and -20 < self.y < HEIGHT + 20):
            self.alive = False

    def draw(self, screen, frame):
        center = (round(self.x), round(self.y))
        pygame.draw.circle(screen, BLACK, center, 6)
        pygame.draw.circle(screen, WHITE if frame // 4 % 2 else PINK, center, 4)


class AirEnemy:
    radius = 14
    score = 30
    destructible = True

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.age = 0
        self.alive = True

    def update(self, game):
        self.age += 1
        self.behave(game)
        self.x += self.vx
        self.y += self.vy
        if self.y > HEIGHT + 60 or self.x < -70 or self.x > WIDTH + 70:
            self.alive = False
        elif self.y < -70 and self.vy < 0:
            self.alive = False

    def behave(self, game):
        pass

    def draw(self, screen, frame):
        pass


class Toroid(AirEnemy):
    """내려오다가 플레이어 앞에서 방향을 틀어 달아나는 링."""

    radius = 13
    score = 30

    def __init__(self, x, y):
        super().__init__(x, y)
        self.vy = 3.2
        self.turn_dir = 0

    def behave(self, game):
        if not self.turn_dir and self.y > game.player.y - 240:
            self.turn_dir = -1 if game.player.x > self.x else 1
            if random.random() < 0.15 + game.rank * 0.06:
                game.fire_at_player(self.x, self.y)
        if self.turn_dir:
            self.vx += self.turn_dir * 0.17
            self.vy -= 0.13

    def draw(self, screen, frame):
        width = max(5, abs(round(26 * math.cos(self.age / 7))))
        rect = pygame.Rect(0, 0, width, 26)
        rect.center = (round(self.x), round(self.y))
        pygame.draw.ellipse(screen, DARK_STEEL, rect.inflate(4, 4))
        pygame.draw.ellipse(screen, SILVER, rect, 5)


class Torkan(AirEnemy):
    """내려와 잠시 멈춰서 조준 사격한 뒤 되돌아간다."""

    radius = 15
    score = 50

    def __init__(self, x, y, stop_y):
        super().__init__(x, y)
        self.vy = 3.4
        self.stop_y = stop_y
        self.hold = 0

    def behave(self, game):
        if self.hold == 0 and self.vy > 0 and self.y >= self.stop_y:
            self.vy = 0
            self.hold = 45
        elif self.hold > 0:
            self.hold -= 1
            if self.hold == 22:
                game.fire_at_player(self.x, self.y)
            if self.hold == 0:
                self.vy = -0.5
        elif self.vy < 0:
            self.vy -= 0.12

    def draw(self, screen, frame):
        x, y = self.x, self.y
        pygame.draw.polygon(screen, DARK_STEEL, [(x, y - 18), (x + 18, y), (x, y + 18), (x - 18, y)])
        pygame.draw.polygon(screen, STEEL, [(x, y - 12), (x + 12, y), (x, y + 12), (x - 12, y)])
        pygame.draw.circle(screen, RED, (round(x), round(y)), 4)


class Zoshi(AirEnemy):
    """플레이어를 쫓아다니며 총을 쏘는 십자 비행체."""

    radius = 13
    score = 70
    CHASE_FRAMES = 300

    def __init__(self, x, y, speed):
        super().__init__(x, y)
        self.speed = speed
        self.vy = speed
        self.fire_timer = random.randint(30, 90)

    def behave(self, game):
        if self.age < self.CHASE_FRAMES and game.player.active:
            want_x, want_y = aimed_velocity(self.x, self.y, game.player.x, game.player.y, self.speed)
            self.vx += (want_x - self.vx) * 0.04
            self.vy += (want_y - self.vy) * 0.04
        elif self.age >= self.CHASE_FRAMES:
            self.vy -= 0.1
        self.fire_timer -= 1
        if self.fire_timer <= 0:
            self.fire_timer = random.randint(70, 130)
            game.fire_at_player(self.x, self.y)

    def draw(self, screen, frame):
        angle = self.age / 8
        center = (round(self.x), round(self.y))
        for i in range(4):
            a = angle + i * math.pi / 2
            tip = (self.x + math.cos(a) * 17, self.y + math.sin(a) * 17)
            pygame.draw.line(screen, DARK_STEEL, center, tip, 7)
            pygame.draw.line(screen, ORANGE, center, tip, 3)
        pygame.draw.circle(screen, WHITE, center, 5)


class Jara(AirEnemy):
    """좌우로 크게 흔들리며 빠르게 내려온다."""

    radius = 13
    score = 150

    def __init__(self, x, y):
        super().__init__(x, y)
        self.base_x = x
        self.vy = 2.8

    def behave(self, game):
        target = self.base_x + math.sin(self.age / 18) * 70
        self.vx = target - self.x

    def draw(self, screen, frame):
        x, y = self.x, self.y
        tilt = max(-10, min(10, self.vx * 3))
        pygame.draw.polygon(screen, DARK_STEEL, [(x, y + 18), (x + 18 + tilt, y - 14), (x, y - 6), (x - 18 + tilt, y - 14)])
        pygame.draw.polygon(screen, (120, 210, 130), [(x, y + 12), (x + 12 + tilt, y - 10), (x, y - 4), (x - 12 + tilt, y - 10)])


class Bacura(AirEnemy):
    """파괴할 수 없는 회전 금속판. 자퍼를 막아내므로 피해야 한다."""

    radius = 15
    score = 0
    destructible = False

    def __init__(self, x, y):
        super().__init__(x, y)
        self.vy = 1.8

    def draw(self, screen, frame):
        height = max(5, abs(round(32 * math.cos(self.age / 12))))
        rect = pygame.Rect(0, 0, 34, height)
        rect.center = (round(self.x), round(self.y))
        pygame.draw.rect(screen, DARK_STEEL, rect.inflate(4, 4), border_radius=3)
        pygame.draw.rect(screen, SILVER, rect, border_radius=3)


class GroundTarget:
    radius = 16
    score = 100
    hidden = False

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alive = True

    def update(self, game):
        self.y += SCROLL_SPEED
        if self.y > HEIGHT + 40:
            self.alive = False
        self.behave(game)

    def behave(self, game):
        pass

    def hit(self, game):
        self.alive = False
        game.add_score(self.score)
        game.explode(self.x, self.y, 26)
        game.sounds.play("hit")

    def on_player_touch(self, game):
        pass

    def draw(self, screen, frame):
        pass


class Barra(GroundTarget):
    """움직이지 않는 피라미드."""

    score = 110

    def draw(self, screen, frame):
        x, y = self.x, self.y
        pygame.draw.polygon(screen, STEEL, [(x - 16, y + 16), (x + 16, y + 16), (x, y)])
        pygame.draw.polygon(screen, SILVER, [(x - 16, y - 16), (x - 16, y + 16), (x, y)])
        pygame.draw.polygon(screen, DARK_STEEL, [(x + 16, y - 16), (x + 16, y + 16), (x, y)])
        pygame.draw.polygon(screen, (150, 158, 172), [(x - 16, y - 16), (x + 16, y - 16), (x, y)])


class Zolbak(GroundTarget):
    """레이더 기지. 파괴하면 적의 공격이 약해진다."""

    score = 200

    def hit(self, game):
        super().hit(game)
        game.rank = max(0.0, game.rank - 0.4)

    def draw(self, screen, frame):
        center = (round(self.x), round(self.y))
        pygame.draw.circle(screen, DARK_STEEL, center, 16)
        pygame.draw.circle(screen, (150, 90, 170), center, 13)
        angle = frame / 18
        tip = (self.x + math.cos(angle) * 12, self.y + math.sin(angle) * 12)
        pygame.draw.line(screen, WHITE, center, tip, 2)


class Logram(GroundTarget):
    """스파리오를 쏘는 돔 포대."""

    score = 300

    def __init__(self, x, y):
        super().__init__(x, y)
        self.fire_timer = random.randint(40, 110)

    def behave(self, game):
        if not 20 < self.y < game.player.y - 40:
            return
        self.fire_timer -= 1
        if self.fire_timer <= 0:
            self.fire_timer = max(70, 140 - int(game.rank * 12))
            game.fire_at_player(self.x, self.y)

    def draw(self, screen, frame):
        center = (round(self.x), round(self.y))
        pygame.draw.circle(screen, DARK_STEEL, center, 16)
        pygame.draw.circle(screen, (178, 150, 92), center, 12)
        pygame.draw.circle(screen, RED if self.fire_timer < 20 else DARK_STEEL, center, 5)


class Domogram(GroundTarget):
    """지상을 가로질러 달리며 사격하는 전차."""

    score = 800

    def __init__(self, x, y, direction):
        super().__init__(x, y)
        self.direction = direction
        self.fire_timer = random.randint(50, 120)

    def behave(self, game):
        self.x += self.direction * 1.4
        if self.x < 20 or self.x > WIDTH - 20:
            self.direction *= -1
        if not 20 < self.y < game.player.y - 40:
            return
        self.fire_timer -= 1
        if self.fire_timer <= 0:
            self.fire_timer = random.randint(90, 150)
            game.fire_at_player(self.x, self.y)

    def draw(self, screen, frame):
        x, y = round(self.x), round(self.y)
        pygame.draw.rect(screen, DARK_STEEL, (x - 18, y - 12, 36, 24), border_radius=4)
        pygame.draw.rect(screen, (112, 140, 90), (x - 13, y - 8, 26, 16), border_radius=3)
        pygame.draw.circle(screen, (70, 96, 58), (x, y), 6)
        pygame.draw.line(screen, DARK_STEEL, (x, y), (x + self.direction * 14, y), 3)


class SolTower(GroundTarget):
    """숨겨진 탑. 첫 폭격에 모습을 드러내고 두 번째 폭격에 파괴된다."""

    score = 2000
    hidden = True

    def hit(self, game):
        if self.hidden:
            self.hidden = False
            game.explode(self.x, self.y, 14)
            game.sounds.play("hit")
        else:
            super().hit(game)
            game.add_popup(self.x, self.y, str(self.score))

    def draw(self, screen, frame):
        if self.hidden:
            return
        x, y = self.x, self.y
        pygame.draw.polygon(screen, DARK_STEEL, [(x - 18, y + 18), (x + 18, y + 18), (x + 9, y - 22), (x - 9, y - 22)])
        pygame.draw.polygon(screen, YELLOW, [(x - 12, y + 12), (x + 12, y + 12), (x + 6, y - 16), (x - 6, y - 16)])


class SpecialFlag(GroundTarget):
    """숨겨진 깃발. 폭격으로 찾아낸 뒤 닿으면 1UP."""

    score = 0
    hidden = True

    def hit(self, game):
        if self.hidden:
            self.hidden = False
            game.sounds.play("bonus")

    def on_player_touch(self, game):
        if self.hidden:
            return
        self.alive = False
        game.lives += 1
        game.add_popup(self.x, self.y, "1UP")
        game.sounds.play("bonus")

    def draw(self, screen, frame):
        if self.hidden:
            return
        x, y = round(self.x), round(self.y)
        pygame.draw.line(screen, WHITE, (x - 6, y + 14), (x - 6, y - 14), 3)
        wave = frame // 8 % 2 * 3
        pygame.draw.polygon(screen, RED, [(x - 5, y - 14), (x + 14, y - 8 + wave), (x - 5, y - 1)])


class AndorGenesis:
    """에어리어 끝에 나타나는 모선. 폭탄으로 코어를 부수면 격파된다."""

    TURRET_OFFSETS = [(-78, -34), (78, -34), (-78, 34), (78, 34)]
    TURRET_RADIUS = 20
    CORE_RADIUS = 26
    HOVER_Y = 170

    def __init__(self, area):
        self.x = WIDTH / 2
        self.y = -140
        self.timer = 0
        self.leaving = False
        self.core_hp = 5 + area
        self.core_flash = 0
        self.turrets = [
            {"offset": offset, "hp": 2, "cooldown": 60 + i * 25, "flash": 0}
            for i, offset in enumerate(self.TURRET_OFFSETS)
        ]
        self.ring_timer = 180

    def turret_position(self, turret):
        return self.x + turret["offset"][0], self.y + turret["offset"][1]

    def update(self, game):
        self.core_flash = max(0, self.core_flash - 1)
        if self.leaving:
            self.y += 2.5
            return
        if self.y < self.HOVER_Y:
            self.y += 1.5
            return

        self.timer += 1
        self.x = WIDTH / 2 + math.sin(self.timer / 70) * 90
        if self.timer >= BOSS_TIME_LIMIT:
            self.leaving = True
            return

        for turret in self.turrets:
            turret["flash"] = max(0, turret["flash"] - 1)
            if turret["hp"] <= 0:
                continue
            turret["cooldown"] -= 1
            if turret["cooldown"] <= 0:
                turret["cooldown"] = max(55, 110 - int(game.rank * 8))
                game.fire_at_player(*self.turret_position(turret))

        self.ring_timer -= 1
        if self.ring_timer <= 0:
            self.ring_timer = 210
            count = 10
            speed = game.bullet_speed() * 0.8
            for i in range(count):
                angle = i / count * math.tau
                game.enemy_bullets.append(
                    EnemyBullet(self.x, self.y, math.cos(angle) * speed, math.sin(angle) * speed)
                )

    @property
    def off_screen(self):
        return self.leaving and self.y > HEIGHT + 150

    def contains_target(self, x, y):
        if self.leaving:
            return False
        if distance(x, y, self.x, self.y) <= self.CORE_RADIUS:
            return True
        return any(
            turret["hp"] > 0
            and distance(x, y, *self.turret_position(turret)) <= self.TURRET_RADIUS
            for turret in self.turrets
        )

    def take_bomb(self, game, x, y):
        """폭탄이 착탄했을 때 처리한다. 코어가 파괴되면 True를 돌려준다."""
        if self.leaving:
            return False
        for turret in self.turrets:
            if turret["hp"] <= 0:
                continue
            turret_x, turret_y = self.turret_position(turret)
            if distance(x, y, turret_x, turret_y) <= self.TURRET_RADIUS + BOMB_RADIUS * 0.5:
                turret["hp"] -= 1
                turret["flash"] = 8
                if turret["hp"] == 0:
                    game.add_score(1000)
                    game.explode(turret_x, turret_y, 30)
                game.sounds.play("hit")
        if distance(x, y, self.x, self.y) <= self.CORE_RADIUS + BOMB_RADIUS * 0.5:
            self.core_hp -= 1
            self.core_flash = 8
            game.sounds.play("hit")
            return self.core_hp <= 0
        return False

    def draw(self, screen, frame):
        x, y = self.x, self.y
        hull = []
        for i in range(8):
            angle = math.pi / 8 + i * math.pi / 4
            hull.append((x + math.cos(angle) * 125, y + math.sin(angle) * 78))
        pygame.draw.polygon(screen, DARK_STEEL, hull)
        inner = [(x + (px - x) * 0.88, y + (py - y) * 0.86) for px, py in hull]
        pygame.draw.polygon(screen, STEEL, inner)
        pygame.draw.polygon(screen, DARK_STEEL, inner, 2)
        pygame.draw.line(screen, DARK_STEEL, (x - 100, y), (x + 100, y), 3)
        pygame.draw.line(screen, DARK_STEEL, (x, y - 62), (x, y + 62), 3)

        for turret in self.turrets:
            tx, ty = self.turret_position(turret)
            center = (round(tx), round(ty))
            if turret["hp"] <= 0:
                pygame.draw.circle(screen, (40, 36, 36), center, self.TURRET_RADIUS - 4)
                continue
            color = WHITE if turret["flash"] else ORANGE
            pygame.draw.circle(screen, BLACK, center, self.TURRET_RADIUS)
            pygame.draw.circle(screen, color, center, self.TURRET_RADIUS - 5)
            pygame.draw.circle(screen, DARK_STEEL, center, 5)

        center = (round(x), round(y))
        core_color = WHITE if self.core_flash else (RED if frame // 10 % 2 else (170, 40, 60))
        pygame.draw.circle(screen, BLACK, center, self.CORE_RADIUS)
        pygame.draw.circle(screen, core_color, center, self.CORE_RADIUS - 6)
        pygame.draw.circle(screen, YELLOW, center, 6)


class Explosion:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size
        self.age = 0
        self.duration = 22
        self.sparks = [
            (random.uniform(0, math.tau), random.uniform(0.5, 1.2))
            for _ in range(10)
        ]

    @property
    def alive(self):
        return self.age < self.duration

    def update(self):
        self.age += 1
        self.y += SCROLL_SPEED * 0.5

    def draw(self, screen):
        t = self.age / self.duration
        radius = max(1, round(self.size * t))
        center = (round(self.x), round(self.y))
        color = lerp_color(YELLOW, RED, t)
        pygame.draw.circle(screen, color, center, radius, max(1, round(self.size * 0.4 * (1 - t))))
        for angle, reach in self.sparks:
            distance_out = self.size * reach * t * 1.3
            spark = (
                round(self.x + math.cos(angle) * distance_out),
                round(self.y + math.sin(angle) * distance_out),
            )
            pygame.draw.circle(screen, lerp_color(WHITE, ORANGE, t), spark, 2)


class Popup:
    def __init__(self, x, y, text):
        self.x = x
        self.y = y
        self.text = text
        self.age = 0

    @property
    def alive(self):
        return self.age < 70

    def update(self):
        self.age += 1
        self.y -= 0.5


class Game:
    TITLE = "title"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"

    def __init__(self, screen):
        self.screen = screen
        self.sounds = SoundBank()
        self.terrain = Terrain()
        self.font_small = pygame.font.SysFont("consolas,menlo,dejavusansmono,arial", 16, bold=True)
        self.font_medium = pygame.font.SysFont("consolas,menlo,dejavusansmono,arial", 22, bold=True)
        self.font_large = pygame.font.SysFont("consolas,menlo,dejavusansmono,arial", 54, bold=True)
        self.high_score = 0
        self.state = self.TITLE
        self.scroll = 0.0
        self.frame = 0
        self.reset_run()

    def reset_run(self):
        self.player = Player()
        self.shots = []
        self.bombs = []
        self.enemy_bullets = []
        self.air = []
        self.ground = []
        self.effects = []
        self.popups = []
        self.boss = None
        self.score = 0
        self.lives = START_LIVES
        self.next_extend = FIRST_EXTEND
        self.area = 1
        self.rank = 0.0
        self.game_over_timer = 0
        self.begin_area()

    def begin_area(self):
        self.area_progress = 0.0
        self.air_timer = 120
        self.ground_timer = 80.0
        self.flag_at = random.randint(1000, AREA_LENGTH - 500)
        self.flag_spawned = False
        self.banner_timer = 150

    def start(self):
        self.reset_run()
        self.state = self.PLAYING

    def bullet_speed(self):
        return 2.8 + min(self.rank, 6) * 0.28

    def fire_at_player(self, x, y):
        if not self.player.active:
            return
        vx, vy = aimed_velocity(x, y, self.player.x, self.player.y, self.bullet_speed())
        self.enemy_bullets.append(EnemyBullet(x, y, vx, vy))

    def add_score(self, points):
        self.score += points
        self.high_score = max(self.high_score, self.score)
        while self.score >= self.next_extend:
            self.lives += 1
            self.next_extend += NEXT_EXTEND
            self.add_popup(self.player.x, self.player.y - 30, "1UP")
            self.sounds.play("bonus")

    def add_popup(self, x, y, text):
        self.popups.append(Popup(x, y, text))

    def explode(self, x, y, size):
        self.effects.append(Explosion(x, y, size))

    def world_at(self, screen_y):
        return self.scroll + HEIGHT - screen_y

    def step(self, controls):
        """게임 진행을 한 프레임 전진시킨다."""
        self.frame += 1
        self.scroll += SCROLL_SPEED
        self.banner_timer = max(0, self.banner_timer - 1)

        self.player.update(self, controls)
        self.update_spawns()

        for shot in self.shots:
            shot.update()
        for bomb in self.bombs:
            bomb.update()
            if bomb.landed:
                self.resolve_bomb(bomb)
        for bullet in self.enemy_bullets:
            bullet.update()
        for enemy in self.air:
            enemy.update(self)
        for target in self.ground:
            target.update(self)
        for effect in self.effects:
            effect.update()
        for popup in self.popups:
            popup.update()

        if self.boss:
            self.boss.update(self)
            if self.boss and self.boss.off_screen:
                self.boss = None
                self.next_area()

        self.check_collisions()
        self.cleanup()

    def update_spawns(self):
        self.area_progress += SCROLL_SPEED
        if self.area_progress >= AREA_LENGTH and not self.boss:
            self.boss = AndorGenesis(self.area)
            self.add_popup(WIDTH / 2, 90, "WARNING")
            return

        self.air_timer -= 1
        if self.air_timer <= 0:
            self.spawn_air_wave()
            base = 150 if self.boss else 105
            self.air_timer = max(40, base - int(self.rank * 10)) + random.randint(0, 30)

        if self.boss:
            return

        self.ground_timer -= SCROLL_SPEED
        if self.ground_timer <= 0:
            self.ground_timer = random.uniform(70, 130)
            self.spawn_ground_target()

        if not self.flag_spawned and self.area_progress >= self.flag_at:
            self.flag_spawned = True
            self.ground.append(SpecialFlag(self.ground_x(), -30))

    def spawn_air_wave(self):
        kinds = ["toroid", "toroid", "torkan"]
        if self.area >= 1:
            kinds += ["jara"]
        if self.area >= 2 or self.rank > 1:
            kinds += ["zoshi", "bacura"]
        if self.area >= 3:
            kinds += ["zoshi", "torkan"]
        kind = random.choice(kinds)

        if kind == "toroid":
            x = random.randint(70, WIDTH - 70)
            for i in range(random.randint(4, 6)):
                self.air.append(Toroid(x, -30 - i * 42))
        elif kind == "torkan":
            for _ in range(random.randint(2, 3)):
                self.air.append(Torkan(random.randint(40, WIDTH - 40), -30, random.randint(70, 240)))
        elif kind == "jara":
            x = random.randint(110, WIDTH - 110)
            for i in range(3):
                self.air.append(Jara(x, -30 - i * 55))
        elif kind == "zoshi":
            for i in range(1 + min(2, self.area // 2)):
                speed = 2.6 + min(self.rank, 6) * 0.15
                self.air.append(Zoshi(random.randint(40, WIDTH - 40), -30 - i * 40, speed))
        elif kind == "bacura":
            for i in range(random.randint(2, 3)):
                self.air.append(Bacura(random.randint(40, WIDTH - 40), -30 - i * 90))

    def ground_x(self):
        for _ in range(8):
            x = random.randint(30, WIDTH - 30)
            world = self.world_at(-30)
            if abs(x - river_x(world)) > river_half_width(world) + 22:
                return x
        return random.randint(30, WIDTH - 30)

    def spawn_ground_target(self):
        x = self.ground_x()
        roll = random.random()
        if roll < 0.32:
            pattern = random.choice(([0], [-34, 34], [-40, 0, 40]))
            for offset in pattern:
                self.ground.append(Barra(max(24, min(WIDTH - 24, x + offset)), -30))
        elif roll < 0.48:
            self.ground.append(Zolbak(x, -30))
        elif roll < 0.76:
            self.ground.append(Logram(x, -30))
        elif roll < 0.92:
            self.ground.append(Domogram(x, -30, random.choice((-1, 1))))
        else:
            self.ground.append(SolTower(x, -30))

    def resolve_bomb(self, bomb):
        hit_boss = False
        if self.boss and self.boss.take_bomb(self, bomb.target_x, bomb.air_target_y):
            hit_boss = True

        self.explode(bomb.target_x, bomb.target_y, BOMB_RADIUS)
        for target in self.ground:
            if not target.alive:
                continue
            reach = BOMB_RADIUS + target.radius * 0.5
            if distance(bomb.target_x, bomb.target_y, target.x, target.y) <= reach:
                target.hit(self)

        if hit_boss:
            self.destroy_boss()

    def destroy_boss(self):
        boss = self.boss
        self.boss = None
        self.enemy_bullets.clear()
        for _ in range(12):
            self.explode(
                boss.x + random.uniform(-110, 110),
                boss.y + random.uniform(-60, 60),
                random.randint(24, 50),
            )
        self.add_score(5000 * self.area)
        self.add_popup(boss.x, boss.y, str(5000 * self.area))
        self.sounds.play("death")
        self.next_area()

    def next_area(self):
        self.area += 1
        self.rank += 1
        self.begin_area()

    def lock_on(self):
        """조준점 아래에 폭격할 수 있는 대상(숨겨진 것 포함)이 있는지 확인한다."""
        x, y = self.player.reticle
        if self.boss and self.boss.contains_target(x, y):
            return True
        return any(
            distance(x, y, target.x, target.y) <= BOMB_RADIUS
            for target in self.ground
        )

    def check_collisions(self):
        for shot in self.shots:
            if not shot.alive:
                continue
            for enemy in self.air:
                if enemy.alive and distance(shot.x, shot.y, enemy.x, enemy.y) <= enemy.radius + 3:
                    shot.alive = False
                    if enemy.destructible:
                        enemy.alive = False
                        self.add_score(enemy.score)
                        self.rank = min(8.0, self.rank + 0.012)
                        self.explode(enemy.x, enemy.y, 22)
                        self.sounds.play("boom")
                    break

        player = self.player
        if not player.active:
            return

        for target in self.ground:
            if target.alive and distance(player.x, player.y, target.x, target.y) <= 22:
                target.on_player_touch(self)

        if player.invulnerable:
            return

        for bullet in self.enemy_bullets:
            if bullet.alive and distance(player.x, player.y, bullet.x, bullet.y) <= player.HIT_RADIUS + 3:
                bullet.alive = False
                self.kill_player()
                return
        for enemy in self.air:
            if enemy.alive and distance(player.x, player.y, enemy.x, enemy.y) <= player.HIT_RADIUS + enemy.radius:
                if enemy.destructible:
                    enemy.alive = False
                    self.explode(enemy.x, enemy.y, 22)
                self.kill_player()
                return

    def kill_player(self):
        player = self.player
        self.explode(player.x, player.y, 46)
        self.explode(player.x - 12, player.y + 8, 28)
        self.sounds.play("death")
        self.enemy_bullets.clear()
        self.lives -= 1
        self.rank = max(0.0, self.rank - 1)
        player.respawn_timer = 90
        if self.lives <= 0:
            self.state = self.GAME_OVER
            self.game_over_timer = 0

    def cleanup(self):
        self.shots = [s for s in self.shots if s.alive]
        self.bombs = [b for b in self.bombs if not b.landed]
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]
        self.air = [e for e in self.air if e.alive]
        self.ground = [t for t in self.ground if t.alive]
        self.effects = [e for e in self.effects if e.alive]
        self.popups = [p for p in self.popups if p.alive]

    def update_idle(self):
        """타이틀과 게임 오버 화면에서도 배경은 계속 움직인다."""
        self.frame += 1
        self.scroll += SCROLL_SPEED
        if self.state == self.GAME_OVER:
            self.game_over_timer += 1
            for effect in self.effects:
                effect.update()
            self.effects = [e for e in self.effects if e.alive]

    def draw_text(self, font, text, center=None, topleft=None, topright=None, color=WHITE):
        shadow = font.render(text, True, TEXT_SHADOW)
        image = font.render(text, True, color)
        rect = image.get_rect()
        if center:
            rect.center = center
        elif topleft:
            rect.topleft = topleft
        elif topright:
            rect.topright = topright
        self.screen.blit(shadow, rect.move(2, 2))
        self.screen.blit(image, rect)

    def draw_reticle(self):
        if not self.player.active:
            return
        x, y = self.player.reticle
        locked = self.lock_on()
        if locked:
            color = RED if self.frame // 4 % 2 else YELLOW
        else:
            color = WHITE
        x, y = round(x), round(y)
        size = 13
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            corner = (x + dx * size, y + dy * size)
            pygame.draw.line(self.screen, color, corner, (corner[0] - dx * 7, corner[1]), 2)
            pygame.draw.line(self.screen, color, corner, (corner[0], corner[1] - dy * 7), 2)
        pygame.draw.circle(self.screen, color, (x, y), 2)

    def draw_hud(self):
        self.draw_text(self.font_small, f"SCORE {self.score:07d}", topleft=(10, 8))
        self.draw_text(self.font_small, f"HI {self.high_score:07d}", topright=(WIDTH - 10, 8), color=YELLOW)
        self.draw_text(self.font_small, f"AREA {self.area}", center=(WIDTH // 2, 18), color=CYAN)
        for i in range(max(0, self.lives - 1)):
            x = 20 + i * 22
            y = HEIGHT - 20
            pygame.draw.polygon(self.screen, SILVER, [(x, y - 10), (x + 9, y + 8), (x, y + 4), (x - 9, y + 8)])

    def draw_world(self):
        self.terrain.draw(self.screen, self.scroll)
        for target in self.ground:
            target.draw(self.screen, self.frame)
        if self.boss:
            self.boss.draw(self.screen, self.frame)
        for bomb in self.bombs:
            bomb.draw(self.screen)
        for enemy in self.air:
            enemy.draw(self.screen, self.frame)
        for shot in self.shots:
            shot.draw(self.screen)
        for bullet in self.enemy_bullets:
            bullet.draw(self.screen, self.frame)
        self.player.draw(self.screen, self.frame)
        for effect in self.effects:
            effect.draw(self.screen)
        for popup in self.popups:
            color = RED if popup.text == "WARNING" else YELLOW
            self.draw_text(self.font_medium, popup.text, center=(popup.x, popup.y), color=color)

    def draw_title(self):
        self.terrain.draw(self.screen, self.scroll)
        self.draw_text(self.font_large, "XEVIOUS", center=(WIDTH // 2, 170), color=CYAN)
        self.draw_text(self.font_small, "VERTICAL SCROLLING SHOOTER", center=(WIDTH // 2, 215))
        lines = [
            "ARROWS / WASD : MOVE",
            "Z / SPACE : ZAPPER (AIR)",
            "X / L-CTRL : BLASTER (GROUND)",
            "P : PAUSE     ESC : QUIT",
            "",
            "RETICLE FLASHES OVER GROUND TARGETS",
            "BOMB HIDDEN TARGETS TO REVEAL THEM",
        ]
        for i, line in enumerate(lines):
            self.draw_text(self.font_small, line, center=(WIDTH // 2, 290 + i * 26))
        if self.frame // 30 % 2:
            self.draw_text(self.font_medium, "PRESS ENTER", center=(WIDTH // 2, 520), color=YELLOW)
        if self.high_score:
            self.draw_text(self.font_small, f"HI {self.high_score:07d}", center=(WIDTH // 2, 565), color=YELLOW)

    def draw(self):
        if self.state == self.TITLE:
            self.draw_title()
            return

        self.draw_world()
        if self.state != self.GAME_OVER:
            self.draw_reticle()
        self.draw_hud()

        if self.banner_timer and self.state == self.PLAYING:
            self.draw_text(self.font_medium, f"AREA {self.area}", center=(WIDTH // 2, HEIGHT // 2 - 60), color=CYAN)
        if self.boss and not self.boss.leaving and self.state == self.PLAYING:
            self.draw_text(self.font_small, "BOMB THE CORE!", center=(WIDTH // 2, 42), color=RED)
        if self.state == self.PAUSED:
            self.draw_text(self.font_large, "PAUSED", center=(WIDTH // 2, HEIGHT // 2))
        elif self.state == self.GAME_OVER:
            self.draw_text(self.font_large, "GAME OVER", center=(WIDTH // 2, HEIGHT // 2 - 30), color=RED)
            self.draw_text(self.font_medium, f"SCORE {self.score}", center=(WIDTH // 2, HEIGHT // 2 + 25))
            if self.game_over_timer > 60:
                self.draw_text(self.font_small, "PRESS ENTER", center=(WIDTH // 2, HEIGHT // 2 + 65), color=YELLOW)

    def handle_key(self, key):
        """키 입력을 처리한다. 게임을 끝내야 하면 False를 돌려준다."""
        if key == pygame.K_ESCAPE:
            return False
        if self.state == self.TITLE:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.start()
        elif self.state == self.PLAYING:
            if key == pygame.K_p:
                self.state = self.PAUSED
        elif self.state == self.PAUSED:
            if key == pygame.K_p:
                self.state = self.PLAYING
        elif self.state == self.GAME_OVER:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.game_over_timer > 60:
                self.reset_run()
                self.state = self.TITLE
        return True


def create_window():
    pygame.display.set_caption("Xevious Style Shooter")
    try:
        return pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
    except pygame.error:
        return pygame.display.set_mode((WIDTH, HEIGHT))


def main():
    pygame.mixer.pre_init(22050, -16, 1, 256)
    pygame.init()
    screen = create_window()
    clock = pygame.time.Clock()
    game = Game(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and not game.handle_key(event.key):
                running = False
            elif event.type == pygame.WINDOWFOCUSLOST and game.state == Game.PLAYING:
                game.state = Game.PAUSED

        if game.state == Game.PLAYING:
            game.step(read_controls())
        elif game.state != Game.PAUSED:
            game.update_idle()

        game.draw()
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
