import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- CONFIGURAÇÃO DA CHAVE NOVA ---
def carregar_credenciais():
    # 1. Abra o arquivo .json NOVO que você baixou (use o Bloco de Notas).
    # 2. Copie TUDO.
    # 3. Cole ABAIXO, substituindo o texto entre as aspas triplas.
    
    # O 'r' antes das aspas é OBRIGATÓRIO (significa Raw String)
    json_texto = r"""{
  "type": "service_account",
  "project_id": "insulina-app-v2",
  "private_key_id": "305b1aadccf01a38484936d7f561cc14ad509aa8",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDReGYniVdLvFTr\noIbqejXl2IpU/QJg8HFciqX4kuITEIeyEDL7cRYgUGPWnDAqVIG5jjK85JCkfELy\nzL6sLnAEjozQYQ7oY6/tPO3ltJipaYLvmj3ZTxwOWZgLsy2LUTJ+71sXLgDRK80d\nXaP1J02shLt2x4GdK8dEcjE3AtSSqcO0VMkYQIbeAa+uRWZXQF9LhJngYDQDVrad\nFFdIYszuDSttnf1DUcxTOGn7UPiRmUWhUqeUnI5awMLfoQcAfkOduOsyUm/YHt8y\ntYimMaCM2ihanFSTllE05tvAEaHCy7k6Vqp865NM2w72y+MJzFKb+4/Ar3DKPEVz\n+XhLXt7/AgMBAAECggEAXC6Y/iMxuJGr6Xnehce8emb+EYK6jkCiErCtc6PoO62V\nmeYJGaBdtWDLXwGjLK293RPX/kqz4L8Sk1lJO+q/vzGghH+CGQDtxgB/TQxZ9owJ\nZDpDp6Np3GLPR67Vhy73gucA9kV3dJXLEXZJFjTyuM481Xvc7Xb7nYKHaAcl11h0\nZyllLvm/roql2ke+Agn0kGJefMl+cs2ViqMzIdlKWQfrjNQVqiy5Y823gcjnVX1U\n/QSIVU+VF/c6MkiRMj7AiykZtj7GUutRrV0s9tjieARb2HIAH+jdJdlCD2Ysx4ek\neis1GwS/6gCetakI1knVr775QVbtbLplODYL/FUWUQKBgQDv2KUH2328dDi38TdA\nZITzm4ZvoACAuWy7UZBsEd3WVN3VxgoTVuBs+9iuadpQ7NVRqVVs4hfm/bcIkrrq\nI3KF3euW8whaWuxv9c8Se+YJptVeAq0i4fQgszqaZRNWazNELANYGwdejLLsvE93\nAj+k3dKSv6IGkBCe3MO1WBaA9wKBgQDflAV/EgpD6uw2OlslrMmeB9LuEa9WA7GU\nL7wknYG9TJ/1z6F0XT0juUTqLo1As8TvHDw0A9EHw3eULB74QmwIXSC/znxTzZVh\ntpqVn1kGeVASNRZpyKHMZNJKdOaqBNanMNJGwuj/9PT0rpJptb1x7fGpoG7KHtVP\n2Lbh86MYOQKBgEIJKAbty8SjSyp543h7NI/N9kmth/XpF6LLZjQbBzUH0LwW9pc0\niD35aUM8Kbu2OVVuhfKgnWwf1tEpdQUaFWH+I+s/psEZ35dD2muAaWmm4YAsxHai\nN5D5R91SjuxwP4E5jQIpDvJdUrYTct2VZOiDmoKE+JtN9wWGSuwXALspAoGBAI+9\nRINbf8oGgPKkNfFU0xKMiSmRqR4tpb9VqSoJMV4Yo0aPxIdhYmtTM2EzqJCOgvAP\nQQ1X3s2U944Fh6uoWHhQFzv5bqkaJQ37Lgs/tSaaW8Y45z3/RTZ5I1HHMnzgO3il\nxKrFqLLWM54TlgHsW+2hQpsBj/jWNeHtvDYsQxDRAoGABe2oAm62jBBg1yvOs/QP\n1HTzHX1oew9ESOUgq+pYz3pLE2yX9TQCGHCNkbh1Bp+WATyMfzZjVLGc+HW9ldJK\niXrIBNShhwHFm11Y3XfKaHgD9+B2KcxrfJnypLdPJdVxWMhCgD3PvH3IyRRYtlRd\nTmJ9tV5SF0HC2FKdEwJ/cro=\n-----END PRIVATE KEY-----\n",
  "client_email": "robo-insulina@insulina-app-v2.iam.gserviceaccount.com",
  "client_id": "108745775536733403179",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/robo-insulina%40insulina-app-v2.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
"""
    
    try:
        # Limpeza e conversão
        credenciais = json.loads(json_texto.strip())
        
        # Correção de quebra de linha (Garante que funcione)
        if "private_key" in credenciais:
            credenciais["private_key"] = credenciais["private_key"].replace("\\n", "\n")
            
        return credenciais
    except Exception as e:
        st.error(f"❌ Erro no JSON: {e}")
        st.stop()

# --- CONEXÃO ---
def conectar():
    if "COLE_AQUI" in """COLE_AQUI_O_CONTEUDO_DO_NOVO_JSON""":
        st.warning("⚠️ **PARE!** Você precisa colar a chave NOVA no código (linha 16).")
        st.stop()

    creds = carregar_credenciais()
    
    try:
        gc = gspread.service_account_from_dict(creds)
        return gc, creds["client_email"]
    except Exception as e:
        st.error(f"❌ Erro Fatal: {e}")
        st.stop()

# --- APP ---
def main():
    st.title("💉 Controle de Insulina")
    
    gc, email = conectar()
    
    try:
        sh = gc.open("banco_dados_insulina")
    except:
        st.error("❌ CONECTOU, MAS FALTA PERMISSÃO!")
        st.info(f"Vá na planilha e compartilhe com: {email}")
        st.stop()

    # Se chegou aqui, funcionou!
    st.success("✅ SISTEMA ONLINE")
    
    # Lógica simplificada para testar
    try:
        ws = sh.worksheet("registros")
        st.write("Leitura da planilha OK!")
    except:
        ws = sh.add_worksheet("registros", 1000, 10)
        ws.append_row(["usuario", "data", "glicemia", "carbos", "icr", "dose"])
        st.write("Aba criada com sucesso!")

if __name__ == "__main__":
    main()
