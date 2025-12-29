import streamlit as st
import pandas as pd
import gspread
import glob
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. CONEXÃO ---
@st.cache_resource(ttl=600)
def conectar_banco():
    arquivos_json = glob.glob("*.json")
    arquivo_chave = None
    
    if len(arquivos_json) == 0:
        st.error("❌ Erro: Nenhum arquivo .json encontrado.")
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
        st.error(f"❌ Erro na chave: {e}")
        st.stop()

# --- 3. PREPARAÇÃO ---
def preparar_abas():
    gc = conectar_banco()
    try:
        sh = gc.open("banco_dados_insulina")
    except:
        st.error("❌ Planilha não encontrada.")
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
def main():
    st.title("💉 Controle de Insulina")
    sh = preparar_abas()

    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

    # --- TELA DE LOGIN / CADASTRO ---
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
                        st.warning("Nenhum usuário cadastrado.")
        
        with tab2:
            with st.form("cadastro"):
                nu = st.text_input("Novo Usuário").lower().strip()
                np = st.text_input("Nova Senha", type="password").strip()
                if st.form_submit_button("Criar Conta"):
                    ws = sh.worksheet("usuarios")
                    existing = ws.col_values(1)
                    if nu in existing:
                        st.error("Usuário já existe.")
                    else:
                        data_br = datetime.now() - timedelta(hours=3)
                        ws.append_row([nu, np, str(data_br)])
                        st.success("Criado! Faça login.")

    # --- ÁREA LOGADA ---
    else:
        c_user, c_logout = st.columns([3, 1])
        c_user.success(f"Olá, **{st.session_state.usuario_atual}**!")
        if c_logout.button("Sair"):
            st.session_state.logado = False
            st.rerun()
        
        st.divider()
        
        # --- FORMULÁRIO ---
        st.subheader("Nova Medição")
        with st.form("calc"):
            with st.expander("⚙️ Configurações Pessoais", expanded=False):
                c_meta, c_fator = st.columns(2)
                alvo = c_meta.number_input("Meta", value=100, step=10)
                fator_sens = c_fator.number_input("Fator Sensibilidade", value=40, step=5)

            c1, c2 = st.columns(2)
            
            glic = c1.number_input("Glicemia", min_value=0, max_value=900, value=None, placeholder="Digite...")
            carbos = c2.number_input("Carboidratos", min_value=0, max_value=500, value=0)
            icr = st.number_input("Fator ICR", min_value=1, max_value=100, value=None, placeholder="Digite...")
            
            if st.form_submit_button("Calcular e Salvar", use_container_width=True):
                if glic is None or icr is None:
                    st.warning("⚠️ Preencha Glicemia e ICR.")
                else:
                    dose_correcao = (glic - alvo) / fator_sens
                    dose_refeicao = carbos / icr
                    dose_total = max(0, dose_correcao + dose_refeicao)
                    dose_final = round(dose_total)
                    
                    data_brasil = datetime.now() - timedelta(hours=3)
                    data_formatada = data_brasil.strftime("%Y-%m-%d %H:%M")
                    
                    ws = sh.worksheet("registros")
                    ws.append_row([
                        st.session_state.usuario_atual, 
                        data_formatada, 
                        glic, carbos, icr, dose_final
                    ])
                    
                    st.divider()
                    if glic > alvo + 40: st.warning(f"⚠️ Glicemia Alta ({glic}).")
                    elif glic < 70: st.error(f"🚨 Hipoglicemia ({glic}).")
                    else: st.success(f"✅ Glicemia Controlada ({glic}).")

                    st.markdown(f"<h1 style='text-align: center; color: #0068c9;'>{dose_final} UI</h1>", unsafe_allow_html=True)
                    
                    st.info(f"""
                    **🧠 Memória de Cálculo:**
                    1. Correção: ({glic} - {alvo}) ÷ {fator_sens} = **{dose_correcao:.2f}**
                    2. Refeição: {carbos} ÷ {icr} = **{dose_refeicao:.2f}**
                    3. Total: **{dose_total:.2f} UI**
                    """)
                    st.rerun()

        # --- HISTÓRICO E GRÁFICO ---
        st.divider()
        st.subheader("📋 Relatório e Gráfico")
        
        try:
            ws = sh.worksheet("registros")
            dados = ws.get_all_records()
            
            if len(dados) > 0:
                df = pd.DataFrame(dados)
                
                if 'usuario' in df.columns and 'data' in df.columns and 'glicemia' in df.columns:
                    # Adiciona o número da linha original (para poder apagar depois)
                    # +2 porque: índice começa em 0, header é linha 1, dados começam na 2
                    df['linha_original'] = df.index + 2
                    
                    # Filtra usuário
                    df = df[df['usuario'] == st.session_state.usuario_atual].copy()
                    
                    if not df.empty:
                        # Tratamento de dados
                        df['data'] = pd.to_datetime(df['data'], errors='coerce')
                        df['glicemia'] = pd.to_numeric(df['glicemia'], errors='coerce')
                        df = df.dropna(subset=['data', 'glicemia'])

                        if not df.empty:
                            # 1. GRÁFICO
                            st.caption("Evolução da Glicemia")
                            st.line_chart(df, x='data', y='glicemia')
                            
                            st.divider()
                            
                            # 2. TABELA DE EXCLUSÃO (NOVA FUNCIONALIDADE)
                            st.subheader("🗑️ Gerenciar Registros")
                            st.caption("Marque a caixa 'Excluir' e clique no botão vermelho para apagar.")
                            
                            # Prepara tabela para edição
                            df_display = df.sort_values(by='data', ascending=False).copy()
                            df_display['Excluir'] = False # Cria coluna de checkbox
                            
                            # Colunas que serão mostradas
                            colunas_visiveis = ['Excluir', 'data', 'glicemia', 'carbos', 'dose', 'linha_original']
                            
                            # Editor de dados
                            df_editado = st.data_editor(
                                df_display[colunas_visiveis],
                                column_config={
                                    "Excluir": st.column_config.CheckboxColumn(
                                        "Apagar?",
                                        help="Marque para excluir este registro",
                                        default=False,
                                    ),
                                    "data": st.column_config.DatetimeColumn(
                                        "Data/Hora",
                                        format="DD/MM HH:mm",
                                        disabled=True
                                    ),
                                    "glicemia": st.column_config.NumberColumn("Glicemia", disabled=True),
                                    "carbos": st.column_config.NumberColumn("Carbos", disabled=True),
                                    "dose": st.column_config.NumberColumn("Dose", disabled=True),
                                    "linha_original": None # Esconde a coluna técnica
                                },
                                hide_index=True,
                                use_container_width=True
                            )
                            
                            # Botão de Apagar
                            if st.button("🚨 Apagar Registros Marcados", type="primary"):
                                # Filtra linhas marcadas
                                linhas_para_apagar = df_editado[df_editado['Excluir'] == True]['linha_original'].tolist()
                                
                                if linhas_para_apagar:
                                    # Apaga de baixo para cima para não bagunçar os índices
                                    for linha in sorted(linhas_para_apagar, reverse=True):
                                        ws.delete_rows(linha)
                                    
                                    st.success("Registros apagados com sucesso!")
                                    st.rerun()
                                else:
                                    st.warning("Nenhum registro marcado para exclusão.")
                                    
                        else:
                            st.info("Dados insuficientes.")
                    else:
                        st.info("Sem registros ainda.")
                else:
                    st.warning("Erro na estrutura da planilha.")
            else:
                st.info("Faça seu primeiro registro!")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

if __name__ == "__main__":
    main()
