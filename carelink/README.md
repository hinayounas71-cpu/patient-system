# Cloud-Based Patient Handling System with ACL and Datasets

## Files
- schema.sql  : all 7 tables + ACL (Row Level Security) + locks
- seed.py     : fake data (6 users, 20 patients, 200 checkups)
- news2.py    : safe-limit rules (NEWS2, if-then, no AI)
- alerts.py   : alert + Telegram + 10-minute escalation to backup doctor
- app.py      : web app (Streamlit) - nurse, doctor, admin screens
- db.py       : cloud database connection
- test_news2.py : tests for the safe-limit rules

## Setup (about 20 minutes)
1. supabase.com -> New project (free). Wait until ready.
2. SQL Editor -> New query -> paste all of schema.sql -> Run.
3. Project Settings -> API: copy Project URL, anon key, service_role key.
4. Copy .env.example to .env and paste the 3 values.
5. In terminal:
       pip install -r requirements.txt
       python seed.py
       streamlit run app.py
6. Login (password for all: Test@12345):
       admin@hospital.test
       dr.ali@hospital.test / dr.sara@hospital.test / dr.omar@hospital.test
       nurse.ayesha@hospital.test (Ward A) / nurse.fatima@hospital.test (Ward B)

## Telegram (optional)
Telegram -> @BotFather -> /newbot -> copy token into .env (TELEGRAM_BOT_TOKEN).
Doctor presses Start on the bot. Get chat id from @userinfobot.
Admin screen -> Users -> paste chat id for that doctor.

## Demo for sir (5 steps)
1. Nurse Ayesha: Bed 5, oxygen 90 -> Save. "UNSAFE, alert sent".
2. Doctor (owner of that patient): Open alerts shows "Bed 5 (Ward A): oxygen 90%". Press OK, write advice.
3. Nurse screen: advice appears in 10 seconds.
4. Do not press OK -> after 10 min alert moves to backup doctor. After 10 more: nurse sees red warning.
5. Admin: Audit log shows who opened which patient. Admin cannot see checkups.

## ACL test list (matches proposal Testing section)
- Doctor A cannot see Doctor B's patient (unless active backup).
- Nurse cannot delete/change a checkup. Admin cannot see checkups. Not logged in = nothing.
- Safe checkup = no alert. Unsafe = alert. Off-duty doctor -> alert goes to backup.
- Every open of a patient adds an audit log line.
