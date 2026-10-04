"""Окно Pygame: ввод с клавиатуры и отрисовка. Запуск: python main.py."""

import os
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from game import Game, State


BG = "#10141f"
PANEL = "#1a2030"
TEXT = "#eef1fb"
MUTED = "#98a4bd"
MINT = "#70e5c0"
PURPLE = "#aa97ff"
GOLD = "#ffcf79"
MIN_SIZE = (840, 680)
INITIAL_SIZE = (1120, 760)


class App:
    """Соединяет независимые правила игры с событиями и графикой Pygame."""

    def __init__(self) -> None:
        """Настраивает окно, шрифты с кириллицей, часы и начальную игровую область."""
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_caption("Пин-понг • Кристальная защита")
        self.screen = pygame.display.set_mode(INITIAL_SIZE, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.fonts = {size: pygame.font.SysFont("segoeui,dejavusans,arial", size)
                      for size in (14, 16, 18, 22, 28, 36, 44)}
        self.field = self._field_rect(INITIAL_SIZE)
        self.game = Game(self.field.width, self.field.height)
        self.running = True
        self.notice = "Меняйте размер окна до начала игры"
        self.notice_until = 0
        self.trail: list[tuple[float, float]] = []

    def _field_rect(self, size: tuple[int, int]) -> pygame.Rect:
        """Выделяет поле, оставляя справа панель магазина, а сверху — заголовок."""
        return pygame.Rect(28, 92, size[0] - 328, size[1] - 152)

    def _set_window_mode(self) -> None:
        """Разрешает изменение окна в подготовке и фиксирует его размер после F5."""
        flags = pygame.RESIZABLE if self.game.state == State.READY else 0
        size = self.screen.get_size()
        if bool(self.screen.get_flags() & pygame.RESIZABLE) != bool(flags):
            # SDL иногда сохраняет RESIZABLE при повторном set_mode с тем же размером.
            # Пересоздание окна гарантирует смену режима; состояние игры не затрагивается.
            pygame.display.quit()
            pygame.display.init()
            pygame.display.set_caption("Пин-понг • Кристальная защита")
        self.screen = pygame.display.set_mode(size, flags)

    def _new_game(self) -> None:
        """Начинает партию, очищает визуальный след и блокирует растягивание окна."""
        self.game.start()
        self.trail.clear()
        self.notice = "Ловите шарик платформой и копите кристаллы"
        self.notice_until = pygame.time.get_ticks() + 3500
        self._set_window_mode()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Обрабатывает выход, размер окна, покупку, старт и паузу с клавиатуры."""
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            if self.game.state == State.READY:
                size = (max(MIN_SIZE[0], event.w), max(MIN_SIZE[1], event.h))
                self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
                self.field = self._field_rect(size)
                self.game.resize(self.field.width, self.field.height)
            elif self.screen.get_size() != (self.field.width + 328, self.field.height + 152):
                self.screen = pygame.display.set_mode((self.field.width + 328, self.field.height + 152))
        elif event.type == pygame.WINDOWFOCUSLOST and self.game.state == State.RUNNING:
            self.game.toggle_pause()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F5:
                self._new_game()
            elif event.key == pygame.K_SPACE:
                self.game.toggle_pause()
            elif event.key == pygame.K_F3:
                self.game.buy_stone()
            elif event.key == pygame.K_ESCAPE:
                self.game.prepare()
                self.trail.clear()
                self._set_window_mode()
                self.notice = "Меняйте размер окна до начала игры"
            elif event.key == pygame.K_q:
                self.running = False

    def _text(self, value: str, position: tuple[float, float], size: int = 18,
              color: str = TEXT, center: bool = False) -> None:
        """Рисует текст выбранного размера с привязкой к левому краю или центру."""
        rendered = self.fonts[size].render(value, True, color)
        rect = rendered.get_rect()
        if center:
            rect.center = (round(position[0]), round(position[1]))
        else:
            rect.topleft = (round(position[0]), round(position[1]))
        self.screen.blit(rendered, rect)

    def _box(self, box, color: str, radius: int = 5) -> pygame.Rect:
        """Переводит прямоугольник из координат поля в координаты окна и рисует его."""
        rect = pygame.Rect(round(self.field.x + box.x), round(self.field.y + box.y),
                           round(box.width), round(box.height))
        pygame.draw.rect(self.screen, color, rect, border_radius=radius)
        return rect

    def _crystal(self, x: int, y: int, size: int = 10) -> None:
        """Рисует ромбик кристалла без внешних картинок и дополнительных зависимостей."""
        pygame.draw.polygon(self.screen, MINT, [(x, y - size), (x + size, y),
                                              (x, y + size), (x - size, y)])
        pygame.draw.line(self.screen, "#b5ffe9", (x, y - size + 2), (x, y + size - 2))

    def _draw_field(self) -> None:
        """Рисует сетку, три стенки, платформу, камни и шарик с коротким следом."""
        f = self.field
        pygame.draw.rect(self.screen, "#151b28", f)
        for x in range(f.left + 36, f.right, 36):
            pygame.draw.line(self.screen, "#1d2535", (x, f.top), (x, f.bottom))
        for y in range(f.top + 36, f.bottom, 36):
            pygame.draw.line(self.screen, "#1d2535", (f.left, y), (f.right, y))
        # Линия снизу обозначает опасную границу, но физической стеной не является.
        for x in range(f.left, f.right - 5, 16):
            pygame.draw.line(self.screen, "#704952", (x, f.bottom), (min(x + 7, f.right), f.bottom), 2)
        pygame.draw.lines(self.screen, "#74809e", False,
                          [(f.left, f.bottom), f.topleft, f.topright, (f.right, f.bottom)], 3)
        for stone in self.game.stones:
            rect = self._box(stone, GOLD, 3)
            pygame.draw.rect(self.screen, "#b98b4e", rect, 1, border_radius=3)
            pygame.draw.line(self.screen, "#ffe7b5", (rect.left + 5, rect.top + 4),
                             (rect.right - 5, rect.top + 4), 2)
        paddle_rect = self._box(self.game.paddle, PURPLE, 6)
        # Метки показывают три клетки; сама платформа остаётся сплошной.
        for index in (1, 2):
            x = round(paddle_rect.left + index * self.game.cell)
            pygame.draw.line(self.screen, "#7969c0", (x, paddle_rect.top + 4), (x, paddle_rect.bottom - 4), 2)
        if self.game.ball:
            for index, (x, y) in enumerate(self.trail):
                shade = 45 + int(75 * index / max(1, len(self.trail)))
                pygame.draw.circle(self.screen, (shade // 2, shade, shade),
                                   (round(f.x + x), round(f.y + y)), 3 + index // 4)
            ball = self.game.ball
            position = (round(f.x + ball.x), round(f.y + ball.y))
            pygame.draw.circle(self.screen, MINT, position, round(ball.radius))
            pygame.draw.circle(self.screen, "#e4fff6", (position[0] - 2, position[1] - 3), 3)

    def _draw_panel(self) -> None:
        """Показывает доступный баланс, статистику, цену покупки и управление."""
        x, y = self.field.right + 24, self.field.top
        width = self.screen.get_width() - x - 24
        pygame.draw.rect(self.screen, PANEL, (x, y, width, 132), border_radius=12)
        self._text("КРИСТАЛЛЫ / ОЧКИ", (x + 18, y + 16), 14, MUTED)
        self._crystal(x + 28, y + 68, 12)
        self._text(str(self.game.crystals), (x + 50, y + 39), 44)
        self._text(f"Всего заработано: {self.game.earned}", (x + 18, y + 104), 14, MUTED)
        y += 152
        self._text("КАМЕННАЯ ЗАЩИТА", (x + 4, y), 16, GOLD)
        self._text(f"Камней: {self.game.stone_count} / {self.game.max_stones}", (x + 4, y + 30), 18)
        button = pygame.Rect(x, y + 66, width, 48)
        can_buy = (self.game.state in (State.RUNNING, State.PAUSED)
                   and self.game.crystals >= self.game.next_price
                   and self.game.stone_count < self.game.max_stones)
        pygame.draw.rect(self.screen, "#254239" if can_buy else "#293144", button, border_radius=8)
        label = "Защита заполнена" if self.game.stone_count >= self.game.max_stones else f"F3  Купить · {self.game.next_price}"
        self._text(label, button.center, 18, MINT if can_buy else MUTED, True)
        self._text("Цена растёт на 20 за камень", (x + 4, y + 124), 14, MUTED)
        y += 164
        self._text(f"Отражений: {self.game.hits}", (x + 4, y), 22)
        self._text("+10 за удар платформой", (x + 4, y + 35), 16, MINT)
        self._text("+20 за каждый 5-й удар", (x + 4, y + 59), 16, MINT)
        self._text("КЛАВИШИ", (x + 4, y + 107), 14, MUTED)
        for index, label in enumerate(("← → / A D    движение", "F5    новая игра", "Пробел    пауза", "Esc    подготовка · Q    выход")):
            self._text(label, (x + 4, y + 133 + index * 25), 14, TEXT)

    def _draw_overlay(self) -> None:
        """Выводит заставку, паузу или итог партии поверх затемнённого поля."""
        state = self.game.state
        if state == State.RUNNING:
            return
        shade = pygame.Surface(self.field.size, pygame.SRCALPHA)
        shade.fill((10, 14, 25, 205))
        self.screen.blit(shade, self.field)
        x, y = self.field.center
        titles = {State.READY: "Кристальная защита", State.PAUSED: "Пауза", State.OVER: "Игра окончена"}
        self._crystal(x, y - 110, 24)
        self._text(titles[state], (x, y - 50), 36, TEXT, True)
        if state == State.READY:
            lines = ["Не дайте шарику покинуть поле.", "Отбивайте его и покупайте камни за кристаллы.", "F5 — начать игру"]
        elif state == State.PAUSED:
            lines = ["Пробел — продолжить", "F3 — купить камень во время паузы", "F5 — начать заново"]
        else:
            lines = [f"Заработано: {self.game.earned}  ·  Отражений: {self.game.hits}",
                     f"Осталось кристаллов: {self.game.crystals}", "F5 — попробовать ещё раз"]
        for index, line in enumerate(lines):
            self._text(line, (x, y + 8 + index * 34), 18, MINT if index == 2 else MUTED, True)

    def draw(self) -> None:
        """Собирает кадр из заголовка, поля, панели магазина и сообщения о событии."""
        self.screen.fill(BG)
        self._text("ПИН-ПОНГ", (28, 20), 28)
        self._text("КРИСТАЛЬНАЯ ЗАЩИТА", (30, 57), 14, MINT)
        labels = {State.READY: "ПОДГОТОВКА", State.RUNNING: "ИГРА ИДЁТ", State.PAUSED: "ПАУЗА", State.OVER: "КОНЕЦ ИГРЫ"}
        self._text(labels[self.game.state], (self.field.right - 160, 36), 16, MUTED)
        self._draw_field()
        self._draw_panel()
        self._draw_overlay()
        message = self.notice if (self.game.state == State.READY or pygame.time.get_ticks() < self.notice_until) else "F3 — защита  ·  Пробел — пауза  ·  Esc — подготовка"
        self._text(message, (28, self.screen.get_height() - 37), 16, MINT)
        pygame.display.flip()

    def run(self) -> None:
        """Выполняет игровой цикл до закрытия окна, поддерживая скорость независимо от FPS."""
        try:
            while self.running:
                dt = self.clock.tick(120) / 1000
                for event in pygame.event.get():
                    self.handle_event(event)
                keys = pygame.key.get_pressed()
                direction = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
                self.game.update(dt, direction)
                if self.game.ball and self.game.state == State.RUNNING:
                    self.trail.append((self.game.ball.x, self.game.ball.y))
                    self.trail = self.trail[-14:]
                for message in self.game.events:
                    self.notice = message
                    self.notice_until = pygame.time.get_ticks() + 2800
                self.game.events.clear()
                self.draw()
        finally:
            pygame.quit()


def main() -> None:
    """Создаёт приложение и запускает игру при выполнении файла напрямую."""
    App().run()


if __name__ == "__main__":
    main()
