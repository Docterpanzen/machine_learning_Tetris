import numpy as np

# Kleine, testbare Implementierung der Reward-Logik aus dem Notebook.
# In deinem Projekt ist die Logik in `TetrisEnv.step()` implementiert;
# es ist sinnvoll, diese Logik in eine separate Funktion zu extrahieren
# (z.B. tetris_env.compute_reward) und hier zu importieren.

def compute_reward(action, prev_state, new_state, lines_removed_prev):
    reward = 0
    if action == 4:
        reward += 5
    # Strafe für Höhenzunahme
    if new_state['height'] > prev_state['height']:
        reward -= (new_state['height'] - prev_state['height']) * 5
    # Belohnung für Lochreduktion
    if new_state['holes'] < prev_state['holes']:
        reward += (prev_state['holes'] - new_state['holes']) * 10
    # Bonus für gelöschte Reihen
    if new_state['lines'] > lines_removed_prev:
        reward += (new_state['lines'] - lines_removed_prev) * 1000
    return reward


def test_reward_drop_and_line_clear():
    prev = {'height': 5, 'holes': 3}
    new = {'height': 5, 'holes': 2, 'lines': 3}
    r = compute_reward(action=4, prev_state=prev, new_state=new, lines_removed_prev=2)
    assert r >= 1005  # +5 for drop and +1000 for one cleared line


def test_reward_height_increase_penalty():
    prev = {'height': 5, 'holes': 2}
    new = {'height': 7, 'holes': 2, 'lines': 2}
    r = compute_reward(action=0, prev_state=prev, new_state=new, lines_removed_prev=2)
    assert r == -(7 - 5) * 5


def test_reward_hole_reduction_bonus():
    prev = {'height': 5, 'holes': 4}
    new = {'height': 5, 'holes': 1, 'lines': 2}
    r = compute_reward(action=1, prev_state=prev, new_state=new, lines_removed_prev=2)
    assert r == (4 - 1) * 10
