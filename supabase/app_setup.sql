-- =====================================================================
-- Wallet Flutter app: secure API layer.
-- Run ONCE in Supabase > SQL Editor (after your normal schema.sql).
--
-- * Adds ONE new column (users.auth_id) and new functions only.
-- * Does not change any existing table permission, policy or function,
--   so the website (Flask / Vercel) keeps working exactly as before.
-- * The app never touches tables. It only calls the api_* functions below,
--   and every one of them works for the signed-in person only.
-- =====================================================================

alter table users add column if not exists auth_id uuid unique references auth.users(id) on delete set null;

-- the wallet user id of the signed-in person (raises if there is none)
create or replace function app_need() returns bigint
language plpgsql stable security definer set search_path = public as $$
declare u bigint;
begin
  select id into u from users where auth_id = auth.uid();
  if u is null then raise exception 'no_profile' using errcode = '42501'; end if;
  return u;
end $$;

-- can this username still be registered? (callable before sign-up)
create or replace function app_username_free(p_username text) returns boolean
language sql stable security definer set search_path = public as $$
  select not exists (select 1 from users where username = lower(trim(p_username)));
$$;

-- columns the website already uses for Google users (safe if they exist)
alter table users add column if not exists google_id text;
alter table users add column if not exists google_only boolean default false;

-- first sign-in: create (or claim) the wallet profile. Does nothing if it already exists.
--  * Google sign-in: claims the website account made with the same Google account, else creates a new one.
--  * Username/password sign-in: creates a new profile.
create or replace function app_bootstrap(p_username text, p_account_name text default 'Main')
returns bigint language plpgsql security definer set search_path = public as $$
declare uid bigint; un text := lower(trim(p_username)); gid text; em text; base text; n int := 0;
        acc_name text := left(coalesce(nullif(trim(p_account_name), ''), 'Main'), 40);
begin
  if auth.uid() is null then raise exception 'not_signed_in' using errcode = '42501'; end if;
  select id into uid from users where auth_id = auth.uid();
  if uid is not null then return uid; end if;

  select i.provider_id, lower(coalesce(i.identity_data->>'email', '')) into gid, em
    from auth.identities i where i.user_id = auth.uid() and i.provider = 'google' limit 1;

  if gid is not null then
    -- an old website account made with this same Google account? take it over (keeps all its data)
    select id into uid from users
      where auth_id is null and (google_id = gid or (coalesce(google_only, false) and em <> '' and lower(email) = em))
      order by (google_id = gid) desc nulls last limit 1;
    if uid is not null then
      update users set auth_id = auth.uid(), google_id = gid where id = uid;
      return uid;
    end if;
    base := left(regexp_replace(split_part(em, '@', 1), '[^a-z0-9._-]', '', 'g'), 24);
    if length(base) < 3 then base := 'user' || base; end if;
    un := base;
    while exists (select 1 from users where username = un) and n < 50 loop
      n := n + 1;
      un := base || (1000 + floor(random() * 9000))::int;
    end loop;
    insert into users(username, pw, auth_id, google_id, email, google_only)
      values (un, 'app-only', auth.uid(), gid, nullif(em, ''), true) returning id into uid;
    insert into accounts(user_id, name, currency) values (uid, acc_name, 'IQD');
    return uid;
  end if;

  if un !~ '^[a-z0-9._-]{3,30}$' then raise exception 'short'; end if;
  if exists (select 1 from users where username = un) then raise exception 'taken' using errcode = '23505'; end if;
  -- pw stays unusable for the website login ('app-only' is not a valid hash)
  insert into users(username, pw, auth_id) values (un, 'app-only', auth.uid()) returning id into uid;
  insert into accounts(user_id, name, currency) values (uid, acc_name, 'IQD');
  return uid;
end $$;

-- ---------- main screen ----------
create or replace function api_dashboard(p_acc bigint, p_today date, p_week date, p_month date, p_from date, p_to date)
returns jsonb language plpgsql security definer set search_path = public as $$
declare u bigint := app_need();
begin
  perform run_recurring(u, p_today);
  perform app_purge_archive(u);
  return dashboard(u, p_acc, p_today, p_week, p_month, p_from, p_to);
