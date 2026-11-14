-- Supabase > SQL Editor > paste > Run
-- Safe for a fresh install AND for upgrading the previous version (keeps your data).

create table if not exists users (
  id bigint generated always as identity primary key,
  username text unique not null,
  pw text not null,
  created timestamptz default now()
);

create table if not exists accounts (
  id bigint generated always as identity primary key,
  user_id bigint not null references users(id) on delete cascade,
  name text not null,
  currency text not null default 'IQD' check (currency in ('IQD','USD')),
  opening numeric(16,2) not null default 0,
  created timestamptz default now()
);

create table if not exists tx (
  id bigint generated always as identity primary key,
  user_id bigint not null references users(id) on delete cascade,
  account_id bigint references accounts(id) on delete cascade,
  type text not null check (type in ('income','expense')),
  amount numeric(16,2) not null check (amount > 0),
  label text default '',
  note text default '',
  date date not null default current_date,
  img text,
  created timestamptz default now()
);

-- upgrade from v1: add account_id, give every user a main account, move old rows into it
alter table tx add column if not exists account_id bigint references accounts(id) on delete cascade;
insert into accounts (user_id, name, currency)
  select u.id, 'Main', 'IQD' from users u
  where not exists (select 1 from accounts a where a.user_id = u.id);
update tx set account_id = (select min(a.id) from accounts a where a.user_id = tx.user_id)
  where account_id is null;
alter table tx alter column account_id set not null;

create index if not exists tx_acc_date on tx(account_id, date desc);
create index if not exists acc_user on accounts(user_id);

-- only the server (service key) may touch the tables
alter table users enable row level security;
alter table accounts enable row level security;
alter table tx enable row level security;

-- legal cases (stored as accounts of kind 'case') + office name
alter table accounts add column if not exists kind text not null default 'personal';
alter table accounts add column if not exists client text default '';
alter table accounts add column if not exists case_no text default '';
alter table accounts add column if not exists court text default '';
alter table accounts add column if not exists fee numeric(16,2) not null default 0;
alter table accounts add column if not exists status text not null default 'open';
alter table users add column if not exists office text default '';

-- v12: payment channel + side on entries, buyer/seller names, client debts
alter table tx add column if not exists method text;
alter table tx add column if not exists side text;
alter table accounts add column if not exists buyer text default '';
alter table accounts add column if not exists seller text default '';

-- v13: several clients and several opposing parties on every case (no buyer / seller)
alter table accounts add column if not exists clients text[] not null default '{}';
alter table accounts add column if not exists parties text[] not null default '{}';
update accounts set clients = array[trim(client)]
  where kind = 'case' and clients = '{}' and coalesce(trim(client), '') <> '';
update accounts set parties = array_remove(array[nullif(trim(party), ''), nullif(trim(buyer), ''), nullif(trim(seller), '')], null)
  where kind = 'case' and parties = '{}' and (coalesce(trim(party), '') <> '' or coalesce(trim(buyer), '') <> '' or coalesce(trim(seller), '') <> '');
update tx set side = 'client' where side = 'buyer';
update tx set side = 'party' where side = 'seller';

-- v10: case types (court / house / car / other) and Google sign-in
alter table accounts add column if not exists case_type text not null default 'court';
alter table accounts add column if not exists party text default '';
alter table accounts add column if not exists price numeric(16,2) not null default 0;
alter table users add column if not exists google_id text;
alter table users add column if not exists email text;
alter table users add column if not exists google_only boolean not null default false;
create unique index if not exists users_google on users(google_id) where google_id is not null;

-- v8: profile (name, photo), print letterhead (phone, logo), case start date
alter table users add column if not exists display_name text default '';
alter table users add column if not exists phone text default '';
alter table users add column if not exists avatar text;
alter table users add column if not exists logo text;
alter table accounts add column if not exists started date;

