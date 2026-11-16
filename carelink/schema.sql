-- Run this whole file once in Supabase: SQL Editor -> New query -> Run
-- ============ TABLES (datasets) ============
create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null,
  role text not null check (role in ('admin','doctor','nurse')),
  ward text,
  telegram_chat_id text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table public.patients (
  id uuid primary key default gen_random_uuid(),
  ward text not null,
  bed_no int not null,
  full_name text not null,
  age int not null,
  doctor_id uuid not null references public.users(id),
  nurse_id uuid references public.users(id),
  created_at timestamptz not null default now(),
  unique (ward, bed_no)
);

create table public.checkups (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patients(id),
  nurse_id uuid not null references public.users(id),
  resp_rate int not null,
  spo2 int not null,
  systolic_bp int not null,
  pulse int not null,
  temp numeric(4,1) not null,
  total_score int not null,
  max_single int not null,
  is_unsafe boolean not null,
  created_at timestamptz not null default now()
);

create table public.advice (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patients(id),
  doctor_id uuid not null references public.users(id),
  advice_text text not null,
  created_at timestamptz not null default now()
);

create table public.doctor_schedule (
  doctor_id uuid primary key references public.users(id),
  on_duty boolean not null default true,
  backup_doctor_id uuid references public.users(id)
);

create table public.alerts (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patients(id),
  checkup_id uuid references public.checkups(id),
  doctor_id uuid not null references public.users(id),          -- who has the alert now
  original_doctor_id uuid not null references public.users(id),
  message text not null,
  status text not null default 'sent' check (status in ('sent','seen','moved','unanswered')),
  sent_at timestamptz not null default now(),
  moved_at timestamptz,
  seen_at timestamptz
);

create table public.audit_log (
  id bigint generated always as identity primary key,
  user_id uuid not null references public.users(id),
  patient_id uuid not null references public.patients(id),
  action text not null,
  created_at timestamptz not null default now()
);

-- ============ HELPER FUNCTIONS ============
create or replace function public.app_role() returns text
language sql stable security definer set search_path = public as
$$ select role from public.users where id = auth.uid() and active $$;

create or replace function public.app_ward() returns text
language sql stable security definer set search_path = public as
$$ select ward from public.users where id = auth.uid() and active $$;

-- Doctor can see a patient if: own patient, OR active backup (covering doctor is off duty),
-- OR an alert for that patient was sent to him in the last 2 hours.
create or replace function public.can_doctor_see(p_patient uuid) returns boolean
language sql stable security definer set search_path = public as
$$
  select public.app_role() = 'doctor' and exists (
    select 1 from public.patients p
    where p.id = p_patient and (
      p.doctor_id = auth.uid()
      or exists (select 1 from public.doctor_schedule ds
                 where ds.doctor_id = p.doctor_id and ds.on_duty = false
                   and ds.backup_doctor_id = auth.uid())
      or exists (select 1 from public.alerts a
                 where a.patient_id = p.id and a.doctor_id = auth.uid()
                   and a.sent_at > now() - interval '2 hours')
    )
  )
$$;

create or replace function public.nurse_ward_has(p_patient uuid) returns boolean
language sql stable security definer set search_path = public as
$$
  select public.app_role() = 'nurse' and exists (
    select 1 from public.patients p where p.id = p_patient and p.ward = public.app_ward())
$$;

-- Doctor changes only his own duty status
create or replace function public.set_my_duty(p_on_duty boolean) returns void
language sql security definer set search_path = public as
$$ update public.doctor_schedule set on_duty = p_on_duty
   where doctor_id = auth.uid() and public.app_role() = 'doctor' $$;

-- Names only (no telegram id) for everyone who is logged in
create or replace view public.staff_directory as
  select id, full_name, role, ward from public.users where active;

-- ============ NOBODY CAN CHANGE OR DELETE (even service key) ============
create or replace function public.block_change() returns trigger
language plpgsql as $$ begin raise exception 'Records cannot be changed or deleted'; end $$;

create trigger checkups_locked before update or delete on public.checkups
  for each row execute function public.block_change();
create trigger audit_locked before update or delete on public.audit_log
  for each row execute function public.block_change();
create trigger advice_locked before update or delete on public.advice
  for each row execute function public.block_change();

-- ============ ACL (Row Level Security) ============
alter table public.users enable row level security;
alter table public.patients enable row level security;
alter table public.checkups enable row level security;
alter table public.advice enable row level security;
alter table public.doctor_schedule enable row level security;
alter table public.alerts enable row level security;
alter table public.audit_log enable row level security;

-- users: admin full access, everyone can read own row
create policy users_self on public.users for select using (id = auth.uid());
create policy users_admin_select on public.users for select using (public.app_role() = 'admin');
create policy users_admin_insert on public.users for insert with check (public.app_role() = 'admin');
create policy users_admin_update on public.users for update using (public.app_role() = 'admin');

-- patients
create policy patients_admin_select on public.patients for select using (public.app_role() = 'admin');
create policy patients_admin_insert on public.patients for insert with check (public.app_role() = 'admin');
create policy patients_admin_update on public.patients for update using (public.app_role() = 'admin');
create policy patients_doctor on public.patients for select using (public.can_doctor_see(id));
create policy patients_nurse on public.patients for select
  using (public.app_role() = 'nurse' and ward = public.app_ward());

-- checkups (admin has NO policy -> cannot see)
create policy checkups_doctor on public.checkups for select using (public.can_doctor_see(patient_id));
create policy checkups_nurse_select on public.checkups for select using (public.nurse_ward_has(patient_id));
create policy checkups_nurse_insert on public.checkups for insert
  with check (nurse_id = auth.uid() and public.nurse_ward_has(patient_id));

-- advice (admin has NO policy)
create policy advice_doctor_select on public.advice for select using (public.can_doctor_see(patient_id));
create policy advice_doctor_insert on public.advice for insert
  with check (doctor_id = auth.uid() and public.can_doctor_see(patient_id));
create policy advice_nurse on public.advice for select using (public.nurse_ward_has(patient_id));

-- alerts (inserted only by the server with service key)
create policy alerts_doctor_select on public.alerts for select
  using (public.app_role() = 'doctor' and doctor_id = auth.uid());
create policy alerts_doctor_update on public.alerts for update
  using (public.app_role() = 'doctor' and doctor_id = auth.uid());
create policy alerts_nurse on public.alerts for select using (public.nurse_ward_has(patient_id));

-- doctor_schedule
create policy sched_admin_select on public.doctor_schedule for select using (public.app_role() = 'admin');
create policy sched_admin_insert on public.doctor_schedule for insert with check (public.app_role() = 'admin');
create policy sched_admin_update on public.doctor_schedule for update using (public.app_role() = 'admin');
create policy sched_doctor on public.doctor_schedule for select
  using (public.app_role() = 'doctor' and (doctor_id = auth.uid() or backup_doctor_id = auth.uid()));

-- audit_log: only admin can read. Inserts come from the server (service key).
create policy audit_admin on public.audit_log for select using (public.app_role() = 'admin');

-- Anonymous (not logged in) users get nothing
revoke all on all tables in schema public from anon;
revoke all on all functions in schema public from anon;
grant select on public.staff_directory to authenticated;
-- the view is owned by postgres, so it shows names only. anon is blocked above.
-- ============ DONE ============
