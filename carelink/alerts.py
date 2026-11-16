"""Alert creation, Telegram sending and 10-minute escalation to the backup doctor."""
import datetime as dt
import requests
from db import cfg

ESCALATE_MINUTES = 10


def now():
    return dt.datetime.now(dt.timezone.utc)


def send_telegram(chat_id, text):
    """Optional. Returns True if sent. If no token/chat id, we just skip (on-screen alert still works)."""
    if not chat_id:
        return False
    try:
        token = cfg("TELEGRAM_BOT_TOKEN")
    except RuntimeError:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        return r.ok
    except requests.RequestException:
        return False


def _schedule(sb, doctor_id):
    rows = sb.table("doctor_schedule").select("*").eq("doctor_id", doctor_id).execute().data
    return rows[0] if rows else None


def _chat_id(sb, user_id):
    rows = sb.table("users").select("telegram_chat_id").eq("id", user_id).execute().data
    return rows[0]["telegram_chat_id"] if rows else None


def create_alert(sb, patient, checkup_id, result):
    """sb = service client. If the doctor is off duty, the alert goes straight to the backup doctor."""
    sched = _schedule(sb, patient["doctor_id"])
    to_id, status, moved_at = patient["doctor_id"], "sent", None
    if sched and not sched["on_duty"] and sched["backup_doctor_id"]:
        to_id, status, moved_at = sched["backup_doctor_id"], "moved", now().isoformat()

    # Message has bed number and unsafe values only. No patient name.
    msg = f"Bed {patient['bed_no']} ({patient['ward']}): {result.summary}"
    sb.table("alerts").insert({
        "patient_id": patient["id"],
        "checkup_id": checkup_id,
        "doctor_id": to_id,
        "original_doctor_id": patient["doctor_id"],
        "message": msg,
        "status": status,
        "moved_at": moved_at,
    }).execute()
    send_telegram(_chat_id(sb, to_id), msg)


def escalate_pending(sb):
    """Run every ~30 seconds. sb = service client."""
    cutoff = (now() - dt.timedelta(minutes=ESCALATE_MINUTES)).isoformat()

    # 1) Doctor did not press OK in 10 minutes -> backup doctor
    for a in sb.table("alerts").select("*").eq("status", "sent").lt("sent_at", cutoff).execute().data:
        sched = _schedule(sb, a["doctor_id"])
        backup = sched["backup_doctor_id"] if sched else None
        if backup and backup != a["doctor_id"]:
            sb.table("alerts").update({
                "doctor_id": backup, "status": "moved", "moved_at": now().isoformat()
            }).eq("id", a["id"]).execute()
            send_telegram(_chat_id(sb, backup), a["message"] + " (not answered by first doctor)")
        else:
            sb.table("alerts").update({"status": "unanswered"}).eq("id", a["id"]).execute()

    # 2) Backup doctor also did not reply in 10 minutes -> nurse sees red warning
    for a in sb.table("alerts").select("*").eq("status", "moved").lt("moved_at", cutoff).execute().data:
        sb.table("alerts").update({"status": "unanswered"}).eq("id", a["id"]).execute()
