import glob
import json
import os
import re
import socket
import subprocess
import sys
import time
from typing import Any

import requests
import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

LOGS_DIR = os.path.join(ROOT, 'streamlit_logs')
MODELS_DIR = os.path.join(ROOT, 'models')
GIFS_DIR = os.path.join(ROOT, 'gifs')
RUN_STATE = os.path.join(LOGS_DIR, 'current_run.json')
API_BASE = 'http://127.0.0.1:8000'
TETRIS_SERVER_HOST = '127.0.0.1'
TETRIS_SERVER_PORT = 10612

os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(GIFS_DIR, exist_ok=True)

st.set_page_config(page_title='Tetris RL Trainer', layout='wide')


def api_get(path: str, timeout: float = 2.0):
    return requests.get(f'{API_BASE}{path}', timeout=timeout)


def api_post(path: str, payload: dict[str, Any], timeout: float = 2.0):
    return requests.post(f'{API_BASE}{path}', json=payload, timeout=timeout)


@st.cache_data(ttl=2)
def backend_available() -> bool:
    try:
        response = api_get('/runs', timeout=1.0)
        return response.ok
    except Exception:
        return False


def read_run_state():
    if os.path.exists(RUN_STATE):
        try:
            with open(RUN_STATE, 'r', encoding='utf-8') as handle:
                return json.load(handle)
        except Exception:
            return None
    return None


def pid_is_alive(pid: int | None):
    if not pid:
        return False
    stat_path = f'/proc/{int(pid)}/stat'
    if os.path.exists(stat_path):
        try:
            with open(stat_path, 'r', encoding='utf-8') as handle:
                parts = handle.read().split()
            if len(parts) > 2 and parts[2] == 'Z':
                return False
        except Exception:
            pass
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def write_run_state(data):
    with open(RUN_STATE, 'w', encoding='utf-8') as handle:
        json.dump(data, handle)


def tail_log(logfile, max_bytes=4096):
    if not logfile or not os.path.exists(logfile):
        return ''
    with open(logfile, 'rb') as handle:
        try:
            handle.seek(-max_bytes, os.SEEK_END)
        except Exception:
            handle.seek(0)
        return handle.read().decode(errors='replace')


def parse_latest_total_timesteps(log_text: str):
    import re

    patterns = [
        r'total[_ ]?timesteps[^0-9\n\r]*(\d{1,20})',
        r'total[_ ]?timesteps\s*\|\s*(\d{1,20})',
        r'total timesteps\s*\|\s*(\d{1,20})',
        r'total_timesteps\s*:\s*(\d{1,20})',
    ]

    last_found = None
    for pattern in patterns:
        for match in re.finditer(pattern, log_text, flags=re.IGNORECASE):
            try:
                last_found = int(match.group(1))
            except Exception:
                continue
    return last_found


