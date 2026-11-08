"""
Canlı demo paneli.

Form cevaplarını Google Sheet CSV'sinden çeker, her satırı JEV'e sorar
ve sonucu http://127.0.0.1:8001 panelinde vagon olarak gösterir.

Çalıştırma:
    python demo.py

Ortam (.env):
    AI_OPEN_ROUTER_API_KEY
    SHEET_ID
"""

import hashlib
import os
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
import csv
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Sunum demosunda model sürümü sabit.
JEV_MODEL = "typesafe/jev-1.13"
JEV_URL = "https://openrouter.ai/api/v1/systemone"

# noul bu değer ve üzerindeyse kartta "evet" gösterilir.
NOUL_YES = 0.70
# choice / score confidence bu değerin altındaysa sınıflandırma belirsiz sayılır.
LOW_CONFIDENCE = 0.60

API_KEY = os.getenv("AI_OPEN_ROUTER_API_KEY", "").strip()
SHEET_ID = os.getenv("SHEET_ID", "").strip()

# Aynı satır ikinci kez "çek" denince JEV'e tekrar gitmesin.
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()
# İki tıklama aynı anda aynı satırları JEV'e yollamasın.
_analyze_lock = threading.Lock()

# CSV başlığı -> state alanı. Karşılaştırma normalize_header() ile yapılır.
HEADER_FIELDS = {
    "zaman damgası": "timestamp",
    "yapay zekâyı üniversitede en çok hangi amaçla kullanırsın?": "ai_usage_area",
    "yapay zekâdan aldığın cevaba ne kadar güvenirsin?": "trust_score",
    "yapay zekânın eğitimde gerçekten faydalı olması için ne yapması gerekir?": "benefit_answer",
    "yapay zekâ kullanırken en büyük endişen nedir?": "concern_answer",
}

PROFILE_LABELS = {
    "explorer": "Denemeye açık",
    "pragmatist": "Faydacı",
    "cautious": "Dikkatli",
    "skeptic": "Mesafeli",
    "other": "Diğer",
}

# Karar tipleri rehberdeki demo konusuyla aynı: choice, score, noul.
QUESTIONS = {
    "profile": {
        "type": "choice",
        "instructions": "Bu kişinin yapay zekâ kullanım yaklaşımı hangisine daha yakın?",
        "criteria": {
            "explorer": "Yapay zekâyı farklı alanlarda denemeye açık ve meraklı kişi.",
            "pragmatist": "Yapay zekâyı belirli ve faydalı işler için kullanan kişi.",
            "cautious": "Yapay zekâyı kullanırken doğrulama ve risklere önem veren kişi.",
            "skeptic": "Yapay zekâ kullanımına mesafeli veya düşük güven duyan kişi.",
            "other": "Bu seçeneklerden hiçbirine açıkça uymayan kişi.",
        },
    },
    "adoption_readiness": {
        "type": "score",
        "instructions": "Bu kişinin eğitimde yapay zekâ kullanımına açıklığını değerlendir.",
        "criteria": [
            "Düşük: Kullanmak istemiyor veya belirgin biçimde karşı.",
            "Orta: Sadece sınırlı ve kontrollü durumlarda kullanır.",
            "Yüksek: Eğitim sürecinde düzenli kullanmaya açık.",
        ],
    },
    "needs_verification": {
        "type": "noul",
        "instructions": "Bu kişinin yapay zekâ cevaplarını mutlaka doğrulaması gerektiği görülüyor mu?",
        "criteria": {
            "true": "Kişi yanlış bilgi, kaynak güvenilirliği veya doğrulama konusunda endişe belirtiyor.",
            "false": "Kişinin cevabı doğrulama ihtiyacına özel bir vurgu yapmıyor.",
        },
    },
}

app = FastAPI(title="JEV canlı demo")


# ---------------------------------------------------------------------------
# Form satırını state'e çevirme
# ---------------------------------------------------------------------------


