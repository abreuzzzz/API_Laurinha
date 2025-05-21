import os
import json
import requests
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 1. Requisição para a API da Conta Azul
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

# Verifica se a resposta foi bem sucedida
if response.status_code != 200:
    raise Exception(f"Erro na requisição: {response.status_code} - {response.text}")

# Converte resposta para DataFrame
dados = response.json()
df = pd.json_normalize(dados)

# 2. Autenticação com Google Sheets
json_secret_str = os.getenv("GDRIVE_SERVICE_ACCOUNT")
if not json_secret_str:
    raise EnvironmentError("Variável de ambiente GDRIVE_SERVICE_ACCOUNT não definida")

service_account_info = json.loads(json_secret_str)
creds = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

service = build('sheets', 'v4', credentials=creds)
sheet_id = '1DAGZ4X16kA8gOtUU3mqIBqEKCb3XZs3CmM9F4gNVLFg'

# 3. Limpar aba existente (opcional, aqui 'Página1')
clear_range = "Página1"
service.spreadsheets().values().clear(
    spreadsheetId=sheet_id,
    range=clear_range
).execute()

# 4. Enviar dados para o Google Sheets
values = [df.columns.tolist()] + df.values.tolist()

body = {
    'values': values
}

service.spreadsheets().values().update(
    spreadsheetId=sheet_id,
    range="Página1!A1",
    valueInputOption="RAW",
    body=body
).execute()

print("Dados exportados com sucesso para o Google Sheets.")
