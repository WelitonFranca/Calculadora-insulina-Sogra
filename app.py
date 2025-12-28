import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. CONEXÃO DIRETA VIA ARQUIVO ---
@st.cache_resource(ttl=600)
def conectar_banco():
    try:
        # Tenta ler o arquivo JSON direto que você subiu
        gc = gspread.service_account(filename="service_account.json")
        
        try:
            sh = gc.open("banco_dados_insulina")
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("❌ Planilha 'banco_dados_insulina' não encontrada no Google Sheets.")
            st.stop()
            
        return sh

    except FileNotFoundError:
        st.error("❌ Arquivo 'service_account.json' não encontrado no GitHub.")
        st.info("Por favor, faça upload do seu arquivo JSON de credenciais com esse nome exato.")
        st.stop()
    except Exception as e:
        st.error(f"Erro na Conexão: {e}")
        st.stop()

# --- 3. PREPARAÇÃO (Igual ao anterior) ---
def preparar_abas():
    sh = conectar_banco()
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
def main():
    st.title("💉 Controle de Insulina")
    
    try:
        sh = preparar_abas()
    except:
        st.stop()

    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

    # TELA DE LOGIN
    if not st.session_state.logado:
        tab1, tab2 = st.tabs(["Login", "Cadastro"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Usuário").lower().strip()
                p = st.text_input("Senha", type="password").strip()
                if st.form_submit_button("Entrar"):
                    ws = sh.worksheet("usuarios")
                    try:
                        df = pd.DataFrame(ws.get_all_records()).astype(str)
                    except:
                        df = pd.DataFrame()
                    
                    if not df.empty:
                        achou = df[(df['usuario'] == u) & (df['senha'] == p)]
                        if not achou.empty:
                            st.session_state.logado = True
                            st.session_state.usuario_atual = u
                            st.rerun()
                        else:
                            st.error("Dados incorretos.")
                    else:
                        st.warning("Nenhum usuário cadastrado.")
        
        with tab2:
            with st.form("cadastro"):
                nu = st.text_input("Novo Usuário").lower().strip()
                np = st.text_input("Nova Senha", type="password").strip()
                if st.form_submit_button("Criar Conta"):
                    if len(nu) < 3 or len(np) < 3:
                        st.warning("Mínimo 3 caracteres.")
                    else:
                        ws = sh.worksheet("usuarios")
                        existing = ws.col_values(1)
                        if nu in existing:
                            st.error("Usuário já existe.")
                        else:
                            ws.append_row([nu, np, str(datetime.now())])
                            st.success("Criado! Faça login.")

    # ÁREA LOGADA
    else:
        st.success(f"Olá, **{st.session_state.usuario_atual}**!")
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()
        
        st.divider()
        with st.form("calc"):
            c1, c2 = st.columns(2)
            glic = c1.number_input("Glicemia", 0, 900)
            carbos = c2.number_input("Carbos", 0, 500)
            icr = st.selectbox("ICR", range(1, 100), index=9)
            
            if st.form_submit_button("Calcular"):
                alvo = 100
                fator = 40
                corr = (glic - alvo) / fator if glic > alvo else 0
                ref = carbos / icr
                dose = round(corr + ref)
                
                ws = sh.worksheet("registros")
                ws.append_row([st.session_state.usuario_atual, datetime.now().strftime("%Y-%m-%d %H:%M"), glic, carbos, icr, dose])
                st.info(f"✅ Dose: **{dose} UI**")

        st.subheader("Histórico")
        try:
            ws = sh.worksheet("registros")
            df = pd.DataFrame(ws.get_all_records())
            if not df.empty:
                df = df[df['usuario'] == st.session_state.usuario_atual]
                st.dataframe(df.tail(5))
        except:
            pass

if __name__ == "__main__":
    main()