-- v6: budget, court hearing date, recurring entries
alter table accounts add column if not exists budget numeric(16,2) not null default 0;
alter table accounts add column if not exists hearing date;
create table if not exists recurring (
  id bigint generated always as identity primary key,
  user_id bigint not null references users(id) on delete cascade,
  account_id bigint not null references accounts(id) on delete cascade,
  type text not null check (type in ('income','expense')),
  amount numeric(16,2) not null check (amount > 0),
  label text default '',
  note text default '',
  day int not null check (day between 1 and 28),
  next_date date not null,
  active boolean not null default true,
  created timestamptz default now()
);
alter table recurring enable row level security;

create or replace function run_recurring(p_user bigint, p_today date)
returns int language plpgsql as $$
declare r record; n int := 0; d date;
begin
  for r in select * from recurring where user_id = p_user and active and next_date <= p_today loop
    d := r.next_date;
    while d <= p_today loop
      insert into tx(user_id, account_id, type, amount, label, note, date)
        values (r.user_id, r.account_id, r.type, r.amount, r.label, r.note, d);
      n := n + 1;
      d := (date_trunc('month', d)::date + interval '1 month')::date + (r.day - 1);
    end loop;
    update recurring set next_date = d where id = r.id;
  end loop;
  return n;
end $$;

-- v7: shared accounts, transfers between accounts
create table if not exists account_members (
  account_id bigint not null references accounts(id) on delete cascade,
  user_id bigint not null references users(id) on delete cascade,
  role text not null default 'editor' check (role in ('editor','viewer')),
  accepted boolean not null default false,
  created timestamptz default now(),
  primary key (account_id, user_id)
);
alter table account_members enable row level security;
alter table tx add column if not exists kind text not null default 'normal';
alter table tx add column if not exists pair bigint;
create index if not exists tx_pair on tx(pair);

-- 'owner' | 'editor' | 'viewer' | null (no access)
create or replace function acc_role(p_user bigint, p_acc bigint)
returns text language sql stable as $$
  select case when a.user_id = p_user then 'owner'
    else (select m.role from account_members m where m.account_id = a.id and m.user_id = p_user and m.accepted) end
  from accounts a where a.id = p_acc;
$$;

drop function if exists add_tx(bigint, bigint, text, numeric, text, text, date, text);
create or replace function add_tx(p_user bigint, p_acc bigint, p_type text, p_amount numeric,
                                  p_label text, p_note text, p_date date, p_img text,
                                  p_method text default null, p_side text default null)
returns bigint language plpgsql as $$
declare r text; new_id bigint;
begin
  r := acc_role(p_user, p_acc);
  if r is null or r = 'viewer' then raise exception 'forbidden' using errcode = '42501'; end if;
  insert into tx(user_id, account_id, type, amount, label, note, date, img, method, side)
    values (p_user, p_acc, p_type, p_amount, p_label, p_note, p_date, p_img, nullif(p_method, ''),
            case when p_side in ('client', 'party') then p_side else null end) returning id into new_id;
  return new_id;
end $$;

drop function if exists edit_tx(bigint, bigint, numeric, text, text, date);
create or replace function edit_tx(p_user bigint, p_id bigint, p_amount numeric, p_label text, p_note text, p_date date,
                                   p_method text default null, p_side text default null, p_set_extra boolean default false)
returns boolean language plpgsql as $$
declare t tx%rowtype; r text;
begin
  select * into t from tx where id = p_id;
  if not found then return false; end if;
  r := acc_role(p_user, t.account_id);
  if r is null or r = 'viewer' or t.kind <> 'normal' or (r = 'editor' and t.user_id <> p_user) then return false; end if;
  update tx set amount = p_amount, label = p_label, note = p_note, date = p_date,
    method = case when p_set_extra then nullif(p_method, '') else method end,
    side = case when p_set_extra then (case when p_side in ('client', 'party') then p_side else null end) else side end
  where id = p_id;
  return true;
end $$;

