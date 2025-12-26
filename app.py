import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from fpdf import FPDF
import pytz
import urllib.parse
import os

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Calculadora Insulina", page_icon="💉")

# --- ARQUIVO DE USUÁRIOS ---
ARQUIVO_USUARIOS = "usuarios_cadastrados.csv"

# --- TRUQUE DE CSS (ESTILO) ---
st.markdown("""
    <style>
        .stFileUploader div[data-testid="stFileUploaderDropzoneInstructions"] > div > span {
            display: none;
        }
        .stFileUploader div[data-testid="stFileUploaderDropzoneInstructions"] > div::after {
            content: "📂 Clique aqui para Recuperar Backup";
            font-size: 18px;
            font-weight: 900;
            color: #000000;
            background-color: rgba(255, 255, 255, 0.8);
            padding: 10px;
            border-radius: 5px;
            display: block;
            text-align: center;
        }
        .stFileUploader small {
            display: none;
        }
        .stButton button {
            width: 100%;
            height: 50px;
        }
    </style>
""", unsafe_allow_html=True)

# --- PARÂMETROS FIXOS ---
ALVO = 100
FATOR_SENSIBILIDADE = 40

# --- FUNÇÕES DE USUÁRIOS ---
def carregar_usuarios():
    if os.path.exists(ARQUIVO_USUARIOS):
        return pd.read_csv(ARQUIVO_USUARIOS)
    else:
        return pd.DataFrame(columns=["usuario", "senha", "palavra_secreta"])

def cadastrar_usuario(usuario, senha, palavra_secreta):
    usuario = usuario.lower().strip().replace(" ", "")
    palavra_secreta = palavra_secreta.lower().strip()
    
    if len(usuario) < 3: return False, "❌ O usuário deve ter pelo menos 3 letras."
    if len(senha) < 4: return False, "❌ A senha deve ter pelo menos 4 caracteres."
    if len(palavra_secreta) < 2: return False, "❌ A palavra secreta é muito curta."
    
    df = carregar_usuarios()
    if usuario in df['usuario'].values:
        return False, "❌ Este usuário já existe! Tente outro."
    
    novo_usuario = pd.DataFrame([{"usuario": usuario, "senha": senha, "palavra_secreta": palavra_secreta}])
    df_final = pd.concat([df, novo_usuario], ignore_index=True)
    df_final.to_csv(ARQUIVO_USUARIOS, index=False)
    return True, "✅ Cadastro realizado com sucesso!"

def verificar_login(usuario, senha):
    usuario = usuario.lower().strip()
    df = carregar_usuarios()
    if df.empty: return False
    # Converte para string para garantir comparação correta
    df['usuario'] = df['usuario'].astype(str)
    df['senha'] = df['senha'].astype(str)
    
    usuario_encontrado = df[(df['usuario'] == usuario) & (df['senha'] == senha)]
    return not usuario_encontrado.empty

def resetar_senha(usuario, palavra_secreta, nova_senha):
    usuario = usuario.lower().strip()
    palavra_secreta = palavra_secreta.lower().strip()
    df = carregar_usuarios()
    mask = (df['usuario'] == usuario) & (df['palavra_secreta'] == palavra_secreta)
    if not df[mask].empty:
        df.loc[mask, 'senha'] = nova_senha
        df.to_csv(ARQUIVO_USUARIOS, index=False)
        return True, "✅ Senha alterada com sucesso!"
    else:
        return False, "❌ Usuário ou Palavra Secreta incorretos."

# --- SISTEMA DE LOGIN ---
if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None

