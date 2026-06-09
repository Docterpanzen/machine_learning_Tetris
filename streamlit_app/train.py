import argparse
import json
import os
import sys
import time

import imageio
import numpy as np
from stable_baselines3 import A2C
from stable_baselines3.common.env_util import make_vec_env

# Ensure project root is on sys.path so imports like `tetris_env` work
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tetris_env import TetrisEnv


RUNS_DIR = os.path.join(PROJECT_ROOT, 'training_runs')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
GIFS_DIR = os.path.join(PROJECT_ROOT, 'gifs')


def ensure_dirs():
    os.makedirs(RUNS_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(GIFS_DIR, exist_ok=True)


def normalize_frame(frame):
    array = np.asarray(frame)
    if array.ndim == 3 and array.shape[0] in (1, 3) and array.shape[-1] not in (1, 3):
        array = np.transpose(array, (1, 2, 0))
    if array.dtype != np.uint8:
        array = np.clip(array, 0, 255).astype(np.uint8)
    return array


def rollout_to_gif(model, vec_env, gif_path, max_steps=200):
    obs = vec_env.reset()
    frames = []
    for _ in range(max_steps):
        action, _ = model.predict(obs, deterministic=True)
        obs, _, _, _ = vec_env.step(action)
        frame = obs[0]
        if frame is None:
            continue
        frames.append(normalize_frame(frame))
    if frames:
        imageio.mimsave(gif_path, frames, loop=0, duration=0.05)


def load_base_timesteps(resume_from: str | None):
    if not resume_from:
        return 0
    summary_path = os.path.join(RUNS_DIR, resume_from, 'summary.json')
    if not os.path.exists(summary_path):
        return 0
    try:
        with open(summary_path, 'r', encoding='utf-8') as handle:
            summary = json.load(handle)
        return int(summary.get('final_timesteps', summary.get('timesteps', 0)) or 0)
    except Exception:
        return 0


def train(name: str, timesteps: int, n_envs: int, logdir: str, resume_from: str | None = None):
    ensure_dirs()

    started_at = time.time()
    run_dir = os.path.join(RUNS_DIR, name)
    os.makedirs(run_dir, exist_ok=True)

    vec_env = make_vec_env(TetrisEnv, n_envs=n_envs)

    resume_model_path = None
    base_timesteps = load_base_timesteps(resume_from)
    if resume_from:
        candidate = os.path.join(MODELS_DIR, f'{resume_from}.zip')
        if os.path.exists(candidate):
            resume_model_path = candidate
        elif os.path.exists(resume_from):
            resume_model_path = resume_from

    if resume_model_path:
        print(f"↻ Lade Modell zum Weitertrainieren: {resume_model_path}")
        model = A2C.load(resume_model_path, env=vec_env)
    else:
        print('Erstelle A2C Modell mit CNN Policy...')
        model = A2C('CnnPolicy', vec_env, verbose=1, tensorboard_log=logdir)

    first_gif_path = os.path.join(GIFS_DIR, f'{name}_first.gif')
    last_gif_path = os.path.join(GIFS_DIR, f'{name}_last.gif')

    print('Erstelle first game gif...')
    rollout_to_gif(model, vec_env, first_gif_path, max_steps=120)

    print('✓ Modell erstellt, beginne Training...')
    print('Dies kann mehrere Minuten dauern...')

    model.learn(total_timesteps=timesteps, reset_num_timesteps=False if resume_model_path else True)

    final_model_path = os.path.join(MODELS_DIR, f'{name}.zip')
    model.save(final_model_path)

    print('Erstelle last game gif...')
    rollout_to_gif(model, vec_env, last_gif_path, max_steps=200)

    finished_at = time.time()
    final_timesteps = base_timesteps + int(timesteps)
    summary = {
        'name': name,
        'status': 'completed',
        'resume_from': resume_from,
        'started_at': started_at,
        'finished_at': finished_at,
        'duration_sec': round(finished_at - started_at, 2),
        'requested_timesteps': int(timesteps),
        'base_timesteps': int(base_timesteps),
        'final_timesteps': int(final_timesteps),
        'n_envs': int(n_envs),
        'model_path': final_model_path,
        'first_gif': first_gif_path,
        'last_gif': last_gif_path,
        'summary_text': (
            f"Run '{name}' trainiert {int(timesteps):,} zusätzliche Timesteps "
            f"in {round(finished_at - started_at, 2):.2f}s mit {n_envs} Envs"
            + (f", weitergeführt von '{resume_from}'" if resume_from else '')
        ),
    }

    summary_path = os.path.join(run_dir, 'summary.json')
    with open(summary_path, 'w', encoding='utf-8') as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)

    print(f"✓ Summary gespeichert: {summary_path}")
    print('✓ Training abgeschlossen!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', type=str, required=True)
    parser.add_argument('--timesteps', type=int, default=10000)
    parser.add_argument('--n_envs', type=int, default=4)
    parser.add_argument('--logdir', type=str, default='./tb_logs')
    parser.add_argument('--resume-from', type=str, default=None)
    args = parser.parse_args()

    train(args.name, args.timesteps, args.n_envs, args.logdir, resume_from=args.resume_from)
