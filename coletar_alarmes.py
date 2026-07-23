"""
Coletor de alarmes - Portal Hughes (Grafana/Zabbix)
----------------------------------------------------
Roda via GitHub Actions (sem interacao humana e sem depender do PC do usuario).
Consulta a API do Grafana/Zabbix para cada cliente e gera um index.html
estatico com a tabela de alarmes, pronto para ser publicado no GitHub Pages.
"""

import html
import os
import sys
from datetime import datetime, timezone

import requests

BASE_URL = "https://portal.tools.hughes.com.br"
PROXY_ENDPOINT = f"{BASE_URL}/api/datasources/proxy/uid/julbqzRSz"

OUTPUT_FILE = "index.html"

CLIENTES = [
    "ABC da Construção", "AMBAR ENERGIA KU", "AMBAR ENERGIA _C",
    "Answer Consultoria", "Answer1", "Atlas Copco", "BP Bunge Bioenergia",
    "Banco Carrefour", "CELPE", "CEMIG", "CLARO", "COELBA", "COMGÁS",
    "COSERN", "CPFL Energia (Banda C)", "CPFL Renováveis",
    "CPFL TRANSMISSÃO_CEEE-T", "EDP", "EDP Renováveis",
    "ENERWATT ENGENHARIA", "ENEVA", "EQUATORIAL-CEA", "EQUATORIAL-CEAL",
    "EQUATORIAL-CEEE", "EQUATORIAL-CELPA", "EQUATORIAL-CEMAR",
    "EQUATORIAL-CEPISA", "EQUATORIAL-GOIÁS", "ES GAS ENERGISA", "Elektro",
    "GAZIN", "GNC", "GRUPO SOMA", "Grupo Bom Jesus", "Guyacom",
    "HF Tecnologia", "HNSA", "IMPORTADORA TV LAR LTDA", "LE BISCUIT",
    "LOJAS CEM", "LOJAS DULAR", "NEOENERGIA RENOVÁVEIS",
    "NEOENERGIA TRANSMISSÃO", "Oi", "OiCOLR", "PRIO", "RESERVA", "RGE",
    "RUMO MALHA PAULISTA", "SERPRO", "SGGO", "SMART",
    "Super Pague Menos", "Supermercados BH", "TDS", "TECBAN", "TELEBRAS",
    "TELEMAR", "TGM", "TIM", "TRANSPETRO", "Telefonica", "VALE S.A",
    "VOTORANTIM BANDA C", "VOTORANTIM ONEWEB", "WILSON SONS",
]

SEVERITY_MAP = {
    "0": "Not classified", "1": "Information", "2": "Warning",
    "3": "Average", "4": "High", "5": "Disaster",
}

SEVERITY_COLOR = {
    "Not classified": "rgb(151,151,102)",
    "Information": "rgb(120,158,183)",
    "Warning": "rgb(175,180,36)",
    "Average": "rgb(255,137,30)",
    "High": "rgb(255,101,72)",
    "Disaster": "rgb(255,0,0)",
}

SEVERITY_ORDER = {
    "Disaster": 5, "High": 4, "Average": 3,
    "Warning": 2, "Information": 1, "Not classified": 0,
}


def buscar_alarmes(session, cliente):
    body = {
        "method": "custom.problem.get",
        "params": {
            "groups": f"BSS/Customers/{cliente}",
            "severity": "-1",
            "tags": {"tag": "template", "value": "all"},
            "name_tag": "DESIG_CLIENTE",
        },
    }
    try:
        resp = session.post(PROXY_ENDPOINT, json=body, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            for item in data:
                item["Cliente"] = cliente
            return data
        return []
    except Exception as e:
        print(f"  [erro] {cliente}: {e}", file=sys.stderr)
        return []


def gerar_html(alarmes, atualizado_em):
    def linha(a):
        sev = SEVERITY_MAP.get(str(a.get("Severity")), str(a.get("Severity")))
        cor = SEVERITY_COLOR.get(sev, "rgb(120,120,120)")
        cliente = html.escape(str(a.get("Cliente", "")))
        host = html.escape(str(a.get("Host", "")))
        name = html.escape(str(a.get("Name", "")))
        problem = html.escape(str(a.get("Problem", "")))
        try:
            ts = int(a.get("Time"))
            tempo = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y/%m/%d %H:%M:%S")
        except Exception:
            tempo = html.escape(str(a.get("Time", "")))
        return (
            f"<tr><td>{cliente}</td><td>{host}</td><td>{name}</td>"
            f"<td style='background:{cor}'>{sev}</td><td>{problem}</td><td>{tempo}</td></tr>"
        )

    alarmes_ordenados = sorted(
        alarmes,
        key=lambda a: (
            SEVERITY_ORDER.get(SEVERITY_MAP.get(str(a.get("Severity")), ""), -1),
            str(a.get("Time", "")),
        ),
        reverse=True,
    )
    linhas = "".join(linha(a) for a in alarmes_ordenados)

    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Alarmes - Todos os Clientes</title>
<style>
  body {{ background:#111; color:#eee; font-family: Arial, sans-serif; margin:0; padding:8px; }}
  h1 {{ font-size:1.2rem; text-align:center; margin-bottom:2px; }}
  p.atualizado {{ text-align:center; color:#888; font-size:0.75rem; margin-top:0; margin-bottom:8px; }}
  input {{ width:100%; padding:8px; margin-bottom:8px; box-sizing:border-box; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.8rem; }}
  th {{ position:sticky; top:0; background:#222; color:#33B5E5; padding:6px 4px; text-align:left; }}
  td {{ padding:6px 4px; border-bottom:1px solid #333; }}
  tr:hover td {{ background:#252627; }}
</style>
</head>
<body>
<h1>Alarmes - Todos os Clientes ({len(alarmes_ordenados)})</h1>
<p class="atualizado">Atualizado em {atualizado_em} (UTC)</p>
<input type="text" id="filtro" placeholder="Filtrar (cliente, host, problema...)" onkeyup="filtrar()">
<table id="tabela">
<thead><tr><th>Cliente</th><th>Host</th><th>Name</th><th>Severity</th><th>Problem</th><th>Time</th></tr></thead>
<tbody>
{linhas}
</tbody>
</table>
<script>
function filtrar() {{
  const termo = document.getElementById('filtro').value.toLowerCase();
  const linhas = document.getElementById('tabela').getElementsByTagName('tr');
  for (let i = 1; i < linhas.length; i++) {{
    const texto = linhas[i].textContent.toLowerCase();
    linhas[i].style.display = texto.includes(termo) ? '' : 'none';
  }}
}}
</script>
</body>
</html>
"""


def main():
    usuario = os.environ["PORTAL_USUARIO"]
    senha = os.environ["PORTAL_SENHA"]

    session = requests.Session()
    session.auth = (usuario, senha)

    todos_alarmes = []
    print(f"Consultando {len(CLIENTES)} clientes...")
    for cliente in CLIENTES:
        todos_alarmes.extend(buscar_alarmes(session, cliente))

    print(f"Total de alarmes agora: {len(todos_alarmes)}")

    agora = datetime.now(tz=timezone.utc).strftime("%Y/%m/%d %H:%M:%S")
    pagina = gerar_html(todos_alarmes, agora)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(pagina)

    print(f"{OUTPUT_FILE} gerado com sucesso.")


if __name__ == "__main__":
    main()
