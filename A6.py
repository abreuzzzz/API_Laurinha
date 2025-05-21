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
response.encoding = 'utf-8'  # Corrige caracteres especiais
csv_text = response.text

# 2. Autenticação com Google Sheets
json_secret = os.getenv("GDRIVE_SERVICE_ACCOUNT")
if not json_secret:
    raise Exception("A variável de ambiente 'GDRIVE_SERVICE_ACCOUNT' não foi encontrada.")

# Carrega as credenciais a partir da variável de ambiente
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

# 5. Escreve os dados na aba
worksheet.update("A1", rows)

print("✅ Dados atualizados com sucesso na aba 'Página1'.")