-- deletes an entry (and the other half of a transfer); returns the photo paths to clean up
create or replace function del_tx(p_user bigint, p_id bigint)
returns jsonb language plpgsql as $$
declare t tx%rowtype; r text; imgs jsonb := '[]'::jsonb;
begin
  select * into t from tx where id = p_id;
  if not found then return null; end if;
  r := acc_role(p_user, t.account_id);
  if r is null or r = 'viewer' or (r = 'editor' and t.user_id <> p_user) then return null; end if;
  if t.kind = 'transfer' and t.pair is not null then delete from tx where id = t.pair; end if;
  delete from tx where id = p_id;
  if t.img is not null then imgs := imgs || to_jsonb(t.img); end if;
  return jsonb_build_object('ok', true, 'imgs', imgs);
end $$;

-- moves money between two accounts you can edit; different currencies need p_amount_in
create or replace function transfer(p_user bigint, p_from bigint, p_to bigint, p_amount numeric,
                                    p_amount_in numeric, p_note text, p_date date)
returns boolean language plpgsql as $$
declare a1 accounts%rowtype; a2 accounts%rowtype; r1 text; r2 text; amt2 numeric; id1 bigint; id2 bigint;
begin
  if p_from = p_to or p_amount is null or p_amount <= 0 then return false; end if;
  select * into a1 from accounts where id = p_from and kind = 'personal';
  select * into a2 from accounts where id = p_to and kind = 'personal';
  if a1.id is null or a2.id is null then return false; end if;
  r1 := acc_role(p_user, p_from); r2 := acc_role(p_user, p_to);
  if r1 is null or r1 = 'viewer' or r2 is null or r2 = 'viewer' then return false; end if;
  if a1.currency = a2.currency then amt2 := p_amount;
  else
    if p_amount_in is null or p_amount_in <= 0 then return false; end if;
    amt2 := p_amount_in;
  end if;
  insert into tx(user_id, account_id, type, amount, label, note, date, kind)
    values (p_user, p_from, 'expense', p_amount, a2.name, coalesce(p_note, ''), p_date, 'transfer') returning id into id1;
  insert into tx(user_id, account_id, type, amount, label, note, date, kind, pair)
    values (p_user, p_to, 'income', amt2, a1.name, coalesce(p_note, ''), p_date, 'transfer', id1) returning id into id2;
  update tx set pair = id2 where id = id1;
  return true;
end $$;

-- everything the main screen needs in ONE call (personal accounts you own or that are shared with you)
drop function if exists dashboard(bigint, bigint, date, date, date, date, date);
create or replace function dashboard(
  p_user bigint, p_acc bigint,
  p_today date, p_week date, p_month date, p_from date, p_to date)
returns jsonb language sql stable as $$
with mine as (
  select a.id from accounts a
  where a.kind = 'personal' and (a.user_id = p_user or exists (
    select 1 from account_members m where m.account_id = a.id and m.user_id = p_user and m.accepted))),
cur as (
  select coalesce((select id from mine where id = p_acc),
                  (select min(a.id) from accounts a where a.user_id = p_user and a.kind = 'personal'),
                  (select min(id) from mine)) as id)
