import socket
import threading
import time
import pytest

# Dieses Testfile demonstriert, wie man gegen einen einfachen TCP-Stub testet,
# der dem Tetris-Server-Protokoll (wie im Notebook) entspricht.
#
# Falls deine `TetrisEnv`-Klasse in ein importierbares Python-Modul extrahiert wurde
# (z.B. in `tetris_env.py`), dann wird der Integrationstest durchlaufen.
# Andernfalls wird der Test übersprungen und du kannst die Unit-Tests (z.B. test_reward)
# trotzdem ausführen.

try:
    from tetris_env import TetrisEnv  # Wenn du die Klasse exportiert hast
except Exception:
    TetrisEnv = None

PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\nIDATx\x9cc``\x00\x00\x00\x02\x00\x01\xe2'\xbc\x9c\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _stub_server(port, n_responses=5):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port))
    s.listen(1)
    conn, _ = s.accept()
    try:
        for _ in range(n_responses):
            data = b""
            # read until newline (simple protocol assumption)
            while not data.endswith(b"\n"):
                chunk = conn.recv(1024)
                if not chunk:
                    break
                data += chunk
            # reply with: 1 byte is_game_over, 4 bytes lines, 4 bytes height, 4 bytes holes, 4 bytes img_size, img
            resp = b"\x00"  # game not over
            resp += (0).to_bytes(4, 'big')  # removed lines
            resp += (1).to_bytes(4, 'big')  # height
            resp += (0).to_bytes(4, 'big')  # holes
            img = PNG_1x1
            resp += len(img).to_bytes(4, 'big')
            resp += img
            conn.sendall(resp)
    finally:
        conn.close()
        s.close()


@pytest.mark.skipif(TetrisEnv is None, reason="TetrisEnv not importable; extract class into tetris_env.py to run integration test")
def test_tetrisenv_with_stub():
    port = 10613
    t = threading.Thread(target=_stub_server, args=(port,), daemon=True)
    t.start()
    time.sleep(0.1)

    env = TetrisEnv(host_ip='127.0.0.1', host_port=port)
    obs, info = env.reset()
    assert hasattr(obs, 'shape')
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    assert isinstance(reward, (int, float))
    env.close()