def tetris_server_available(timeout: float = 0.35):
    try:
        with socket.create_connection((TETRIS_SERVER_HOST, TETRIS_SERVER_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def log_has_tcp_refused(log_text: str):
    return (
        'ConnectionRefusedError' in log_text
        or 'Errno 111' in log_text
        or 'Connection refused' in log_text
    )


def format_duration(seconds: float | None):
    if seconds is None:
        return 'läuft noch'
    total_seconds = int(max(0, round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    if hours:
        return f'{hours}h {minutes}m {remaining_seconds}s'
    if minutes:
        return f'{minutes}m {remaining_seconds}s'
    return f'{remaining_seconds}s'


def format_timestamp(value):
    if not value:
        return 'n/a'
    try:
        return time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(float(value)))
    except Exception:
        return str(value)


def local_run_summary_path(name: str):
    return os.path.join(ROOT, 'training_runs', name, 'summary.json')


def load_local_summary(name: str):
    path = local_run_summary_path(name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception:
        return None


def list_local_runs(status: str | None = None):
    summary_root = os.path.join(ROOT, 'training_runs')
    if not os.path.exists(summary_root):
        return []
    runs = []
    for summary_path in sorted(glob.glob(os.path.join(summary_root, '*', 'summary.json'))):
        try:
            with open(summary_path, 'r', encoding='utf-8') as handle:
                summary = json.load(handle)
            summary.setdefault('summary_path', summary_path)
            if status is None or summary.get('status', 'completed') == status:
                runs.append(summary)
        except Exception:
            continue
    runs.sort(key=lambda item: item.get('started_at', 0) or 0, reverse=True)
    return runs


def fetch_runs(status: str | None = None):
    if backend_available():
        try:
            query = f'?status={status}' if status else ''
            response = api_get(f'/runs{query}', timeout=2.0)
            response.raise_for_status()
            return response.json().get('runs', [])
        except Exception:
            pass
    return list_local_runs(status=status)


def fetch_run_detail(name: str):
    if backend_available():
        try:
            response = api_get(f'/runs/{name}', timeout=2.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            pass
    return load_local_summary(name)


def fetch_run_log(name: str, logfile: str | None = None):
    if backend_available() and name:
        try:
            response = api_get(f'/runs/{name}/log', timeout=2.0)
            response.raise_for_status()
            return response.json().get('log', '')
        except Exception:
            pass
    return tail_log(logfile, max_bytes=8192)


def resolve_base_timesteps(run_detail: dict[str, Any]):
    summary = run_detail.get('summary') or {}
    if run_detail.get('base_timesteps') is not None:
        return int(run_detail.get('base_timesteps') or 0)
    if summary.get('base_timesteps') is not None:
        return int(summary.get('base_timesteps') or 0)

    resume_from = run_detail.get('resume_from')
    if not resume_from:
        return 0

    source_detail = fetch_run_detail(resume_from) or {}
    source_summary = source_detail.get('summary') or {}
    return int(
        source_detail.get(
            'final_timesteps',
            source_summary.get('final_timesteps', source_summary.get('timesteps', 0)),
        )
        or 0
    )


def all_known_run_names():
    names = set()
    for run in fetch_runs():
        if run.get('name'):
            names.add(run['name'])
    for folder in (os.path.join(ROOT, 'training_runs'), MODELS_DIR):
        if os.path.exists(folder):
            for path in glob.glob(os.path.join(folder, '*')):
                name = os.path.basename(path)
                if folder == MODELS_DIR and name.endswith('.zip'):
                    name = name[:-4]
                if name:
                    names.add(name)
    return names


def run_name_exists(name: str):
    return name in all_known_run_names()


def safe_filename(value: str):
    cleaned = re.sub(r'[^A-Za-z0-9_.-]+', '_', value).strip('_')
    return cleaned or 'model'


def list_models():
    models = []
    seen_paths = set()

    for run in completed_runs:
        detail = fetch_run_detail(run.get('name', '')) or {}
        summary = detail.get('summary') or {}
        model_path = detail.get('model_path') or summary.get('model_path')
        if model_path and os.path.exists(model_path) and model_path not in seen_paths:
            models.append({
                'label': f"{detail.get('name') or run.get('name')} · Historie",
                'name': detail.get('name') or run.get('name') or os.path.basename(model_path),
                'path': model_path,
            })
            seen_paths.add(model_path)

    for model_path in sorted(glob.glob(os.path.join(MODELS_DIR, '*.zip'))):
        if model_path in seen_paths:
            continue
        name = os.path.splitext(os.path.basename(model_path))[0]
        models.append({
            'label': f'{name} · Modell-Datei',
            'name': name,
            'path': model_path,
        })
        seen_paths.add(model_path)

    return models


def list_playback_gifs():
    gifs = []
    for gif_path in sorted(glob.glob(os.path.join(GIFS_DIR, 'play_*.gif')), key=os.path.getmtime, reverse=True):
        stats_path = os.path.splitext(gif_path)[0] + '.json'
        gifs.append({
            'path': gif_path,
            'name': os.path.basename(gif_path),
            'created_at': os.path.getmtime(gif_path),
            'stats_path': stats_path,
            'stats': load_json_file(stats_path),
        })
    return gifs


def load_json_file(path: str):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception:
        return None


def save_json_file(path: str, data: dict[str, Any]):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def render_game_stats(stats: dict[str, Any] | None):
    if not stats:
        st.info('Für dieses Spiel sind noch keine Stats gespeichert.')
        return

    metric_cols = st.columns(5)
    metric_cols[0].metric('Schritte', f"{int(stats.get('steps', 0)):,}")
    metric_cols[1].metric('Eliminierte Zeilen', f"{int(stats.get('removed_lines', 0)):,}")
    metric_cols[2].metric('Reward gesamt', f"{float(stats.get('total_reward', 0.0)):.1f}")
    metric_cols[3].metric('Höhe', f"{int(stats.get('final_height', 0)):,}")
    metric_cols[4].metric('Löcher', f"{int(stats.get('final_holes', 0)):,}")

    detail_cols = st.columns(3)
    detail_cols[0].metric('Ø Reward/Schritt', f"{float(stats.get('avg_reward', 0.0)):.2f}")
    detail_cols[1].metric('Dauer', format_duration(stats.get('duration_sec')))
    detail_cols[2].metric('Game Over', 'Ja' if stats.get('terminated') else 'Nein')
    st.caption(f"Modell: {stats.get('model_name', 'n/a')}")

    action_counts = stats.get('action_counts') or {}
    if action_counts:
        action_labels = {
            '0': 'Links',
            '1': 'Rechts',
            '2': 'Rotieren links',
            '3': 'Rotieren rechts',
            '4': 'Drop',
        }
        st.caption(
            'Aktionen: '
            + ' · '.join(
                f"{action_labels.get(str(action), str(action))}: {count}"
                for action, count in sorted(action_counts.items(), key=lambda item: int(item[0]))
            )
        )


def run_model_game(
    model_path: str,
    model_name: str,
    max_steps: int,
    frame_delay: float,
    live_placeholder,
    stats_placeholder,
):
    import imageio
    import numpy as np
    from stable_baselines3 import A2C
    from stable_baselines3.common.env_util import make_vec_env

    from tetris_env import TetrisEnv

    def normalize_frame(frame):
        array = np.asarray(frame)
        if array.ndim == 3 and array.shape[0] in (1, 3) and array.shape[-1] not in (1, 3):
            array = np.transpose(array, (1, 2, 0))
        if array.dtype != np.uint8:
            array = np.clip(array, 0, 255).astype(np.uint8)
        return array

    vec_env = None
    frames = []
    started_at = time.time()
    total_reward = 0.0
    removed_lines = 0
    final_height = 0
    final_holes = 0
    terminated = False
    action_counts = {str(action): 0 for action in range(5)}
    try:
        vec_env = make_vec_env(TetrisEnv, n_envs=1)
        model = A2C.load(model_path, env=vec_env)
        obs = vec_env.reset()

        for step in range(int(max_steps)):
            action, _ = model.predict(obs, deterministic=True)
            action_id = int(np.asarray(action).reshape(-1)[0])
            action_counts[str(action_id)] = action_counts.get(str(action_id), 0) + 1
            obs, rewards, dones, infos = vec_env.step(action)
            reward = float(np.asarray(rewards).reshape(-1)[0])
            info = infos[0] if infos else {}
            total_reward += reward
            removed_lines = max(removed_lines, int(info.get('removed_lines', removed_lines) or 0))
            final_height = int(info.get('height', final_height) or 0)
            final_holes = int(info.get('holes', final_holes) or 0)
            frame = normalize_frame(obs[0])
            frames.append(frame)
            live_placeholder.image(frame, caption=f'Schritt {step + 1:,}', use_container_width=False)
            stats_placeholder.empty()
            with stats_placeholder.container():
                render_game_stats({
                    'steps': step + 1,
                    'removed_lines': removed_lines,
                    'total_reward': total_reward,
                    'avg_reward': total_reward / float(step + 1),
                    'final_height': final_height,
                    'final_holes': final_holes,
                    'terminated': bool(dones[0]),
                    'duration_sec': time.time() - started_at,
                    'model_name': model_name,
                    'action_counts': action_counts,
                })
            if frame_delay > 0:
                time.sleep(frame_delay)
            if bool(dones[0]):
                terminated = True
                break
    finally:
        if vec_env is not None:
            vec_env.close()

    if not frames:
        raise RuntimeError('Das Spiel hat keine Frames erzeugt.')

    gif_path = os.path.join(GIFS_DIR, f'play_{safe_filename(model_name)}_{int(time.time())}.gif')
    imageio.mimsave(gif_path, frames, loop=0, duration=max(0.03, float(frame_delay) or 0.05))
    stats = {
        'model_name': model_name,
        'model_path': model_path,
        'gif_path': gif_path,
        'created_at': time.time(),
        'steps': len(frames),
        'max_steps': int(max_steps),
        'removed_lines': int(removed_lines),
        'total_reward': round(float(total_reward), 4),
        'avg_reward': round(float(total_reward) / float(len(frames)), 4),
        'final_height': int(final_height),
        'final_holes': int(final_holes),
        'terminated': bool(terminated),
        'duration_sec': round(time.time() - started_at, 2),
        'frame_delay': float(frame_delay),
        'action_counts': action_counts,
    }
    save_json_file(os.path.splitext(gif_path)[0] + '.json', stats)
    return gif_path, stats


def continuation_name(source_name: str):
    known_names = all_known_run_names()
    base = f'{source_name}_cont'
    candidate = f'{base}_{int(time.time())}'
    counter = 2
    while candidate in known_names:
        candidate = f'{base}_{int(time.time())}_{counter}'
        counter += 1
    return candidate


def active_run_from_state():
    active_runs = fetch_runs('running')
    if active_runs:
        return active_runs[0]

    run_state = read_run_state()
    if not run_state or not pid_is_alive(run_state.get('pid')):
        return None

    run_name = run_state.get('name')
    detail = fetch_run_detail(run_name) if run_name else None
    if detail and detail.get('status') not in (None, 'running'):
        return None
    return {
        **run_state,
        **(detail or {}),
        'status': 'running',
    }


def start_training(name: str, timesteps: int, n_envs: int, resume_from: str | None = None):
    logfile = os.path.join(LOGS_DIR, f'{name}.log')
    payload = {
        'name': name,
        'timesteps': int(timesteps),
        'n_envs': int(n_envs),
        'resume_from': resume_from,
    }

    if not tetris_server_available():
        return False, (
            f'Tetris TCP Server nicht erreichbar auf {TETRIS_SERVER_HOST}:{TETRIS_SERVER_PORT}. '
            'Starte zuerst: java -jar TetrisTCPserver_v0.6.jar'
        )

    if backend_available():
        try:
            response = api_post('/runs/start', payload, timeout=3.0)
            response.raise_for_status()
            data = response.json()
            write_run_state({
                'pid': data.get('pid'),
                'log': data.get('log'),
                'name': name,
                'requested_timesteps': int(timesteps),
                'resume_from': resume_from,
            })
            return True, f'Started via backend: {name}'
        except requests.HTTPError as exc:
            detail = None
            try:
                detail = exc.response.json().get('detail')
            except Exception:
                pass
            return False, detail or str(exc)
        except Exception:
            pass

    cmd = [
        sys.executable,
        os.path.join(ROOT, 'streamlit_app', 'train.py'),
        '--name', name,
        '--timesteps', str(int(timesteps)),
        '--n_envs', str(int(n_envs)),
    ]
    if resume_from:
        cmd.extend(['--resume-from', resume_from])

    with open(logfile, 'wb') as out:
        proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT)

    write_run_state({
        'pid': proc.pid,
        'log': logfile,
        'name': name,
        'requested_timesteps': int(timesteps),
        'resume_from': resume_from,
    })
    return True, f'Started locally: {name}'


def render_live_monitor(
    run_name: str,
    requested_timesteps: int | None,
    logfile: str | None = None,
):
    if not run_name:
        st.info('Kein aktiver Run ausgewählt.')
        return

    def render_snapshot():
        detail = fetch_run_detail(run_name) or {}
        log_text = fetch_run_log(run_name, logfile)
        current = parse_latest_total_timesteps(log_text) or 0
        base_timesteps = resolve_base_timesteps(detail)
        current_additional = max(0, int(current) - int(base_timesteps))
        total = int(detail.get('target_timesteps') or detail.get('requested_timesteps') or requested_timesteps or 0)
        progress = min(1.0, current_additional / total) if total else 0.0
        status = detail.get('status') or 'running'

        metric_cols = st.columns(3)
        metric_cols[0].metric('Run', run_name)
        metric_cols[1].metric('Status', status)
        metric_cols[2].metric('Zusätzliche Timesteps', f'{total:,}' if total else 'n/a')

        st.progress(progress)
        if total:
            if base_timesteps:
                st.caption(
                    f'{current_additional:,} / {total:,} zusätzliche Timesteps '
                    f'(gesamt: {current:,} / {base_timesteps + total:,})'
                )
            else:
                st.caption(f'{current_additional:,} / {total:,} Timesteps')
        else:
            st.caption(f'{current:,} Timesteps')

        if log_has_tcp_refused(log_text):
            st.error(
                f'Training konnte nicht starten: Der Tetris TCP Server auf '
                f'{TETRIS_SERVER_HOST}:{TETRIS_SERVER_PORT} ist nicht erreichbar.'
            )

        st.text_area('Log Tail', log_text or 'Noch kein Log-Output vorhanden.', height=360, disabled=True)

    if hasattr(st, 'fragment'):
        @st.fragment(run_every='1s')
        def poll_run():
            render_snapshot()

        poll_run()
    else:
        render_snapshot()


st.title('Tetris RL - Trainer UI')
st.caption('Neue Trainings startest du hier. Die Historie zeigt nur abgeschlossene Läufe.')

active_run = active_run_from_state()
completed_runs = fetch_runs('completed')

if 'nav_page' not in st.session_state:
    st.session_state['nav_page'] = 'Run'
if 'selected_run' not in st.session_state:
    st.session_state['selected_run'] = completed_runs[0]['name'] if completed_runs else ''
if 'new_run_name' not in st.session_state:
    st.session_state['new_run_name'] = f'train_{int(time.time())}'

with st.sidebar:
    st.header('Navigation')
    nav_pages = ['Run', 'Spiel', 'Historie']
    nav_index = nav_pages.index(st.session_state['nav_page']) if st.session_state['nav_page'] in nav_pages else 0
    st.session_state['nav_page'] = st.radio('Ansicht', nav_pages, index=nav_index, key='nav_radio')
    st.divider()
    if active_run:
        st.subheader('Aktiver Run')
        st.caption(active_run.get('name', 'n/a'))
        st.caption(f"{active_run.get('requested_timesteps', 0):,} Timesteps")
    st.subheader('Historie')
    if completed_runs:
        for run in completed_runs:
            run_name = run.get('name', 'unknown')
            status = run.get('status', 'completed')
            label = f'{run_name} · {status}'
            if st.button(label, key=f'select_{run_name}', use_container_width=True):
                st.session_state['selected_run'] = run_name
                st.session_state['nav_page'] = 'Historie'
                st.rerun()
    else:
        st.caption('Noch keine abgeschlossenen Trainings gefunden.')


def render_run_page():
    st.subheader('Neues Training')
    if not tetris_server_available():
        st.warning(
            f'Tetris TCP Server nicht erreichbar auf {TETRIS_SERVER_HOST}:{TETRIS_SERVER_PORT}. '
            'Trainings starten erst, wenn der Java-Server läuft.'
        )

    with st.form('new_training_form', border=True):
        st.text_input('Training name', key='new_run_name')
        timesteps = st.number_input('Timesteps', min_value=1000, value=10000, step=1000)
        n_envs = st.number_input('n_envs', min_value=1, value=4, step=1)
        submitted = st.form_submit_button('Training starten')

    if submitted:
        ok, message = start_training(st.session_state['new_run_name'], int(timesteps), int(n_envs))
        if ok:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    st.divider()
    st.subheader('Aktiver Status')
    if active_run:
        render_live_monitor(
            active_run.get('name', ''),
            active_run.get('requested_timesteps'),
            logfile=active_run.get('log'),
        )
    else:
        st.info('Der Live-Monitor erscheint hier, sobald ein Run läuft.')

    st.divider()
    st.subheader('Weiterführen eines Trainings')
    if completed_runs:
        resume_options = [run['name'] for run in completed_runs]
        resume_source_name = st.selectbox(
            'Trainingsquelle auswählen',
            options=resume_options,
            index=0,
            key='resume_source_select',
        )
        source_detail = fetch_run_detail(resume_source_name) or {}
        st.caption(
            f"Ausgewählt: {resume_source_name} · "
            f"letzte Dauer: {format_duration(source_detail.get('duration_sec'))}"
        )
        if st.session_state.get('resume_name_source') != resume_source_name:
            st.session_state['resume_name_source'] = resume_source_name
            st.session_state['resume_run_name'] = continuation_name(resume_source_name)

        with st.form('resume_training_form', border=True):
            resume_name = st.text_input('Name für den Fortsetzungs-Run', key='resume_run_name')
            overwrite_existing = st.checkbox(
                'Bestehenden Run/Modell mit diesem Namen überschreiben',
                value=False,
                key='resume_overwrite_existing',
            )
            additional_timesteps = st.number_input('Zusätzliche Timesteps', min_value=1000, value=10000, step=1000)
            env_count = source_detail.get('n_envs') or 4
            st.text_input('Env-Anzahl', value=str(env_count), disabled=True)
            resume_submitted = st.form_submit_button('Weiterführen')

        if resume_submitted:
            raw_resume_name = (resume_name or '').strip()
            cleaned_resume_name = safe_filename(raw_resume_name)
            if not raw_resume_name:
                st.error('Bitte einen Namen für den Fortsetzungs-Run eingeben.')
            elif active_run and active_run.get('name') == cleaned_resume_name:
                st.error('Dieser Run läuft gerade und kann nicht überschrieben werden.')
            elif run_name_exists(cleaned_resume_name) and not overwrite_existing:
                st.error(
                    f"'{cleaned_resume_name}' existiert bereits. "
                    'Wähle einen anderen Namen oder aktiviere bewusst das Überschreiben.'
                )
            else:
                ok, message = start_training(
                    cleaned_resume_name,
                    int(additional_timesteps),
                    int(env_count),
                    resume_from=resume_source_name,
                )
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    else:
        st.info('Für das Weiterführen brauchst du zuerst ein abgeschlossenes Training.')


def render_history_page():
    if not completed_runs:
        st.info('Noch keine abgeschlossenen Trainings vorhanden.')
        return

    selected_run_name = st.session_state.get('selected_run') or completed_runs[0]['name']
    selected_run_detail = fetch_run_detail(selected_run_name)
    if not selected_run_detail:
        st.info('Wähle links einen abgeschlossenen Run aus.')
        return

    summary = selected_run_detail.get('summary') if isinstance(selected_run_detail, dict) else None
    summary_text = selected_run_detail.get('summary_text') if isinstance(selected_run_detail, dict) else None
    if not summary_text and summary:
        summary_text = summary.get('summary_text')

    st.subheader(selected_run_detail.get('name', 'Training'))
    metric_cols = st.columns(5)
    metric_cols[0].metric('Status', selected_run_detail.get('status', 'n/a'))
    metric_cols[1].metric('Dauer', format_duration(selected_run_detail.get('duration_sec')))
    metric_cols[2].metric('Timesteps', f"{int(selected_run_detail.get('requested_timesteps', 0)):,}")
    metric_cols[3].metric('Envs', selected_run_detail.get('n_envs', 'n/a'))
    metric_cols[4].metric('Resume von', selected_run_detail.get('resume_from') or '—')

    st.markdown(f"**Gestartet:** {format_timestamp(selected_run_detail.get('started_at'))}  ")
    st.markdown(f"**Beendet:** {format_timestamp(selected_run_detail.get('finished_at'))}  ")

    if summary_text:
        st.markdown('### Zusammenfassung')
        st.write(summary_text)

    gif_first = selected_run_detail.get('first_gif') or (summary.get('first_gif') if summary else None)
    gif_last = selected_run_detail.get('last_gif') or (summary.get('last_gif') if summary else None)

    st.markdown('### Vergleich')
    gif_col1, gif_col2 = st.columns(2)
    with gif_col1:
        st.caption('Erstes Spiel')
        if gif_first and os.path.exists(gif_first):
            st.image(gif_first, use_container_width=True)
        else:
            st.info('Kein erstes GIF gefunden.')
    with gif_col2:
        st.caption('Letztes Spiel')
        if gif_last and os.path.exists(gif_last):
            st.image(gif_last, use_container_width=True)
        else:
            st.info('Kein letztes GIF gefunden.')

    model_path = selected_run_detail.get('model_path') or (summary.get('model_path') if summary else None)
    if model_path:
        st.caption(f'Modell: {model_path}')

    with st.expander('Log anzeigen', expanded=False):
        log_text = tail_log(selected_run_detail.get('log'))
        st.text(log_text or 'Noch kein Log vorhanden.')


def render_play_page():
    st.subheader('Modell spielen lassen')

    if not tetris_server_available():
        st.warning(
            f'Tetris TCP Server nicht erreichbar auf {TETRIS_SERVER_HOST}:{TETRIS_SERVER_PORT}. '
            'Starte das Backend neu, damit der Java-Server automatisch mitläuft.'
        )

    models = list_models()
    if not models:
        st.info('Noch kein trainiertes Modell gefunden.')
        return

    selected_label = st.selectbox(
        'Trainiertes Modell auswählen',
        options=[model['label'] for model in models],
        key='play_model_select',
    )
    selected_model = models[[model['label'] for model in models].index(selected_label)]

    col_steps, col_delay = st.columns(2)
    with col_steps:
        max_steps = st.number_input('Maximale Spielschritte', min_value=20, max_value=2000, value=300, step=20)
    with col_delay:
        frame_delay = st.number_input('Frame-Dauer in Sekunden', min_value=0.03, max_value=0.5, value=0.05, step=0.01)

    st.caption(f"Modell-Datei: {selected_model['path']}")
    live_placeholder = st.empty()
    stats_placeholder = st.empty()

    if st.button('Spiel starten', type='primary'):
        if not tetris_server_available():
            st.error(
                f'Tetris TCP Server nicht erreichbar auf {TETRIS_SERVER_HOST}:{TETRIS_SERVER_PORT}. '
                'Bitte Backend neu starten.'
            )
        else:
            try:
                with st.spinner('Modell spielt Tetris...'):
                    gif_path, stats = run_model_game(
                        selected_model['path'],
                        selected_model['name'],
                        int(max_steps),
                        float(frame_delay),
                        live_placeholder,
                        stats_placeholder,
                    )
                stats_placeholder.empty()
                st.success(f"Spiel gespeichert: {os.path.basename(gif_path)} · {int(stats.get('steps', 0)):,} Frames")
                render_game_stats(stats)
                st.image(gif_path, caption='Gespeichertes Spiel', use_container_width=False)
            except Exception as exc:
                st.error(f'Spiel konnte nicht ausgeführt werden: {exc}')

    st.divider()
    st.subheader('Gespeicherte Spiele')
    playback_gifs = list_playback_gifs()
    if not playback_gifs:
        st.info('Noch keine gespeicherten Spiel-GIFs vorhanden.')
        return

    selected_gif_name = st.selectbox(
        'Spiel ansehen',
        options=[gif['name'] for gif in playback_gifs],
        key='playback_gif_select',
    )
    selected_gif = playback_gifs[[gif['name'] for gif in playback_gifs].index(selected_gif_name)]
    st.caption(f"Erstellt: {format_timestamp(selected_gif['created_at'])}")
    render_game_stats(selected_gif.get('stats'))
    st.image(selected_gif['path'], caption=selected_gif['name'], use_container_width=False)


if st.session_state['nav_page'] == 'Historie':
    render_history_page()
elif st.session_state['nav_page'] == 'Spiel':
    render_play_page()
else:
    render_run_page()

if st.button('Seite neu laden'):
    if hasattr(st, 'rerun'):
        st.rerun()
    else:
        st.info('Bitte den Browser neu laden.')