select jsonb_build_object(
  'acc', (select id from cur),
  'accounts', coalesce((select jsonb_agg(jsonb_build_object('id', x.id, 'name', x.name, 'currency', x.currency,
        'ni', (select count(*) from tx t where t.account_id = x.id and t.type = 'income' and t.kind = 'normal'),
        'ne', (select count(*) from tx t where t.account_id = x.id and t.type = 'expense' and t.kind = 'normal'),
        'budget', x.budget, 'role', acc_role(p_user, x.id),
        'owner', (select u.username from users u where u.id = x.user_id),
        'shared', (x.user_id <> p_user or exists (select 1 from account_members m where m.account_id = x.id and m.accepted)))
        order by (x.user_id <> p_user), x.id)
      from accounts x where x.id in (select id from mine)), '[]'::jsonb),
  'invites', coalesce((select jsonb_agg(jsonb_build_object('acc', m.account_id, 'name', a.name, 'role', m.role, 'kind', a.kind,
        'owner', (select u.username from users u where u.id = a.user_id)))
      from account_members m join accounts a on a.id = m.account_id
      where m.user_id = p_user and not m.accepted), '[]'::jsonb),
  'members', coalesce((select jsonb_agg(jsonb_build_object('acc', m.account_id, 'uid', m.user_id, 'username', u.username,
        'role', m.role, 'accepted', m.accepted))
      from account_members m join users u on u.id = m.user_id join accounts a on a.id = m.account_id
      where a.user_id = p_user), '[]'::jsonb),
  'cases', coalesce((select jsonb_agg(jsonb_build_object('id', c.id, 'name', c.name, 'client', c.client, 'case_no', c.case_no,
                          'court', c.court, 'currency', c.currency, 'fee', c.fee, 'status', c.status, 'hearing', c.hearing, 'started', c.started, 'ctype', c.case_type, 'party', c.party, 'price', c.price, 'buyer', c.buyer, 'seller', c.seller,
                          'owner_dname', (select u.display_name from users u where u.id = c.user_id),
                          'role', acc_role(p_user, c.id),
                          'owner', (select u.username from users u where u.id = c.user_id),
                          'shared', exists (select 1 from account_members m where m.account_id = c.id and m.accepted),
                          'inc', coalesce((select sum(t.amount) from tx t where t.account_id = c.id and t.type = 'income'), 0),
                          'exp', coalesce((select sum(t.amount) from tx t where t.account_id = c.id and t.type = 'expense'), 0))
                          order by (c.status = 'closed'), c.id desc)
                     from accounts c where c.kind = 'case' and acc_role(p_user, c.id) is not null), '[]'::jsonb),
  'periods', (
    select jsonb_object_agg(s.k, jsonb_build_object('i', s.i, 'e', s.e)) from (
      select v.k,
        coalesce(sum(t.amount) filter (where t.type = 'income'), 0) as i,
        coalesce(sum(t.amount) filter (where t.type = 'expense'), 0) as e
      from (values
        ('today', p_today, p_today),
        ('week',  p_week,  p_today),
        ('month', p_month, p_today),
        ('range', p_from,  p_to)
      ) as v(k, a, b)
      left join tx t on t.account_id = (select id from cur) and t.kind = 'normal' and t.date between v.a and v.b
      group by v.k) s),
  'daily', coalesce((
    select jsonb_agg(jsonb_build_object('d', x.d, 'i', x.i, 'e', x.e) order by x.d) from (
      select t.date as d,
        coalesce(sum(t.amount) filter (where t.type = 'income'), 0) as i,
        coalesce(sum(t.amount) filter (where t.type = 'expense'), 0) as e
      from tx t
      where t.account_id = (select id from cur) and t.kind = 'normal' and t.date between p_from and p_to
      group by t.date) x), '[]'::jsonb),
  'cats', coalesce((
    select jsonb_agg(jsonb_build_object('t', c.type, 'l', c.label, 'v', c.v) order by c.v desc) from (
      select t.type, coalesce(nullif(t.label, ''), '-') as label, sum(t.amount) as v
      from tx t
      where t.account_id = (select id from cur) and t.kind = 'normal' and t.date between p_from and p_to
      group by t.type, coalesce(nullif(t.label, ''), '-')) c), '[]'::jsonb),
  'items_in', coalesce((
    select jsonb_agg(to_jsonb(i) order by i.date desc, i.id desc) from (
      select t.id, t.type, t.amount, t.label, t.note, t.date, t.img, t.user_id as uid,
             (select u.username from users u where u.id = t.user_id) as by_user
      from tx t
      where t.account_id = (select id from cur) and t.kind = 'normal' and t.type = 'income' and t.date between p_from and p_to
      order by t.date desc, t.id desc limit 300) i), '[]'::jsonb),
  'items_ex', coalesce((
    select jsonb_agg(to_jsonb(i) order by i.date desc, i.id desc) from (
      select t.id, t.type, t.amount, t.label, t.note, t.date, t.img, t.user_id as uid,
             (select u.username from users u where u.id = t.user_id) as by_user
      from tx t
      where t.account_id = (select id from cur) and t.kind = 'normal' and t.type = 'expense' and t.date between p_from and p_to
      order by t.date desc, t.id desc limit 300) i), '[]'::jsonb),
  'transfers', coalesce((
    select jsonb_agg(to_jsonb(i) order by i.date desc, i.id desc) from (
      select t.id, t.type, t.amount, t.label, t.note, t.date, t.user_id as uid,
             (select u.username from users u where u.id = t.user_id) as by_user
      from tx t where t.account_id = (select id from cur) and t.kind = 'transfer'
      order by t.date desc, t.id desc limit 8) i), '[]'::jsonb),
  'recurring', coalesce((select jsonb_agg(jsonb_build_object('id', r.id, 'account_id', r.account_id, 'type', r.type,
                          'amount', r.amount, 'label', r.label, 'day', r.day, 'next', r.next_date) order by r.id)
                        from recurring r where r.user_id = p_user and r.active), '[]'::jsonb),
  'bal', coalesce((
    select jsonb_agg(jsonb_build_object('id', ac.id, 'b',
      ac.opening + coalesce((select sum(case when t.type = 'income' then t.amount else -t.amount end)
                             from tx t where t.account_id = ac.id), 0)))
    from accounts ac where ac.id in (select id from mine)), '[]'::jsonb)
);
$$;

