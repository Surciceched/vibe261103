"""뱀게임 (표준 라이브러리 tkinter 사용)

실행: python snake.py
조작: 방향키 또는 WASD 이동, P 일시정지, R 또는 Space 재시작, Esc 종료
"""

import random
import tkinter as tk
from collections import deque

COLS = 20
ROWS = 20
CELL_SIZE = 24
START_DELAY_MS = 150
MIN_DELAY_MS = 60
SPEEDUP_MS = 3  # 먹이를 먹을 때마다 줄어드는 틱 간격
FOOD_SCORE = 10

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

KEY_DIRECTIONS = {
    "up": UP,
    "down": DOWN,
    "left": LEFT,
    "right": RIGHT,
    "w": UP,
    "s": DOWN,
    "a": LEFT,
    "d": RIGHT,
}

BG_COLOR = "#1e1e2e"
GRID_COLOR = "#2a2a3c"
HEAD_COLOR = "#a6e3a1"
BODY_COLOR = "#40a02b"
FOOD_COLOR = "#f38ba8"
TEXT_COLOR = "#cdd6f4"


class SnakeGame:
    """화면과 분리된 게임 규칙."""

    def __init__(self, cols=COLS, rows=ROWS):
        self.cols = cols
        self.rows = rows
        self.reset()

    def reset(self):
        center_x, center_y = self.cols // 2, self.rows // 2
        # 머리가 맨 앞이다.
        self.snake = deque((center_x - i, center_y) for i in range(3))
        self.direction = RIGHT
        self.pending_turns = deque()
        self.score = 0
        self.game_over = False
        self.won = False
        self.food = self._spawn_food()

    def _spawn_food(self):
        occupied = set(self.snake)
        free = [
            (x, y)
            for x in range(self.cols)
            for y in range(self.rows)
            if (x, y) not in occupied
        ]
        return random.choice(free) if free else None

    def turn(self, direction):
        """방향 전환을 예약한다. 한 틱에 키를 빠르게 두 번 눌러도 입력이 유지된다."""
        last = self.pending_turns[-1] if self.pending_turns else self.direction
        is_reverse = direction[0] == -last[0] and direction[1] == -last[1]
        if direction != last and not is_reverse and len(self.pending_turns) < 2:
            self.pending_turns.append(direction)

    def step(self):
        """한 칸 이동한다. 먹이를 먹었으면 True를 반환한다."""
        if self.game_over:
            return False

        if self.pending_turns:
            self.direction = self.pending_turns.popleft()

        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])
        ate = new_head == self.food

        hit_wall = not (0 <= new_head[0] < self.cols and 0 <= new_head[1] < self.rows)
        # 먹지 않으면 꼬리가 비켜나므로 꼬리 칸으로는 이동할 수 있다.
        body = list(self.snake)
        if not ate:
            body.pop()
        if hit_wall or new_head in body:
            self.game_over = True
            return False

        self.snake.appendleft(new_head)
        if ate:
            self.score += FOOD_SCORE
            self.food = self._spawn_food()
            if self.food is None:
                self.won = True
                self.game_over = True
        else:
            self.snake.pop()
        return ate


class SnakeApp:
    """tkinter 화면, 입력, 타이머를 담당한다."""

    def __init__(self, root):
        self.root = root
        self.game = SnakeGame()
        self.high_score = 0
        self.paused = False
        self.delay = START_DELAY_MS
        self.after_id = None

        root.title("뱀게임")
        root.resizable(False, False)

        self.status = tk.Label(
            root, font=("Malgun Gothic", 12, "bold"), bg=BG_COLOR, fg=TEXT_COLOR, pady=6
        )
        self.status.pack(fill="x")

        self.canvas = tk.Canvas(
            root,
            width=COLS * CELL_SIZE,
            height=ROWS * CELL_SIZE,
            bg=BG_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack()

        root.bind("<Key>", self.on_key)

        self.restart()

    def restart(self):
        self.game.reset()
        self.paused = False
        self.delay = START_DELAY_MS
        self.schedule_tick()
        self.draw()

    def schedule_tick(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self.after_id = self.root.after(self.delay, self.tick)

    def tick(self):
        self.after_id = None
        if self.paused or self.game.game_over:
            return

        if self.game.step():
            self.delay = max(MIN_DELAY_MS, self.delay - SPEEDUP_MS)
        self.high_score = max(self.high_score, self.game.score)
        self.draw()

        if not self.game.game_over:
            self.schedule_tick()

    def on_key(self, event):
        key = event.keysym.lower()

        if key == "escape":
            self.root.destroy()
        elif key in ("r", "space"):
            # Space는 게임이 끝났을 때만 재시작한다.
            if key == "r" or self.game.game_over:
                self.restart()
        elif key == "p":
            self.toggle_pause()
        elif key in KEY_DIRECTIONS and not self.paused:
            self.game.turn(KEY_DIRECTIONS[key])

    def toggle_pause(self):
        if self.game.game_over:
            return
        self.paused = not self.paused
        if not self.paused:
            self.schedule_tick()
        self.draw()

    def draw_cell(self, cell, color, inset=1):
        x, y = cell
        self.canvas.create_rectangle(
            x * CELL_SIZE + inset,
            y * CELL_SIZE + inset,
            (x + 1) * CELL_SIZE - inset,
            (y + 1) * CELL_SIZE - inset,
            fill=color,
            outline="",
        )

    def draw_overlay(self, title, subtitle):
        center_x = COLS * CELL_SIZE // 2
        center_y = ROWS * CELL_SIZE // 2
        self.canvas.create_text(
            center_x,
            center_y - 18,
            text=title,
            fill=TEXT_COLOR,
            font=("Malgun Gothic", 24, "bold"),
        )
        self.canvas.create_text(
            center_x,
            center_y + 18,
            text=subtitle,
            fill=TEXT_COLOR,
            font=("Malgun Gothic", 12),
        )

    def draw(self):
        self.canvas.delete("all")

        for x in range(1, COLS):
            self.canvas.create_line(
                x * CELL_SIZE, 0, x * CELL_SIZE, ROWS * CELL_SIZE, fill=GRID_COLOR
            )
        for y in range(1, ROWS):
            self.canvas.create_line(
                0, y * CELL_SIZE, COLS * CELL_SIZE, y * CELL_SIZE, fill=GRID_COLOR
            )

        if self.game.food is not None:
            self.draw_cell(self.game.food, FOOD_COLOR, inset=4)
        for index, cell in enumerate(self.game.snake):
            self.draw_cell(cell, HEAD_COLOR if index == 0 else BODY_COLOR)

        self.status.config(
            text=f"점수: {self.game.score}    최고 점수: {self.high_score}"
        )

        if self.game.won:
            self.draw_overlay("승리!", "R 또는 Space: 다시 시작")
        elif self.game.game_over:
            self.draw_overlay("게임 오버", "R 또는 Space: 다시 시작")
        elif self.paused:
            self.draw_overlay("일시정지", "P: 계속하기")


def main():
    root = tk.Tk()
    SnakeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
