# CMPT 371 - Assignment 3
# Description: Client side of the multiplayer quiz game.
# IT handles the GUI and connects to the server over TCP.
# Built with Tkinter for the interface.
 
import socket
import threading
import json
import tkinter as tk
import time
 
# change this to the server's IP if running on different machines
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5050
 
# color palette going for a soft girly pastel look
C = {
    "bg":           "#FFF0F5",
    "card":         "#FFFFFF",
    "header":       "#FFD6E7",
    "sidebar":      "#FFE4EE",
    "btn":          "#FF85A1",
    "btn_hover":    "#FF6B8A",
    "btn_disabled": "#E0C0CC",
    "accent":       "#FF85A1",
    "accent2":      "#C9A0DC",
    "green":        "#A8E6CF",
    "red":          "#FFB3B3",
    "yellow":       "#FFE0A0",
    "text_dark":    "#5C3D4E",
    "text_mid":     "#9B7189",
    "text_light":   "#C8A4B8",
    "border":       "#FFD6E7",
    "shadow":       "#F7C5D8",
    "option_bg":    "#FFF8FA",
    "option_sel":   "#FFD6E7",
    "option_right": "#C8F5D8",
    "option_wrong": "#FFD0D0",
}
 
 
class QuizClient:
 
    def __init__(self, root):
        self.root = root
        self.root.title("Quiz")
        self.root.geometry("700x640")
        self.root.resizable(False, False)
        self.root.configure(bg=C["bg"])
 
        self.sock = None
        self.my_name = ""
 
        # track which answer the player selected (-1 means nothing yet)
        self.selected = -1
        self.submitted = False
 
        # this event is how we signal the network thread that the player answered
        self.answer_event = threading.Event()
 
        # timer stuff
        self.timer_val = 0
        self.timer_running = False
 
        # keep references to option buttons so we can style them
        self.option_btns = []
        self.confetti_running = False  # flag to stop confetti when leaving screen
 
        self.build_login()
 

    # LOGIN SCREEN

    def build_login(self):
        self.clear()
        self.root.unbind("<Return>")
 
        canvas = tk.Canvas(self.root, bg=C["bg"], highlightthickness=0)
        canvas.place(relwidth=1, relheight=1)
        for x, y, r, col in [
            (60, 60, 45, "#FFD6E7"), (740, 90, 65, "#E8D5F5"),
            (90, 490, 55, "#D5EAF5"), (720, 500, 40, "#FFE4C4"),
            (400, 25, 30, "#C9F0D0"),
        ]:
            canvas.create_oval(x-r, y-r, x+r, y+r, fill=col, outline="")
 
        # center card
        card = tk.Frame(self.root, bg=C["card"], highlightbackground=C["shadow"],
                        highlightthickness=2)
        card.place(relx=0.5, rely=0.5, anchor="center", width=400, height=420)
 
        tk.Label(card, text="🎯", font=("Georgia", 46), bg=C["card"]).pack(pady=(28, 0))
        tk.Label(card, text="Quiz", font=("Georgia", 26, "bold"),
                 fg=C["accent"], bg=C["card"]).pack()
        tk.Label(card, text="multiplayer trivia · same questions · live scores",
                 font=("Georgia", 9, "italic"), fg=C["text_light"], bg=C["card"]).pack(pady=(2, 22))
 
        tk.Label(card, text="Server IP", font=("Georgia", 9),
                 fg=C["text_mid"], bg=C["card"]).pack(anchor="w", padx=40)
        self.ip_var = tk.StringVar(value=SERVER_HOST)
        self._entry(card, self.ip_var).pack(padx=40, pady=(2, 12), fill="x")
 
        tk.Label(card, text="Your name", font=("Georgia", 9),
                 fg=C["text_mid"], bg=C["card"]).pack(anchor="w", padx=40)
        self.name_var = tk.StringVar()
        ne = self._entry(card, self.name_var)
        ne.pack(padx=40, pady=(2, 6), fill="x")
        ne.winfo_children()[0].focus()
 
        # status label shows errors e.g connection failed
        self.status = tk.Label(card, text="", font=("Georgia", 9),
                               fg="#FF6B8A", bg=C["card"])
        self.status.pack()
 
        tk.Button(card, text="Join Game 🎯", font=("Georgia", 12, "bold"),
                  fg="white", bg=C["btn"], activebackground=C["btn_hover"],
                  activeforeground="white", relief="flat", bd=0,
                  pady=10, cursor="hand2",
                  command=self.connect).pack(padx=40, pady=14, fill="x")
 
        self.root.bind("<Return>", lambda e: self.connect())
 
    def _entry(self, parent, var):
        f = tk.Frame(parent, bg=C["border"], bd=0)
        tk.Entry(f, textvariable=var, font=("Georgia", 12),
                 fg=C["text_dark"], bg=C["card"],
                 insertbackground=C["accent"],
                 relief="flat", bd=7).pack(padx=1, pady=1, fill="x")
        return f
 

    # LOBBY SCREEN

    def build_lobby(self, data):
        # show waiting room with list of players
        self.clear()
 
        outer = tk.Frame(self.root, bg=C["bg"])
        outer.place(relx=0.5, rely=0.5, anchor="center", width=500)
 
        tk.Label(outer, text="🎯 Quiz", font=("Georgia", 26, "bold"),
                 fg=C["accent"], bg=C["bg"]).pack(pady=(0, 4))
        tk.Label(outer, text="Waiting for players...",
                 font=("Georgia", 11, "italic"), fg=C["text_mid"],
                 bg=C["bg"]).pack(pady=(0, 20))
 
        card = tk.Frame(outer, bg=C["card"], highlightbackground=C["border"],
                        highlightthickness=1)
        card.pack(fill="x", padx=20, ipadx=20, ipady=16)
 
        tk.Label(card, text="Players in lobby",
                 font=("Georgia", 10, "bold"), fg=C["text_mid"],
                 bg=C["card"]).pack(anchor="w", padx=16, pady=(12, 6))
 
        self.lobby_players_frame = tk.Frame(card, bg=C["card"])
        self.lobby_players_frame.pack(fill="x", padx=16, pady=(0, 12))
 
        self.update_lobby_players(data.get("players", []))
 
        self.lobby_status = tk.Label(
            outer,
            text=f"Need {data.get('min_players', 2)} players to start",
            font=("Georgia", 10, "italic"), fg=C["text_light"], bg=C["bg"]
        )
        self.lobby_status.pack(pady=16)
 
    def update_lobby_players(self, players):
        for w in self.lobby_players_frame.winfo_children():
            w.destroy()
        medals = ["🥇", "🥈", "🥉", "🎮", "🎮", "🎮", "🎮", "🎮"]
        for i, name in enumerate(players):
            row = tk.Frame(self.lobby_players_frame, bg=C["card"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=medals[i], font=("Georgia", 13),
                     bg=C["card"]).pack(side="left", padx=(0, 8))
            # bold if it's us
            style = ("Georgia", 11, "bold") if name == self.my_name else ("Georgia", 11)
            tk.Label(row, text=name + (" (you)" if name == self.my_name else ""),
                     font=style, fg=C["text_dark"], bg=C["card"]).pack(side="left")
 
    # COUNTDOWN SCREEN
    def build_countdown(self, count):
        self.clear()
        outer = tk.Frame(self.root, bg=C["bg"])
        outer.place(relx=0.5, rely=0.5, anchor="center")
 
        tk.Label(outer, text="Get Ready!", font=("Georgia", 22, "bold"),
                 fg=C["text_mid"], bg=C["bg"]).pack(pady=(0, 10))
        tk.Label(outer, text=str(count), font=("Georgia", 90, "bold"),
                 fg=C["accent"], bg=C["bg"]).pack()
        tk.Label(outer, text="Same questions for everyone 🎯",
                 font=("Georgia", 11, "italic"), fg=C["text_light"],
                 bg=C["bg"]).pack(pady=10)
 
    # QUESTION SCREEN
    def build_question(self, data):
        self.clear()
        self.selected = -1
        self.submitted = False
        self.option_btns = []
 
        # top bar with question number and timer
        topbar = tk.Frame(self.root, bg=C["header"], pady=10)
        topbar.pack(fill="x")
 
        tk.Label(topbar, text=f"Question {data['number']} of {data['total']}",
                 font=("Georgia", 11, "bold"), fg=C["text_dark"],
                 bg=C["header"], padx=16).pack(side="left")
 
        self.timer_lbl = tk.Label(topbar, text=f"⏱ {data['time_limit']}s",
                                  font=("Georgia", 11, "bold"),
                                  fg=C["text_dark"], bg=C["header"], padx=16)
        self.timer_lbl.pack(side="right")
 
        # progress bar showing how much quiz left
        prog_bg = tk.Frame(self.root, bg=C["border"], height=5)
        prog_bg.pack(fill="x")
        prog_fill = tk.Frame(prog_bg, bg=C["accent"], height=5)
        prog_fill.place(relwidth=data["number"]/data["total"], relheight=1)
 
        content = tk.Frame(self.root, bg=C["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=12)
 
        left = tk.Frame(content, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True)
 
        # question text box
        q_card = tk.Frame(left, bg=C["card"], highlightbackground=C["border"],
                          highlightthickness=1)
        q_card.pack(fill="x", pady=(0, 12))
        tk.Label(q_card, text=data["question"],
                 font=("Georgia", 13, "bold"), fg=C["text_dark"],
                 bg=C["card"], wraplength=460, justify="left",
                 padx=18, pady=16).pack()
 
        #4 answer options
        letters = ["A", "B", "C", "D"]
        for i, opt in enumerate(data["options"]):
            row = tk.Frame(left, bg=C["option_bg"],
                           highlightbackground=C["border"],
                           highlightthickness=1, cursor="hand2")
            row.pack(fill="x", pady=4)
 
            badge = tk.Label(row, text=letters[i],
                             font=("Georgia", 10, "bold"),
                             fg="white", bg=C["accent"],
                             width=3, pady=10)
            badge.pack(side="left")
 
            lbl = tk.Label(row, text=opt,
                           font=("Georgia", 11), fg=C["text_dark"],
                           bg=C["option_bg"], anchor="w",
                           padx=10, pady=10)
            lbl.pack(side="left", fill="x", expand=True)

            for w in [row, badge, lbl]:
                w.bind("<Button-1>", lambda e, idx=i: self.select(idx))
 
            self.option_btns.append((row, badge, lbl))
 
        # submit button disabled until user pick an answer
        self.submit_btn = tk.Button(
            left, text="Submit Answer ✓",
            font=("Georgia", 11, "bold"),
            fg="white", bg=C["btn_disabled"],
            activebackground=C["btn"],
            relief="flat", bd=0, pady=9,
            cursor="hand2", state="disabled",
            command=self.submit
        )
        self.submit_btn.pack(fill="x", pady=(10, 0))
 
        # right side panel showing who has already answered
        right = tk.Frame(content, bg=C["sidebar"], width=160)
        right.pack(side="right", fill="y", padx=(14, 0))
        right.pack_propagate(False)
 
        tk.Label(right, text="answered",
                 font=("Georgia", 8, "bold"), fg=C["text_light"],
                 bg=C["sidebar"], pady=10).pack()
 
        self.answered_frame = tk.Frame(right, bg=C["sidebar"])
        self.answered_frame.pack(fill="x", padx=8)
 
        self.answered_labels = {}
 
        self.timer_val = data["time_limit"]
        self.timer_running = True
        self.root.after(1000, self.tick)
 
    def select(self, idx):
        if self.submitted:
            return
        self.selected = idx
 
        for i, (row, badge, lbl) in enumerate(self.option_btns):
            if i == idx:
                # highlight selected one
                row.configure(bg=C["option_sel"], highlightbackground=C["accent"])
                badge.configure(bg=C["accent"])
                lbl.configure(bg=C["option_sel"])
            else:
                row.configure(bg=C["option_bg"], highlightbackground=C["border"])
                badge.configure(bg=C["text_light"])
                lbl.configure(bg=C["option_bg"])
 
        self.submit_btn.configure(state="normal", bg=C["btn"])
 
    def submit(self):
        if self.selected == -1 or self.submitted:
            return
        self.submitted = True
        self.timer_running = False
        self.submit_btn.configure(state="disabled", text="Submitted ✓",
                                  bg=C["btn_disabled"])
        self.answer_event.set()
 
    def tick(self):
        if not self.timer_running:
            return
        self.timer_val -= 1
 
        # change color as time gets low
        color = C["red"] if self.timer_val <= 5 else (
                C["yellow"] if self.timer_val <= 8 else C["text_dark"])
        try:
            self.timer_lbl.configure(text=f"⏱ {self.timer_val}s", fg=color)
        except tk.TclError:
            return  
 
        if self.timer_val <= 0:
            # time's up then auto submit with no answer selected
            self.timer_running = False
            if not self.submitted:
                self.submitted = True
                self.answer_event.set()
        else:
            self.root.after(1000, self.tick)
 
    def mark_player_answered(self, name):
        try:
            row = tk.Frame(self.answered_frame, bg=C["sidebar"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text="✓", font=("Georgia", 9, "bold"),
                     fg=C["green"], bg=C["sidebar"]).pack(side="left")
            style = ("Georgia", 9, "bold") if name == self.my_name else ("Georgia", 9)
            tk.Label(row, text=name, font=style,
                     fg=C["text_dark"], bg=C["sidebar"]).pack(side="left", padx=4)
        except Exception:
            pass

    # RESULT SCREEN 
    def build_result(self, data):
        # show who got it right/wrong
        self.clear()
        self.timer_running = False
 
        correct_idx = data["correct_index"]
        correct_text = data["correct_text"]
        results = data.get("results", [])
        scoreboard = data.get("scoreboard", [])
 
        outer = tk.Frame(self.root, bg=C["bg"])
        outer.pack(fill="both", expand=True, padx=24, pady=16)
 
        left = tk.Frame(outer, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True)
 
        tk.Label(left, text="✅ Correct Answer",
                 font=("Georgia", 13, "bold"), fg=C["text_dark"],
                 bg=C["bg"]).pack(anchor="w", pady=(0, 6))
 
        # green box showing the correct answer
        ans_card = tk.Frame(left, bg=C["option_right"],
                            highlightbackground=C["green"],
                            highlightthickness=2)
        ans_card.pack(fill="x", pady=(0, 16))
        tk.Label(ans_card, text=f"  {chr(65+correct_idx)}.  {correct_text}",
                 font=("Georgia", 12, "bold"), fg=C["text_dark"],
                 bg=C["option_right"], anchor="w",
                 padx=14, pady=12).pack(fill="x")
 
        tk.Label(left, text="Results",
                 font=("Georgia", 10, "bold"), fg=C["text_mid"],
                 bg=C["bg"]).pack(anchor="w", pady=(0, 6))
 
        for r in results:
            row = tk.Frame(left, bg=C["option_right"] if r["correct"] else C["option_wrong"],
                           highlightbackground=C["border"], highlightthickness=1)
            row.pack(fill="x", pady=3)
            icon = "✓" if r["correct"] else "✗"
            icon_color = "#2E7D32" if r["correct"] else "#B71C1C"
            tk.Label(row, text=icon, font=("Georgia", 11, "bold"),
                     fg=icon_color, bg=row.cget("bg"),
                     width=3, pady=8).pack(side="left")
            style = ("Georgia", 10, "bold") if r["name"] == self.my_name else ("Georgia", 10)
            tk.Label(row, text=r["name"] + (" (you)" if r["name"] == self.my_name else ""),
                     font=style, fg=C["text_dark"],
                     bg=row.cget("bg")).pack(side="left")
 
        # scoreboard on the right side
        right = tk.Frame(outer, bg=C["sidebar"], width=200)
        right.pack(side="right", fill="y", padx=(18, 0))
        right.pack_propagate(False)
 
        tk.Label(right, text="🏆 Scoreboard",
                 font=("Georgia", 11, "bold"), fg=C["text_dark"],
                 bg=C["sidebar"], pady=12).pack()
 
        medals = ["🥇", "🥈", "🥉"] + ["🎮"] * 5
        for i, entry in enumerate(scoreboard):
            row = tk.Frame(right, bg=C["sidebar"])
            row.pack(fill="x", padx=10, pady=4)
            tk.Label(row, text=medals[i], font=("Georgia", 12),
                     bg=C["sidebar"]).pack(side="left")
            style = ("Georgia", 10, "bold") if entry["name"] == self.my_name else ("Georgia", 10)
            tk.Label(row, text=entry["name"],
                     font=style, fg=C["text_dark"],
                     bg=C["sidebar"]).pack(side="left", padx=6)
            tk.Label(row, text=str(entry["score"]),
                     font=("Georgia", 10, "bold"), fg=C["accent"],
                     bg=C["sidebar"]).pack(side="right")
 
        tk.Label(right, text="next question soon...",
                 font=("Georgia", 8, "italic"), fg=C["text_light"],
                 bg=C["sidebar"]).pack(side="bottom", pady=10)

    # GAME OVER SCREEN

    def build_game_over(self, data):
        self.clear()
 
        winner = data.get("winner", "")
        scoreboard = data.get("scoreboard", [])
        total = data.get("total_questions", 7)
        is_tie = data.get("is_tie", False)
 
        if is_tie:
            self.build_tie_screen(winner, scoreboard, total)
        elif winner == self.my_name:
            self.build_winner_screen(winner, scoreboard, total)
        else:
            self.build_loser_screen(winner, scoreboard, total)
 
    def build_tie_screen(self, tied_names, scoreboard, total):
        self.end_canvas = tk.Canvas(self.root, bg=C["bg"], highlightthickness=0)
        self.end_canvas.pack(fill="both", expand=True)
 
        frame = tk.Frame(self.end_canvas, bg=C["bg"])
        frame.place(relx=0.5, rely=0, anchor="n")
 
        tk.Label(frame, text="🤝", font=("Georgia", 54), bg=C["bg"]).pack(pady=(20, 0))
        tk.Label(frame, text="It's a Tie!", font=("Georgia", 28, "bold"),
                 fg=C["accent2"], bg=C["bg"]).pack()
        tk.Label(frame, text=f"A perfect match between {tied_names}",
                 font=("Georgia", 12, "italic"), fg=C["text_mid"],
                 bg=C["bg"], wraplength=500, justify="center").pack(pady=(6, 4))
        tk.Label(frame, text="Great minds think alike 🧠",
                 font=("Georgia", 11), fg=C["text_light"], bg=C["bg"]).pack(pady=(0, 18))
 
        self._scoreboard_rows(frame, scoreboard, total)
 
        tk.Button(frame, text="Play Again 🎯",
                  font=("Georgia", 12, "bold"),
                  fg="white", bg=C["accent2"],
                  activebackground="#B088CC",
                  relief="flat", bd=0,
                  padx=20, pady=10, cursor="hand2",
                  command=self.play_again).pack(pady=20)
 
    def build_winner_screen(self, winner, scoreboard, total):
        # winner gets confetti animation
        self.confetti_running = True
 
        self.end_canvas = tk.Canvas(self.root, bg=C["bg"], highlightthickness=0)
        self.end_canvas.pack(fill="both", expand=True)
 
        frame = tk.Frame(self.end_canvas, bg=C["bg"])
        frame.place(relx=0.5, rely=0, anchor="n")
        self.end_canvas.create_window((400, 10), window=frame, anchor="n")
 
        tk.Label(frame, text="🏆", font=("Georgia", 54), bg=C["bg"]).pack(pady=(20, 0))
        tk.Label(frame, text="You Won!", font=("Georgia", 28, "bold"),
                 fg=C["accent"], bg=C["bg"]).pack()
        tk.Label(frame, text=f"Congratulations {winner}! 🎉",
                 font=("Georgia", 13, "italic"), fg=C["text_mid"], bg=C["bg"]).pack(pady=(4, 18))
 
        self._scoreboard_rows(frame, scoreboard, total)
 
        tk.Button(frame, text="Play Again 🎯",
                  font=("Georgia", 12, "bold"),
                  fg="white", bg=C["btn"],
                  activebackground=C["btn_hover"],
                  relief="flat", bd=0,
                  padx=20, pady=10, cursor="hand2",
                  command=self.play_again).pack(pady=20)
 
        self.confetti_pieces = []
        self._spawn_confetti()
        self._animate_confetti()
 
    def build_loser_screen(self, winner, scoreboard, total):
        # loser gets a motivational message
        self.end_canvas = tk.Canvas(self.root, bg="#FFF0F5", highlightthickness=0)
        self.end_canvas.pack(fill="both", expand=True)
 
        frame = tk.Frame(self.end_canvas, bg=C["bg"])
        self.end_canvas.create_window((400, 10), window=frame, anchor="n")
 
        #give motivational message.
        import random
        messages = [
            ("💪", "Don't give up!", "You'll get them next time — keep grinding!"),
        ]
        emoji, title, subtitle = random.choice(messages)
 
        tk.Label(frame, text=emoji, font=("Georgia", 54), bg=C["bg"]).pack(pady=(20, 0))
        tk.Label(frame, text=title, font=("Georgia", 26, "bold"),
                 fg=C["accent2"], bg=C["bg"]).pack()
        tk.Label(frame, text=subtitle,
                 font=("Georgia", 12, "italic"), fg=C["text_mid"],
                 bg=C["bg"], wraplength=400, justify="center").pack(pady=(6, 4))
        tk.Label(frame, text=f"🏆 {winner} won this round",
                 font=("Georgia", 10), fg=C["text_light"], bg=C["bg"]).pack(pady=(0, 18))
 
        self._scoreboard_rows(frame, scoreboard, total)
 
        tk.Button(frame, text="Try Again 🔄",
                  font=("Georgia", 12, "bold"),
                  fg="white", bg=C["accent2"],
                  activebackground="#B088CC",
                  relief="flat", bd=0,
                  padx=20, pady=10, cursor="hand2",
                  command=self.play_again).pack(pady=20)
 
    def _scoreboard_rows(self, frame, scoreboard, total):
        # helper to draw the final scoreboard rows
        medals = ["🥇", "🥈", "🥉"] + ["🎮"] * 5
        for i, entry in enumerate(scoreboard):
            row = tk.Frame(frame, bg=C["card"],
                           highlightbackground=C["border"], highlightthickness=1)
            row.pack(fill="x", padx=100, pady=4, ipadx=10, ipady=8)
 
            tk.Label(row, text=medals[i], font=("Georgia", 14),
                     bg=C["card"]).pack(side="left", padx=10)
 
            is_me = entry["name"] == self.my_name
            style = ("Georgia", 12, "bold") if is_me else ("Georgia", 12)
            tk.Label(row, text=entry["name"] + (" ← you" if is_me else ""),
                     font=style, fg=C["text_dark"], bg=C["card"]).pack(side="left")
 
            pct = int(entry["score"] / total * 100)
            tk.Label(row, text=f"{entry['score']}/{total}  ({pct}%)",
                     font=("Georgia", 11, "bold"), fg=C["accent"],
                     bg=C["card"]).pack(side="right", padx=10)
 
    def _spawn_confetti(self):
        # create 60 confetti pieces at random positions along the top
        import random
        colors = ["#FF85A1", "#FFD6E7", "#C9A0DC", "#A8E6CF",
                  "#FFE0A0", "#B5DEFF", "#FFB3C6", "#C8F5D8"]
        self.confetti_pieces = []
        for _ in range(60):
            x = random.randint(0, 800)
            y = random.randint(-200, -10)   # start above the screen
            w = random.randint(8, 16)
            h = random.randint(5, 10)
            color = random.choice(colors)
            speed = random.uniform(2, 5)    # falling speed
            drift = random.uniform(-1.5, 1.5)  # horizontal drift
            spin = random.choice([-1, 1])   # which way it rotates
            shape_id = self.end_canvas.create_rectangle(
                x, y, x+w, y+h, fill=color, outline=""
            )
            self.confetti_pieces.append({
                "id": shape_id, "x": x, "y": y,
                "w": w, "h": h, "speed": speed,
                "drift": drift, "spin": spin
            })
 
    def _animate_confetti(self):
        # move each confetti piece down a little each frame
        if not self.confetti_running:
            return
        try:
            import random
            for p in self.confetti_pieces:
                p["y"] += p["speed"]
                p["x"] += p["drift"]

                if p["y"] > 600:
                    p["y"] = random.randint(-100, -10)
                    p["x"] = random.randint(0, 800)
                self.end_canvas.coords(
                    p["id"],
                    p["x"], p["y"],
                    p["x"] + p["w"], p["y"] + p["h"]
                )
            self.root.after(33, self._animate_confetti)
        except Exception:
            pass  
 
    # NETWORKING
    def connect(self):
        name = self.name_var.get().strip()
        ip   = self.ip_var.get().strip()
        if not name:
            self.status.configure(text="Please enter your name.")
            return
        if not ip:
            self.status.configure(text="Please enter a server IP.")
            return
        self.my_name = name
        self.status.configure(text="Connecting...")
        threading.Thread(target=self.net_loop, args=(ip, name), daemon=True).start()
 
    def net_send(self, d):
        try:
            self.sock.sendall((json.dumps(d) + "\n").encode())
        except Exception:
            pass
 
    def net_recv(self):
        try:
            data = b""
            while True:
                c = self.sock.recv(1)
                if not c:
                    return None
                if c == b"\n":
                    break
                data += c
            return json.loads(data.decode())
        except Exception:
            return None
 
    def net_loop(self, ip, name):
        # this runs in a background thread so the GUI doesn't freeze
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(8)
            self.sock.connect((ip, SERVER_PORT))
            self.sock.settimeout(None)
 
            # send the initial connect message
            self.net_send({"type": "connect"})
 
            # now just listen for messages from the server and react
            while True:
                msg = self.net_recv()
                if msg is None:
                    self.root.after(0, lambda: self._err("Disconnected from server."))
                    break
 
                t = msg.get("type")
 
                if t == "request_name":
                    self.net_send({"type": "name", "name": name})
 
                elif t == "rejected":
                    self.root.after(0, lambda m=msg: self._err(m.get("message", "Rejected.")))
                    break
 
                elif t == "lobby":
                    self.root.after(0, lambda m=msg: self.build_lobby(m))
 
                elif t == "player_joined":
                    # update player list in lobby when someone new joins
                    self.root.after(0, lambda m=msg: (
                        self.update_lobby_players(m.get("players", []))
                        if hasattr(self, "lobby_players_frame") else None
                    ))
 
                elif t == "player_left":
                    self.root.after(0, lambda m=msg: (
                        self.update_lobby_players(m.get("players", []))
                        if hasattr(self, "lobby_players_frame") else None
                    ))
 
                elif t == "countdown":
                    c = msg.get("count")
                    self.root.after(0, lambda n=c: self.build_countdown(n))
 
                elif t == "game_start":
                    self.root.after(0, lambda m=msg: self._show_starting(m))
 
                elif t == "question":
                    # new question coming 
                    self.answer_event.clear()
                    self.selected = -1
                    self.root.after(0, lambda m=msg: self.build_question(m))
 
                    # block here until the player submits or timer runs out
                    self.answer_event.wait()
 
                    # send whatever they picked to the server
                    self.net_send({"type": "answer", "answer": self.selected})
 
                elif t == "player_answered":
                    # someone else answered show checkmark in sidebar
                    answered_name = msg.get("name")
                    self.root.after(0, lambda n=answered_name: self.mark_player_answered(n))
 
                elif t == "question_result":
                    self.root.after(0, lambda m=msg: self.build_result(m))
 
                elif t == "game_over":
                    self.root.after(0, lambda m=msg: self.build_game_over(m))
                    break
 
        except ConnectionRefusedError:
            self.root.after(0, lambda: self._err("Connection refused. Is the server running?"))
        except socket.timeout:
            self.root.after(0, lambda: self._err("Connection timed out."))
        except Exception as e:
            self.root.after(0, lambda: self._err(f"Error: {e}"))
        finally:
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
 
    def _show_starting(self, data):
        # brief screen between countdown and first question
        self.clear()
        f = tk.Frame(self.root, bg=C["bg"])
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="🎯", font=("Georgia", 48), bg=C["bg"]).pack()
        tk.Label(f, text=data.get("message", "Game starting!"),
                 font=("Georgia", 16, "bold"), fg=C["accent"], bg=C["bg"]).pack(pady=8)
 
    def _err(self, msg):
        self.build_login()
        self.status.configure(text=msg)
 
    def play_again(self):
        # stop confetti if it was running
        self.confetti_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.build_login()
 
    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()
 
 
if __name__ == "__main__":
    root = tk.Tk()
    app = QuizClient(root)
    root.mainloop()