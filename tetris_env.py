import numpy as np
import socket
import cv2
import gymnasium as gym
from gymnasium import spaces


class TetrisEnv(gym.Env):
    """
    Gymnasium Umgebung für Tetris.
    Kommuniziert mit dem Java Tetris Server über TCP/IP.
    """

    metadata = {"render_modes": ["human"], "render_fps": 20}

    # Spielfeldparameter (anpassbar)
    N_DISCRETE_ACTIONS = 5  # 5 mögliche Aktionen
    IMG_HEIGHT = 200        # Höhe des Spielfeldbildes
    IMG_WIDTH = 100         # Breite des Spielfeldbildes
    IMG_CHANNELS = 3        # RGB-Kanäle

    def __init__(self, host_ip="127.0.0.1", host_port=10612, timeout=5.0):
        """Initialisiert die Tetris Umgebung."""
        super().__init__()

        # Definiere Action Space (5 diskrete Aktionen)
        self.action_space = spaces.Discrete(self.N_DISCRETE_ACTIONS)

        # Definiere Observation Space (Spielfeldbilder)
        self.observation_space = spaces.Box(
            low=0, high=255,
            shape=(self.IMG_HEIGHT, self.IMG_WIDTH, self.IMG_CHANNELS),
            dtype=np.uint8
        )

        # Verbinde dich mit dem Server
        self.server_ip = host_ip
        self.server_port = host_port
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_sock.settimeout(timeout)
        self.client_sock.connect((self.server_ip, self.server_port))

        # interne Variablen
        self.observation = np.zeros((self.IMG_HEIGHT, self.IMG_WIDTH, self.IMG_CHANNELS), dtype=np.uint8)
        self.reward = 0
        self.lines_removed = 0
        self.holes = 0
        self.height = 0
        self.lifetime = 0

    def step(self, action):
        """
        Führe eine Aktion aus und erhalte das Spielergebnis.
        Returns: observation, reward, terminated, truncated, info
        """
        # Sende die Aktion an den Server
        if action == 0:
            self.client_sock.sendall(b"move -1\n")  # Links
        elif action == 1:
            self.client_sock.sendall(b"move 1\n")   # Rechts
        elif action == 2:
            self.client_sock.sendall(b"rotate 0\n") # Gegen Uhrzeigersinn
        elif action == 3:
            self.client_sock.sendall(b"rotate 1\n") # Im Uhrzeigersinn
        elif action == 4:
            self.client_sock.sendall(b"drop\n")     # Fallen lassen

        # Erhalte die Antwort vom Server
        terminated, lines, height, holes, observation = self.get_tetris_server_response(self.client_sock)
        self.observation = observation

        # Berechne die Belohnung basierend auf dem Spielzustand
        reward = 0

        # Belohne das Fallen von Blöcken
        if action == 4:
            reward += 5

        # Bestrafe Höhenzunahme
        if height > self.height:
            reward -= (height - self.height) * 5

        # Belohne Lochreduktion
        if holes < self.holes:
            reward += (self.holes - holes) * 10

        # Große Belohnung für vollständige Reihen
        if lines > self.lines_removed:
            reward = reward + (lines - self.lines_removed) * 1000
            self.lines_removed = lines

        # Aktualisiere den internen Zustand
        self.holes = holes
        self.height = height
        self.lifetime += 1
        truncated = False

        info = {
            'removed_lines': self.lines_removed,
            'lifetime': self.lifetime,
            'height': self.height,
            'holes': self.holes,
        }

        return (observation, float(reward), bool(terminated), bool(truncated), info)

    def reset(self, seed=None, options=None):
        """Setze die Umgebung zurück für ein neues Spiel."""
        self.client_sock.sendall(b"start\n")
        terminated, lines, height, holes, observation = self.get_tetris_server_response(self.client_sock)

        # Initialisiere Spielvariablen
        self.observation = observation
        self.reward = 0
        self.lines_removed = 0
        self.holes = 0
        self.height = 0
        self.lifetime = 0
        info = {}

        return observation, info

    def render(self):
        """Optional: Zeige das Spiel an."""
        pass

    def close(self):
        """Schließe die Verbindung zum Server."""
        try:
            self.client_sock.close()
        except Exception:
            pass

    def _recv_all(self, sock, n):
        data = b''
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError('Socket closed while receiving')
            data += chunk
        return data

    def get_tetris_server_response(self, sock):
        """Lese die Antwort vom Tetris Server im vereinbarten Protokoll."""
        # 1 byte: is_game_over
        b = self._recv_all(sock, 1)
        is_game_over = (b == b'\x01')
        removed_lines = int.from_bytes(self._recv_all(sock, 4), 'big')
        height = int.from_bytes(self._recv_all(sock, 4), 'big')
        holes = int.from_bytes(self._recv_all(sock, 4), 'big')
        img_size = int.from_bytes(self._recv_all(sock, 4), 'big')
        img_png = self._recv_all(sock, img_size)

        # Dekodiere das PNG-Bild
        nparr = np.frombuffer(img_png, np.uint8)
        np_image = cv2.imdecode(nparr, -1)

        return is_game_over, removed_lines, height, holes, np_image
