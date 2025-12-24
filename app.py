import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from fpdf import FPDF
import sys

# --- CONFIGURAÇÕES FIXAS ---
FATOR_SENSIBILIDADE = 40
ALVO_GLICEMIA = 100
ARQUIVO_DADOS = "historico_glicemia.csv"

def salvar_dados(glicemia, carbs, icr, dose):
    novo_registro = {
        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Glicemia": glicemia,
        "Carbos": carbs,
        "ICR": icr,
        "Dose_Total": dose
    }
    df = pd.DataFrame([novo_registro])
    if not os.path.isfile(ARQUIVO_DADOS):
        df.to_csv(ARQUIVO_DADOS, index=False)
    else:
        df.to_csv(ARQUIVO_DADOS, mode='a', header=False, index=False)

def gerar_grafico(salvar_imagem=False):
    if not os.path.isfile(ARQUIVO_DADOS): 
        if not salvar_imagem: print("Sem dados para gerar gráfico.")
        return

    df = pd.read_csv(ARQUIVO_DADOS)
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
    
    plt.figure(figsize=(10, 5))
    plt.plot(df['Data'], df['Glicemia'], marker='o', color='blue', label='Glicemia')
    plt.axhline(y=ALVO_GLICEMIA, color='red', linestyle='--', label='Alvo (100)')
    plt.title('Tendencia Glicemica')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if salvar_imagem:
        plt.savefig("grafico_temp.png")
        plt.close()
    else:
        plt.show()

def exportar_pdf():
    if not os.path.isfile(ARQUIVO_DADOS):
        print("Sem dados para exportar.")
        return

    try:
        df = pd.read_csv(ARQUIVO_DADOS)
        df['Data_dt'] = pd.to_datetime(df['Data'], dayfirst=True)
        
        # Cálculo da Média dos últimos 7 dias
        hoje = datetime.now()
        ultima_semana = hoje - timedelta(days=7)
        df_semana = df[df['Data_dt'] >= ultima_semana]
        media_semanal = df_semana['Glicemia'].mean() if not df_semana.empty else 0

        gerar_grafico(salvar_imagem=True)
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "Relatorio de Controle Glicemico", ln=True, align='C')
        
        pdf.set_font("Arial", size=10)
        pdf.ln(5)
        pdf.cell(200, 7, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
        pdf.cell(200, 7, f"Parametros: Alvo {ALVO_GLICEMIA} mg/dL | Sensibilidade {FATOR_SENSIBILIDADE}", ln=True)
        
        # DESTAQUE: MÉDIA SEMANAL
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(0, 0, 255) # Azul
        pdf.cell(200, 10, f"Media Glicemica (Ultimos 7 dias): {media_semanal:.1f} mg/dL", ln=True)
        pdf.set_text_color(0, 0, 0) # Volta para preto
        
        # Inserir Gráfico
        if os.path.exists("grafico_temp.png"):
            pdf.image("grafico_temp.png", x=10, y=60, w=190)
        pdf.ln(95)
        
        # Tabela de Dados (Últimos 15 registros)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(45, 8, "Data/Hora", 1)
        pdf.cell(30, 8, "Glicemia", 1)
        pdf.cell(30, 8, "Carbos", 1)
        pdf.cell(30, 8, "ICR", 1)
        pdf.cell(30, 8, "Dose", 1)
        pdf.ln()
        
        pdf.set_font("Arial", size=10)
        for i, row in df.tail(15).iterrows():
            pdf.cell(45, 8, str(row['Data']), 1)
            pdf.cell(30, 8, str(row['Glicemia']), 1)
            pdf.cell(30, 8, str(row['Carbos']), 1)
            pdf.cell(30, 8, str(row['ICR']), 1)
            pdf.cell(30, 8, str(row['Dose_Total']), 1)
            pdf.ln()

        pdf.output("Relatorio_Glicemia_Completo.pdf")
        if os.path.exists("grafico_temp.png"): os.remove("grafico_temp.png")
        print("\n[Sucesso] 'Relatorio_Glicemia_Completo.pdf' gerado na pasta!")
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")

def calcular_insulina():
    print("\n--- NOVO CALCULO ---")
    try:
        glic_input = input("Glicemia atual: ")
        if not glic_input: return
        glic = float(glic_input)
        
        carbs_input = input("Carboidratos (g): ")
        if not carbs_input: return
        carbs = float(carbs_input)
        
        print("Escolha o ICR: [8, 10, 15]")
        icr_input = input("ICR: ")
        try:
            icr = int(icr_input)
        except:
            icr = 10
            
        if icr not in [8, 10, 15]: 
            print("ICR invalido, usando 10.")
            icr = 10 

        # Fórmula: ((Glicemia - Alvo) / Sensibilidade) + (Carbos / ICR)
        correcao = max(0, (glic - ALVO_GLICEMIA) / FATOR_SENSIBILIDADE)
        refeicao = carbs / icr
        
        # Arredondamento para 1 unidade (Caneta)
        dose_final = round(correcao + refeicao)
        
        print(f"\n>>> DOSE: {dose_final} unidades")
        if input("Deseja salvar no historico? (s/n): ").lower() == 's':
            salvar_dados(glic, carbs, icr, dose_final)
            print("Dados salvos!")
    except ValueError: print("Erro: Digite apenas numeros.")

# Menu Principal
while True:
    print("\n" + "="*30)
    print("1. Novo Calculo")
    print("2. Ver Tabela no Terminal")
    print("3. Ver Grafico na Tela")
    print("4. Exportar PDF para Medico")
    print("5. Sair")
    op = input("Escolha uma opcao: ")
    
    if op == '1': calcular_insulina()
    elif op == '2': 
        if os.path.exists(ARQUIVO_DADOS):
            print("\n", pd.read_csv(ARQUIVO_DADOS).tail(10))
        else: print("\nNenhum dado encontrado.")
    elif op == '3': gerar_grafico()
    elif op == '4': exportar_pdf()
    elif op == '5': break
