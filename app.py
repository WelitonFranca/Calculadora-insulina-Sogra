import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime
from fpdf import FPDF
import os
import matplotlib.pyplot as plt

# 1. CONFIGURAÇÃO IMEDIATA (Previne Loop)
st.set_page_config(page_title="Calculadora Insulina", page_icon="💉", layout="centered")

# 2. FUNÇÃO DE LIMPEZA DE CHAVE (A "Mágica")
def limpar_chave_privada(chave):
    """Corrige a chave se ela vier com espaços ou quebras erradas"""
    if not chave: return ""
    # Remove aspas extras se houver
    chave = chave.strip().strip('"').strip("'")
    # Garante que as quebras de linha sejam reais
    return chave.replace("\\n", "\n")

# 3. CONEXÃO ROBUSTA (Sem oauth2client)
@st.cache_resource(ttl=600) # Recarrega a cada 10min para não cair
def get_banco_dados():
    try:
        # Verifica se existe a config
        if "gcp_service_account" not in st.secrets:
            st.error("⚙️ Configure os Secrets no painel do Streamlit.")
            st.stop()

        # Carrega e corrige as credenciais
        creds = dict(st.secrets["gcp_service_account"])
        creds["private_key"] = limpar_chave_privada(creds.get("private_key", ""))

        # Conecta usando apenas gspread (mais moderno e estável)
        gc = gspread.service_account_from_dict(creds)
        
        # Tenta abrir a planilha
        try:
            sh = gc.open("banco_dados_insulina")
            return sh
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("❌ Planilha 'banco_dados_insulina' não encontrada no Google Drive.")
            st.stop()
            
    except Exception as e:
        st.error(f"Erro de Conexão: {str(e)}")
        st.stop()

# 4. FUNÇÕES DE ACESSO A DADOS (Com tratamento de erro)
def ler_aba(nome_aba):
    sh = get_banco_dados()
    try:
        ws = sh.worksheet(nome_aba)
        dados = ws.get_all_records()
        return pd.DataFrame(dados).astype(str)
    except gspread.exceptions.WorksheetNotFound:
        st.warning(f"⚠️ A aba '{nome_aba}' não existe. Criando agora...")
        sh.add_worksheet(title=nome_aba, rows=100, cols=10)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def adicionar_linha(nome_aba, lista_dados):
    sh = get_banco_dados()
    try:
        ws = sh.worksheet(nome_aba)
        ws.append_row(lista_dados)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# 5. LÓGICA DO APP
def main():
    # Inicializa Sessão
    if 'usuario' not in st.session_state: st.session_state.usuario = None
    if 'resultado' not in st.session_state: st.session_state.resultado = None

    # --- TELA DE LOGIN ---
    if not st.session_state.usuario:
        st.title("☁️ Diário de Insulina")
        st.info("Sistema Online e Seguro")
        
        tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
        
        with tab1:
            u = st.text_input("Usuário").lower().strip()
            p = st.text_input("Senha", type="password").strip()
            if st.button("Acessar", type="primary"):
                df = ler_aba("usuarios")
                if not df.empty:
                    # Verifica login
                    user_ok = df[(df['usuario'] == u) & (df['senha'] == p)]
                    if not user_ok.empty:
                        st.session_state.usuario = u
                        st.rerun()
                    else:
                        st.error("Dados incorretos.")
                else:
                    st.warning("Nenhum usuário cadastrado.")

        with tab2:
            nu = st.text_input("Novo Usuário (Sem espaços)").lower().strip()
            np = st.text_input("Nova Senha", type="password").strip()
            if st.button("Cadastrar"):
                if len(nu) &lt; 3 or len(np) &lt; 3:
                    st.warning("Mínimo 3 caracteres.")
                else:
                    df = ler_aba("usuarios")
                    if not df.empty and nu in df['usuario'].values:
                        st.error("Usuário já existe.")
                    else:
                        # Salva: usuario, senha, data
                        adicionar_linha("usuarios", [nu, np, str(datetime.now())])
                        st.success("Criado! Faça login.")
        return # Para a execução aqui se não estiver logado

    # --- ÁREA LOGADA ---
    st.sidebar.title(f"Olá, {st.session_state.usuario.capitalize()}")
    if st.sidebar.button("Sair"):
        st.session_state.usuario = None
        st.rerun()

    st.title("Calculadora & Diário")
    
    # Formulário
    with st.form("calc_form"):
        c1, c2 = st.columns(2)
        glic = c1.number_input("Glicemia", 0, 600)
        carb = c2.number_input("Carbos (g)", 0, 500)
        icr = st.selectbox("Fator ICR", range(1, 50), index=9)
        
        enviar = st.form_submit_button("Calcular e Salvar")

    if enviar:
        alvo = 100
        fator = 40
        corr = (glic - alvo) / fator if glic > alvo else 0
        ref = carb / icr
        dose = round(corr + ref)
        
        # Salva na nuvem
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        dados_salvar = [st.session_state.usuario, agora, glic, carb, icr, dose]
        
        if adicionar_linha("registros", dados_salvar):
            st.session_state.resultado = f"Dose: {dose} unidades (C:{corr:.1f} + R:{ref:.1f})"
            st.rerun()

    # Mostra Resultado
    if st.session_state.resultado:
        st.success(st.session_state.resultado)

    # Histórico e Gráfico
    st.divider()
    st.subheader("Histórico")
    df_reg = ler_aba("registros")
    
    if not df_reg.empty and 'usuario' in df_reg.columns:
        # Filtra usuário
        meus_dados = df_reg[df_reg['usuario'] == st.session_state.usuario].copy()
        
        if not meus_dados.empty:
            # Mostra Tabela
            st.dataframe(meus_dados, use_container_width=True)
            
            # Tenta gerar gráfico se tiver dados numéricos
            try:
                meus_dados['Glicemia'] = pd.to_numeric(meus_dados['Glicemia'], errors='coerce')
                meus_dados = meus_dados.dropna(subset=['Glicemia'])
                
                if len(meus_dados) > 1:
                    st.line_chart(meus_dados['Glicemia'])
            except:
                pass # Se der erro no gráfico, apenas não mostra, não trava o app
        else:
            st.info("Nenhum registro ainda.")

# Executa o App
if __name__ == "__main__":
    main()
