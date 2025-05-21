import requests
import json
import os
import gspread
from google.oauth2.service_account import Credentials
import csv
import io

# 1. Requisição para a API do Conta Azul
url = "https://services.contaazul.com/finance-pro-reports/api/v1/monthly-cash-flow/export"

payload = json.dumps({
  "year": 2025,
  "view": "ALL"
})
headers = {
  'X-Authorization': 'd26f41fc-c283-4685-bd17-12f63bf9919c',
  'Content-Type': 'application/json',
  'User-Agent': 'Mozilla/5.0'
}

response = requests.post(url, headers=headers, data=payload)
csv_text = response.content.decode('latin1')

# 2. Autenticação com Google Sheets
json_secret = os.getenv("GDRIVE_SERVICE_ACCOUNT")
if not json_secret:
    raise Exception("A variável de ambiente 'GDRIVE_SERVICE_ACCOUNT' não foi encontrada.")

service_account_info = json.loads(json_secret)
scopes = ['https://www.googleapis.com/auth/spreadsheets']
credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)

client = gspread.authorize(credentials)

# 3. Abre a planilha e limpa a aba "Página1"
spreadsheet = client.open_by_key("1DAGZ4X16kA8gOtUU3mqIBqEKCb3XZs3CmM9F4gNVLFg")
worksheet = spreadsheet.worksheet("Página1")
worksheet.clear()

# 4. Converte CSV para lista de listas
reader = csv.reader(io.StringIO(csv_text), delimiter=';')
rows = list(reader)

# 4.1 Ajusta o cabeçalho para juntar as duas primeiras linhas
new_header = []
for col1, col2 in zip(rows[0], rows[1]):
    if col2.strip():
        new_header.append(f"{col1.strip()} {col2.strip()}")
    else:
        new_header.append(col1.strip())

# 4.2 Identifica os pares Previsto e Realizado por mês
month_pairs = []
for i, col in enumerate(new_header):
    if col.startswith("Previsto (R$)"):
        month = col.split("Previsto (R$)")[1].strip()
        for j in range(i + 1, len(new_header)):
            if new_header[j].startswith("Realizado (R$)") and new_header[j].endswith(month):
                month_pairs.append((i, j, month))
                break

# 4.3 Adiciona colunas de Diferença % para os meses
for _, _, month in month_pairs:
    new_header.append(f"Diferença % {month}")

# 4.4 Localiza os totais e adiciona coluna de Diferença % Total
try:
    idx_prev_total = new_header.index("Previsto (R$) Total")
    idx_real_total = new_header.index("Realizado (R$) Total")
    new_header.append("Diferença % Total")
except ValueError:
    idx_prev_total = idx_real_total = None

# 4.5 Junta o cabeçalho e inicia nova lista de linhas
new_rows = [new_header]

# 4.6 Processa os dados linha a linha
for row in rows[2:]:
    new_row = row.copy()

    # Diferença % por mês
    for idx_prev, idx_real, _ in month_pairs:
        try:
            previsto = float(row[idx_prev].replace('.', '').replace(',', '.'))
            realizado = float(row[idx_real].replace('.', '').replace(',', '.'))
            if previsto == 0:
                diff_percent = ""
            else:
                diff_percent = f"{((realizado - previsto) / previsto) * 100:.2f}%"
        except:
            diff_percent = ""
        new_row.append(diff_percent)

    # Diferença % Total
    if idx_prev_total is not None and idx_real_total is not None:
        try:
            previsto_total = float(row[idx_prev_total].replace('.', '').replace(',', '.'))
            realizado_total = float(row[idx_real_total].replace('.', '').replace(',', '.'))
            if previsto_total == 0:
                diff_total = ""
            else:
                diff_total = f"{((realizado_total - previsto_total) / previsto_total) * 100:.2f}%"
        except:
            diff_total = ""
        new_row.append(diff_total)

    new_rows.append(new_row)

# 5. Escreve os dados na aba
worksheet.update("A1", new_rows)

print("✅ Dados atualizados com sucesso na aba 'Página1' com colunas de Diferença %.")