if st.session_state.usuario_logado is None:
    st.title("🔐 Acesso ao Diário")
    
    tab1, tab2, tab3 = st.tabs(["Entrar", "Criar Nova Conta", "Recuperar Senha"])
    
    # ABA 1: LOGIN
    with tab1:
        st.write("Acesse seus dados:")
        login_user = st.text_input("Usuário", key="login_u").lower().strip()
        login_pass = st.text_input("Senha", type="password", key="login_p")
        
        if st.button("ENTRAR", type="primary"):
            if verificar_login(login_user, login_pass):
                st.session_state.usuario_logado = login_user
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
        
        st.caption("💡 Se o navegador preencher automático, clique em ENTRAR.")

    # ABA 2: CADASTRO
    with tab2:
        st.write("📝 **Crie sua conta:**")
        with st.form("form_cadastro"):
            novo_user = st.text_input("Escolha um Usuário (min 3 letras)")
            novo_pass = st.text_input("Escolha uma Senha (min 4 digitos)", type="password")
            st.markdown("**Segurança:** Palavra secreta para recuperar senha (Ex: nome do cachorro).")
            nova_secret = st.text_input("Palavra Secreta", type="password")
            submit_cadastro = st.form_submit_button("CRIAR CONTA")
        
        if submit_cadastro:
            if novo_user and novo_pass and nova_secret:
                sucesso, mensagem = cadastrar_usuario(novo_user, novo_pass, nova_secret)
                if sucesso:
                    st.success(mensagem)
                    st.balloons()
                    st.info("Agora vá na aba 'Entrar' e faça login.")
                else:
                    st.error(mensagem)
            else:
                st.warning("Preencha todos os campos.")

    # ABA 3: RECUPERAÇÃO
    with tab3:
        st.write("Esqueceu a senha?")
        with st.form("form_recuperacao"):
            rec_user = st.text_input("Qual seu usuário?").lower().strip()
            rec_secret = st.text_input("Qual sua Palavra Secreta?", type="password")
            rec_new_pass = st.text_input("Nova Senha", type="password")
            submit_reset = st.form_submit_button("REDEFINIR SENHA")
        
        if submit_reset:
            if rec_user and rec_secret and rec_new_pass:
                if len(rec_new_pass) < 4:
                    st.error("A nova senha deve ter no mínimo 4 caracteres.")
                else:
                    sucesso, msg = resetar_senha(rec_user, rec_secret, rec_new_pass)
                    if sucesso:
                        st.success(msg)
                        st.info("Senha atualizada! Volte na aba 'Entrar'.")
                    else:
                        st.error(msg)
            else:
                st.warning("Preencha todos os campos.")
    
    st.stop()

# 
# USUÁRIO LOGADO
# 

usuario_atual = st.session_state.usuario_logado
ARQUIVO_DB = f"db_{usuario_atual}.csv"

# --- FUNÇÕES DE BANCO DE DADOS ---
def carregar_dados():
    if os.path.exists(ARQUIVO_DB):
        df = pd.read_csv(ARQUIVO_DB)
        try:
            df['Data_DT'] = pd.to_datetime(df['Data'], format="%d/%m/%Y %H:%M")
        except:
            pass
        return df
    else:
        return pd.DataFrame(columns=["Data", "Glicemia", "Carbos", "ICR", "Dose"])

def salvar_registro(novo_dado):
    df = carregar_dados()
    if 'Data_DT' in df.columns:
        df = df.drop(columns=['Data_DT'])
    novo_df = pd.DataFrame([novo_dado])
    df_final = pd.concat([df, novo_df], ignore_index=True)
    df_final.to_csv(ARQUIVO_DB, index=False)
    return df_final

def sobrescrever_banco(df_novo):
    if 'Data_DT' in df_novo.columns:
        df_novo = df_novo.drop(columns=['Data_DT'])
    df_novo.to_csv(ARQUIVO_DB, index=False)

if 'resultado_tela' not in st.session_state:
    st.session_state.resultado_tela = None