-- one legal case with all its entries (owner, or a member who accepted the invitation)
create or replace function case_view(p_user bigint, p_case bigint)
returns jsonb language sql stable as $$
select jsonb_build_object(
  'case', jsonb_build_object('id', c.id, 'name', c.name, 'client', c.client, 'case_no', c.case_no,
                             'court', c.court, 'currency', c.currency, 'fee', c.fee, 'status', c.status, 'hearing', c.hearing, 'started', c.started, 'ctype', c.case_type, 'party', c.party, 'price', c.price, 'buyer', c.buyer, 'seller', c.seller, 'clients', c.clients, 'parties', c.parties),
  'role', acc_role(p_user, c.id),
  'owner', (select u.username from users u where u.id = c.user_id),
  'members', case when c.user_id = p_user then coalesce((
      select jsonb_agg(jsonb_build_object('uid', m.user_id, 'username', u.username, 'role', m.role, 'accepted', m.accepted) order by m.created)
      from account_members m join users u on u.id = m.user_id where m.account_id = c.id), '[]'::jsonb)
    else '[]'::jsonb end,
  'inc', coalesce((select sum(t.amount) from tx t where t.account_id = c.id and t.type = 'income'), 0),
  'exp', coalesce((select sum(t.amount) from tx t where t.account_id = c.id and t.type = 'expense'), 0),
  'items', coalesce((
    select jsonb_agg(to_jsonb(i) order by i.date desc, i.id desc) from (
      select t.id, t.type, t.amount, t.label, t.note, t.date, t.img, t.method, t.side, t.user_id as uid,
             (select u.username from users u where u.id = t.user_id) as by_user
      from tx t where t.account_id = c.id order by t.date desc, t.id desc limit 1000) i), '[]'::jsonb))
from accounts c where c.id = p_case and c.kind = 'case' and acc_role(p_user, c.id) is not null;
$$;

