import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 🔐 Lê o segredo e salva como credentials.json
gdrive_credentials = os.getenv("GDRIVE_SERVICE_ACCOUNT")
with open("credentials.json", "w") as f:
    json.dump(json.loads(gdrive_credentials), f)

# 📌 Autenticação com Google
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# === IDs das planilhas ===
planilhas_ids = {
    "Financeiro_contas_a_receber_Laurinha": "1jSGG9ON1KK-vP39JsbcHx7GwPUlBtZitoTaZSH4bNAs",
    "Financeiro_contas_a_pagar_Laurinha": "1V8eno5o9fWUfA3xIHzY748sc8DGKvU6wA76LHqc4Shs",
    "Financeiro_Completo_Laurinha": "1jTuY_4wcegFjkt_e4dV2ZoM_7ZIUSlpZIGgZ-sNr7o4"
}

def limpar_aba_completa(aba, nome_aba):
    """Limpa conteúdo E formatação de uma aba"""
    print(f"  🗑️ Limpando conteúdo de {nome_aba}...")
    aba.clear()
    
    print(f"  🎨 Removendo formatação de {nome_aba}...")
    aba.format('A:ZZ', {
        "numberFormat": {"type": "TEXT"},  # Força formato texto
        "backgroundColor": {"red": 1, "green": 1, "blue": 1},  # Branco
        "textFormat": {
            "bold": False,
            "italic": False,
            "foregroundColor": {"red": 0, "green": 0, "blue": 0}
        }
    })
    print(f"  ✅ {nome_aba} - Conteúdo e formatação removidos")

print("🗑️ Iniciando exclusão COMPLETA de todas as linhas das planilhas...")

# 1. Limpa TUDO de Contas a Receber
print("\n📋 Limpando: Financeiro_contas_a_receber_Laurinha")
planilha_receber = client.open_by_key(planilhas_ids["Financeiro_contas_a_receber_Laurinha"])
aba_receber = planilha_receber.sheet1
limpar_aba_completa(aba_receber, "Contas a Receber")

# 2. Limpa TUDO de Contas a Pagar
print("\n📋 Limpando: Financeiro_contas_a_pagar_Laurinha")
planilha_pagar = client.open_by_key(planilhas_ids["Financeiro_contas_a_pagar_Laurinha"])
aba_pagar = planilha_pagar.sheet1
limpar_aba_completa(aba_pagar, "Contas a Pagar")

# 3. Limpa TUDO de Financeiro Completo - Aba principal (sheet1)
print("\n📋 Limpando: Financeiro_Completo_Laurinha (sheet1)")
planilha_completo = client.open_by_key(planilhas_ids["Financeiro_Completo_Laurinha"])
aba_completo = planilha_completo.sheet1
limpar_aba_completa(aba_completo, "Financeiro Completo - Principal")

# 4. Limpa TUDO de Financeiro Completo - Aba Dados_Pivotados (se existir)
print("\n📋 Limpando: Financeiro_Completo_Laurinha (Dados_Pivotados)")
try:
    aba_pivotada = planilha_completo.worksheet("Dados_Pivotados")
    limpar_aba_completa(aba_pivotada, "Dados Pivotados")
except:
    print("  ⚠️ Aba 'Dados_Pivotados' não encontrada")

print("\n🎉 Limpeza completa concluída com sucesso!")
print("⚠️ ATENÇÃO: Conteúdo e formatação removidos. Células resetadas para formato TEXTO")