end $$;

-- ---------- entries ----------
create or replace function api_add_tx(p_acc bigint, p_type text, p_amount numeric, p_label text, p_note text, p_date date,
                                      p_method text default null, p_side text default null)
returns bigint language plpgsql security definer set search_path = public as $$
declare u bigint := app_need();
begin
  if p_type not in ('income', 'expense') or p_amount is null or p_amount <= 0 then raise exception 'bad_input'; end if;
  return add_tx(u, p_acc, p_type, p_amount, left(coalesce(p_label, ''), 120), left(coalesce(p_note, ''), 500),
                coalesce(p_date, current_date), null, p_method, p_side);
end $$;

create or replace function api_edit_tx(p_id bigint, p_amount numeric, p_label text, p_note text, p_date date)
returns boolean language plpgsql security definer set search_path = public as $$
declare u bigint := app_need();
begin
  if p_amount is null or p_amount <= 0 then raise exception 'bad_input'; end if;
  return edit_tx(u, p_id, p_amount, left(coalesce(p_label, ''), 120), left(coalesce(p_note, ''), 500), coalesce(p_date, current_date));
end $$;

create or replace function api_del_tx(p_id bigint) returns jsonb
language plpgsql security definer set search_path = public as $$
declare u bigint := app_need();
begin
  return del_tx(u, p_id);
end $$;

create or replace function api_transfer(p_from bigint, p_to bigint, p_amount numeric, p_amount_in numeric, p_note text, p_date date)
returns boolean language plpgsql security definer set search_path = public as $$
declare u bigint := app_need();
begin
  return transfer(u, p_from, p_to, p_amount, p_amount_in, left(coalesce(p_note, ''), 500), coalesce(p_date, current_date));
end $$;

-- ---------- accounts ----------
create or replace function api_new_account(p_name text, p_currency text, p_opening numeric default 0)
returns bigint language plpgsql security definer set search_path = public as $$
declare u bigint := app_need(); new_id bigint;
begin
  if coalesce(trim(p_name), '') = '' or p_currency not in ('IQD', 'USD') then raise exception 'bad_input'; end if;
  insert into accounts(user_id, name, currency, opening) values (u, left(trim(p_name), 40), p_currency, coalesce(p_opening, 0))
    returning id into new_id;
  return new_id;
end $$;

create or replace function api_delete_account(p_acc bigint) returns boolean
language plpgsql security definer set search_path = public as $$
declare u bigint := app_need(); n int;
begin
  select count(*) into n from accounts where user_id = u and kind = 'personal';
  if n <= 1 or not exists (select 1 from accounts where id = p_acc and user_id = u and kind = 'personal') then return false; end if;
  delete from tx where account_id = p_acc;
  delete from accounts where id = p_acc and user_id = u;
  return true;
end $$;

create or replace function api_set_budget(p_acc bigint, p_budget numeric) returns boolean
language plpgsql security definer set search_path = public as $$
declare u bigint := app_need();
begin
  update accounts set budget = greatest(0, coalesce(p_budget, 0)) where id = p_acc and user_id = u and kind = 'personal';
  return found;
end $$;

-- ---------- cases ----------
create or replace function api_case_view(p_case bigint) returns jsonb
language plpgsql security definer set search_path = public as $$
declare u bigint := app_need();
begin
  return case_view(u, p_case);
end $$;

create or replace function api_new_case(p_name text, p_currency text, p_clients text[], p_parties text[], p_case_no text,
                                        p_court text, p_fee numeric, p_ctype text, p_started date, p_hearing date,
                                        p_price numeric default 0, p_advance numeric default 0)
