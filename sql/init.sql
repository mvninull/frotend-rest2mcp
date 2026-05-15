-- Tabela profiles no Supabase
-- Executar no SQL Editor do Supabase Dashboard

create table if not exists profiles (
  id          uuid references auth.users not null primary key,
  email       text,
  name        text,
  avatar_url  text,
  status      text check (status in ('active', 'suspended', 'banned')) default 'active',
  plan_tier   text check (plan_tier in ('free', 'pro', 'enterprise')) default 'free',
  paypal_subscription_id text,
  created_at  timestamp default now(),
  updated_at  timestamp default now()
);

-- Trigger: criar profile automaticamente após signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, name, avatar_url)
  values (new.id, new.email, new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'avatar_url');
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Políticas RLS (Row Level Security)
alter table profiles enable row level security;

-- Users podem ver apenas o próprio profile
create policy "Users can view own profile"
  on profiles for select
  using (auth.uid() = id);

-- Users podem atualizar o próprio profile (exceto campos críticos)
create policy "Users can update own profile"
  on profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);
