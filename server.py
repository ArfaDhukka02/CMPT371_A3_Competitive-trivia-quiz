# CMPT 371 - Assignment 3
# File: server.py
# This is the server side of our multiplayer quiz game.
# This server handles all the game logic - it picks the questions,
# keeps track of scores, and makes sure everyone gets the same questions
# at the same time. Uses TCP sockets and threading.
 
import socket
import threading
import json
import time
import random
import queue
 
# server will listen on all interfaces, port 5050
HOST = '0.0.0.0'
PORT = 5050

MIN_PLAYERS        = 2   # need at least 2 people to start
MAX_PLAYERS        = 8   # don't want too many people at once
QUESTIONS_PER_GAME = 7   # how many questions each round
TIME_PER_QUESTION  = 15  # seconds per question
 
# all questions
ALL_QUESTIONS = [
    {
        "question": "What does HTTP stand for?",
        "options": ["HyperText Transfer Protocol", "High Transfer Text Protocol",
                    "Hyperlink Text Transfer Process", "Host Transfer Text Protocol"],
        "answer": 0
    },
    {
        "question": "Which layer of the OSI model handles routing?",
        "options": ["Data Link", "Transport", "Network", "Session"],
        "answer": 2
    },
    {
        "question": "What port does HTTPS use by default?",
        "options": ["80", "8080", "443", "22"],
        "answer": 2
    },
    {
        "question": "Which protocol is connection-oriented?",
        "options": ["UDP", "ICMP", "TCP", "ARP"],
        "answer": 2
    },
    {
        "question": "What does DNS stand for?",
        "options": ["Dynamic Network System", "Domain Name System",
                    "Data Network Service", "Digital Naming Structure"],
        "answer": 1
    },
    {
        "question": "Which device connects different networks together?",
        "options": ["Switch", "Hub", "Repeater", "Router"],
        "answer": 3
    },
    {
        "question": "What is the maximum segment size in TCP called?",
        "options": ["MTU", "MSS", "MFS", "MPS"],
        "answer": 1
    },
    {
        "question": "Which protocol assigns IP addresses automatically?",
        "options": ["FTP", "SMTP", "DHCP", "ARP"],
        "answer": 2
    },
    {
        "question": "What does IP stand for?",
        "options": ["Internal Protocol", "Internet Protocol",
                    "Integrated Process", "Interface Port"],
        "answer": 1
    },
    {
        "question": "How many bits are in an IPv4 address?",
        "options": ["16", "64", "128", "32"],
        "answer": 3
    },
    {
        "question": "Which protocol sends email?",
        "options": ["POP3", "IMAP", "SMTP", "FTP"],
        "answer": 2
    },
    {
        "question": "What is a subnet mask used for?",
        "options": ["Encrypting data",
                    "Dividing IP addresses into network and host parts",
                    "Assigning MAC addresses",
                    "Routing packets between continents"],
        "answer": 1
    },
    {
        "question": "Which of the following is a private IP address?",
        "options": ["8.8.8.8", "172.16.0.1", "200.100.50.25", "54.240.196.1"],
        "answer": 1
    },
    {
        "question": "At which OSI layer does a switch operate?",
        "options": ["Layer 1", "Layer 3", "Layer 2", "Layer 4"],
        "answer": 2
    },
    {
        "question": "What is the purpose of TCP's three-way handshake?",
        "options": ["To encrypt data", "To establish a reliable connection",
                    "To transfer files", "To assign IP addresses"],
        "answer": 1
    },
]
 