returns bigint language plpgsql security definer set search_path = public as $$
declare u bigint := app_need(); new_id bigint; cl text[]; pa text[]; st date := coalesce(p_started, current_date);
begin
  if coalesce(trim(p_name), '') = '' or p_currency not in ('IQD', 'USD') then raise exception 'bad_input'; end if;
  select coalesce(array_agg(x), '{}') into cl from (select distinct left(trim(v), 80) as x from unnest(coalesce(p_clients, '{}')) v where trim(v) <> '' limit 12) s;
  select coalesce(array_agg(x), '{}') into pa from (select distinct left(trim(v), 80) as x from unnest(coalesce(p_parties, '{}')) v where trim(v) <> '' limit 12) s;
  insert into accounts(user_id, kind, name, currency, opening, client, clients, party, parties, case_no, court, fee,
                       case_type, started, hearing, price)
    values (u, 'case', left(trim(p_name), 80), p_currency, 0, left(array_to_string(cl, ' + '), 200), cl,
            left(array_to_string(pa, ' + '), 200), pa, left(coalesce(p_case_no, ''), 40), left(coalesce(p_court, ''), 80),
            greatest(0, coalesce(p_fee, 0)), case when p_ctype in ('court', 'house', 'car', 'other') then p_ctype else 'court' end,
            st, p_hearing, greatest(0, coalesce(p_price, 0)))
    returning id into new_id;
  if coalesce(p_advance, 0) > 0 then
    perform add_tx(u, new_id, 'income', p_advance, 'Advance', '', st, null);
  end if;
  return new_id;
end $$;

create or replace function api_case_status(p_case bigint, p_status text) returns boolean
language plpgsql security definer set search_path = public as $$
declare u bigint := app_need(); nm text;
begin
  if p_status not in ('open', 'closed') then return false; end if;
  update accounts set status = p_status,
                      archive_kind = case when p_status = 'closed' then 'finished' else null end
    where id = p_case and user_id = u and kind = 'case'
    returning name into nm;
  if not found then return false; end if;
  insert into case_log(user_id, case_id, case_name, event)
    values (u, p_case, nm, case when p_status = 'closed' then 'finished' else 'restored' end);
  return true;
end $$;

create or replace function api_delete_case(p_case bigint) returns boolean
language plpgsql security definer set search_path = public as $$
declare u bigint := app_need(); nm text;
begin
  update accounts set status = 'closed', archive_kind = 'deleted', closed_at = now()
    where id = p_case and user_id = u and kind = 'case'
    returning name into nm;
  if not found then return false; end if;
  insert into case_log(user_id, case_id, case_name, event) values (u, p_case, nm, 'deleted');
  return true;
end $$;

-- delete forever, right now (only for cases that are already in the archive)
create or replace function api_purge_case(p_case bigint) returns boolean
language plpgsql security definer set search_path = public as $$
declare u bigint := app_need(); nm text;
begin
  select name into nm from accounts where id = p_case and user_id = u and kind = 'case' and status = 'closed';
  if not found then return false; end if;
  insert into case_log(user_id, case_id, case_name, event) values (u, p_case, nm, 'purged');
  delete from tx where account_id = p_case;
  delete from accounts where id = p_case and user_id = u;
  return true;
end $$;

-- ---------- archive: finished cases are kept for N days, then deleted ----------
alter table accounts add column if not exists closed_at timestamptz;
alter table accounts add column if not exists archive_kind text;   -- 'finished' | 'deleted'

-- written record of every finish / delete / restore / permanent delete (kept after the case is gone)
create table if not exists case_log (
  id bigint generated always as identity primary key,
  user_id bigint not null,
  case_id bigint,
  case_name text,
  event text not null,
  at timestamptz not null default now()
);
alter table case_log enable row level security;   -- no policies: only the api_* functions can read it

-- how many days a finished case stays in the archive (0 = keep forever)
create or replace function app_archive_days() returns int language sql immutable as $$ select 30 $$;

-- stamps/clears closed_at whenever a case is closed/reopened (from the app OR the website)
create or replace function trg_case_closed() returns trigger language plpgsql as $$
begin
  if new.kind = 'case' and new.status is distinct from old.status then
    new.closed_at := case when new.status = 'closed' then now() else null end;
  end if;
  return new;