-- printable report: per account (yours and shared with you) totals for a period + balance
create or replace function report(p_user bigint, p_from date, p_to date)
returns jsonb language sql stable as $$
select coalesce(jsonb_agg(jsonb_build_object(
  'id', a.id, 'name', a.name, 'currency', a.currency, 'opening', a.opening, 'kind', a.kind,
  'client', a.client, 'case_no', a.case_no, 'court', a.court, 'fee', a.fee, 'status', a.status, 'started', a.started, 'ctype', a.case_type, 'party', a.party, 'price', a.price, 'buyer', a.buyer, 'seller', a.seller,
  'role', acc_role(p_user, a.id),
  'inc', coalesce((select sum(t.amount) from tx t where t.account_id = a.id and t.type = 'income'  and t.kind = 'normal' and t.date between p_from and p_to), 0),
  'exp', coalesce((select sum(t.amount) from tx t where t.account_id = a.id and t.type = 'expense' and t.kind = 'normal' and t.date between p_from and p_to), 0),
  'tin', coalesce((select sum(t.amount) from tx t where t.account_id = a.id and t.type = 'income'  and t.kind = 'transfer' and t.date between p_from and p_to), 0),
  'tout', coalesce((select sum(t.amount) from tx t where t.account_id = a.id and t.type = 'expense' and t.kind = 'transfer' and t.date between p_from and p_to), 0),
  'bal', a.opening + coalesce((select sum(case when t.type = 'income' then t.amount else -t.amount end)
                               from tx t where t.account_id = a.id), 0)
) order by a.id), '[]'::jsonb)
from accounts a
where a.user_id = p_user or exists (select 1 from account_members m where m.account_id = a.id and m.user_id = p_user and m.accepted);
$$;

-- clients: everything a lawyer is owed, grouped by client name (own cases only)
create or replace function clients_summary(p_user bigint) returns jsonb language sql stable as $$
with c as (
  select a.id, a.currency, a.fee,
         coalesce((select sum(t.amount) from tx t where t.account_id = a.id and t.type = 'income'), 0) as rec,
         coalesce((select sum(t.amount) from tx t where t.account_id = a.id and t.type = 'expense'), 0) as spent,
         case when coalesce(array_length(a.clients, 1), 0) = 0 then array[''] else a.clients end as names
  from accounts a where a.user_id = p_user and a.kind = 'case'),
rws as (
  select coalesce(min(nullif(trim(n.name), '')), '') as client, lower(trim(n.name)) as k, c.currency,
         count(*) as cases, sum(c.fee) as fee, sum(c.rec) as received, sum(c.spent) as spent,
         sum(greatest(c.fee - c.rec, 0)) as rem
  from c cross join lateral unnest(c.names) as n(name)
  group by lower(trim(n.name)), c.currency),
tot as (
  select c.currency, count(*) as cases, sum(c.fee) as fee, sum(c.rec) as received, sum(greatest(c.fee - c.rec, 0)) as rem
  from c group by c.currency)
select jsonb_build_object(
  'rows', coalesce((select jsonb_agg(to_jsonb(r) order by r.rem desc, r.client) from rws r), '[]'::jsonb),
  'totals', coalesce((select jsonb_agg(to_jsonb(t)) from tot t), '[]'::jsonb));
$$;

create or replace function client_view(p_user bigint, p_name text) returns jsonb language sql stable as $$
with m as (
  select a.* from accounts a
  where a.user_id = p_user and a.kind = 'case'
    and ((lower(trim(p_name)) = '' and coalesce(array_length(a.clients, 1), 0) = 0)
         or lower(trim(p_name)) in (select lower(trim(x)) from unnest(a.clients) x)))
select jsonb_build_object(
  'cases', coalesce((select jsonb_agg(jsonb_build_object('id', a.id, 'name', a.name, 'currency', a.currency, 'fee', a.fee,
      'status', a.status, 'ctype', a.case_type, 'started', a.started, 'clients', a.clients,
      'received', coalesce((select sum(t.amount) from tx t where t.account_id = a.id and t.type = 'income'), 0),
      'spent', coalesce((select sum(t.amount) from tx t where t.account_id = a.id and t.type = 'expense'), 0))
      order by (a.status = 'closed'), a.id desc) from m a), '[]'::jsonb),
  'payments', coalesce((select jsonb_agg(to_jsonb(p) order by p.date desc, p.id desc) from (
      select t.id, t.amount, t.date, t.method, t.label, a.name as case_name, a.currency, a.id as case_id
      from tx t join m a on a.id = t.account_id where t.type = 'income'
      order by t.date desc, t.id desc limit 100) p), '[]'::jsonb));
$$;

-- private bucket for photos
insert into storage.buckets (id, name, public) values ('receipts', 'receipts', false)
on conflict (id) do nothing;

-- make the API see the new functions immediately
notify pgrst, 'reload schema';
