#CMPT 371 A3 Socket Programming — Competitive Trivia Quiz
Course: CMPT 371 - Data Communications & Networking
Instructor: Mirza Zaeem Baig
Semester: Spring 2026

Group Members
NameStudent IDEmail[ARFA DHUKKA][301563496][ada144@sfu.ca]

1. Project Overview & Description
This project is a synchronized multiplayer trivia quiz game built using Python's Socket API (TCP). Multiple players connect to a central server, enter a matchmaking lobby, and compete against each other in real time. The server handles all game logic — it picks the questions, keeps track of scores, and broadcasts the same questions to all players simultaneously so no one has an advantage. After each question the server reveals the correct answer and sends the updated scoreboard to everyone. At the end the player with the most correct answers wins.
The GUI is built with Tkinter and includes a lobby screen, live "who answered" sidebar, per-question result screen, and a final winner/loser/tie screen.

2. System Limitations & Edge Cases
As required by the project specifications, we identified the following limitations and potential issues:
No mid-game join:
Once a game is in progress the server rejects new connections until the current game finishes and the lobby resets. A player trying to join mid-game will see a "game already in progress" message.
No reconnection support:
If a player disconnects mid-game their slot is removed. The remaining players continue but the disconnected player cannot rejoin the same session.
TCP Stream Buffering:
TCP is a continuous byte stream so multiple JSON messages can arrive together. We fixed this at the application layer by appending a newline \n to every JSON payload and reading byte by byte until the delimiter is found, so messages are always processed one at a time.
Timer synchronization:
The visual countdown runs on the client side. The server uses its own hard timeout as a backup. If there is high network latency these two may be slightly off — the server timeout is what actually ends the question.
LAN only:
The server binds to a local address. Playing over the internet would require port forwarding or a VPN which is outside the scope of this project.
Scalability:
One thread is created per client using Python's threading module. This works fine for a small number of players but for a large scale deployment a thread pool or async I/O would be needed.

3. Video Demo
It is in the Git repo you can download and watch it.

4. Prerequisites (Fresh Environment)
To run this project you need:

Python 3.8 or higher
No external pip installations required — uses standard library only (socket, threading, json, tkinter, time, random, queue)

A requirements.txt is included for completeness and lists the standard library modules used.

To verify Python is installed:
python --version
If Python is not installed download it from https://python.org/downloads


To verify tkinter works:
python -c "import tkinter; print('tkinter OK')"
If tkinter is missing:

macOS: brew install python-tk
Ubuntu/Debian: sudo apt-get install python3-tk
Windows: reinstall Python and make sure the tcl/tk option is selected

5. Step-by-Step Run Guide

Step 1: Start the Server
Open a terminal, navigate to the project folder, and run:
python server.py
Expected output:
[SERVER] quiz server started on 0.0.0.0:5050
[SERVER] waiting for 2+ players...
Keep this terminal open the whole time. If you close it the game stops.
Step 2: Connect Player 1
Open a new terminal window (keep the server running) and run:
python client.py
A GUI window will open. Enter:

Server IP: 127.0.0.1 (same machine) or the host's IP on a shared network
Name: anything you want
Click Join Game

Expected: lobby screen appears showing 1 player connected, waiting for more.
Step 3: Connect Player 2
Open a third terminal window and run:
python client.py
Enter the same server IP and a different name, click Join Game.
Expected: both screens show the lobby updating, then a 3-2-1 countdown fires automatically and the game begins.
Step 4: Gameplay

Both players see the same question and 4 answer options
Click an option to select it, then click Submit Answer
A checkmark appears on the other player's screen when you answer
After both answer (or timer runs out) the correct answer is revealed and the scoreboard updates
This repeats for 7 questions

Step 5: Game End
After all questions are done:

Winner sees a confetti screen
Loser sees a motivational message
If scores are equal both see a tie screen

Close the client windows and press Ctrl+C in the server terminal to stop the server.
Running on different computers (same WiFi):
Find the server machine's local IP:

Windows: ipconfig → look for IPv4 Address
macOS/Linux: ifconfig | grep "inet "

Other players enter that IP in the Server IP field instead of 127.0.0.1.

6. Technical Protocol Details (JSON over TCP)
We designed a custom application-layer protocol using JSON over TCP:
Message Format: {"type": <string>, ...fields}
PhaseDirectionTypeDescriptionHandshakeClient → ServerconnectClient initiates contactHandshakeServer → Clientrequest_nameServer asks for player nameHandshakeClient → ServernamePlayer sends their nameLobbyServer → ClientlobbyWelcome message + player listLobbyServer → Clientplayer_joinedSomeone new joinedGameServer → Clientcountdown3-2-1 before game startsGameServer → ClientquestionQuestion text + 4 options + timerGameClient → ServeranswerPlayer's selected option index (0-3)GameServer → Clientplayer_answeredSomeone answered (answer not revealed)GameServer → Clientquestion_resultCorrect answer + updated scoreboardEndServer → Clientgame_overFinal scores + winner + is_tie flag

7. Academic Integrity & References
Code Origin:
The socket boilerplate structure was inspired by the course TA tutorial on TCP socket programming. The game logic, matchmaking queue, synchronized question flow, scoring system, and GUI were written by me.
GenAI Usage:
- Claude AI was used to assist in building and debugging the Tkinter GUI frontend and to help structure the JSON messaging protocol.
- Claude was used to add comments in the code for explanation.
- Chatgpt was used to help plan the workflow of the application.
- Chatgpt helped in README.md writing and polishing.
References:

Python Socket Programming HOWTO — https://docs.python.org/3/howto/sockets.html
Python Threading Documentation — https://docs.python.org/3/library/threading.html
Course TA Tutorial — Multiplayer Socket Programming https://youtube.com/playlist?list=PL-8C2cUhmkO1yWLTCiqf4mFXId73phvdx&si=FIq3OxypbBeWHhYm (CMPT 371 Canvas)