def normalize_header(value: str) -> str:
    return " ".join(value.replace("\ufeff", "").strip().lower().split())


def clean_text(value: str | None) -> str:
    return " ".join((value or "").split())


def parse_trust(value: str):
    """1-5 ölçeği. Boş veya okunamayan değer None kalır, istek yine gider."""
    text = clean_text(value).replace(",", ".")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number


def row_id(fields: dict) -> str:
    """Satırın içeriğinden sabit kimlik. Sıra değişse de önbellek bozulmasın."""
    raw = "|".join(
        [
            fields["timestamp"],
            fields["ai_usage_area"],
            "" if fields["trust_score"] is None else str(fields["trust_score"]),
            fields["benefit_answer"],
            fields["concern_answer"],
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def parse_csv(text: str) -> list[dict]:
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise RuntimeError("Sheet boş görünüyor.")

    columns = {}
    for header in reader.fieldnames:
        key = HEADER_FIELDS.get(normalize_header(header))
        if key:
            columns[key] = header

    missing = [name for name in HEADER_FIELDS.values() if name not in columns]
    if missing:
        found = ", ".join(reader.fieldnames)
        raise RuntimeError(
            f"Beklenen sütunlar yok ({', '.join(missing)}). Gelen başlıklar: {found}"
        )

    rows = []
    for raw in reader:
        fields = {
            "timestamp": clean_text(raw.get(columns["timestamp"])),
            "ai_usage_area": clean_text(raw.get(columns["ai_usage_area"])),
            "trust_score": parse_trust(raw.get(columns["trust_score"]) or ""),
            "benefit_answer": clean_text(raw.get(columns["benefit_answer"])),
            "concern_answer": clean_text(raw.get(columns["concern_answer"])),
        }
        # Tamamen boş satırı atla. Zaman damgası tek başına cevap sayılmaz.
        if not any(
            [
                fields["ai_usage_area"],
                fields["trust_score"] is not None,
                fields["benefit_answer"],
                fields["concern_answer"],
            ]
        ):
            continue
        fields["id"] = row_id(fields)
        rows.append(fields)

    for index, row in enumerate(rows, start=1):
        row["number"] = index
        row["state"] = {
            "participant_id": f"cevap-{index:02d}",
            "ai_usage_area": row["ai_usage_area"],
            "trust_score": row["trust_score"],
            "benefit_answer": row["benefit_answer"],
            "concern_answer": row["concern_answer"],
        }
    return rows


def fetch_rows() -> list[dict]:
    if not SHEET_ID:
        raise RuntimeError("SHEET_ID ortam değişkeni tanımlı değil.")

    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        response = requests.get(url, timeout=20)
    except requests.RequestException as exc:
        raise RuntimeError(f"Sheet okunamadı: {exc}") from exc

    if not response.ok:
        raise RuntimeError(
            f"Sheet okunamadı ({response.status_code}). Dosya bağlantıya açık olmalı."
        )

    text = response.content.decode("utf-8-sig", errors="replace")
    if text.lstrip().startswith("<"):
        raise RuntimeError(
            "Sheet CSV yerine bir sayfa döndü. Paylaşımda 'bağlantısı olan herkes görüntüleyebilir' açık olmalı."
        )
    return parse_csv(text)


# ---------------------------------------------------------------------------
# JEV
# ---------------------------------------------------------------------------


def ask_jev(state: dict) -> dict:
    if not API_KEY:
        raise RuntimeError("AI_OPEN_ROUTER_API_KEY ortam değişkeni tanımlı değil.")

    response = requests.post(
        JEV_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-OpenRouter-Title": "JEV Canli Demo",
        },
        json={"model": JEV_MODEL, "state": state, "questions": QUESTIONS},
        timeout=90,
    )
    if not response.ok:
        detail = response.text.strip().replace("\n", " ")[:240]
        raise RuntimeError(f"JEV yanıt vermedi ({response.status_code}): {detail}")

    payload = response.json()
    answers = payload.get("answers") or {}
    expected = ("profile", "adoption_readiness", "needs_verification")
    if any(name not in answers for name in expected):
        raise RuntimeError("JEV cevabında beklenen karar alanları yok.")
    return {
        "model": payload.get("model") or JEV_MODEL,
        "answers": answers,
        "usage": payload.get("usage") or {},
    }


def analyze(rows: list[dict]) -> dict[str, str]:
    """Önbellekte olmayan satırları paralel gönderir. Hata önbelleğe yazılmaz."""
    errors: dict[str, str] = {}
    with _cache_lock:
        pending = [row for row in rows if row["id"] not in _cache]

    if not pending:
        print(f"JEV: {len(rows)} satırın tamamı önbellekte")
        return errors

    print(f"JEV: {len(pending)} yeni satır, model {JEV_MODEL}")

    def run(row: dict) -> tuple[str, dict | None, str | None]:
        label = row["state"]["participant_id"]
        print(f"  → {label}")
        try:
            result = ask_jev(row["state"])
        except Exception as exc:
            print(f"  ! {label}: {exc}")
            return row["id"], None, str(exc)
        print(f"  ← {label}")
        return row["id"], result, None

    workers = min(4, len(pending))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run, row) for row in pending]
        for future in as_completed(futures):
            rid, result, error = future.result()
            if error:
                errors[rid] = error
                continue
            with _cache_lock:
                _cache[rid] = result
    return errors


