import streamlit as st
import pandas as pd
import re
import gc

# Configuração da página - Identidade Alvinegra
st.set_page_config(page_title="Consolidador FOPAG Direct - Contax", layout="wide")

def extrair_valor_bruto(texto):
    padrao = r'\d+(?:\.\d+)*(?:,\d{2})'
    encontrados = re.findall(padrao, texto)
    if encontrados:
        return float(encontrados[-1].replace('.', '').replace(',', '.'))
    return 0.0

# --- INTERFACE ---
st.title("🦅 Consolidador MANAD - FOPAG CONTAX")
st.info("Sistema de Limpeza Automática e Download Direto ativado.")

# Upload de múltiplos arquivos
arquivos_enviados = st.file_uploader("Arraste seus arquivos MANAD (.txt) aqui", type=['txt'], accept_multiple_files=True)

if arquivos_enviados:
    if st.button("🚀 Gerar Base de Dados FOPAG (Limpa)"):
        # Reinicialização obrigatória da lista para evitar duplicidade
        lista_final_dados = []
        
        progresso = st.progress(0)
        status = st.empty()
        
        for i, arquivo in enumerate(arquivos_enviados):
            status.text(f"Processando arquivo {i+1} de {len(arquivos_enviados)}: {arquivo.name}")
            
            tabela_verbas = {}
            cnpj_full = "00000000000000"
            data_ref = "01/00/0000"
            
            # Leitura do arquivo
            conteudo = arquivo.getvalue().decode('latin-1').splitlines()
            soma_arquivo = {}

            for linha in conteudo:
                parts = linha.strip().split('|')
                if not parts: continue
                reg = parts[0]
                
                if reg == '0000':
                    for campo in parts:
                        limpo = re.sub(r'\D', '', campo)
                        if len(limpo) == 14: cnpj_full = limpo
                        if len(limpo) == 8 and campo.isdigit():
                            data_ref = f"01/{limpo[2:4]}/{limpo[4:8]}"

                elif reg == 'K150' and len(parts) >= 5:
                    tabela_verbas[parts[3].strip()] = parts[4].strip().upper()
                
                elif reg == 'K300':
                    try:
                        cod_v = parts[6] if len(parts[6]) > 1 else parts[7]
                        nome_v = tabela_verbas.get(cod_v.strip(), f"RUBRICA_{cod_v}")
                        valor = extrair_valor_bruto(linha)
                        if valor > 0:
                            soma_arquivo[nome_v] = soma_arquivo.get(nome_v, 0.0) + valor
                    except: continue

            cnpj_raiz = cnpj_full[:8] if len(cnpj_full) >= 8 else "00000000"

            # Adicionando ao banco de dados interno
            for rubrica, valor in soma_arquivo.items():
                lista_final_dados.append({
                    'CNPJ_RAIZ': cnpj_raiz,
                    'CNPJ_COMPLETO': cnpj_full,
                    'DATA_REF': data_ref,
                    'RUBRICA': rubrica,
                    'VALOR': valor
                })
            
            # Limpeza de memória imediata
            del conteudo
            del soma_arquivo
            gc.collect()
            progresso.progress((i + 1) / len(arquivos_enviados))

        # Geração do DataFrame final
        df_final = pd.DataFrame(lista_final_dados)
        
        if not df_final.empty:
            # Drop duplicates garante que registros idênticos não coexistam
            df_final = df_final.drop_duplicates()
            
            st.success(f"✅ Concluído! {len(df_final)} linhas únicas processadas.")
            
            # CSV com codificação para Excel Brasil
            csv_data = df_final.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig')
            
            st.download_button(
                label="📥 Baixar FOPAG_CONTAX.csv",
                data=csv_data,
                file_name="FOPAG_CONTAX.csv",
                mime="text/csv"
            )
        else:
            st.warning("Nenhum dado financeiro encontrado nos arquivos.")
            