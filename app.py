import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. SISTEMA DE LOGIN DO ROBÔ (NA TELA) ---
def obter_conexao():
    # Se já estiver conectado na sessão, retorna a conexão
    if 'gc_connection' in st.session_state:
        return st.session_state.gc_connection, st.session_state.email_robo

    st.title("🔐 Configuração Inicial")
    st.markdown("""
    Para evitar erros de código, vamos conectar pelo navegador.
    **Abra seu arquivo JSON, copie tudo e cole na caixa abaixo:**
    """)
    
    # Caixa de texto grande para colar o JSON
    json_input = st.text_area("Cole o conteúdo do seu arquivo JSON aqui:", height=200)
    
    if st.button("Conectar"):
        if not json_input.strip():
            st.warning("A caixa está vazia.")
            st.stop()
            
        try:
            # 1. Lê o texto colado
            creds = json.loads(json_input)
            
            # 2. Conecta no Google
            gc = gspread.service_account_from_dict(creds)
            email = creds.get("client_email")
            
            # 3. Teste de Fogo: Tenta abrir a planilha
            try:
                sh = gc.open("banco_dados_insulina")
                st.success(f"✅ Conectado com sucesso! (Robô: {email})")
                
                # Salva na memória para não pedir de novo
                st.session_state.gc_connection = gc
                st.session_state.email_robo = email
                st.session_state.planilha_nome = "banco_dados_insulina"
                st.rerun()
                
            except gspread.exceptions.SpreadsheetNotFound:
                st.error("❌ Conexão OK, mas Planilha não encontrada!")
                st.markdown(f"""
                O robô conectou, mas não tem permissão.
                1. Vá na planilha **banco_dados_insulina**
                2. Compartilhe com: `{email}` (Editor)
                3. Clique em 'Conectar' novamente.
                """)
                st.stop()
                
        except json.JSONDecodeError:
            st.error("❌ O texto colado não é um JSON válido.")
        except Exception as e:
            st.error(f"❌ Erro na conexão: {e}")
            st.stop()
    
    # Para a execução aqui até o usuário conectar
    st.stop()

# --- 3. LÓGICA DO APP ---
def main():
    # Só passa daqui se conectar
    gc, email_robo = obter_conexao()
    sh = gc.open("banco_dados_insulina")

    # Garante as abas
    try: sh.worksheet("usuarios")
    except: sh.add_worksheet("usuarios", 100, 5).append_row(["usuario", "senha", "criado_em"])
    try: sh.worksheet("registros")
    except: sh.add_worksheet("registros", 1000, 10).append_row(["usuario", "data", "glicemia", "carbos", "icr", "dose"])

    st.title("💉 Controle de Insulina")

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
                        dados = ws.get_all_records()
                        df = pd.DataFrame(dados).astype(str)
                    except: df = pd.DataFrame()
                    
                    if not df.empty and 'usuario' in df.columns:
                        achou = df[(df['usuario'] == u) & (df['senha'] == p)]
                        if not achou.empty:
                            st.session_state.logado = True
                            st.session_state.usuario_atual = u
                            st.rerun()
                        else: st.error("Dados incorretos.")
                    else: st.warning("Sem usuários.")
        
        with tab2:
            with st.form("cadastro"):
                nu = st.text_input("Novo Usuário").lower().strip()
                np = st.text_input("Nova Senha", type="password").strip()
                if st.form_submit_button("Criar Conta"):
                    ws = sh.worksheet("usuarios")
                    exist = ws.col_values(1)
                    if nu in exist: st.error("Usuário já existe.")
                    else:
                        ws.append_row([nu, np, str(datetime.now())])
                        st.success("Criado! Faça login.")

    # ÁREA LOGADA
    else:
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
                    st.rerun()

if __name__ == "__main__":
    main()
