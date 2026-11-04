import os, re, io, csv, json, zipfile, hashlib, sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

INDEX_URL = "https://dadosabertos.pgfn.gov.br/"
BASE_URL = "https://dadosabertos.pgfn.gov.br/"
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
UF_FILTER = os.getenv("UF_FILTER", "SP").upper()
MAX_ROWS = int(os.getenv("MAX_ROWS", "1000"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "250"))

def get(url):
    req = Request(url, headers={"User-Agent":"GlobalSystem01/0.1 (public-data research)"})
    with urlopen(req, timeout=120) as r:
        return r.read()

def latest_sida_url():
    html = get(INDEX_URL).decode("utf-8", "replace")
    folders = re.findall(r'href="(20\d{2}_trimestre_0[1-4]/)"', html)
    if not folders:
        raise RuntimeError("Não foi possível localizar pastas trimestrais no índice oficial PGFN.")
    folder = sorted(set(folders))[-1]
    page = get(BASE_URL + folder).decode("utf-8", "replace")
    links = re.findall(r'href="([^"]*Dados_abertos_Sistema_SIDA\.zip)"', page)
    if not links:
        raise RuntimeError(f"Arquivo SIDA não encontrado em {folder}.")
    return BASE_URL + folder + links[0], folder

def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def choose(headers, candidates):
    normalized = {norm(h):h for h in headers}
    for candidate in candidates:
        if norm(candidate) in normalized:
            return normalized[norm(candidate)]
    for key, original in normalized.items():
        if any(norm(c) in key for c in candidates):
            return original
    return None

def parse_money(value):
    if value is None: return None
    s = str(value).strip().replace("R$","").replace(" ","")
    if not s: return None
    if "," in s: s = s.replace(".","").replace(",",".")
    try: return round(float(s),2)
    except ValueError: return None

def parse_cnpj(row, col):
    raw = re.sub(r"\D","",str(row.get(col,""))) if col else ""
    return raw if len(raw)==14 else None

def post_batch(rows):
    if not rows: return
    url = SUPABASE_URL + "/rest/v1/pgfn_registros?on_conflict=chave_origem"
    body = json.dumps(rows, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, method="POST", headers={
        "apikey": SERVICE_KEY,
        "Authorization": "Bearer " + SERVICE_KEY,
        "Content-Type":"application/json",
        "Prefer":"resolution=merge-duplicates,return=minimal"
    })
    try:
        with urlopen(req, timeout=120) as resp:
            if resp.status not in (200,201,204): raise RuntimeError(f"Supabase retornou HTTP {resp.status}")
    except HTTPError as e:
        raise RuntimeError(f"Erro Supabase HTTP {e.code}: {e.read(1500).decode('utf-8','replace')}")

def main():
    url, quarter = latest_sida_url()
    print(f"Fonte oficial: {url}")
    print(f"Referência: {quarter}; filtro UF: {UF_FILTER}; limite: {MAX_ROWS or 'sem limite'}")
    archive = get(url)
    zf = zipfile.ZipFile(io.BytesIO(archive))
    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if not csv_names: raise RuntimeError("ZIP oficial não contém CSV.")
    total = sent = 0
    for name in csv_names:
        print("Processando:", name)
        with zf.open(name) as raw:
            # A base oficial pode variar a codificação e o delimitador.
            text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
            sample = text.read(8192); text.seek(0)
            try: dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t")
            except csv.Error: dialect = csv.excel
            reader = csv.DictReader(text, dialect=dialect)
            headers = reader.fieldnames or []
            print("Colunas detectadas:", headers)
            cnpj_col = choose(headers, ["CPF_CNPJ", "CPF/CNPJ", "CNPJ", "NI_DEVEDOR", "NUMERO_DOCUMENTO"])
            name_col = choose(headers, ["NOME_DEVEDOR", "NOME", "DEVEDOR", "NOME_RAZAO_SOCIAL"])
            nature_col = choose(headers, ["TIPO_CREDITO", "NATUREZA", "NATUREZA_DIVIDA", "DESCRICAO_NATUREZA"])
            status_col = choose(headers, ["TIPO_SITUACAO_INSCRICAO", "SITUACAO_INSCRICAO", "SITUACAO"])
            value_col = choose(headers, ["VALOR_CONSOLIDADO", "VALOR_INSCRICAO", "VALOR_TOTAL", "VALOR"])
            type_col = choose(headers, ["TIPO_DEVEDOR"])
            uf_col = choose(headers, ["UF", "UF_DEVEDOR", "UF_UNIDADE"])
            city_col = choose(headers, ["MUNICIPIO", "MUNICIPIO_DEVEDOR"])
            inscr_col = choose(headers, ["NUMERO_INSCRICAO", "INSCRICAO", "NUMERO_CDA"])
            date_col = choose(headers, ["DATA_INSCRICAO", "DATA_INSCRICAO_DIVIDA"])
            if not cnpj_col:
                print("AVISO: coluna de CNPJ não reconhecida. Arquivo não importado; revisar dicionário/layout.")
                continue
            batch=[]
            for row in reader:
                cnpj = parse_cnpj(row, cnpj_col)
                if not cnpj: continue
                uf = str(row.get(uf_col,"")).strip().upper() if uf_col else None
                if UF_FILTER not in ("ALL","BR","BRASIL","") and uf and uf != UF_FILTER: continue
                raw_value = row.get(value_col) if value_col else None
                identity = "|".join([quarter, name, cnpj, str(row.get(inscr_col,"")), str(row.get(type_col,""))])
                item = {
                    "chave_origem": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                    "cnpj": cnpj,
                    "nome_devedor": (row.get(name_col) or "").strip() if name_col else None,
                    "natureza": (row.get(nature_col) or "").strip() if nature_col else None,
                    "situacao": (row.get(status_col) or "").strip() if status_col else None,
                    "valor_divida": parse_money(raw_value),
                    "tipo_devedor": (row.get(type_col) or "").strip() if type_col else None,
                    "uf": uf,
                    "municipio": (row.get(city_col) or "").strip() if city_col else None,
                    "numero_inscricao": (row.get(inscr_col) or "").strip() if inscr_col else None,
                    "data_inscricao": (row.get(date_col) or "").strip() or None if date_col else None,
                    "fonte": "PGFN Dados Abertos - SIDA",
                    "url_fonte": url,
                    "importado_em": datetime.now(timezone.utc).isoformat(),
                    "dados_originais": row
                }
                batch.append(item); total += 1
                if len(batch)>=BATCH_SIZE:
                    post_batch(batch); sent += len(batch); batch=[]
                    if sent % 1000 == 0: print("Registros enviados:", sent)
                if MAX_ROWS and total>=MAX_ROWS: break
            if batch: post_batch(batch); sent += len(batch)
        if MAX_ROWS and total>=MAX_ROWS: break
    print(f"Concluído. Registros processados: {total}; enviados/upsert: {sent}")
    if sent == 0:
        raise RuntimeError("Nenhum registro importado. Verifique UF, layout e colunas reconhecidas.")

if __name__ == "__main__":
    main()
