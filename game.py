"""Правила и физика игры. Этот модуль не зависит от графической библиотеки."""

from dataclasses import dataclass
from enum import Enum, auto
import math
import random


class State(Enum):
    """Четыре состояния игры определяют доступные действия и обновление физики."""

    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    OVER = auto()


@dataclass(frozen=True)
class Box:
    """Прямоугольник в координатах поля: начало находится в левом верхнем углу."""

    x: float
    y: float
    width: float
    height: float


@dataclass
class Ball:
    """Положение центра, скорость в пикселях в секунду и радиус шарика."""

    x: float
    y: float
    vx: float
    vy: float
    radius: float = 9.0


class Game:
    """Хранит состояние партии, начисляет кристаллы и рассчитывает столкновения."""

    HIT_REWARD = 10
    BONUS_EVERY = 5
    BONUS_REWARD = 20
    FIRST_PRICE = 30
    PRICE_STEP = 20
    PADDLE_SPEED = 560.0
    MAX_BALL_SPEED = 650.0
    STONE_HEIGHT = 20.0

    def __init__(self, width: int, height: int, rng: random.Random | None = None):
        """Создаёт поле и генератор случайных чисел; rng удобно подменять в тестах."""
        self.rng = rng if rng is not None else random.Random()
        self.width = width
        self.height = height
        self.state = State.READY
        self.crystals = 0
        self.earned = 0
        self.hits = 0
        self.stone_count = 0
        self.ball: Ball | None = None
        self.events: list[str] = []
        self._set_geometry()

    def _set_geometry(self) -> None:
        """Делит ширину на клетки и создаёт цельную платформу ровно из трёх клеток."""
        self.columns = max(12, round(self.width / 36))
        self.cell = self.width / self.columns
        self.paddle_width = 3 * self.cell
        self.paddle_x = (self.width - self.paddle_width) / 2
        self.paddle_y = self.height - 78
        self.paddle_height = 16.0

    @property
    def paddle(self) -> Box:
        """Возвращает актуальную геометрию платформы для физики и отрисовки."""
        return Box(self.paddle_x, self.paddle_y, self.paddle_width, self.paddle_height)

    @property
    def next_price(self) -> int:
        """Каждый следующий камень дороже предыдущего на PRICE_STEP кристаллов."""
        return self.FIRST_PRICE + self.PRICE_STEP * self.stone_count

    @property
    def max_stones(self) -> int:
        """Оставляет проём шириной не менее трёх клеток, чтобы риск проигрыша сохранялся."""
        return self.columns - 3

    @property
    def stones(self) -> list[Box]:
        """Строит камни попеременно слева и справа, постепенно сужая нижний проём."""
        result = []
        for index in range(self.stone_count):
            column = index // 2 if index % 2 == 0 else self.columns - 1 - index // 2
            result.append(Box(column * self.cell, self.height - self.STONE_HEIGHT,
                              self.cell, self.STONE_HEIGHT))
        return result

    def resize(self, width: int, height: int) -> bool:
        """Меняет геометрию только в режиме подготовки, до начала партии."""
        if self.state != State.READY:
            return False
        self.width, self.height = width, height
        self._set_geometry()
        return True

    def start(self) -> None:
        """Начинает чистую партию: сбрасывает покупки и запускает шарик сверху."""
        self.crystals = self.earned = self.hits = self.stone_count = 0
        self.events.clear()
        self._set_geometry()
        angle = math.radians(self.rng.uniform(-38, 38))
        speed = 310.0
        self.ball = Ball(self.rng.uniform(12, self.width - 12), 12,
                         speed * math.sin(angle), speed * math.cos(angle))
        self.state = State.RUNNING

    def prepare(self) -> None:
        """Возвращает к подготовке; после этого окно снова можно растягивать."""
        self.state = State.READY
        self.ball = None
        self.crystals = self.earned = self.hits = self.stone_count = 0
        self.events.clear()
        self._set_geometry()

    def toggle_pause(self) -> None:
        """Переключает паузу только у текущей, ещё не законченной партии."""
        if self.state == State.RUNNING:
            self.state = State.PAUSED
        elif self.state == State.PAUSED:
            self.state = State.RUNNING

    def buy_stone(self) -> bool:
        """Покупает камень во время игры или паузы, проверяя баланс и размер проёма."""
        if self.state not in (State.RUNNING, State.PAUSED):
            self.events.append("Начните игру клавишей F5")
            return False
        if self.stone_count >= self.max_stones:
            self.events.append("Минимальный проём — 3 клетки")
            return False
        price = self.next_price
        if self.crystals < price:
            self.events.append(f"Не хватает {price - self.crystals} кристаллов")
            return False
        self.crystals -= price
        self.stone_count += 1
        self.events.append(f"Камень куплен: −{price} кристаллов")
        return True

    def update(self, dt: float, direction: int = 0) -> None:
        """Двигает объекты малыми шагами: быстрый шарик не проскочит сквозь платформу."""
        if self.state != State.RUNNING or self.ball is None or dt <= 0:
            return
        # Ограничение защищает от огромного скачка после зависания или перетаскивания окна.
        dt = min(dt, 0.05)
        speed = math.hypot(self.ball.vx, self.ball.vy)
        steps = max(1, math.ceil(max(speed, self.PADDLE_SPEED) * dt / (self.ball.radius / 2)))
        step = dt / steps
        for _ in range(steps):
            self.paddle_x = max(0, min(self.width - self.paddle_width,
                                      self.paddle_x + direction * self.PADDLE_SPEED * step))
            self._move_ball(step)
            if self.state == State.OVER:
                break

    def _move_ball(self, dt: float) -> None:
        """Обрабатывает стенки, верх платформы, купленные камни и выход через низ."""
        ball = self.ball
        assert ball is not None
        previous_bottom = ball.y + ball.radius
        ball.x += ball.vx * dt
        ball.y += ball.vy * dt
        if ball.x < ball.radius:
            ball.x, ball.vx = ball.radius, abs(ball.vx)
        elif ball.x > self.width - ball.radius:
            ball.x, ball.vx = self.width - ball.radius, -abs(ball.vx)
        if ball.y < ball.radius:
            ball.y, ball.vy = ball.radius, abs(ball.vy)

        # Платформа отбивает падающий шарик; точка удара задаёт направление отскока.
        nearest_x = max(self.paddle_x, min(ball.x, self.paddle_x + self.paddle_width))
        horizontal_distance = abs(ball.x - nearest_x)
        if horizontal_distance <= ball.radius:
            contact_y = self.paddle_y - math.sqrt(max(0, ball.radius ** 2 - horizontal_distance ** 2))
            if ball.vy > 0 and previous_bottom <= self.paddle_y + ball.radius and ball.y >= contact_y and ball.y - ball.radius < self.paddle_y:
                ball.y = contact_y - 0.01
                self._paddle_bounce()

        for stone in self.stones:
            self._stone_bounce(stone)
        if ball.y - ball.radius >= self.height:
            self.state = State.OVER
            self.events.append("Шарик покинул поле")

    def _paddle_bounce(self) -> None:
        """Начисляет награду и ускоряет шарик; попадание у края даёт более косой отскок."""
        ball = self.ball
        assert ball is not None
        relative = (ball.x - (self.paddle_x + self.paddle_width / 2)) / (self.paddle_width / 2)
        angle = math.radians(62 * max(-1, min(1, relative)))
        speed = min(self.MAX_BALL_SPEED, math.hypot(ball.vx, ball.vy) + 8)
        ball.vx, ball.vy = speed * math.sin(angle), -speed * math.cos(angle)
        self.hits += 1
        reward = self.HIT_REWARD
        if self.hits % self.BONUS_EVERY == 0:
            reward += self.BONUS_REWARD
        self.crystals += reward
        self.earned += reward
        self.events.append(f"+{reward} кристаллов" + (" · серия из 5!" if reward > self.HIT_REWARD else ""))

    def _stone_bounce(self, stone: Box) -> None:
        """Отражает круг от прямоугольного камня, включая его боковые стороны и углы."""
        ball = self.ball
        assert ball is not None
        closest_x = max(stone.x, min(ball.x, stone.x + stone.width))
        closest_y = max(stone.y, min(ball.y, stone.y + stone.height))
        dx, dy = ball.x - closest_x, ball.y - closest_y
        distance = math.hypot(dx, dy)
        if distance >= ball.radius:
            return
        if distance > 0:
            nx, ny = dx / distance, dy / distance
            penetration = ball.radius - distance
        else:
            # Если камень куплен прямо под шариком, вытолкнем шарик к ближайшей грани.
            edges = [(ball.x - stone.x, -1, 0),
                     (stone.x + stone.width - ball.x, 1, 0),
                     (ball.y - stone.y, 0, -1),
                     (stone.y + stone.height - ball.y, 0, 1)]
            depth, nx, ny = min(edges)
            penetration = ball.radius + depth
        ball.x += nx * (penetration + 0.01)
        ball.y += ny * (penetration + 0.01)
        approach = ball.vx * nx + ball.vy * ny
        if approach < 0:
            ball.vx -= 2 * approach * nx
            ball.vy -= 2 * approach * ny
        # Камни не дают очков: пассивное отражение не позволяет бесконечно копить валюту.
