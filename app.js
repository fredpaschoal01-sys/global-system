// Configure com a URL do projeto e a chave anon/public do Supabase.
// Nunca use a chave service_role neste arquivo.
const SUPABASE_URL = "SUPABASE_URL_AQUI";
const SUPABASE_ANON_KEY = "SUPABASE_ANON_KEY_AQUI";
const PAGE_SIZE = 25;
let page = 0, allRows = [];

const $ = (id) => document.getElementById(id);
const money = (v) => Number(v || 0).toLocaleString("pt-BR",{style:"currency",currency:"BRL",maximumFractionDigits:2});
const digits = (v) => String(v || "").replace(/\D/g,"");

function setupClient(){
  if(!window.supabase || SUPABASE_URL.includes("_AQUI") || SUPABASE_ANON_KEY.includes("_AQUI")){
    $("connection").textContent = "Configure URL e chave pública do Supabase";
    return null;
  }
  $("connection").textContent = "Conectando ao Supabase";
  return window.supabase.createClient(SUPABASE_URL,SUPABASE_ANON_KEY);
}
const client = setupClient();

async function loadRows(){
  if(!client){$("connection").textContent="Configure o Supabase em app.js.";return;}
  const {data:sessionData}=await client.auth.getSession();
  if(!sessionData.session){$("loginBox").hidden=false;$("appContent").hidden=true;$("connection").textContent="Aguardando login";return;}
  $("loginBox").hidden=true;$("appContent").hidden=false;
  $("connection").textContent = "Carregando dados";
  const {data,error}=await client.from("pgfn_registros").select("*").order("valor_divida",{ascending:false}).range(0,4999);
  if(error){$("connection").textContent="Erro ao consultar banco";$("rows").innerHTML=`<tr><td colspan="5" class="empty">${escapeHtml(error.message)}</td></tr>`;return;}
  allRows=data||[];
  $("connection").textContent="Conectado";
  $("total").textContent=allRows.length.toLocaleString("pt-BR");
  $("companies").textContent=new Set(allRows.map(x=>x.cnpj).filter(Boolean)).size.toLocaleString("pt-BR");
  $("amount").textContent=money(allRows.reduce((s,x)=>s+Number(x.valor_divida||0),0));
  $("lastUpdate").textContent=allRows.length?new Date(Math.max(...allRows.map(x=>new Date(x.importado_em||0).getTime()))).toLocaleDateString("pt-BR"):"—";
  fillFilters(); render();
}
function fillFilters(){
  const statuses=[...new Set(allRows.map(x=>x.situacao).filter(Boolean))].sort();
  const natures=[...new Set(allRows.map(x=>x.natureza).filter(Boolean))].sort();
  $("status").innerHTML='<option value="">Todas as situações</option>'+statuses.map(x=>`<option>${escapeHtml(x)}</option>`).join("");
  $("nature").innerHTML='<option value="">Todas as naturezas</option>'+natures.map(x=>`<option>${escapeHtml(x)}</option>`).join("");
}
function filtered(){
  const q=$("search").value.toLowerCase().trim();
  return allRows.filter(x=>(!q||[x.nome_devedor,x.cnpj].some(v=>String(v||"").toLowerCase().includes(q)))&&(!$("status").value||x.situacao===$("status").value)&&(!$("nature").value||x.natureza===$("nature").value));
}
function render(){
  const rows=filtered(), start=page*PAGE_SIZE, slice=rows.slice(start,start+PAGE_SIZE);
  $("count").textContent=`${rows.length.toLocaleString("pt-BR")} registros`;
  $("rows").innerHTML=slice.length?slice.map(x=>{
    const phone=digits(x.telefone_comercial);
    const wa=phone?`https://wa.me/55${phone}`:"";
    const title=escapeHtml(x.nome_devedor||"Devedor não identificado");
    return `<tr><td><strong>${title}</strong><small>${escapeHtml(x.cnpj||"CNPJ não disponível")}</small></td><td>${escapeHtml(x.natureza||"Não informado")}</td><td><span class="tag">${escapeHtml(x.situacao||"Não informada")}</span></td><td>${money(x.valor_divida)}</td><td>${wa?`<a class="contact-link" target="_blank" rel="noopener" href="${wa}">WhatsApp</a>`:"<span class='tag'>Contato não localizado</span>"}</td></tr>`;
  }).join(""):'<tr><td colspan="5" class="empty">Nenhum registro encontrado com esses filtros.</td></tr>';
  $("prev").disabled=page===0;$("next").disabled=start+PAGE_SIZE>=rows.length;
}
function escapeHtml(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
["search","status","nature"].forEach(id=>$(id).addEventListener(id==="search"?"input":"change",()=>{page=0;render();}));
$("refresh").addEventListener("click",loadRows);
$("clear").addEventListener("click",()=>{$("search").value="";$("status").value="";$("nature").value="";page=0;render();});
$("prev").addEventListener("click",()=>{page=Math.max(0,page-1);render();});
$("next").addEventListener("click",()=>{page++;render();});
loadRows();

$("login").addEventListener("click", async ()=>{
  $("loginError").textContent="";
  if(!client){$("loginError").textContent="Configure primeiro o Supabase em app.js.";return;}
  const {error}=await client.auth.signInWithPassword({email:$("email").value,password:$("password").value});
  if(error){$("loginError").textContent=error.message;return;}
  await loadRows();
});
