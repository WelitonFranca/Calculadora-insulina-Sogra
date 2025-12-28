import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime

# --- 1. CONFIGURAÇÃO INICIAL (Primeira linha obrigatória) ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. FUNÇÃO DE CONEXÃO SEGURA ---
@st.cache_resource(ttl=600)
def conectar_banco():
    # Verifica se os Secrets existem
    if "gcp_service_account" not in st.secrets:
        st.error("🚨 ERRO CRÍTICO: Secrets não configurados.")
        st.info("Vá em Settings > Secrets e cole suas credenciais.")
        st.stop()

    try:
        # Carrega e corrige a chave (Resolve o erro de base64)
        creds = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds:
            creds["private_key"] = creds["private_key"].replace("\\n", "\n")
        
        # Conecta no Google
        gc = gspread.service_account_from_dict(creds)
        
        # Tenta abrir a planilha
        try:
            sh = gc.open("banco_dados_insulina")
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("❌ Planilha 'banco_dados_insulina' não encontrada.")
            st.info("Crie uma planilha com EXATAMENTE este nome no Google Sheets.")
            st.stop()
            
        return sh

    except Exception as e:
        st.error(f"❌ Erro Técnico na Conexão: {e}")
        st.stop()

# --- 3. PREPARAÇÃO DAS ABAS (Auto-Correção) ---
def preparar_abas():
    sh = conectar_banco()
    
    # Verifica/Cria aba 'usuarios'
    try:
        sh.worksheet("usuarios")
    except:
        ws = sh.add_worksheet("usuarios", 100, 5)
        ws.append_row(["usuario", "senha", "criado_em"])
        
    # Verifica/Cria aba 'registros'
    try:
        sh.worksheet("registros")
    except:
        ws = sh.add_worksheet("registros", 1000, 10)
        ws.append_row(["usuario", "data", "glicemia", "carbos", "icr", "dose"])

    return sh

# --- 4. APP PRINCIPAL ---
def main():
    st.title("💉 Controle de Insulina")
    
    # Inicializa conexão e abas
    try:
        sh = preparar_abas()
    except:
        st.stop()

    # Gerenciamento de Sessão (Login)
    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

    # --- TELA DE LOGIN / CADASTRO ---
    if not st.session_state.logado:
        tab1, tab2 = st.tabs(["Login", "Cadastro"])
        
        with tab1:
            with st.form("login_form"):
                u = st.text_input("Usuário").lower().strip()
                p = st.text_input("Senha", type="password").strip()
                
                if st.form_submit_button("Entrar"):
                    ws = sh.worksheet("usuarios")
                    try:
                        records = ws.get_all_records()
                        df = pd.DataFrame(records).astype(str)
                    except:
                        df = pd.DataFrame() # Previne erro se planilha vazia
                    
                    if not df.empty:
                        # Verifica login
                        achou = df[(df['usuario'] == u) & (df['senha'] == p)]
                        if not achou.empty:
                            st.session_state.logado = True
                            st.session_state.usuario_atual = u
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")
                    else:
                        st.warning("Nenhum usuário cadastrado ainda.")

        with tab2:
            with st.form("cad_form"):
                nu = st.text_input("Novo Usuário").lower().strip()
                np = st.text_input("Nova Senha", type="password").strip()
                
                if st.form_submit_button("Criar Conta"):
                    # VERIFICAÇÃO CORRIGIDA (Símbolo < correto)
                    if len(nu) < 3 or len(np) < 3:
                        st.warning("Usuário e senha devem ter no mínimo 3 caracteres.")
                    else:
                        ws = sh.worksheet("usuarios")
                        existing = ws.col_values(1)
                        if nu in existing:
                            st.error("Usuário já existe.")
                        else:
                            ws.append_row([nu, np, str(datetime.now())])
                            st.success("Conta criada! Faça login na aba ao lado.")

    # --- ÁREA LOGADA (Calculadora) ---
    else:
        c_top1, c_top2 = st.columns([3, 1])
        c_top1.success(f"Olá, **{st.session_state.usuario_atual}**!")
        if c_top2.button("Sair"):
            st.session_state.logado = False
            st.rerun()
            
        st.divider()
        
        # Formulário de Cálculo
        with st.form("calculo"):
            st.subheader("Nova Medição")
            c1, c2 = st.columns(2)
            glic = c1.number_input("Glicemia Atual", 0, 900)
            carbos = c2.number_input("Carbos (g)", 0, 500)
            icr = st.selectbox("Fator ICR", range(1, 100), index=9)
            
            if st.form_submit_button("Calcular Dose"):
                alvo = 100
                fator = 40
                
                # Cálculo Seguro
                if glic > alvo:
                    corr = (glic - alvo) / fator
                else:
                    corr = 0
                    
                ref = carbos / icr
                dose = round(corr + ref)
                
                # Salva no Google Sheets
                ws_reg = sh.worksheet("registros")
                data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ws_reg.append_row([st.session_state.usuario_atual, data_hora, glic, carbos, icr, dose])
                
                # Mostra Resultado
                st.balloons()
                st.info(f"✅ Dose Recomendada: **{dose} UI**")
                st.caption(f"Detalhes: Correção ({corr:.1f}) + Refeição ({ref:.1f})")

        # Histórico
        st.divider()
        st.subheader("Seus Últimos Registros")
        ws_reg = sh.worksheet("registros")
        try:
            records = ws_reg.get_all_records()
            df = pd.DataFrame(records)
            if not df.empty:
                # Filtra apenas dados do usuário logado
                df = df[df['usuario'] == st.session_state.usuario_atual]
                # Mostra os 5 últimos
                st.dataframe(df.tail(5), use_container_width=True)
            else:
                st.info("Nenhum registro encontrado.")
        except:
            st.info("Comece a usar para ver o histórico.")

if __name__ == "__main__":
    main()