# --- FUNÇÃO: GERAR PDF ---
def gerar_pdf(df_historico, filtro_msg="Geral"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Relatorio de Controle Glicemico", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, f"Paciente: {usuario_atual.capitalize()} | Filtro: {filtro_msg}", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    if os.path.exists("grafico_temp.png"):
        pdf.image("grafico_temp.png", x=10, y=50, w=190)
        pdf.ln(100)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 10, "Data/Hora", 1)
    pdf.cell(30, 10, "Glicemia", 1)
    pdf.cell(30, 10, "Carbos", 1)
    pdf.cell(30, 10, "ICR", 1)
    pdf.cell(30, 10, "Dose", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    for index, row in df_historico.iterrows():
        pdf.cell(40, 10, str(row['Data']), 1)
        pdf.cell(30, 10, str(row['Glicemia']), 1)
        pdf.cell(30, 10, str(row['Carbos']), 1)
        pdf.cell(30, 10, str(row['ICR']), 1)
        pdf.cell(30, 10, str(row['Dose']), 1)
        pdf.ln()
        
    pdf.output("relatorio_final.pdf")

# --- INTERFACE PRINCIPAL ---
st.title(f"💉 Olá, {usuario_atual.capitalize()}!")

with st.sidebar:
    st.success(f"👤 Logado: **{usuario_atual.capitalize()}**")
    if st.button("Sair"):
        st.session_state.usuario_logado = None
        st.rerun()

st.markdown(f"**Configuração:** Alvo {ALVO} | Sensibilidade {FATOR_SENSIBILIDADE}")

# --- ENTRADA DE DADOS ---
st.write("---")
st.subheader("1. Dados da Medição")

col1, col2 = st.columns(2)
with col1:
    glicemia_input = st.number_input("Glicemia (mg/dL)", min_value=0, max_value=600, value=None, placeholder="0")
with col2:
    carbos_input = st.number_input("Carboidratos (g)", min_value=0, max_value=300, value=None, placeholder="0")

# --- DATA E HORA ---
st.write("---")
st.subheader("2. Quando foi?")

if 'modo_manual' not in st.session_state:
    st.session_state.modo_manual = False
if 'data_fixada' not in st.session_state:
    st.session_state.data_fixada = datetime.now()

fuso_br = pytz.timezone('America/Sao_Paulo')
agora = datetime.now(fuso_br)

if not st.session_state.modo_manual:
    st.info(f"🕒 Horário Automático: **{agora.strftime('%d/%m/%Y %H:%M')}**")
    if st.button("✏️ Alterar Data/Hora"):
        st.session_state.modo_manual = True
        st.rerun()
    data_final_para_salvar = agora
else:
    st.warning("✏️ Editando Data e Hora...")
    c1, c2 = st.columns(2)
    d = c1.date_input("Data", value=agora, format="DD/MM/YYYY")
    t = c2.time_input("Hora", value=agora)
    
    col_save, col_cancel = st.columns(2)
    
    if col_save.button("💾 SALVAR DATA E HORA", type="primary"):
        data_combinada = datetime.combine(d, t)
        st.session_state.data_fixada = data_combinada
        st.session_state.modo_manual = "FIXADO"
        st.rerun()
        
    if col_cancel.button("Cancelar"):
        st.session_state.modo_manual = False
        st.rerun()
    
    data_final_para_salvar = datetime.combine(d, t)

if st.session_state.modo_manual == "FIXADO":
    st.success(f"🔒 Data Fixada: **{st.session_state.data_fixada.strftime('%d/%m/%Y %H:%M')}**")
    if st.button("🔄 Liberar / Usar Agora"):
        st.session_state.modo_manual = False
        st.rerun()
    data_final_para_salvar = st.session_state.data_fixada

# --- SELEÇÃO DE ICR ---
st.write("---")
st.subheader("3. Configuração")
lista_opcoes = list(range(1, 21))
icr = st.selectbox("Fator ICR", options=lista_opcoes, index=9)

# --- CÁLCULO ---
if st.button("CALCULAR E REGISTRAR", type="primary", use_container_width=True):
    
    glicemia = glicemia_input if glicemia_input is not None else 0
    carbos = carbos_input if carbos_input is not None else 0

    if glicemia == 0 and carbos == 0:
        st.warning("⚠️ Digite a Glicemia ou os Carboidratos.")
    else:
        if glicemia > ALVO:
            correcao = (glicemia - ALVO) / FATOR_SENSIBILIDADE
        else:
            correcao = 0
        
        refeicao = carbos / icr
        dose_total = correcao + refeicao
        dose_final = round(dose_total)
        
        data_str = data_final_para_salvar.strftime("%d/%m/%Y %H:%M")
        novo_registro = {
            "Data": data_str,
            "Glicemia": glicemia,
            "Carbos": carbos,
            "ICR": icr,
            "Dose": dose_final
        }
        
        salvar_registro(novo_registro)
        
        st.session_state.resultado_tela = {
            "glicemia": glicemia,
            "dose_final": dose_final,
            "correcao": correcao,
            "refeicao": refeicao,
            "dose_total": dose_total
        }
        
        st.rerun()

# --- EXIBIÇÃO DO RESULTADO ---
if st.session_state.resultado_tela is not None:
    res = st.session_state.resultado_tela
    
    st.markdown("---")
    
    if res["glicemia"] < 70 and res["glicemia"] > 0:
        st.error("⚠️ HIPOGLICEMIA! Não aplique insulina. Coma 15g de açúcar.")
    else:
        st.success(f"## Dose Recomendada: {res['dose_final']} Unidades")
        with st.expander("Ver detalhes do cálculo"):
            st.write(f"🔹 Correção: {res['correcao']:.2f} u")
            st.write(f"🔹 Comida: {res['refeicao']:.2f} u")
            st.write(f"🔹 Total exato: {res['dose_total']:.2f} u")
            
    if st.button("🔄 Novo Cálculo / Limpar Tela"):
        st.session_state.resultado_tela = None
        st.rerun()

# --- ÁREA DE GERENCIAMENTO DE DADOS ---
st.write("---")
st.subheader("💾 Gerenciamento de Dados")

df = carregar_dados()

st.write("⬇️ **1º Passo: Salvar no Celular**")
if not df.empty:
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Fazer Backup (Salvar)",
        data=csv,
        file_name=f"backup_insulina_{usuario_atual}.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True
    )
