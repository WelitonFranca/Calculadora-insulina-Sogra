import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials # Biblioteca Oficial do Google
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E LIMPEZA ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# Limpa qualquer lixo de memória das tentativas anteriores
st.cache_resource.clear()
st.cache_data.clear()

st.title("💉 Controle de Insulina")

# --- 2. CONEXÃO BLINDADA (VIA UPLOAD) ---
def conectar_seguro():
    # Se já conectou, usa a conexão salva
    if 'conexao_google' in st.session_state:
        return st.session_state.conexao_google

    st.markdown("### 🔐 Conexão Segura")
    st.warning("⚠️ A chave anterior foi descartada. Por favor, use a **NOVA CHAVE** que você acabou de baixar.")
    
    arquivo = st.file_uploader("Arraste o NOVO arquivo JSON aqui", type="json", key="novo_upload")
    
    if arquivo:
        try:
            # 1. Lê o arquivo cru (sem tocar no texto)
            info_conta = json.load(arquivo)
            
            # 2. Define permissões
            escopos = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            # 3. Autenticação OFICIAL (Google Auth)
            # Essa biblioteca corrige a assinatura JWT automaticamente
            creds = Credentials.from_service_account_info(info_conta, scopes=escopos)
            
            # 4. Conecta no Gspread usando a credencial oficial
            gc = gspread.authorize(creds)
            
            # Sucesso!
            email = info_conta.get("client_email")
            st.session_state.conexao_google = (gc, email)
            st.success("✅ CONECTADO! O problema era a chave antiga.")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Erro: {e}")
            st.stop()
    else:
        st.info("Aguardando arquivo...")
        st.stop()

# --- 3. LÓGICA DO APP ---
def main():
    gc, email_robo = conectar_seguro()
    
    # Tenta abrir a planilha
    try:
        sh = gc.open("banco_dados_insulina")
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ PLANILHA NÃO ENCONTRADA")
        st.markdown(f"""
        **Conexão OK!** Agora só falta a permissão.
        
        1. Vá na planilha **banco_dados_insulina**
        2. Compartilhe com:
        """)
        st.code(email_robo, language="text")
        st.stop()

    # Cria abas se necessário
    try: sh.worksheet("usuarios")
    except: sh.add_worksheet("usuarios", 100, 5).append_row(["usuario", "senha", "criado_em"])
    try: sh.worksheet("registros")
    except: sh.add_worksheet("registros", 1000, 10).append_row(["usuario", "data", "glicemia", "carbos", "icr", "dose"])

    # --- RESTO DO APP ---
    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

    if not st.session_state.logado:
        tab1, tab2 = st.tabs(["Login", "Cadastro"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Usuário").lower().strip()
                p = st.text_input("Senha", type="password").strip()
                if st.form_submit_button("Entrar"):
                    ws = sh.worksheet("usuarios")
                    try: dados = ws.get_all_records(); df = pd.DataFrame(dados).astype(str)
                    except: df = pd.DataFrame()
                    if not df.empty and 'usuario' in df.columns:
                        if not df[(df['usuario'] == u) & (df['senha'] == p)].empty:
                            st.session_state.logado = True; st.session_state.usuario_atual = u; st.rerun()
                        else: st.error("Dados incorretos.")
                    else: st.warning("Sem usuários.")
        with tab2:
            with st.form("cadastro"):
                nu = st.text_input("Novo Usuário").lower().strip()
                np = st.text_input("Nova Senha", type="password").strip()
                if st.form_submit_button("Criar Conta"):
                    ws = sh.worksheet("usuarios")
                    if nu in ws.col_values(1): st.error("Existe.")
                    else: ws.append_row([nu, np, str(datetime.now())]); st.success("Criado!")

    else:
        c1, c2 = st.columns([3, 1])
        c1.success(f"Olá, **{st.session_state.usuario_atual}**!")
        if c2.button("Sair"): st.session_state.logado = False; st.rerun()
        st.divider()
        st.subheader("Nova Medição")
        with st.form("calc"):
            c_glic, c_carb = st.columns(2)
            glic = c_glic.number_input("Glicemia", min_value=0, max_value=900, value=None)
            carbos = c_carb.number_input("Carboidratos", min_value=0, max_value=500, value=0)
            icr = st.number_input("Fator ICR", min_value=1, max_value=100, value=None)
            if st.form_submit_button("Calcular"):
                if glic and icr:
                    dose = round(((glic - 100) / 40) + (carbos / icr))
                    st.success(f"Dose: {dose} UI")
                    sh.worksheet("registros").append_row([st.session_state.usuario_atual, str(datetime.now()), glic, carbos, icr, dose])

if __name__ == "__main__":
    main()
