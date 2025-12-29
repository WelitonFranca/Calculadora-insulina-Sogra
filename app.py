import streamlit as st
import pandas as pd
import gspread
import glob
from datetime import datetime

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
                        ws.append_row([nu, np, str(datetime.now())])
                        st.success("Criado! Faça login.")

    # --- ÁREA LOGADA ---
    else:
        c_user, c_logout = st.columns([3, 1])
        c_user.success(f"Olá, **{st.session_state.usuario_atual}**!")
        if c_logout.button("Sair"):
            st.session_state.logado = False
            st.rerun()
        
        st.divider()
        
        # --- FORMULÁRIO DE CÁLCULO ---
        st.subheader("Nova Medição")
        
        with st.form("calc"):
            # Configurações Pessoais (Expansível para não poluir)
            with st.expander("⚙️ Configurações Pessoais (Meta e Fator)", expanded=False):
                st.caption("Ajuste conforme orientação médica:")
                c_meta, c_fator = st.columns(2)
                # Valores padrão: Meta 100, Fator 40
                alvo = c_meta.number_input("Meta de Glicemia", value=100, step=10)
                fator_sens = c_fator.number_input("Fator de Sensibilidade", value=40, step=5)

            c1, c2 = st.columns(2)
            glic = c1.number_input("Glicemia (mg/dL)", min_value=0, max_value=900, value=None, placeholder="Digite...")
            carbos = c2.number_input("Carboidratos (g)", min_value=0, max_value=500, value=0)
            icr = st.number_input("Fator ICR (1 UI para X g)", min_value=1, max_value=100, value=None, placeholder="Digite...")
            
            if st.form_submit_button("Calcular e Salvar", use_container_width=True):
                if glic is None or icr is None:
                    st.warning("⚠️ Preencha Glicemia e ICR.")
                else:
                    # --- LÓGICA DE CÁLCULO ---
                    # 1. Correção: (Glicemia - Meta) / Fator
                    # Se glicemia for menor que a meta, o resultado é negativo (reduz a dose da comida)
                    dose_correcao = (glic - alvo) / fator_sens
                    
                    # 2. Refeição: Carbos / ICR
                    dose_refeicao = carbos / icr
                    
                    # 3. Total
                    dose_total = dose_correcao + dose_refeicao
                    
                    # Segurança: Dose nunca pode ser menor que 0
                    if dose_total < 0: dose_total = 0
                    
                    dose_final = round(dose_total)
                    
                    # Salvar no Google Sheets
                    ws = sh.worksheet("registros")
                    ws.append_row([
                        st.session_state.usuario_atual, 
                        datetime.now().strftime("%Y-%m-%d %H:%M"), 
                        glic, carbos, icr, dose_final
                    ])
                    
                    # --- EXIBIÇÃO DO RESULTADO ---
                    st.divider()
                    
                    # Status da Glicemia
                    if glic > alvo + 40:
                        st.warning(f"⚠️ Glicemia Alta ({glic} mg/dL). Correção necessária.")
                    elif glic < 70:
                        st.error(f"🚨 Hipoglicemia ({glic} mg/dL). Cuidado com a insulina!")
                    else:
                        st.success(f"✅ Glicemia Controlada ({glic} mg/dL).")

                    # Resultado Grande
                    st.markdown(f"<h1 style='text-align: center; color: #0068c9;'>{dose_final} UI</h1>", unsafe_allow_html=True)
                    st.caption("Dose Recomendada (Arredondada)")
                    
                    # Memória de Cálculo Detalhada
                    st.info(f"""
                    **🧠 Memória de Cálculo:**
                    
                    1. **Correção:** ({glic} - {alvo} meta) ÷ {fator_sens} fator = **{dose_correcao:.2f} UI**
                    2. **Refeição:** {carbos}g ÷ {icr} ICR = **{dose_refeicao:.2f} UI**
                    3. **Soma:** {dose_correcao:.2f} + {dose_refeicao:.2f} = **{dose_total:.2f} UI**
                    """)
                    
                    # Botão para atualizar histórico
                    st.button("Atualizar Histórico")

        # --- HISTÓRICO ---
        st.divider()
        st.subheader("📋 Histórico")
        
        try:
            ws = sh.worksheet("registros")
            dados = ws.get_all_records()
            
            if len(dados) > 0:
                df = pd.DataFrame(dados)
                if 'usuario' in df.columns and 'data' in df.columns:
                    df = df[df['usuario'] == st.session_state.usuario_atual]
                    if not df.empty:
                        df['data'] = pd.to_datetime(df['data'], errors='coerce')
                        st.line_chart(df, x='data', y='glicemia')
                        st.dataframe(df.sort_values(by='data', ascending=False).head(5), hide_index=True, use_container_width=True)
                    else:
                        st.info("Sem registros ainda.")
            else:
                st.info("Faça seu primeiro registro!")
        except Exception as e:
            st.error(f"Erro no histórico: {e}")

if __name__ == "__main__":
    main()