else:
    st.info("Sem dados para salvar.")

st.write("") 
st.write("📂 **2º Passo: Restaurar Antigo**")
arquivo_upload = st.file_uploader(" ", type=["csv"], label_visibility="collapsed")
if arquivo_upload is not None:
    try:
        df_restaurado = pd.read_csv(arquivo_upload)
        sobrescrever_banco(df_restaurado)
        st.success("✅ Backup Restaurado!")
        st.rerun()
    except:
        st.error("Arquivo inválido.")

# --- ÁREA DE RELATÓRIOS AVANÇADOS ---
st.write("---")
st.subheader("📊 Relatórios Personalizados")

if not df.empty:
    try:
        if 'Data_DT' not in df.columns:
            df['Data_DT'] = pd.to_datetime(df['Data'], format="%d/%m/%Y %H:%M")
        df = df.sort_values(by='Data_DT')
    except:
        pass

    st.write("🔎 **O que você deseja ver?**")
    
    col_filtro1, col_filtro2 = st.columns(2)
    
    with col_filtro1:
        min_date = df['Data_DT'].min().date()
        max_date = df['Data_DT'].max().date()
        periodo = st.date_input("Período", value=(min_date, max_date), min_value=min_date, max_value=max_date, format="DD/MM/YYYY")
    
    with col_filtro2:
        opcoes_metricas = ["Glicemia", "Carbos", "Dose"]
        metricas_selecionadas = st.multiselect("Indicadores", opcoes_metricas, default=["Glicemia"])
        if not metricas_selecionadas: metricas_selecionadas = opcoes_metricas

    mask_data = (df['Data_DT'].dt.date >= periodo[0]) & (df['Data_DT'].dt.date <= periodo[1]) if isinstance(periodo, tuple) and len(periodo) == 2 else (df['Data_DT'].dt.date == periodo[0]) if isinstance(periodo, tuple) and len(periodo) == 1 else True
    
    if isinstance(periodo, tuple) and len(periodo) == 2:
        df_filtrado = df.loc[mask_data]
    elif isinstance(periodo, tuple) and len(periodo) == 1:
        df_filtrado = df[df['Data_DT'].dt.date == periodo[0]]
    else:
        df_filtrado = df

    if not df_filtrado.empty:
        st.write(f"Exibindo **{len(df_filtrado)}** registros.")
        
        fig, ax = plt.subplots(figsize=(8, 4))
        if "Glicemia" in metricas_selecionadas:
            ax.plot(df_filtrado['Data'], df_filtrado['Glicemia'], marker='o', label='Glicemia', color='blue')
            ax.axhline(y=ALVO, color='red', linestyle='--', alpha=0.5, label='Alvo')
        if "Carbos" in metricas_selecionadas:
            ax.plot(df_filtrado['Data'], df_filtrado['Carbos'], marker='s', label='Carbos (g)', color='orange', linestyle='-.')
        if "Dose" in metricas_selecionadas:
            ax.plot(df_filtrado['Data'], df_filtrado['Dose'], marker='^', label='Dose (u)', color='green')

        ax.set_title("Evolução no Período")
        ax.grid(True, alpha=0.3)
        ax.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
        plt.savefig("grafico_temp.png")

        st.write("📋 **Dados Detalhados**")
        
        # CORREÇÃO AQUI: FORÇA TODAS AS COLUNAS A APARECEREM NA TABELA
        cols_to_show = ["Data", "Glicemia", "Carbos", "ICR", "Dose"]
        cols_final = [c for c in cols_to_show if c in df_filtrado.columns]
        
        df_visual = df_filtrado[cols_final].copy()
        df_visual["Excluir"] = False
        
        df_editado = st.data_editor(
            df_visual,
            column_config={"Excluir": st.column_config.CheckboxColumn("Excluir?", default=False)},
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("🗑️ Apagar Linhas Selecionadas"):
            linhas_excluir = df_editado[df_editado["Excluir"] == True]
            if not linhas_excluir.empty:
                datas_para_apagar = linhas_excluir['Data'].tolist()
                df_original = carregar_dados()
                df_limpo = df_original[~df_original['Data'].isin(datas_para_apagar)]
                sobrescrever_banco(df_limpo)
                st.success("Registros apagados!")
                st.rerun()

        st.write("### 📤 Exportar Relatório Personalizado")
        col_zap, col_pdf = st.columns(2)
        
        gerar_pdf(df_filtrado, filtro_msg=f"Periodo: {periodo[0].strftime('%d/%m')} a {periodo[1].strftime('%d/%m') if isinstance(periodo, tuple) and len(periodo) > 1 else ''}")
        with open("relatorio_final.pdf", "rb") as pdf_file:
            col_pdf.download_button("📄 Baixar PDF (Filtrado)", pdf_file, "relatorio.pdf", "application/pdf", use_container_width=True)

        if not df_filtrado.empty:
            media_glic = df_filtrado['Glicemia'].mean()
            total_dose = df_filtrado['Dose'].sum()
            msg_zap = (f"*RESUMO DO PERÍODO*\n"
                       f"🗓️ {periodo[0].strftime('%d/%m')} até {periodo[1].strftime('%d/%m') if isinstance(periodo, tuple) and len(periodo) > 1 else ''}\n"
                       f"🩸 Glicemia Média: {media_glic:.0f}\n"
                       f"💉 Total Insulina: {total_dose} u\n"
                       f"📝 Registros: {len(df_filtrado)}")
            msg_encoded = urllib.parse.quote(msg_zap)
            link_zap = f"https://wa.me/?text={msg_encoded}"
            col_zap.link_button("💚 Resumo no WhatsApp", link_zap, use_container_width=True)

    else:
        st.info("Nenhum dado encontrado para este período.")

else:
    st.info("Histórico vazio. Faça um cálculo ou recupere um backup.")

# --- RODAPÉ PERSONALIZADO ---
st.write("---")
st.markdown(
    """
    <div style='text-align: center; color: grey; padding: 20px;'>
        Desenvolvido por <b>Weliton França</b> - Genro da Marina ❤️
    </div>
    """,
    unsafe_allow_html=True
)
