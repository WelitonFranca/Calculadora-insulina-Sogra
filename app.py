import streamlit as st
import pandas as pd
import gspread
import re
from datetime import datetime

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. FUNÇÃO MÁGICA DE REPARO DA CHAVE ---
def reparar_chave_secreta(chave_suja):
    """
    Pega a chave de qualquer jeito (com espaços, enters, \\n) 
    e formata para o padrão PEM exato (linhas de 64 chars).
    """
    # 1. Remove cabeçalhos e rodapés antigos para limpar
    chave_limpa = re.sub(r'-----(BEGIN|END) PRIVATE KEY-----', '', chave_suja)
    
    # 2. Remove TUDO que não for letra/número da chave (tira espaços, \n, \\n, tabs)
    chave_limpa = re.sub(r'[\s\]+n?', '', chave_limpa)
    
    # 3. Reconstrói a chave do zero com linhas de 64 caracteres
    chave_formatada = "-----BEGIN PRIVATE KEY-----\n"
    for i in range(0, len(chave_limpa), 64):
        chave_formatada += chave_limpa[i:i+64] + "\n"
    chave_formatada += "-----END PRIVATE KEY-----\n"
    
    return chave_formatada

# --- 3. CONEXÃO SEGURA ---
@st.cache_resource(ttl=600)
def conectar_banco():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Secrets não configurados.")
        st.stop()

    try:
        creds = dict(st.secrets["gcp_service_account"])
        
        # AQUI ESTÁ A CORREÇÃO AUTOMÁTICA
        if "private_key" in creds:
            creds["private_key"] = reparar_chave_secreta(creds["private_key"])
        
        # Conecta
        gc = gspread.service_account_from_dict(creds)
        
        # Abre Planilha
        try:
            sh = gc.open("banco_dados_insulina")
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("❌ Planilha 'banco_dados_insulina' não encontrada.")
            st.stop()
            
        return sh

    except Exception as e:
        st.error(f"Erro na Conexão: {e}")
        st.info("O sistema tentou corrigir a chave, mas ela parece estar incompleta nos Secrets.")
        st.stop()

# --- 4. PREPARAÇÃO DAS ABAS ---
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

# --- 5. APP PRINCIPAL ---
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
            with st.form("login_form"):
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
            with st.form("cad_form"):
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
        
        with st.form("calculo"):
            c1, c2 = st.columns(2)
            glic = c1.number_input("Glicemia", 0, 900)
            carbos = c2.number_input("Carbos (g)", 0, 500)
            icr = st.selectbox("ICR", range(1, 100), index=9)
            
            if st.form_submit_button("Calcular"):
                alvo = 100
                fator = 40
                corr = (glic - alvo) / fator if glic > alvo else 0
                ref = carbos / icr
                dose = round(corr + ref)
                
                ws_reg = sh.worksheet("registros")
                ws_reg.append_row([st.session_state.usuario_atual, datetime.now().strftime("%Y-%m-%d %H:%M"), glic, carbos, icr, dose])
                
                st.info(f"✅ Dose: **{dose} UI**")

        st.subheader("Histórico")
        ws_reg = sh.worksheet("registros")
        try:
            df = pd.DataFrame(ws_reg.get_all_records())
            if not df.empty:
                df = df[df['usuario'] == st.session_state.usuario_atual]
                st.dataframe(df.tail(5))
        except:
            pass

if __name__ == "__main__":
    main()