end $$;
drop trigger if exists case_closed_at on accounts;
create trigger case_closed_at before update of status on accounts
  for each row execute function trg_case_closed();

-- cases that were already closed before this feature get their 30 days starting now;
-- then expired ones are deleted
create or replace function app_purge_archive(p_user bigint) returns void
language plpgsql security definer set search_path = public as $$
declare d int := app_archive_days(); ids bigint[];
begin
  update accounts set closed_at = now()
    where user_id = p_user and kind = 'case' and status = 'closed' and closed_at is null;
  if d > 0 then
    select coalesce(array_agg(id), '{}') into ids from accounts
      where user_id = p_user and kind = 'case' and status = 'closed' and closed_at < now() - make_interval(days => d);
    if coalesce(array_length(ids, 1), 0) > 0 then
      insert into case_log(user_id, case_id, case_name, event)
        select user_id, id, name, 'expired' from accounts where id = any(ids);
      delete from tx where account_id = any(ids);
      delete from accounts where id = any(ids);
    end if;
  end if;
end $$;

create or replace function api_archive() returns jsonb
language plpgsql security definer set search_path = public as $$
declare u bigint := app_need(); d int := app_archive_days();
begin
  perform app_purge_archive(u);
  return jsonb_build_object('days', d,
    'items', coalesce((
      select jsonb_agg(jsonb_build_object(
          'id', a.id, 'name', a.name, 'client', a.client, 'currency', a.currency, 'case_no', a.case_no,
          'court', a.court, 'fee', a.fee, 'closed_at', a.closed_at, 'kind', coalesce(a.archive_kind, 'finished'),
          'days_left', case when d > 0 then greatest(0, ceil(extract(epoch from (a.closed_at + make_interval(days => d) - now())) / 86400))::int else null end,
          'inc', coalesce((select sum(t.amount) from tx t where t.account_id = a.id and t.type = 'income'), 0),
          'exp', coalesce((select sum(t.amount) from tx t where t.account_id = a.id and t.type = 'expense'), 0))
        order by a.closed_at desc)
      from accounts a where a.user_id = u and a.kind = 'case' and a.status = 'closed'), '[]'::jsonb),
    'log', coalesce((
      select jsonb_agg(jsonb_build_object('name', l.case_name, 'event', l.event, 'at', l.at) order by l.at desc)
      from (select * from case_log where user_id = u order by at desc limit 50) l), '[]'::jsonb));
end $$;

-- ---------- profile ----------
create or replace function api_profile() returns jsonb
language plpgsql stable security definer set search_path = public as $$
declare u bigint := app_need();
begin
  return (select jsonb_build_object('id', id, 'username', username, 'display_name', coalesce(display_name, ''),
                                    'phone', coalesce(phone, ''), 'office', coalesce(office, ''))
          from users where id = u);
end $$;

create or replace function api_set_profile(p_display_name text, p_phone text, p_office text) returns boolean
language plpgsql security definer set search_path = public as $$
declare u bigint := app_need();
begin
  update users set display_name = left(coalesce(p_display_name, ''), 80), phone = left(coalesce(p_phone, ''), 40),
                   office = left(coalesce(p_office, ''), 120) where id = u;
  return true;
end $$;

-- ---------- permissions: only signed-in people may call the api, nothing else ----------
do $$
declare f text;
begin
  for f in
    select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public' and (p.proname like 'api\_%' or p.proname in ('app_bootstrap', 'app_username_free', 'app_need', 'app_purge_archive', 'app_archive_days'))
  loop
    execute format('revoke all on function %s from public, anon, authenticated', f);
    if f not like 'app_need%' and f not like 'app_purge_archive%' and f not like 'app_archive_days%' then
      execute format('grant execute on function %s to authenticated', f);
    end if;
    if f like 'app_username_free%' then
      execute format('grant execute on function %s to anon', f);
    end if;
  end loop;
end $$;

notify pgrst, 'reload schema';
