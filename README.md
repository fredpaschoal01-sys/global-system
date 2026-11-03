# GLOBAL SYSTEM 0.1

Primeira estrutura funcional para importar dados públicos da PGFN, armazenar registros no Supabase e exibir empresas em um painel web.

## O que esta versão faz
- Descobre automaticamente a pasta trimestral mais recente no índice público da PGFN.
- Baixa o arquivo `Dados_abertos_Sistema_SIDA.zip`.
- Lê CSVs em fluxo, sem carregar o arquivo inteiro na memória.
- Identifica CNPJs e tenta mapear campos comuns de devedor, inscrição, natureza, situação e valores.
- Grava os registros no Supabase via REST.
- Exibe os registros importados no painel, com filtros e links de telefone/WhatsApp quando esses dados existirem.

## Limites importantes da versão 0.1
- A base SIDA é uma base de créditos inscritos e inclui situações diferentes (ativos, garantidos, suspensos e negociados). O painel mostra a situação encontrada e NÃO presume que tudo seja dívida exigível ou oportunidade comercial.
- Esta versão não inventa telefone, e-mail, nome fantasia ou sócio. Esses dados só aparecerão quando forem fornecidos por uma fonte legítima integrada em uma etapa posterior.
- O cruzamento com Receita Federal / quadro societário e o enriquecimento de telefone ainda precisam de uma fonte de dados e integração próprias.
- A automação usa o arquivo oficial da PGFN. A frequência da publicação depende da PGFN; executar semanalmente não torna a base semanal.
- O importador faz upsert por chave de origem para evitar duplicação.

## 1. Criar o Supabase
1. Crie um projeto Supabase NOVO para não alterar seu CRM anterior.
2. Abra SQL Editor e execute `supabase/schema.sql`.
3. Em Project Settings > API, copie:
   - Project URL
   - `service_role` key (NUNCA coloque no frontend ou no GitHub público).

## 2. Configurar GitHub Secrets
No repositório `global-system-01`, abra Settings > Secrets and variables > Actions e crie:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Opcional:
- `UF_FILTER` (padrão `SP`; use `ALL` para Brasil inteiro)
- `MAX_ROWS` (padrão `1000`; para processar a base completa, defina `0`)

## 3. Publicar
Envie todos os arquivos deste pacote para a raiz do repositório GitHub `global-system-01`.

O GitHub Pages pode hospedar o frontend. Em Settings > Pages, selecione Deploy from a branch, branch `main`, pasta `/ (root)`.

Crie também um usuário em Authentication > Users no Supabase. O painel exige login.\n\nEm `app.js`, substitua:
- `SUPABASE_URL_AQUI`
- `SUPABASE_ANON_KEY_AQUI`

Use somente a chave `anon/public` no frontend. Nunca use `service_role` no navegador.

## 4. Primeiro teste manual
No GitHub:
1. Abra Actions.
2. Escolha `Importar dados PGFN`.
3. Clique em Run workflow.
4. Para teste inicial, configure o secret `MAX_ROWS=1000`.
5. Acompanhe os logs. O importador informa o arquivo e os nomes de colunas reconhecidos.

Depois de validar o layout e a execução, defina `MAX_ROWS=0` para tentar processar tudo. Bases grandes podem exceder o tempo/armazenamento de uma execução do GitHub Actions; nesse caso, migre o processamento para um worker dedicado ou processamento em nuvem. A automação está manual nesta primeira entrega para evitar uma importação pesada sem validação.

## 5. Segurança
- Ative RLS: o SQL já cria políticas para usuários autenticados.
- Não publique dados pessoais de sócios ou telefones particulares.
- Use contatos comerciais e observe LGPD, finalidade, transparência e pedidos de não contato.
- Faça revisão jurídica antes de usar dados em prospecção.
