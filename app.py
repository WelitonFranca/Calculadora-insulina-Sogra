import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")
st.title("💉 Controle de Insulina")

# --- 2. CONEXÃO VIA SECRETS (COFRE DIGITAL) ---
def conectar_banco():
    try:
        # Busca a chave direto do cofre do Streamlit
        # Isso evita erros de formatação de arquivo
        if "google_creds" in st.secrets:
            json_string = st.secrets["google_creds"]["json_content"]
            credenciais = json.loads(json_string)
        else:
            st.error("❌ ERRO: Cofre não configurado!")
            st.info("Vá em Settings > Secrets e configure conforme o tutorial.")
            st.stop()
            
        # Conecta no Google
        gc = gspread.service_account_from_dict(credenciais)
        return gc, credenciais.get("client_email")
        
    except Exception as e:
        st.error(f"❌ Erro de Conexão: {e}")
        st.stop()

# --- 3. PREPARAÇÃO ---
def preparar_abas():
    gc, email_robo = conectar_banco()
    
    try:
        sh = gc.open("banco_dados_insulina")
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ PLANILHA NÃO ENCONTRADA")
        st.markdown(f"""
        **Conexão Segura Estabelecida!** 
        
        O robô conectou, mas não tem permissão na planilha.
        
        1. Vá na planilha **banco_dados_insulina**
        2. Compartilhe com este e-mail (Editor):
        """)
        st.code(email_robo, language="text")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao abrir planilha: {e}")
        st.stop()

    try:
        sh.worksheet("usuarios")
    except:
        ws = sh.add_worksheet("usuarios", 100, 5)
        ws.append_row(["usuario", "senha", "criado_em"])
            
    try:
        sh.worksheet("registros")
    except:
        ws = sh.add_worksheet("registros", 1000, 10)
        ws.append_row(["usuario", "data", "glicemia", "carbos", "icr", "dose"])
            
    return sh

# --- 4. APP PRINCIPAL ---
sh = preparar_abas()

if 'logado' not in st.session_state: st.session_state.logado = False
if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

# TELA DE LOGIN
if not st.session_state.logado:
    st.markdown("---")
    tab1, tab2 = st.tabs(["Login", "Cadastro"])
    
    with tab1:
        with st.form("login"):
            u = st.text_input("Usuário").lower().strip()
            p = st.text_input("Senha", type="password").strip()
            if st.form_submit_button("Entrar"):
                ws = sh.worksheet("usuarios")
                try:
                    dados = ws.get_all_records()
                    df = pd.DataFrame(dados).astype(str)
                except:
                    df = pd.DataFrame()
                
                if not df.empty and 'usuario' in df.columns:
                    achou = df[(df['usuario'] == u) & (df['senha'] == p)]
                    if not achou.empty:
                        st.session_state.logado = True
                        st.session_state.usuario_atual = u
                        st.rerun()
                    else:
                        st.error("Dados incorretos.")
                else:
                    st.warning("Sem usuários.")
    
    with tab2:
        with st.form("cadastro"):
            nu = st.text_input("Novo Usuário").lower().strip()
            np = st.text_input("Nova Senha", type="password").strip()
            if st.form_submit_button("Criar Conta"):
                ws = sh.worksheet("usuarios")
                exist = ws.col_values(1)
                if nu in exist:
                    st.error("Usuário já existe.")
                else:
                    d = datetime.now() - timedelta(hours=3)
                    ws.append_row([nu, np, str(d)])
                    st.success("Criado! Faça login.")

# ÁREA LOGADA
else:
    st.markdown("---")
    c1, c2 = st.columns([3, 1])
    c1.success(f"Olá, **{st.session_state.usuario_atual}**!")
    if c2.button("Sair"):
        st.session_state.logado = False
        st.rerun()
    
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
                ws = sh.worksheet("registros")
                ws.append_row([st.session_state.usuario_atual, str(datetime.now()), glic, carbos, icr, dose])