# ---------------------------------------------------------------------------
# Panele giden görünüm
# ---------------------------------------------------------------------------


def short_label(text: str) -> str:
    """'Orta: açıklama' gibi seviye metninden kartta duracak kısa adı alır."""
    return text.split(":", 1)[0].strip()


def present_choice(answer: dict) -> dict:
    selected = answer.get("choice")
    confidence = float(answer.get("confidence") or 0)
    ranked = sorted(
        (answer.get("probabilities") or {}).items(),
        key=lambda item: item[1],
        reverse=True,
    )
    return {
        "type": "choice",
        "choice": selected,
        "label": PROFILE_LABELS.get(selected, selected or "—"),
        "confidence": confidence,
        "uncertain": confidence < LOW_CONFIDENCE,
        "options": [
            {
                "key": key,
                "label": PROFILE_LABELS.get(key, key),
                "p": float(prob),
                "selected": key == selected,
            }
            for key, prob in ranked
        ],
    }


def present_score(answer: dict) -> dict:
    score = float(answer.get("score") or 0)
    confidence = float(answer.get("confidence") or 0)
    legend = answer.get("legend") or {}
    levels = sorted(legend, key=lambda level: int(level))
    nearest = str(round(score)) if levels else ""
    if nearest not in legend and levels:
        nearest = min(levels, key=lambda level: abs(int(level) - score))
    full = legend.get(nearest, "")
    probabilities = answer.get("probabilities") or {}
    return {
        "type": "score",
        "score": score,
        "max": (len(legend) - 1) if legend else 0,
        "level": short_label(full) if full else "—",
        "level_full": full,
        "confidence": confidence,
        "uncertain": confidence < LOW_CONFIDENCE,
        "levels": [
            {
                "key": level,
                "label": short_label(legend[level]),
                "full": legend[level],
                "p": float(probabilities.get(level, 0)),
                "selected": level == nearest,
            }
            for level in levels
        ],
    }


def present_noul(answer: dict) -> dict:
    probability = float(answer.get("noul") or 0)
    return {
        "type": "noul",
        "noul": probability,
        "yes": probability >= NOUL_YES,
        "threshold": NOUL_YES,
    }


def present_jev(cached: dict) -> dict:
    answers = cached["answers"]
    usage = cached.get("usage") or {}
    return {
        "model": cached.get("model") or JEV_MODEL,
        "profile": present_choice(answers["profile"]),
        "adoption": present_score(answers["adoption_readiness"]),
        "verification": present_noul(answers["needs_verification"]),
        "usage": {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "cost": usage.get("cost"),
        },
    }


