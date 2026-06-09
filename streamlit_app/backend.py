import asyncio
from contextlib import asynccontextmanager
import json
import glob

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import subprocess
import os
import sqlite3
import socket
import time
from typing import Optional
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOGS_DIR = os.path.join(ROOT, 'streamlit_logs')
os.makedirs(LOGS_DIR, exist_ok=True)
DB_PATH = os.path.join(ROOT, 'streamlit_app.db')
RUNS_DIR = os.path.join(ROOT, 'training_runs')
os.makedirs(RUNS_DIR, exist_ok=True)
TETRIS_SERVER_HOST = '127.0.0.1'
TETRIS_SERVER_PORT = 10612
TETRIS_SERVER_JAR = os.path.join(ROOT, 'TetrisTCPserver_v0.6.jar')
TETRIS_SERVER_LOG = os.path.join(LOGS_DIR, 'tetris_server.log')
tetris_server_proc: subprocess.Popen | None = None


def tetris_server_available(timeout: float = 0.35):
    try:
        with socket.create_connection((TETRIS_SERVER_HOST, TETRIS_SERVER_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def start_tetris_server():
    global tetris_server_proc

    if tetris_server_available():
        return True, 'Tetris TCP Server läuft bereits.'
    if not os.path.exists(TETRIS_SERVER_JAR):
        return False, f'Tetris Server JAR nicht gefunden: {TETRIS_SERVER_JAR}'

    try:
        log_handle = open(TETRIS_SERVER_LOG, 'ab')
        tetris_server_proc = subprocess.Popen(
            ['java', '-jar', TETRIS_SERVER_JAR],
            cwd=ROOT,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )
    except Exception as exc:
        return False, f'Tetris TCP Server konnte nicht gestartet werden: {exc}'

    deadline = time.time() + 8.0
    while time.time() < deadline:
        if tetris_server_proc.poll() is not None:
            return False, f'Tetris TCP Server wurde sofort beendet. Siehe Log: {TETRIS_SERVER_LOG}'
        if tetris_server_available():
            return True, 'Tetris TCP Server wurde gestartet.'
        time.sleep(0.2)

    return False, f'Tetris TCP Server startet nicht auf Port {TETRIS_SERVER_PORT}. Siehe Log: {TETRIS_SERVER_LOG}'


def stop_tetris_server():
    global tetris_server_proc

    if not tetris_server_proc or tetris_server_proc.poll() is not None:
        tetris_server_proc = None
        return

    tetris_server_proc.terminate()
    try:
        tetris_server_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        tetris_server_proc.kill()
        tetris_server_proc.wait(timeout=5)
    finally:
        tetris_server_proc = None


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    ok, message = start_tetris_server()
    if ok:
        print(message)
    else:
        print(f'WARN: {message}')
    yield
    stop_tetris_server()


app = FastAPI(title='Tetris Trainer Backend', lifespan=lifespan)


def parse_latest_total_timesteps(log_text: str):
    import re

    patterns = [
        r"total[_ ]?timesteps[^0-9\n\r]*(\d{1,20})",
        r"total[_ ]?timesteps\s*\|\s*(\d{1,20})",
        r"total timesteps\s*\|\s*(\d{1,20})",
        r"total_timesteps\s*:\s*(\d{1,20})",
    ]

    last_found = None
    for patt in patterns:
        for m in re.finditer(patt, log_text, flags=re.IGNORECASE):
            try:
                last_found = int(m.group(1))
            except Exception:
                continue
    return last_found


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            name TEXT PRIMARY KEY,
            pid INTEGER,
            log_path TEXT,
            requested_timesteps INTEGER,
            created_at REAL,
            started_at REAL,
            finished_at REAL,
            resume_from TEXT,
            n_envs INTEGER,
            summary_path TEXT,
            status TEXT,
            base_timesteps INTEGER,
            final_timesteps INTEGER,
            algorithm TEXT
        )
        """
    )
    cur.execute('PRAGMA table_info(runs)')
    existing_columns = {row[1] for row in cur.fetchall()}
    additions = {
        'started_at': 'REAL',
        'finished_at': 'REAL',
        'resume_from': 'TEXT',
        'n_envs': 'INTEGER',
        'summary_path': 'TEXT',
        'status': 'TEXT',
        'base_timesteps': 'INTEGER',
        'final_timesteps': 'INTEGER',
        'algorithm': 'TEXT',
    }
    for column_name, column_type in additions.items():
        if column_name not in existing_columns:
            cur.execute(f'ALTER TABLE runs ADD COLUMN {column_name} {column_type}')
    conn.commit()
    conn.close()


init_db()


def get_run(name: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        'SELECT name,pid,log_path,requested_timesteps,created_at,started_at,finished_at,resume_from,n_envs,summary_path,status,base_timesteps,final_timesteps,algorithm FROM runs WHERE name=?',
        (name,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    summary = load_summary(row[9])
    started_at = row[5] or row[4]
    finished_at = row[6] or (summary.get('finished_at') if summary else None)
    duration_sec = None
    if started_at and finished_at:
        duration_sec = round(float(finished_at) - float(started_at), 2)
    return {
        'name': row[0],
        'pid': row[1],
        'log': row[2],
        'requested_timesteps': row[3],
        'created_at': row[4],
        'started_at': started_at,
        'finished_at': finished_at,
        'resume_from': row[7],
        'n_envs': row[8],
        'summary_path': row[9],
        'status': row[10],
        'base_timesteps': row[11],
        'final_timesteps': row[12],
        'algorithm': row[13],
        'duration_sec': duration_sec,
        'summary': summary,
    }


class StartRequest(BaseModel):
    name: str
    timesteps: int
    n_envs: int = 1
    resume_from: Optional[str] = None
    algorithm: str = 'A2C'


def load_summary(summary_path: str | None):
    if not summary_path or not os.path.exists(summary_path):
        return None
    try:
        with open(summary_path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception:
        return None


def load_base_timesteps(resume_from: str | None):
    if not resume_from:
        return 0
    summary_path = os.path.join(RUNS_DIR, resume_from, 'summary.json')
    summary = load_summary(summary_path) or {}
    return int(summary.get('final_timesteps', summary.get('timesteps', 0)) or 0)


def attach_timestep_totals(run: dict):
    summary = run.get('summary') or {}
    base_timesteps = int(
        run.get('base_timesteps')
        if run.get('base_timesteps') is not None
        else summary.get('base_timesteps', load_base_timesteps(run.get('resume_from')))
        or 0
    )
    requested_timesteps = int(run.get('requested_timesteps') or 0)
    final_timesteps = int(
        run.get('final_timesteps')
        if run.get('final_timesteps') is not None
        else summary.get('final_timesteps', base_timesteps + requested_timesteps)
        or 0
    )
    run['base_timesteps'] = base_timesteps
    run['target_timesteps'] = requested_timesteps
    run['final_timesteps'] = final_timesteps
    run['algorithm'] = run.get('algorithm') or summary.get('algorithm') or 'A2C'
    return run


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


def touch_run_state(name: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT pid, status, summary_path, finished_at FROM runs WHERE name=?', (name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    pid, status, summary_path, finished_at = row
    summary = load_summary(summary_path)
    if not status:
        status = 'completed' if summary else ('running' if pid_is_alive(pid) else 'stopped')
        cur.execute('UPDATE runs SET status=? WHERE name=?', (status, name))
        conn.commit()
    if status == 'running' and not pid_is_alive(pid):
        now = time.time()
        finished_at = finished_at or now
        status = 'completed' if summary else 'stopped'
        cur.execute('UPDATE runs SET status=?, finished_at=? WHERE name=?', (status, finished_at, name))
        conn.commit()
    conn.close()
    return summary


@app.post('/runs/start')
def start_run(req: StartRequest):
    if not tetris_server_available():
        raise HTTPException(
            status_code=409,
            detail=(
                f'Tetris TCP Server not reachable on '
                f'{TETRIS_SERVER_HOST}:{TETRIS_SERVER_PORT}'
            ),
        )

    # create log path
    logfile = os.path.join(LOGS_DIR, f"{req.name}.log")
    py_exec = sys.executable
    summary_path = os.path.join(RUNS_DIR, req.name, 'summary.json')
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    n_envs = int(req.n_envs)
    algorithm = (req.algorithm or 'A2C').upper()
    if req.resume_from:
        source = get_run(req.resume_from)
        source_summary = (source or {}).get('summary') or {}
        algorithm = (source or {}).get('algorithm') or source_summary.get('algorithm') or algorithm or 'A2C'
    base_timesteps = load_base_timesteps(req.resume_from)
    final_timesteps = base_timesteps + int(req.timesteps)
    if req.resume_from and not req.n_envs:
        source = get_run(req.resume_from)
        if source and source.get('n_envs'):
            n_envs = int(source['n_envs'])
    cmd = [
        py_exec,
        os.path.join(ROOT, 'streamlit_app', 'train.py'),
        '--name', req.name,
        '--timesteps', str(req.timesteps),
        '--n_envs', str(n_envs),
        '--algorithm', algorithm,
    ]
    if req.resume_from:
        cmd.extend(['--resume-from', req.resume_from])

    try:
        f = open(logfile, 'wb')
        proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        'INSERT OR REPLACE INTO runs (name,pid,log_path,requested_timesteps,created_at,started_at,finished_at,resume_from,n_envs,summary_path,status,base_timesteps,final_timesteps,algorithm) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (req.name, proc.pid, logfile, req.timesteps, time.time(), time.time(), None, req.resume_from, n_envs, summary_path, 'running', base_timesteps, final_timesteps, algorithm)
    )
    conn.commit()
    conn.close()

    return {
        'name': req.name,
        'pid': proc.pid,
        'log': logfile,
        'summary_path': summary_path,
        'base_timesteps': base_timesteps,
        'final_timesteps': final_timesteps,
        'algorithm': algorithm,
    }


@app.post('/runs/stop/{name}')
def stop_run(name: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT pid FROM runs WHERE name=?', (name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail='Run not found')
    pid = row[0]
    try:
        os.kill(pid, 15)
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

    cur.execute('UPDATE runs SET status=? WHERE name=?', ('stopped', name))
    conn.commit()
    conn.close()
    return {'name': name, 'stopped': True}


@app.get('/runs')
def list_runs(status: Optional[str] = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT name FROM runs ORDER BY created_at DESC')
    rows = cur.fetchall()
    conn.close()
    runs = []
    for r in rows:
        touch_run_state(r[0])
        run = get_run(r[0])
        if run:
            summary = run.get('summary') or {}
            attach_timestep_totals(run)
            run['summary_text'] = summary.get('summary_text')
            run['first_gif'] = summary.get('first_gif')
            run['last_gif'] = summary.get('last_gif')
            run['model_path'] = summary.get('model_path')
            if status is None or run.get('status') == status:
                runs.append(run)
    return {'runs': runs}


@app.get('/runs/{name}')
def get_run_detail(name: str):
    touch_run_state(name)
    run = get_run(name)
    if not run:
        raise HTTPException(status_code=404, detail='Run not found')
    summary = run.get('summary') or {}
    run['summary_text'] = summary.get('summary_text') or (
        f"Run {name} trainiert {run.get('requested_timesteps', 0)} zusätzliche Timesteps"
    )
    run['first_gif'] = summary.get('first_gif')
    run['last_gif'] = summary.get('last_gif')
    run['model_path'] = summary.get('model_path')
    attach_timestep_totals(run)
    return run


def tail_file(path, max_bytes=8192):
    if not os.path.exists(path):
        return ''
    with open(path, 'rb') as f:
        try:
            f.seek(-max_bytes, os.SEEK_END)
        except Exception:
            f.seek(0)
        return f.read().decode(errors='replace')


@app.get('/runs/{name}/log')
def get_log(name: str, lines: Optional[int] = 200):
    touch_run_state(name)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT log_path FROM runs WHERE name=?', (name,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail='Run not found')
    logpath = row[0]
    txt = tail_file(logpath)
    return {'log': txt}


@app.websocket('/ws/runs/{name}')
async def ws_run_status(websocket: WebSocket, name: str):
    await websocket.accept()
    last_payload = None

    try:
        while True:
            touch_run_state(name)
            run = get_run(name)
            if not run:
                payload = {'name': name, 'status': 'missing', 'log': '', 'current_timesteps': None, 'progress': 0.0}
            else:
                log_text = tail_file(run['log'])
                current = parse_latest_total_timesteps(log_text)
                attach_timestep_totals(run)
                requested = run.get('requested_timesteps') or 0
                base = run.get('base_timesteps') or 0
                additional_current = max(0, int(current or 0) - int(base))
                progress = float(additional_current) / float(requested) if requested else 0.0
                payload = {
                    **run,
                    'log': log_text,
                    'current_timesteps': current,
                    'current_additional_timesteps': additional_current,
                    'progress': min(1.0, max(0.0, progress)),
                }

            encoded = json.dumps(payload, sort_keys=True)
            if encoded != last_payload:
                await websocket.send_text(encoded)
                last_payload = encoded

            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
