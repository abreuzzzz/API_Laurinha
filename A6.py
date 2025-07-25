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

# 4.1 Cria o novo cabeçalho combinando as duas primeiras linhas
header_1 = rows[0]
header_2 = rows[1]
combined_header = []
for col1, col2 in zip(header_1, header_2):
    if col2.strip():
        combined_header.append(f"{col1.strip()} {col2.strip()}")
    else:
        combined_header.append(col1.strip())

# 4.2 Identifica os pares de colunas Previsto / Realizado e suas posições
month_indices = []
new_header = []
i = 0
while i < len(combined_header):
    col = combined_header[i]
    if col.startswith("Previsto (R$)"):
        month = col.split("Previsto (R$)")[1].strip()
        if i + 1 < len(combined_header) and combined_header[i + 1].startswith("Realizado (R$)") and combined_header[i + 1].endswith(month):
            new_header.append(combined_header[i])     # Previsto
            new_header.append(combined_header[i + 1]) # Realizado
            new_header.append(f"Diferença % {month}") # Nova coluna
            month_indices.append((i, i + 1, f"Diferença % {month}"))
            i += 2
            continue
    new_header.append(col)
    i += 1

# 4.3 Localiza índice do Total e insere "Diferença % Total" após Realizado Total (somente se não foi inserido)
try:
    idx_prev_total = new_header.index("Previsto (R$) Total")
    idx_real_total = new_header.index("Realizado (R$) Total")
    if "Diferença % Total" not in new_header:
        new_header.insert(idx_real_total + 1, "Diferença % Total")
        insert_diff_total = True
    else:
        insert_diff_total = False
except ValueError:
    insert_diff_total = False
    idx_prev_total = idx_real_total = None

# 4.4 Inicia nova matriz de dados com cabeçalho atualizado
new_rows = [new_header]

# 4.5 Processa cada linha de dados
for row in rows[2:]:
    new_row = []
    i = 0
    col_pointer = 0
    while i < len(row):
        inserted = False
        for idx_prev, idx_real, diff_col in month_indices:
            if i == idx_prev:
                previsto = row[idx_prev].replace('.', '').replace(',', '.')
                realizado = row[idx_real].replace('.', '').replace(',', '.')
                try:
                    previsto_val = float(previsto)
                    realizado_val = float(realizado)
                    if previsto_val == 0:
                        diff_percent = "0.00%"
                    else:
                        diff_percent = f"{((realizado_val - previsto_val) / previsto_val) * 100:.2f}%"
                except:
                    diff_percent = "0.00%"
                new_row.append(row[idx_prev])
                new_row.append(row[idx_real])
                new_row.append(diff_percent)
                i += 2
                col_pointer += 3
                inserted = True
                break
        if not inserted:
            new_row.append(row[i])
            i += 1
            col_pointer += 1

    # Inserir Diferença % Total
    if insert_diff_total and idx_prev_total is not None and idx_real_total is not None:
        try:
            previsto_total = float(row[idx_prev_total].replace('.', '').replace(',', '.'))
            realizado_total = float(row[idx_real_total].replace('.', '').replace(',', '.'))
            if previsto_total == 0:
                diff_total = "0.00%"
            else:
                diff_total = f"{((realizado_total - previsto_total) / previsto_total) * 100:.2f}%"
        except:
            diff_total = "0.00%"
        new_row.insert(idx_real_total + 1, diff_total)

    new_rows.append(new_row)

# 5. Escreve os dados na aba
worksheet.update("A1", new_rows)

print("✅ Dados atualizados com sucesso na aba 'Página1', com Diferença % inserida corretamente após cada mês e total.")
