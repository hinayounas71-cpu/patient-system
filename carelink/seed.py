"""Creates fake data: 1 admin, 3 doctors, 2 nurses, 20 patients (2 wards x 10 beds), 200 checkups.
Run once:  python seed.py"""
import random, datetime as dt
from db import service_client
import news2

PASSWORD = "Test@12345"
random.seed(7)
sb = service_client()

STAFF = [
    ("admin@hospital.test", "Admin Hospital", "admin", None),
    ("dr.ali@hospital.test", "Dr. Ali Raza", "doctor", None),
    ("dr.sara@hospital.test", "Dr. Sara Khan", "doctor", None),
    ("dr.omar@hospital.test", "Dr. Omar Farooq", "doctor", None),
    ("nurse.ayesha@hospital.test", "Nurse Ayesha", "nurse", "Ward A"),
    ("nurse.fatima@hospital.test", "Nurse Fatima", "nurse", "Ward B"),
]
NAMES = ["Imran Shah", "Bushra Bibi", "Tariq Mehmood", "Nasreen Akhtar", "Zahid Hussain",
         "Rukhsana Kausar", "Waseem Abbas", "Shazia Parveen", "Kamran Ali", "Samina Noor",
         "Farhan Iqbal", "Aneela Rafiq", "Javed Iqbal", "Mehwish Tariq", "Arif Hameed",
         "Sadia Yousaf", "Naveed Anjum", "Rabia Sultan", "Shahid Mahmood", "Humera Bashir"]


def get_or_create_user(email, name, role, ward):
    try:
        res = sb.auth.admin.create_user({"email": email, "password": PASSWORD, "email_confirm": True})
        uid = res.user.id
    except Exception:
        uid = next(u.id for u in sb.auth.admin.list_users() if u.email == email)
    sb.table("users").upsert({"id": uid, "full_name": name, "role": role, "ward": ward}).execute()
    return uid


ids = {r[0]: get_or_create_user(*r) for r in STAFF}
ali, sara, omar = ids["dr.ali@hospital.test"], ids["dr.sara@hospital.test"], ids["dr.omar@hospital.test"]

# doctor schedule: each doctor has a backup doctor
sb.table("doctor_schedule").upsert([
    {"doctor_id": ali, "on_duty": True, "backup_doctor_id": sara},
    {"doctor_id": sara, "on_duty": True, "backup_doctor_id": omar},
    {"doctor_id": omar, "on_duty": True, "backup_doctor_id": ali},
]).execute()

# patients
patients = []
for i, name in enumerate(NAMES):
    ward = "Ward A" if i < 10 else "Ward B"
    doc = (ali if i % 2 == 0 else sara) if ward == "Ward A" else (sara if i % 2 == 0 else omar)
    nurse = ids["nurse.ayesha@hospital.test"] if ward == "Ward A" else ids["nurse.fatima@hospital.test"]
    patients.append({"ward": ward, "bed_no": (i % 10) + 1, "full_name": name,
                     "age": random.randint(25, 80), "doctor_id": doc, "nurse_id": nurse})
patients = sb.table("patients").upsert(patients, on_conflict="ward,bed_no").execute().data


def vitals(unsafe):
    v = dict(resp_rate=random.randint(12, 20), spo2=random.randint(96, 99),
             systolic_bp=random.randint(111, 140), pulse=random.randint(51, 90),
             temp=round(random.uniform(36.1, 38.0), 1))
    if unsafe:
        for k in random.sample(list(v), random.randint(1, 3)):
            v[k] = {"resp_rate": random.randint(21, 28), "spo2": random.randint(88, 95),
                    "systolic_bp": random.randint(80, 105), "pulse": random.randint(111, 140),
                    "temp": round(random.uniform(38.5, 39.8), 1)}[k]
    return v


rows = []
now = dt.datetime.now(dt.timezone.utc)
for p in patients:
    for j in range(10):
        v = vitals(random.random() < 0.25)
        r = news2.check(v)
        rows.append({**v, "patient_id": p["id"], "nurse_id": p["nurse_id"],
                     "total_score": r.total, "max_single": r.max_single, "is_unsafe": r.unsafe,
                     "created_at": (now - dt.timedelta(hours=6 * (10 - j))).isoformat()})
sb.table("checkups").insert(rows).execute()
print(f"Done: {len(patients)} patients, {len(rows)} checkups, {len(STAFF)} users.")
print("Login password for all users:", PASSWORD)