def cached_result(row_id: str) -> dict | None:
    with _cache_lock:
        cached = _cache.get(row_id)
    if not cached:
        return None
    return present_jev(cached)


def top_labels(counter: Counter) -> list[str]:
    if not counter:
        return []
    best = max(counter.values())
    return [label for label, count in counter.items() if count == best]


def build_summary(rows: list[dict]) -> dict | None:
    """Toplu sayılar JEV'e tekrar sorulmaz; kart sonuçlarından hesaplanır."""
    profiles: Counter = Counter()
    areas: Counter = Counter()
    scores: list[float] = []
    high_verification = 0
    uncertain = 0
    decided = 0
    tokens_in = 0
    tokens_out = 0
    cost = 0.0

    for row in rows:
        if row.get("ai_usage_area"):
            areas[row["ai_usage_area"]] += 1
        jev = row.get("jev")
        if not jev:
            continue
        decided += 1
        profiles[jev["profile"]["label"]] += 1
        scores.append(jev["adoption"]["score"])
        if jev["verification"]["yes"]:
            high_verification += 1
        if jev["profile"]["uncertain"] or jev["adoption"]["uncertain"]:
            uncertain += 1
        usage = jev.get("usage") or {}
        tokens_in += int(usage.get("input_tokens") or 0)
        tokens_out += int(usage.get("output_tokens") or 0)
        cost += float(usage.get("cost") or 0)

    if decided == 0:
        return None

    return {
        "responses": len(rows),
        "decided": decided,
        "profiles": top_labels(profiles),
        "average_adoption": sum(scores) / len(scores),
        "adoption_max": next(
            (row["jev"]["adoption"]["max"] for row in rows if row.get("jev")),
            2,
        ),
        "high_verification": high_verification,
        "uncertain": uncertain,
        "usage_areas": top_labels(areas),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": cost,
    }


def public_row(row: dict, error: str | None = None) -> dict:
    jev = cached_result(row["id"])
    return {
        "id": row["id"],
        "number": row["number"],
        "timestamp": row["timestamp"],
        "ai_usage_area": row["ai_usage_area"],
        "trust_score": row["trust_score"],
        "benefit_answer": row["benefit_answer"],
        "concern_answer": row["concern_answer"],
        "state": row["state"],
        "jev": jev,
        "error": None if jev else error,
    }


def payload(rows: list[dict], errors: dict[str, str] | None = None) -> dict:
    errors = errors or {}
    public = [public_row(row, errors.get(row["id"])) for row in rows]
    return {"rows": public, "summary": build_summary(public), "model": JEV_MODEL}


def api_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=502, detail=str(exc))


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


@app.get("/")
def demo_panel():
    return FileResponse(ROOT / "demo_panel.html")


@app.get("/sunum")
def sunum():
    return FileResponse(ROOT / "sunum.html")


@app.get("/api/cevaplar")
def cevaplar():
    """Sheet'teki güncel satırlar. Varsa önbellekteki JEV sonucu da gelir."""
    try:
        rows = fetch_rows()
    except Exception as exc:
        raise api_error(exc) from exc
    print(f"Form: {len(rows)} cevap")
    return payload(rows)


@app.post("/api/analiz")
def analiz():
    """Sheet'i yeniden okur, yeni satırları JEV'e sorar, hepsini döner."""
    with _analyze_lock:
        try:
            rows = fetch_rows()
        except Exception as exc:
            raise api_error(exc) from exc
        print(f"Form: {len(rows)} cevap")
        errors = analyze(rows)
        return payload(rows, errors)


if __name__ == "__main__":
    import uvicorn

    print("Panel: http://127.0.0.1:8001")
    uvicorn.run(app, host="127.0.0.1", port=8001)
