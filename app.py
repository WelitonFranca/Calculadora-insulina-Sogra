import streamlit as st
import pandas as pd
import gspread
import glob
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. CONEXÃO SILENCIOSA ---
@st.cache_resource(ttl=600)
def conectar_banco():
    # Procura silenciosamente o arquivo JSON
    arquivos_json = glob.glob("*.json")
    arquivo_chave = None
    
    if len(arquivos_json) == 0:
        st.error("❌ Erro: Nenhum arquivo de credencial (.json) encontrado.")
        st.stop()
    elif len(arquivos_json) == 1:
        arquivo_chave = arquivos_json[0]
    else:
        for f in arquivos_json:
            if "tranquil" in f or "service" in f:
                arquivo_chave = f
                break
        if not arquivo_chave: arquivo_chave = arquivos_json[0]

    try:
        gc = gspread.service_account(filename=arquivo_chave)
        return gc
    except Exception as e:
        st.error(f"❌ Erro na chave de segurança: {e}")
        st.stop()

# --- 3. PREPARAÇÃO DAS ABAS ---
def preparar_abas():
    gc = conectar_banco()
    
    try:
        sh = gc.open("banco_dados_insulina")
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ Planilha 'banco_dados_insulina' não encontrada. Verifique o nome e o compartilhamento.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro de conexão: {e}")
        st.stop()

    # Garante que as abas existem (silenciosamente)
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
    
    # Conecta sem mostrar mensagens
    sh = preparar_abas()

    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

    # TELA DE LOGIN / CADASTRO
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
                    
                    if not df.empty and 'usuario' in df.columns:
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
            with st.form("cadastro"):
                nu = st.text_input("Novo Usuário").lower().strip()
                np = st.text_input("Nova Senha", type="password").strip()
                if st.form_submit_button("Criar Conta"):
                    if len(nu) < 3 or len(np) < 3:
                        st.warning("Usuário e senha devem ter no mínimo 3 caracteres.")
                    else:
                        ws = sh.worksheet("usuarios")
                        existing = ws.col_values(1)
                        if nu in existing:
                            st.error("Este usuário já existe.")
                        else:
                            ws.append_row([nu, np, str(datetime.now())])
                            st.success("Conta criada com sucesso! Faça login na aba ao lado.")

    # ÁREA LOGADA (CALCULADORA)
    else:
        c_user, c_logout = st.columns([3, 1])
        c_user.success(f"Olá, **{st.session_state.usuario_atual}**!")
        if c_logout.button("Sair"):
            st.session_state.logado = False
            st.rerun()
        
        st.divider()
        st.subheader("Calculadora de Dose")
        
        with st.form("calc"):
            c1, c2 = st.columns(2)
            glic = c1.number_input("Glicemia Atual (mg/dL)", 0, 900, value=100)
            carbos = c2.number_input("Carboidratos (g)", 0, 500, value=0)
            icr = st.selectbox("Fator ICR (1 UI para X g)", range(1, 100), index=9, help="Quantos gramas de carbo 1 unidade de insulina cobre.")
            
            if st.form_submit_button("Calcular Dose", use_container_width=True):
                alvo = 100
                fator_sensibilidade = 40 # Pode ser ajustado no futuro
                
                # Cálculo
                correcao = (glic - alvo) / fator_sensibilidade if glic > alvo else 0
                refeicao = carbos / icr
                dose_total = correcao + refeicao
                dose_final = round(dose_total)
                
                # Salvar
                ws = sh.worksheet("registros")
                ws.append_row([
                    st.session_state.usuario_atual, 
                    datetime.now().strftime("%Y-%m-%d %H:%M"), 
                    glic, carbos, icr, dose_final
                ])
                
                st.info(f"📊 Correção: {correcao:.1f} UI | Refeição: {refeicao:.1f} UI")
                st.success(f"✅ **Dose Recomendada: {dose_final} UI**")

        st.divider()
        st.subheader("Últimos Registros")
        try:
            ws = sh.worksheet("registros")
            dados = ws.get_all_records()
            if dados:
                df = pd.DataFrame(dados)
                df = df[df['usuario'] == st.session_state.usuario_atual]
                if not df.empty:
                    st.dataframe(df.tail(5).sort_index(ascending=False), use_container_width=True)
                else:
                    st.caption("Nenhum registro encontrado.")
            else:
                st.caption("Nenhum registro encontrado.")
        except:
            st.caption("Erro ao carregar histórico.")

if __name__ == "__main__":
    main()
