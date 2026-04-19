from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from random import choice, sample, shuffle
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "history.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Saint Petersburg History Quiz")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@dataclass
class QuestionMeta:
    correct_id: int
    building_name: str
    description: str


ACTIVE_QUESTIONS: dict[str, QuestionMeta] = {}


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS buildings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                image_path TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    conn.close()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def menu(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/play", response_class=HTMLResponse)
def play(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("play.html", {"request": request})


@app.get("/learn", response_class=HTMLResponse)
def learn(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("learn.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("admin.html", {"request": request})


def fetch_all_buildings() -> list[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, description, image_path FROM buildings"
    ).fetchall()
    conn.close()
    return rows


@app.get("/api/lessons")
def lessons() -> dict[str, Any]:
    rows = fetch_all_buildings()
    return {
        "items": [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "image": row["image_path"],
            }
            for row in rows
        ]
    }


@app.get("/api/quiz/next")
def next_question() -> dict[str, Any]:
    rows = fetch_all_buildings()
    if len(rows) < 4:
        raise HTTPException(
            status_code=400,
            detail="Добавьте минимум 4 здания через /admin для запуска квиза.",
        )

    correct = choice(rows)
    distractors = sample([r for r in rows if r["id"] != correct["id"]], 3)
    options = distractors + [correct]
    shuffle(options)

    mode = choice(["question_to_images", "image_to_names"])

    question_id = uuid.uuid4().hex
    ACTIVE_QUESTIONS[question_id] = QuestionMeta(
        correct_id=correct["id"],
        building_name=correct["name"],
        description=correct["description"],
    )

    if len(ACTIVE_QUESTIONS) > 500:
        for key in list(ACTIVE_QUESTIONS.keys())[:250]:
            ACTIVE_QUESTIONS.pop(key, None)

    if mode == "question_to_images":
        payload_options = [
            {"id": r["id"], "label": r["name"], "image": r["image_path"]} for r in options
        ]
        return {
            "question_id": question_id,
            "mode": mode,
            "prompt": f"Где находится: {correct['name']}?",
            "options": payload_options,
        }

    payload_options = [{"id": r["id"], "label": r["name"]} for r in options]
    return {
        "question_id": question_id,
        "mode": mode,
        "prompt": "Что это за здание?",
        "image": correct["image_path"],
        "options": payload_options,
    }


@app.post("/api/quiz/check")
def check_answer(payload: dict[str, Any]) -> dict[str, Any]:
    question_id = payload.get("question_id")
    selected_id = payload.get("selected_id")

    if not question_id or selected_id is None:
        raise HTTPException(status_code=400, detail="question_id и selected_id обязательны")

    meta = ACTIVE_QUESTIONS.pop(question_id, None)
    if not meta:
        raise HTTPException(status_code=404, detail="Вопрос устарел, получите новый")

    is_correct = int(selected_id) == meta.correct_id
    return {
        "correct": is_correct,
        "correct_name": meta.building_name,
        "description": meta.description,
    }


@app.post("/api/admin/buildings")
async def upload_building(
    name: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
) -> dict[str, Any]:
    if not image.filename:
        raise HTTPException(status_code=400, detail="Файл изображения обязателен")

    extension = Path(image.filename).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Допустимые форматы: jpg, jpeg, png, webp")

    file_name = f"{uuid.uuid4().hex}{extension}"
    dst = UPLOAD_DIR / file_name
    content = await image.read()
    dst.write_bytes(content)

    image_path = f"/static/uploads/{file_name}"

    conn = get_conn()
    try:
        with conn:
            conn.execute(
                "INSERT INTO buildings(name, description, image_path) VALUES (?, ?, ?)",
                (name.strip(), description.strip(), image_path),
            )
    except sqlite3.IntegrityError:
        dst.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Здание с таким названием уже существует")
    finally:
        conn.close()

    return {"ok": True, "name": name, "image": image_path}
