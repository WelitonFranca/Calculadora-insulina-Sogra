import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. CONEXÃO BLINDADA (A MESMA QUE FUNCIONOU) ---
def conectar_seguro():
    if 'conexao_google' in st.session_state:
        return st.session_state.conexao_google

    st.markdown("### 🔐 Conexão Segura")
    
    # Se já tivermos a chave na memória (de um upload anterior), usamos ela
    # Caso contrário, pede o upload
    arquivo = st.file_uploader("Se necessário, arraste o arquivo JSON aqui", type="json", key="reupload_final")
    
    if arquivo:
        try:
            info_conta = json.load(arquivo)
            escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_info(info_conta, scopes=escopos)
            gc = gspread.authorize(creds)
            email = info_conta.get("client_email")
            
            st.session_state.conexao_google = (gc, email)
            st.success("✅ Conectado!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erro: {e}")
            st.stop()
    else:
        # Se não tem arquivo e não tem conexão na memória, para.
        if 'conexao_google' not in st.session_state:
            st.info("Aguardando arquivo de chave...")
            st.stop()
            
    return st.session_state.conexao_google

# --- 3. FUNÇÕES AUXILIARES ---
def preparar_planilha(gc, email):
    try:
        sh = gc.open("banco_dados_insulina")
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ PLANILHA NÃO ENCONTRADA")
        st.markdown(f"Compartilhe 'banco_dados_insulina' com: `{email}`")
        st.stop()

    # Garante as abas
    try: sh.worksheet("usuarios")
    except: sh.add_worksheet("usuarios", 100, 5).append_row(["usuario", "senha", "criado_em"])
    
    try: sh.worksheet("registros")
    except: sh.add_worksheet("registros", 1000, 10).append_row(["usuario", "data", "glicemia", "carbos", "icr", "dose"])
            
    return sh

# --- 4. APP PRINCIPAL ---
def main():
    st.title("💉 Controle de Insulina")
    
    # Conecta
    gc, email_robo = conectar_seguro()
    sh = preparar_planilha(gc, email_robo)

    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

    # --- TELA DE LOGIN ---
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

    # --- ÁREA LOGADA (COM TODAS AS FUNÇÕES) ---
    else:
        c1, c2 = st.columns([3, 1])
        c1.success(f"Olá, **{st.session_state.usuario_atual}**!")
        if c2.button("Sair"): st.session_state.logado = False; st.rerun()
        
        st.divider()
        
        # 1. CÁLCULO E INSERÇÃO
        st.subheader("Nova Medição")
        with st.form("calc"):
            # Configurações (Meta e Sensibilidade)
            with st.expander("⚙️ Configurações Pessoais (Meta e Fator)", expanded=True):
                col_a, col_b = st.columns(2)
                alvo = col_a.number_input("Meta de Glicemia", value=100, step=10)
                fator = col_b.number_input("Fator de Sensibilidade", value=40, step=5)

            c_glic, c_carb = st.columns(2)
            glic = c_glic.number_input("Glicemia Atual", min_value=0, max_value=900, value=None)
            carbos = c_carb.number_input("Carboidratos (g)", min_value=0, max_value=500, value=0)
            icr = st.number_input("Fator ICR (1 unidade cobre X carbos)", min_value=1, max_value=100, value=None)
            
            if st.form_submit_button("Calcular e Salvar", use_container_width=True):
                if glic and icr:
                    # Lógica de Cálculo
                    correcao = (glic - alvo) / fator
                    bolus_alim = carbos / icr
                    total = max(0, correcao + bolus_alim)
                    dose = round(total)
                    
                    # Salva no Google Sheets
                    ws = sh.worksheet("registros")
                    agora = datetime.now() - timedelta(hours=3) # Horário Brasil
                    ws.append_row([
                        st.session_state.usuario_atual, 
                        agora.strftime("%Y-%m-%d %H:%M"), 
                        glic, carbos, icr, dose
                    ])
                    
                    # Exibe Resultados
                    st.divider()
                    if glic > alvo + 40: st.warning(f"⚠️ Glicemia Alta: {glic}")
                    elif glic < 70: st.error(f"🚨 Hipoglicemia: {glic}")
                    else: st.success(f"✅ Glicemia na Meta: {glic}")

                    # O GRANDE NÚMERO DA DOSE
                    st.markdown(f"<h1 style='text-align:center; color:#0068c9; font-size: 60px'>{dose} UI</h1>", unsafe_allow_html=True)
                    
                    # MEMÓRIA DE CÁLCULO
                    st.info(f"""
                    **Memória de Cálculo:**
                    1. Correção: ({glic} - {alvo}) ÷ {fator} = {correcao:.2f}
                    2. Comida: {carbos} ÷ {icr} = {bolus_alim:.2f}
                    3. Total Real: {total:.2f} (Arredondado para {dose})
                    """)
                else:
                    st.warning("Preencha Glicemia e ICR para calcular.")

        # 2. HISTÓRICO E GRÁFICOS
        st.divider()
        st.subheader("Histórico e Gráficos")
        
        try:
            ws = sh.worksheet("registros")
            dados = ws.get_all_records()
            
            if len(dados) > 0:
                df = pd.DataFrame(dados)
                
                # Filtra apenas o usuário atual
                if 'usuario' in df.columns:
                    df = df[df['usuario'] == st.session_state.usuario_atual].copy()
                    
                    if not df.empty:
                        # Tratamento de dados para o gráfico
                        df['data'] = pd.to_datetime(df['data'], errors='coerce')
                        df['glicemia'] = pd.to_numeric(df['glicemia'], errors='coerce')
                        df = df.sort_values('data')
                        
                        # GRÁFICO DE LINHA
                        st.line_chart(df, x='data', y='glicemia')
                        
                        # TABELA COM OPÇÃO DE APAGAR
                        st.caption("Selecione para excluir registros errados:")
                        # Adiciona ID da linha original para poder apagar
                        # (Adicionamos 2 porque a planilha tem cabeçalho e começa no índice 1)
                        df['id_linha_planilha'] = df.index + 2 
                        
                        df_display = df[['data', 'glicemia', 'carbos', 'dose', 'id_linha_planilha']].sort_values('data', ascending=False)
                        df_display['Apagar'] = False
                        
                        tabela_editavel = st.data_editor(
                            df_display,
                            column_config={
                                "Apagar": st.column_config.CheckboxColumn(default=False),
                                "data": st.column_config.DatetimeColumn(format="DD/MM HH:mm"),
                                "id_linha_planilha": None # Esconde essa coluna
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # Botão de Exclusão
                        if st.button("🗑️ Apagar Selecionados"):
                            linhas_para_apagar = tabela_editavel[tabela_editavel['Apagar'] == True]['id_linha_planilha'].tolist()
                            if linhas_para_apagar:
                                # Apaga de baixo para cima para não bagunçar os índices
                                for linha in sorted(linhas_para_apagar, reverse=True):
                                    ws.delete_rows(linha)
                                st.success("Registros apagados!")
                                st.rerun()
            else:
                st.info("Nenhum registro encontrado.")
                
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

if __name__ == "__main__":
    main()
