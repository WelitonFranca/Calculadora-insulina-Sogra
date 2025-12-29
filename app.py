import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2 import service_account # Biblioteca oficial do Google
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")
st.title("💉 Controle de Insulina")

# --- 2. CONEXÃO ROBUSTA (MÉTODO GOOGLE AUTH) ---
def conectar_banco():
    if 'conexao_ok' in st.session_state:
        return st.session_state.conexao_ok

    st.markdown("---")
    st.warning("📂 **Arraste seu arquivo JSON abaixo:**")
    
    arquivo = st.file_uploader("Solte o arquivo aqui", type=["json"], key="loader_google_auth")
    
    if arquivo is not None:
        try:
            # 1. Lê o arquivo JSON
            info_conta = json.load(arquivo)
            
            # 2. Define as permissões (Escopos)
            escopos = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            # 3. Autenticação via Biblioteca Oficial (Mais segura)
            creds = service_account.Credentials.from_service_account_info(
                info_conta, 
                scopes=escopos
            )
            
            # 4. Conecta no gspread usando as credenciais oficiais
            gc = gspread.authorize(creds)
            
            # Salva na memória
            email_robo = info_conta.get("client_email")
            st.session_state.conexao_ok = (gc, email_robo)
            
            st.success(f"✅ CONEXÃO SEGURA REALIZADA! (Robô: {email_robo})")
            st.rerun()
            
        except Exception as e:
            st.error("❌ Falha na Autenticação:")
            st.error(f"{e}")
            st.stop()
    else:
        st.stop()

# --- 3. PREPARAÇÃO DA PLANILHA ---
def preparar_abas():
    gc, email_robo = conectar_banco()
    
    try:
        sh = gc.open("banco_dados_insulina")
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ PLANILHA NÃO ENCONTRADA")
        st.markdown(f"""
        **Atenção:** O robô conectou, mas não tem permissão na planilha.
        
        1. Vá na planilha **banco_dados_insulina**
        2. Compartilhe com este e-mail (como **EDITOR**):
        """)
        st.code(email_robo, language="text")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao abrir planilha: {e}")
        st.stop()

    # Cria as abas se não existirem
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
