create extension if not exists pgcrypto;

create table if not exists public.pgfn_registros (
  id uuid primary key default gen_random_uuid(),
  chave_origem text not null unique,
  cnpj text,
  nome_devedor text,
  natureza text,
  situacao text,
  valor_divida numeric(18,2),
  tipo_devedor text,
  uf text,
  municipio text,
  numero_inscricao text,
  data_inscricao date,
  telefone_comercial text,
  email_comercial text,
  fonte text not null default 'PGFN Dados Abertos - SIDA',
  url_fonte text,
  importado_em timestamptz not null default now(),
  dados_originais jsonb not null default '{}'::jsonb
);

create index if not exists idx_pgfn_cnpj on public.pgfn_registros(cnpj);
create index if not exists idx_pgfn_uf on public.pgfn_registros(uf);
create index if not exists idx_pgfn_situacao on public.pgfn_registros(situacao);
create index if not exists idx_pgfn_valor on public.pgfn_registros(valor_divida desc);

alter table public.pgfn_registros enable row level security;

-- Leitura somente para usuários autenticados. A chave service_role do importador
-- ignora RLS e deve ficar exclusivamente nos GitHub Actions Secrets.
drop policy if exists "Leitura autenticada de registros PGFN" on public.pgfn_registros;
create policy "Leitura autenticada de registros PGFN"
on public.pgfn_registros for select to authenticated using (true);
