import os
import json
import gspread
import pandas as pd
from gspread_dataframe import get_as_dataframe, set_with_dataframe
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
    "Detalhe_centro_pagamento": "18xhCs_Tr-N9npS0rg15teXYyXIX8_V4RohuqWssY7VM",
    "Detalhe_centro_recebimento": "1kekOp-xYnE79deNp627GHIi5oir-fUEkmZMf2nMwGcI",
    "Financeiro_Completo_Laurinha": "1jTuY_4wcegFjkt_e4dV2ZoM_7ZIUSlpZIGgZ-sNr7o4"
}

# === Função para abrir e ler planilha por ID ===
def ler_planilha_por_id(nome_arquivo):
    planilha = client.open_by_key(planilhas_ids[nome_arquivo])
    aba = planilha.sheet1
    df = get_as_dataframe(aba).dropna(how="all")
    return df

# Lê os dados das planilhas
df_receber = ler_planilha_por_id("Financeiro_contas_a_receber_Laurinha")
df_pagar = ler_planilha_por_id("Financeiro_contas_a_pagar_Laurinha")
df_pagamento = ler_planilha_por_id("Detalhe_centro_pagamento")
df_recebimento = ler_planilha_por_id("Detalhe_centro_recebimento")

# Adiciona a coluna tipo
df_receber["tipo"] = "receber"
df_pagar["tipo"] = "pagar"

# Junta os dois dataframes
df_completo = pd.concat([df_receber, df_pagar], ignore_index=True)

# 1º join com Detalhe_centro_pagamento usando financialEvent.id
df_merge = df_completo.merge(
    df_pagamento,
    how="left",
    left_on="financialEvent.id",
    right_on="id",
    suffixes=('', '_detalhe_pagamento')
)

# Filtra os que ainda não foram encontrados (onde campos de detalhe estão nulos)
nao_encontrados = df_merge[df_merge['id_detalhe_pagamento'].isna()].copy()

# 2º join com Detalhe_centro_recebimento usando financialEvent.id
df_enriquecido = nao_encontrados.drop(columns=[col for col in df_pagamento.columns if col != 'id'])
df_enriquecido = df_enriquecido.merge(
    df_recebimento,
    how='left',
    left_on="financialEvent.id",
    right_on="id",
    suffixes=('', '_detalhe_recebimento')
)

# Atualiza as linhas originais com os detalhes de recebimento
df_merge.update(df_enriquecido)

# 📄 Abrir a planilha de saída
planilha_saida = client.open_by_key(planilhas_ids["Financeiro_Completo_Laurinha"])
aba_saida = planilha_saida.sheet1

# Limpa a aba e sobrescreve
aba_saida.clear()
set_with_dataframe(aba_saida, df_merge)

print("✅ Planilha sobrescrita com sucesso.")
