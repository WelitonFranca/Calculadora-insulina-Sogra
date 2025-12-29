import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. CONEXÃO BLINDADA ---
def conectar_seguro():
    if 'conexao_google' in st.session_state:
        return st.session_state.conexao_google

    st.markdown("### 🔐 Conexão Segura")
    arquivo = st.file_uploader("Se necessário, arraste o arquivo JSON aqui", type="json", key="reupload_final_v4")
    
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
        if 'conexao_google' not in st.session_state:
            st.info("Aguardando arquivo de chave...")
            st.stop()
    return st.session_state.conexao_google

# --- 3. PREPARAÇÃO ---
def preparar_planilha(gc, email):
    try: sh = gc.open("banco_dados_insulina")
    except: st.error("❌ PLANILHA NÃO ENCONTRADA"); st.stop()
    try: sh.worksheet("usuarios")
    except: sh.add_worksheet("usuarios", 100, 5).append_row(["usuario", "senha", "criado_em"])
    try: sh.worksheet("registros")
    except: sh.add_worksheet("registros", 1000, 10).append_row(["usuario", "data", "glicemia", "carbos", "icr", "dose"])
    return sh

# --- 4. APP PRINCIPAL ---
def main():
    st.title("💉 Controle de Insulina")
    gc, email_robo = conectar_seguro()
    sh = preparar_planilha(gc, email_robo)

    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""
    if 'ultimo_resultado' not in st.session_state: st.session_state.ultimo_resultado = None

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

    # --- ÁREA LOGADA ---
    else:
        c1, c2 = st.columns([3, 1])
        c1.success(f"Olá, **{st.session_state.usuario_atual}**!")
        if c2.button("Sair"): st.session_state.logado = False; st.rerun()
        
        st.divider()
        
        # --- CÁLCULO ---
        st.subheader("Nova Medição")
        with st.form("calc"):
            with st.expander("⚙️ Configurações (Meta e Fator)", expanded=True):
                col_a, col_b = st.columns(2)
                alvo = col_a.number_input("Meta", value=100, step=10)
                fator = col_b.number_input("Sensibilidade", value=40, step=5)

            c_glic, c_carb = st.columns(2)
            glic = c_glic.number_input("Glicemia", min_value=0, max_value=900, value=None)
            carbos = c_carb.number_input("Carboidratos (g)", min_value=0, max_value=500, value=0)
            icr = st.number_input("Fator ICR", min_value=1, max_value=100, value=None)
            
            if st.form_submit_button("Calcular e Salvar", use_container_width=True):
                if glic and icr:
                    correcao = (glic - alvo) / fator
                    bolus_alim = carbos / icr
                    total = max(0, correcao + bolus_alim)
                    dose = round(total)
                    
                    # DATA E HORA BRASÍLIA
                    fuso_brasilia = timezone(timedelta(hours=-3))
                    agora = datetime.now(fuso_brasilia)
                    data_formatada = agora.strftime("%d/%m/%Y %H:%M")
                    
                    ws = sh.worksheet("registros")
                    ws.append_row([st.session_state.usuario_atual, data_formatada, glic, carbos, icr, dose])
                    
                    st.session_state.ultimo_resultado = {
                        "glic": glic, "alvo": alvo, "fator": fator,
                        "carbos": carbos, "icr": icr,
                        "correcao": correcao, "bolus": bolus_alim,
                        "total": total, "dose": dose,
                        "msg": "Glicemia Alta" if glic > alvo + 40 else "Hipoglicemia" if glic < 70 else "Glicemia OK"
                    }
                    st.rerun()
                else:
                    st.warning("Preencha Glicemia e ICR.")

        # --- MEMÓRIA DE CÁLCULO ---
        if st.session_state.ultimo_resultado:
            res = st.session_state.ultimo_resultado
            st.markdown("---")
            st.markdown(f"<h3 style='text-align:center'>Resultado: {res['dose']} UI</h3>", unsafe_allow_html=True)
            st.warning(f"""
            **📝 Memória de Cálculo:**
            1. **Correção:** ({res['glic']} - {res['alvo']}) ÷ {res['fator']} = **{res['correcao']:.2f}**
            2. **Comida:** {res['carbos']}g ÷ {res['icr']} = **{res['bolus']:.2f}**
            3. **Soma:** {res['correcao']:.2f} + {res['bolus']:.2f} = **{res['total']:.2f}**
            👉 **Dose Final:** {res['dose']} UI
            """)
            if st.button("Limpar Resultado"):
                st.session_state.ultimo_resultado = None
                st.rerun()

        # --- HISTÓRICO ---
        st.divider()
        st.subheader("Histórico")
        try:
            ws = sh.worksheet("registros")
            dados = ws.get_all_records()
            if len(dados) > 0:
                df = pd.DataFrame(dados)
                if 'usuario' in df.columns:
                    df = df[df['usuario'] == st.session_state.usuario_atual].copy()
                    if not df.empty:
                        # --- CORREÇÃO DE LEITURA DE DATAS ---
                        # 1. Garante que tudo é texto
                        df['data'] = df['data'].astype(str)
                        
                        # 2. Tenta converter usando o padrão Brasileiro (Dia primeiro)
                        # O errors='coerce' faz com que, se falhar, vire NaT (Not a Time)
                        df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
                        
                        # 3. Remove linhas onde a data ficou inválida (opcional, mas limpa o visual)
                        df = df.dropna(subset=['data'])
                        
                        df['glicemia'] = pd.to_numeric(df['glicemia'], errors='coerce')
                        df = df.sort_values('data')
                        
                        # Gráfico
                        st.line_chart(df, x='data', y='glicemia')
                        
                        # Tabela
                        df['id'] = df.index + 2
                        df_show = df[['data', 'glicemia', 'carbos', 'dose', 'id']].sort_values('data', ascending=False)
                        df_show['Apagar'] = False
                        
                        edit = st.data_editor(
                            df_show, 
                            column_config={
                                "data": st.column_config.DatetimeColumn("Data/Hora", format="DD/MM/YYYY HH:mm"),
                                "Apagar": st.column_config.CheckboxColumn(default=False),
                                "id": None
                            },
                            hide_index=True, 
                            use_container_width=True
                        )
                        
                        if st.button("🗑️ Apagar Selecionados"):
                            for L in sorted(edit[edit['Apagar']]['id'].tolist(), reverse=True): ws.delete_rows(L)
                            st.success("Apagado!"); st.rerun()
            else: st.info("Sem dados.")
        except Exception as e: 
            st.error(f"Erro ao ler histórico: {e}")

if __name__ == "__main__":
    main()
