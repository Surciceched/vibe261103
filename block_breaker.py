# tkinter는 파이썬에 기본으로 포함된 GUI(창 만들기) 라이브러리입니다.
import tkinter as tk
# 목숨을 잃은 뒤 공의 시작 방향을 무작위로 선택하기 위해 사용합니다.
import random


# 블록 깨기 게임의 화면, 상태, 움직임을 관리하는 클래스입니다.
class BreakoutGame:
    def __init__(self, root: tk.Tk) -> None:
        # 게임 창과 캔버스(도형을 그리는 화면)를 설정합니다.
        self.root = root
        self.root.title("블록 깨기")
        self.width = 640
        self.height = 480

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, bg="#101827", highlightthickness=0)
        self.canvas.pack()

        # 점수, 남은 목숨, 게임 진행 상태를 저장합니다.
        self.score = 0
        self.lives = 3
        self.running = False
        self.game_over = False

        # 아래쪽에서 움직이는 패들, 위의 공, 공의 이동 속도를 생성합니다.
        self.paddle = self.canvas.create_rectangle(270, 440, 370, 452, fill="#4cc9f0", outline="")
        self.ball = self.canvas.create_oval(310, 420, 326, 436, fill="#f72585", outline="")
        self.ball_dx = 4.0
        self.ball_dy = -4.0

        self.score_text = self.canvas.create_text(12, 12, anchor="nw", text="점수: 0", fill="white", font=("맑은 고딕", 12, "bold"))
        self.lives_text = self.canvas.create_text(self.width - 12, 12, anchor="ne", text="목숨: 3", fill="white", font=("맑은 고딕", 12, "bold"))

        # 여러 줄의 블록을 반복문으로 화면에 배치합니다.
        self.bricks = []
        colors = ["#ef476f", "#ffd166", "#06d6a0", "#118ab2", "#8338ec"]
        brick_width = 56
        brick_height = 22
        gap = 5
        columns = 10
        left = 20
        top = 60
        for row in range(5):
            for column in range(columns):
                x1 = left + column * (brick_width + gap)
                y1 = top + row * (brick_height + gap)
                x2 = x1 + brick_width
                y2 = y1 + brick_height
                brick = self.canvas.create_rectangle(x1, y1, x2, y2, fill=colors[row], outline="#101827", width=2)
                self.bricks.append(brick)

        self.message = self.canvas.create_text(
            self.width / 2,
            self.height / 2,
            text="스페이스를 눌러 시작",
            fill="#ffffff",
            font=("맑은 고딕", 20, "bold"),
        )

        # 키보드와 마우스 입력을 게임 함수에 연결합니다.
        root.bind("<Left>", lambda event: self.move_paddle(-35))
        root.bind("<Right>", lambda event: self.move_paddle(35))
        root.bind("<Motion>", self.move_paddle_mouse)
        root.bind("<space>", self.start_or_restart)
        root.bind("<r>", self.start_or_restart)

    def move_paddle(self, distance: float) -> None:
        """왼쪽 또는 오른쪽 방향키로 패들을 움직이고 화면 밖으로 나가지 않게 합니다."""
        x1, _, x2, _ = self.canvas.coords(self.paddle)
        new_x1 = max(0, min(self.width - (x2 - x1), x1 + distance))
        self.canvas.move(self.paddle, new_x1 - x1, 0)

    def move_paddle_mouse(self, event: tk.Event) -> None:
        """마우스 위치의 가운데에 패들 중앙이 오도록 패들을 움직입니다."""
        x1, _, x2, _ = self.canvas.coords(self.paddle)
        paddle_width = x2 - x1
        new_x1 = max(0, min(self.width - paddle_width, event.x - paddle_width / 2))
        self.canvas.move(self.paddle, new_x1 - x1, 0)

    def start_or_restart(self, event=None) -> None:
        """게임을 시작하거나, 게임 종료 후 전체 게임을 처음 상태로 재시작합니다."""
        if self.game_over:
            self.reset_game()
        elif not self.running:
            self.running = True
            self.canvas.itemconfigure(self.message, text="")
            self.update_game()

    def reset_game(self) -> None:
        """점수와 목숨, 블록, 패들, 공을 초기 상태로 되돌립니다."""
        self.canvas.delete("all")

        self.score = 0
        self.lives = 3
        self.running = False
        self.game_over = False

        self.paddle = self.canvas.create_rectangle(270, 440, 370, 452, fill="#4cc9f0", outline="")
        self.ball = self.canvas.create_oval(310, 420, 326, 436, fill="#f72585", outline="")
        self.ball_dx = random.choice((-4.0, 4.0))
        self.ball_dy = -4.0

        self.score_text = self.canvas.create_text(12, 12, anchor="nw", text="점수: 0", fill="white", font=("맑은 고딕", 12, "bold"))
        self.lives_text = self.canvas.create_text(self.width - 12, 12, anchor="ne", text="목숨: 3", fill="white", font=("맑은 고딕", 12, "bold"))

        colors = ["#ef476f", "#ffd166", "#06d6a0", "#118ab2", "#8338ec"]
        self.bricks = []
        for row in range(5):
            for column in range(10):
                x1 = 20 + column * 61
                y1 = 60 + row * 27
                brick = self.canvas.create_rectangle(x1, y1, x1 + 56, y1 + 22, fill=colors[row], outline="#101827", width=2)
                self.bricks.append(brick)

        self.message = self.canvas.create_text(
            self.width / 2,
            self.height / 2,
            text="스페이스를 눌러 다시 시작",
            fill="#ffffff",
            font=("맑은 고딕", 20, "bold"),
        )

    def reset_ball(self) -> None:
        """공을 처음 위치로 되돌리고 무작위로 좌우 방향을 선택합니다."""
        self.canvas.coords(self.ball, 310, 420, 326, 436)
        self.ball_dx = random.choice((-4.0, 4.0))
        self.ball_dy = -4.0

    def update_game(self) -> None:
        """공을 움직이고 벽, 패들, 블록과의 충돌을 확인합니다."""
        if not self.running:
            return

        self.canvas.move(self.ball, self.ball_dx, self.ball_dy)
        x1, y1, x2, y2 = self.canvas.coords(self.ball)

        # 좌우 벽에 닿으면 가로 방향의 속도를 반대로 바꿉니다.
        if x1 <= 0 or x2 >= self.width:
            self.ball_dx *= -1
        # 천장에 닿으면 세로 방향의 속도를 반대로 바꿉니다.
        if y1 <= 0:
            self.ball_dy *= -1

        # 공이 바닥 아래로 떨어지면 목숨을 하나 감소시킵니다.
        if y2 >= self.height:
            self.lives -= 1
            self.canvas.itemconfigure(self.lives_text, text=f"목숨: {self.lives}")
            if self.lives <= 0:
                self.end_game(False)
                return
            self.running = False
            self.reset_ball()
            self.canvas.itemconfigure(self.message, text="공을 놓쳤습니다! 스페이스로 계속")
            return

        # 패들과 충돌한 위치에 따라 공이 튀어 나가는 방향을 결정합니다.
        paddle_x1, paddle_y1, paddle_x2, paddle_y2 = self.canvas.coords(self.paddle)
        if x2 >= paddle_x1 and x1 <= paddle_x2 and y2 >= paddle_y1 and y1 <= paddle_y2 and self.ball_dy > 0:
            hit_position = ((x1 + x2) / 2 - (paddle_x1 + paddle_x2) / 2) / ((paddle_x2 - paddle_x1) / 2)
            self.ball_dx = hit_position * 6
            if abs(self.ball_dx) < 1.5:
                self.ball_dx = 1.5 if hit_position >= 0 else -1.5
            self.ball_dy = -abs(self.ball_dy)

        # 남아 있는 블록 목록을 확인하여 공이 닿은 블록을 제거합니다.
        for brick in list(self.bricks):
            brick_x1, brick_y1, brick_x2, brick_y2 = self.canvas.coords(brick)
            if x2 >= brick_x1 and x1 <= brick_x2 and y2 >= brick_y1 and y1 <= brick_y2:
                overlap_left = x2 - brick_x1
                overlap_right = brick_x2 - x1
                overlap_top = y2 - brick_y1
                overlap_bottom = brick_y2 - y1
                # 충돌한 면이 좌우인지 위아래인지 계산해 공의 진행 방향을 바꿉니다.
                minimum_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)
                if minimum_overlap in (overlap_left, overlap_right):
                    self.ball_dx *= -1
                else:
                    self.ball_dy *= -1

                self.canvas.delete(brick)
                self.bricks.remove(brick)
                self.score += 10
                self.canvas.itemconfigure(self.score_text, text=f"점수: {self.score}")
                if not self.bricks:
                    self.end_game(True)
                    return
                break

        # 약 60FPS로 다음 프레임을 예약하여 공의 움직임을 반복합니다.
        self.root.after(16, self.update_game)

    def end_game(self, won: bool) -> None:
        """승리 또는 패배 메시지를 화면 가운데에 표시합니다."""
        self.running = False
        self.game_over = True
        text = "승리! 모든 블록을 깼습니다!" if won else "게임 오버"
        self.canvas.itemconfigure(self.message, text=f"{text}\nR 또는 스페이스로 다시 시작")


# 이 파일을 직접 실행했을 때만 아래 코드를 실행합니다.
if __name__ == "__main__":
    root = tk.Tk()
    game = BreakoutGame(root)
    root.resizable(False, False)
    root.mainloop()