# these are the game states so we know what phase we're in
STATE_LOBBY    = "lobby"     # waiting for players
STATE_STARTING = "starting"  # countdown happening
STATE_QUESTION = "question"  # question is active right now
STATE_REVIEW   = "review"    # showing the answer between questions
STATE_FINISHED = "finished"  # game is done
 
 
class QuizServer:
 
    def __init__(self):
        self.clients = {}
 
        # lock to avoid race conditions when multiple threads access self.clients
        self.lock = threading.Lock()
 
        # matchmaking queue which makes players sit here until we have enough to start
        # once MIN_PLAYERS are in the queue, we launch the game thread
        self.matchmaking_queue = queue.Queue()
 
        # track what phase the game is in
        self.state = STATE_LOBBY
 
        self.questions = []
        self.current_q_index = -1
 
        # count how many players answered the current question
        self.answers_received = 0
 
        # this event fires when everyone has answered so we don't have to wait for the full timer
        self.all_answered_event = threading.Event()
 
        self.question_timer = None
 
    def send(self, sock, data):
        try:
            sock.sendall((json.dumps(data) + "\n").encode())
        except Exception:
            pass 
 
    # send a message to every connected client
    def broadcast(self, data, exclude=None):
        with self.lock:
            targets = list(self.clients.keys())
        for sock in targets:
            if sock != exclude:
                self.send(sock, data)

    def recv(self, sock):
        try:
            data = b""
            while True:
                chunk = sock.recv(1)
                if not chunk:
                    return None  # connection closed
                if chunk == b"\n":
                    break
                data += chunk
            return json.loads(data.decode())
        except Exception:
            return None
 
    # returns a sorted leaderboard list (highest score first)
    def get_scoreboard(self):
        with self.lock:
            board = [
                {"name": v["name"], "score": v["score"]}
                for v in self.clients.values()
            ]
        board.sort(key=lambda x: x["score"], reverse=True)
        return board
 
    # just returns a list of player names currently connected
    def get_player_names(self):
        with self.lock:
            return [v["name"] for v in self.clients.values()]
 
    def player_count(self):
        with self.lock:
            return len(self.clients)
 
    def handle_client(self, sock, address):
        name = None
        try:
            connect_msg = self.recv(sock)
            if not connect_msg or connect_msg.get("type") != "connect":
                print(f"[SERVER] bad handshake from {address}, closing connection")
                sock.close()
                return
 
            print(f"[SERVER] handshake ok from {address}")
 
            # ask their name
            self.send(sock, {"type": "request_name"})
            msg = self.recv(sock)
            if not msg or msg.get("type") != "name":
                sock.close()
                return
 
            name = msg.get("name", "Player").strip() or "Player"
 
            # register the player - need the lock here because multiple threads
            # could be trying to register at the same time
            with self.lock:
                # if a game is already running don't let anyone in
                if self.state != STATE_LOBBY:
                    self.send(sock, {
                        "type": "rejected",
                        "message": "A game is already in progress. Please wait."
                    })
                    sock.close()
                    return
 
                # reject if lobby is full
                if len(self.clients) >= MAX_PLAYERS:
                    self.send(sock, {
                        "type": "rejected",
                        "message": "Lobby is full!"
                    })
                    sock.close()
                    return
                
                self.clients[sock] = {
                    "name": name,
                    "score": 0,
                    "answered": False,
                    "answer": -1
                }
 
            print(f"[SERVER] '{name}' joined from {address}")
 
            # put in the matchmaking queue
            self.matchmaking_queue.put(sock)
            print(f"[SERVER] '{name}' in matchmaking queue (size: {self.matchmaking_queue.qsize()})")
 
            # send the lobby screen with the current player list
            self.send(sock, {
                "type": "lobby",
                "message": f"Welcome {name}! Waiting for players...",
                "players": self.get_player_names(),
                "min_players": MIN_PLAYERS
            })
 
            self.broadcast({
                "type": "player_joined",
                "name": name,
                "players": self.get_player_names(),
                "count": self.player_count(),
                "min_players": MIN_PLAYERS
            }, exclude=sock)
 
            # if we have enough players now, kick off the game thread
            if self.matchmaking_queue.qsize() >= MIN_PLAYERS and self.state == STATE_LOBBY:
                threading.Thread(target=self.run_game, daemon=True).start()
 
            # keep listening for answers while the game is running
            while True:
                msg = self.recv(sock)
                if msg is None:
                    break  
 
                # only process answers when a question is actually active
                if msg.get("type") == "answer" and self.state == STATE_QUESTION:
                    self.handle_answer(sock, msg.get("answer", -1))
 
        except Exception as e:
            print(f"[SERVER] error handling '{name}': {e}")
        finally:
            with self.lock:
                if sock in self.clients:
                    del self.clients[sock]
            sock.close()
            if name:
                print(f"[SERVER] '{name}' disconnected")
                self.broadcast({
                    "type": "player_left",
                    "name": name,
                    "players": self.get_player_names()
                })
                # if someone leaves mid-question check if everyone else already answered
                if self.state == STATE_QUESTION:
                    self.check_all_answered()
 
    # called when a player submits an answer
    def handle_answer(self, sock, answer_index):
        with self.lock:
            if sock not in self.clients:
                return
            player = self.clients[sock]
 
            # ignore if they already answered avoid double submit
            if player["answered"]:
                return
 
            player["answered"] = True
            player["answer"] = answer_index
            self.answers_received += 1
            name = player["name"]
 
        print(f"[SERVER] '{name}' answered: {answer_index}")
 
        # tell everyone this person answered
        self.broadcast({
            "type": "player_answered",
            "name": name,
            "answers_in": self.answers_received,
            "total_players": self.player_count()
        })
 
        # check if everyone's done so we can move to results
        self.check_all_answered()
 
    #if all players have answered no need to wait for timer
    def check_all_answered(self):
        with self.lock:
            total = len(self.clients)
            answered = sum(1 for p in self.clients.values() if p["answered"])
 
        if total > 0 and answered >= total:
            self.all_answered_event.set()
 
    # main game loop
    # handles the whole flow: countdown, questions, results
    def run_game(self):
        # send a 3-2-1 countdown to everyone
        self.state = STATE_STARTING
        for i in range(3, 0, -1):
            self.broadcast({
                "type": "countdown",
                "count": i,
                "message": f"Game starts in {i}..."
            })
            time.sleep(1)
 
        # pick the questions randomly same set for all players
        self.questions = random.sample(ALL_QUESTIONS, QUESTIONS_PER_GAME)
 
        self.broadcast({
            "type": "game_start",
            "total_questions": QUESTIONS_PER_GAME,
            "message": "Game started! Good luck!"
        })
        time.sleep(0.5)
 
        # loop through each question
        for q_index, q_data in enumerate(self.questions):
            self.current_q_index = q_index
            self.state = STATE_QUESTION
            self.answers_received = 0
            self.all_answered_event.clear()
 
            with self.lock:
                for player in self.clients.values():
                    player["answered"] = False
                    player["answer"] = -1
 
            # broadcast the question to all players at the same time
            self.broadcast({
                "type": "question",
                "number": q_index + 1,
                "total": QUESTIONS_PER_GAME,
                "question": q_data["question"],
                "options": q_data["options"],
                "time_limit": TIME_PER_QUESTION
            })
 
            # wait for all answers or until time runs out
            self.all_answered_event.wait(timeout=TIME_PER_QUESTION)
 
            # grade everyone's answers
            self.state = STATE_REVIEW
            correct_index = q_data["answer"]
            correct_text = q_data["options"][correct_index]
 
            results = []
            with self.lock:
                for sock, player in self.clients.items():
                    chose = player["answer"]
                    is_correct = (chose == correct_index)
                    if is_correct:
                        player["score"] += 1 
                    results.append({
                        "name": player["name"],
                        "correct": is_correct,
                        "score": player["score"]
                    })
 
            results.sort(key=lambda x: x["score"], reverse=True)
 
            # send the answer reveal and also show current scores to everyone
            self.broadcast({
                "type": "question_result",
                "correct_index": correct_index,
                "correct_text": correct_text,
                "results": results,
                "scoreboard": self.get_scoreboard()
            })
 
            # pause before the next question
            time.sleep(1)
 
        # all done, send final results
        self.state = STATE_FINISHED
        final_board = self.get_scoreboard()
 
        # check if there's a tie at the top (multiple players with same highest score)
        is_tie = (
            len(final_board) > 1 and
            final_board[0]["score"] == final_board[1]["score"]
        )
 
        if is_tie:
            top_score = final_board[0]["score"]
            tied_names = [p["name"] for p in final_board if p["score"] == top_score]
            winner = ", ".join(tied_names)
            print(f"[SERVER] game over! it's a tie between: {winner}")
        else:
            winner = final_board[0]["name"] if final_board else "Nobody"
            print(f"[SERVER] game over! winner: {winner}")
 
        self.broadcast({
            "type": "game_over",
            "scoreboard": final_board,
            "winner": winner,
            "is_tie": is_tie,
            "total_questions": QUESTIONS_PER_GAME,
            "message": f"It's a tie!" if is_tie else f"{winner} wins!"
        })
 
        # reset after a few seconds so people can play again
        time.sleep(5)
        self.state = STATE_LOBBY
        self.current_q_index = -1
        print("[SERVER] lobby reset, ready for new game")
 
    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
 
        server_socket.bind((HOST, PORT))
        server_socket.listen(MAX_PLAYERS)
        print(f"[SERVER] quiz server started on {HOST}:{PORT}")
        print(f"[SERVER] waiting for {MIN_PLAYERS}+ players...")
 
        try:
            while True:
                sock, address = server_socket.accept()
                threading.Thread(
                    target=self.handle_client,
                    args=(sock, address),
                    daemon=True
                ).start()
        except KeyboardInterrupt:
            print("\n[SERVER] shutting down...")
        finally:
            server_socket.close()
 
 
if __name__ == "__main__":
    server = QuizServer()
    server.start()