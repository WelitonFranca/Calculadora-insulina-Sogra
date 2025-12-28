import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. FUNÇÃO DE CONEXÃO SEGURA ---
@st.cache_resource(ttl=600)
def conectar_banco():
    # Verifica Secrets
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Secrets não configurados.")
        st.stop()

    try:
        # Carrega e corrige a chave
        creds = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds:
            creds["private_key"] = creds["private_key"].replace("\\n", "\n")
        
        # Conecta
        gc = gspread.service_account_from_dict(creds)
        
        # Tenta abrir ou criar planilha
        try:
            sh = gc.open("banco_dados_insulina")
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("❌ Planilha 'banco_dados_insulina' não encontrada.")
            st.stop()
            
        return sh

    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        st.stop()

# --- 3. PREPARAÇÃO DAS ABAS ---
def preparar_abas():
    sh = conectar_banco()
    
    # Garante aba usuarios
    try:
        sh.worksheet("usuarios")
    except:
        ws = sh.add_worksheet("usuarios", 100, 5)
        ws.append_row(["usuario", "senha", "criado_em"])
        
    # Garante aba registros
    try:
        sh.worksheet("registros")
    except:
        ws = sh.add_worksheet("registros", 1000, 10)
        ws.append_row(["usuario", "data", "glicemia", "carbos", "icr", "dose"])

    return sh

# --- 4. APP PRINCIPAL ---
def main():
    st.title("💉 Controle de Insulina")
    
    # Inicializa conexão
    try:
        sh = preparar_abas()
    except:
        st.stop()

    # Sessão
    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

    # TELA DE LOGIN / CADASTRO
    if not st.session_state.logado:
        tab1, tab2 = st.tabs(["Login", "Cadastro"])
        
        with tab1:
            with st.form("login_form"):
                u = st.text_input("Usuário").lower().strip()
                p = st.text_input("Senha", type="password").strip()
                if st.form_submit_button("Entrar"):
                    ws = sh.worksheet("usuarios")
                    df = pd.DataFrame(ws.get_all_records()).astype(str)
                    
                    if not df.empty:
                        # Verifica login
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
            with st.form("cad_form"):
                nu = st.text_input("Novo Usuário").lower().strip()
                np = st.text_input("Nova Senha", type="password").strip()
                
                if st.form_submit_button("Criar Conta"):
                    # --- AQUI ESTAVA O ERRO, AGORA CORRIGIDO ---
                    if len(nu) < 3 or len(np) < 3:
                        st.warning("Usuário e senha devem ter no mínimo 3 caracteres.")
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
        st.success(f"Logado como: **{st.session_state.usuario_atual}**")
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()
            
        st.divider()
        
        # Formulário de Cálculo
        with st.form("calculo"):
            c1, c2 = st.columns(2)
            glic = c1.number_input("Glicemia", 0, 900)
            carbos = c2.number_input("Carbos (g)", 0, 500)
            icr = st.selectbox("ICR", range(1, 100), index=9)
            
            if st.form_submit_button("Calcular e Salvar"):
                alvo = 100
                fator = 40
                
                corr = (glic - alvo) / fator if glic > alvo else 0
                ref = carbos / icr
                dose = round(corr + ref)
                
                # Salva
                ws_reg = sh.worksheet("registros")
                data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ws_reg.append_row([st.session_state.usuario_atual, data_hora, glic, carbos, icr, dose])
                
                st.info(f"✅ Dose: **{dose} UI**")

        # Histórico
        st.subheader("Últimos Registros")
        ws_reg = sh.worksheet("registros")
        df = pd.DataFrame(ws_reg.get_all_records())
        
        if not df.empty:
            df = df[df['usuario'] == st.session_state.usuario_atual]
            st.dataframe(df.tail(5))

if __name__ == "__main__":
    main()
