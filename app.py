import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# Configuração global da página
st.set_page_config(page_title="Portal de Relatórios Diários ODS", layout="wide")

# Substitua pela URL da SUA planilha do Google Sheets
PLANILHA_URL = "https://docs.google.com/spreadsheets/d/1aNCwIHQteT-_3NzbbNf_bO5sj_nhT0zHFlZhJlo2FdY/edit?gid=0#gid=0"

# Definições operacionais padrão
equipamentos = ["Unidade ODS 1", "Unidade ODS 2", "Unidade ODS 3", "Unidade ODS 4", "Unidade ODS 5"]
fases = ["Não Iniciado", "Enchimento", "Desague", "Remoção"]
fases_progresso = {"Não Iniciado": 0, "Enchimento": 33, "Desague": 66, "Remoção": 100}

ODS_ICONS = {
    "Unidade ODS 1": "https://img.icons8.com/fluency/96/000000/gear.png",
    "Unidade ODS 2": "https://img.icons8.com/fluency/96/000000/settings.png",
    "Unidade ODS 3": "https://img.icons8.com/fluency/96/000000/services.png",
    "Unidade ODS 4": "https://img.icons8.com/fluency/96/000000/process.png",
    "Unidade ODS 5": "https://img.icons8.com/fluency/96/000000/engineering.png"
}

# --- CONEXÃO COM O GOOGLE SHEETS ---
# A função de cache garante que não faça requisições ao Google o tempo todo
@st.cache_resource
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

conn = get_connection()

def carregar_historico():
    """Lê a aba 'Historico' do Google Sheets."""
    try:
        # Lê os dados da planilha. ttl=0 significa que ele sempre pega o dado mais fresco.
        df = conn.read(spreadsheet=PLANILHA_URL, worksheet="Historico", ttl=0)
        
        # Remove linhas completamente vazias que o Google Sheets possa trazer
        df = df.dropna(how="all")
        
        if df.empty or "Data" not in df.columns:
            return pd.DataFrame(columns=["Data", "Equipamento", "Fase Atual", "Status do Prazo", "Justificativa de Atraso", "Pendências", "Progresso (%)"])
        
        # Garante que a coluna de progresso seja número e as datas sejam string
        df["Progresso (%)"] = pd.to_numeric(df["Progresso (%)"], errors='coerce').fillna(0)
        df["Data"] = df["Data"].astype(str)
        return df
    except Exception as e:
        st.error(f"Erro ao conectar com a planilha: {e}")
        return pd.DataFrame(columns=["Data", "Equipamento", "Fase Atual", "Status do Prazo", "Justificativa de Atraso", "Pendências", "Progresso (%)"])

def salvar_historico(df_hist):
    """Atualiza a aba 'Historico' no Google Sheets."""
    try:
        # O update substitui a aba inteira pelo novo DataFrame atualizado
        conn.update(spreadsheet=PLANILHA_URL, worksheet="Historico", data=df_hist)
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")

def gerar_grafico(df_plot):
    """Gera o gráfico visual de progresso das unidades."""
    df_plot['icon_url'] = df_plot['Equipamento'].map(ODS_ICONS)
    fig = px.bar(
        df_plot, 
        x="Progresso (%)", 
        y="Equipamento", 
        orientation='h',
        color="Status do Prazo",
        color_discrete_map={"No Prazo": "#28a745", "Em Atraso": "#dc3545"},
        text="Fase Atual",
        range_x=[0, 105],
        height=400
    )
    for i, row in df_plot.iterrows():
        fig.add_layout_image(
            dict(
                source=row['icon_url'],
                xref="paper", yref="y",
                x=-0.01, y=row['Equipamento'],
                sizex=0.08, sizey=0.08,
                xanchor="right", yanchor="middle",
                sizing="contain", opacity=1
            )
        )
    fig.update_layout(
        xaxis_title="Progresso do Ciclo (%)", yaxis_title="",
        yaxis_autorange="reversed", showlegend=True,
        legend_title="Status do Prazo", font=dict(size=14),
        margin=dict(l=150, r=20, t=20, b=50)
    )
    fig.update_traces(textposition='inside', insidetextanchor='middle', textfont_color="white", textfont_size=12)
    return fig

# --- INTERFACE PRINCIPAL ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>📊 Portal de Relatórios Diários ODS</h1>", unsafe_allow_html=True)
st.divider()

menu = st.radio(
    "Escolha a tela de acesso:", 
    ["📂 Acessar Relatórios Antigos (Histórico)", "📝 Abrir / Registrar Novo Relatório Diário"], 
    horizontal=True
)

df_historico = carregar_historico()

# --- TELA 1: CONSULTA DE HISTÓRICO ---
if menu == "📂 Acessar Relatórios Antigos (Histórico)":
    st.subheader("🗂️ Consulta de Histórico Operacional na Nuvem")
    
    if df_historico.empty:
        st.info("A planilha do Google Sheets está vazia. Registre um novo dia para iniciar.")
    else:
        datas_disponiveis = sorted(df_historico["Data"].unique(), reverse=True)
        data_selecionada = st.selectbox("Selecione o dia:", datas_disponiveis)
        
        df_dia = df_historico[df_historico["Data"] == data_selecionada].copy()
        st.markdown(f"### 🗓️ Status Consolidado - Dia: **{data_selecionada}**")
        
        fig_historico = gerar_grafico(df_dia)
        st.plotly_chart(fig_historico, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("#### Resumo Técnico das Unidades")
        df_exibicao = df_dia.drop(columns=["Progresso (%)", "icon_url"], errors='ignore')
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

# --- TELA 2: ENTRADA DE DADOS / NOVOS REGISTROS ---
elif menu == "📝 Abrir / Registrar Novo Relatório Diário":
    st.subheader("🛠️ Entrada de Dados Operacionais")
    
    data_input = st.date_input("Escolha a data de referência deste preenchimento:", date.today())
    data_str = data_input.strftime("%Y-%m-%d")
    
    if 'data_trabalho' not in st.session_state or st.session_state['data_trabalho'] != data_str:
        st.session_state['data_trabalho'] = data_str
        
        df_existente = df_historico[df_historico["Data"] == data_str]
        
        if not df_existente.empty:
            st.session_state['dados_operacao'] = df_existente.copy().reset_index(drop=True)
            st.toast(f"Dados carregados da nuvem para o dia {data_str}.", icon="☁️")
        else:
            st.session_state['dados_operacao'] = pd.DataFrame({
                "Data": [data_str] * 5, "Equipamento": equipamentos,
                "Fase Atual": ["Não Iniciado"] * 5, "Status do Prazo": ["No Prazo"] * 5,
                "Justificativa de Atraso": [""] * 5, "Pendências": ["Nenhuma"] * 5,
                "Progresso (%)": [0] * 5
            })
            st.toast(f"Nova ficha criada para {data_str}.", icon="✨")

    df_atual = st.session_state['dados_operacao']
    
    # Formulário Lateral
    st.sidebar.markdown(f"### 📝 Atualizar Unidades\n**Data Base:** {data_str}")
    eq_selecionado = st.sidebar.selectbox("Selecione qual ODS atualizar:", df_atual["Equipamento"].tolist())
    idx = df_atual[df_atual["Equipamento"] == eq_selecionado].index[0]
    
    st.sidebar.image(ODS_ICONS[eq_selecionado], width=50)
    
    nova_fase = st.sidebar.radio("Fase Atual da Sequência:", fases, index=fases.index(df_atual.at[idx, "Fase Atual"]))
    novo_status = st.sidebar.selectbox("Status em relação à Meta:", ["No Prazo", "Em Atraso"], index=0 if df_atual.at[idx, "Status do Prazo"] == "No Prazo" else 1)
    
    justificativa = ""
    if novo_status == "Em Atraso":
        justificativa = st.sidebar.text_area("Motivo do Atraso:", value=df_atual.at[idx, "Justificativa de Atraso"])
        
    valor_pendencia = df_atual.at[idx, "Pendências"]
    if valor_pendencia == "Nenhuma": valor_pendencia = ""
    nova_pendencia = st.sidebar.text_area("Pendências / Observações Gerais:", value=valor_pendencia)
    
    if st.sidebar.button("Aplicar Alterações na Ficha"):
        df_atual.at[idx, "Fase Atual"] = nova_fase
        df_atual.at[idx, "Status do Prazo"] = novo_status
        df_atual.at[idx, "Justificativa de Atraso"] = justificativa if novo_status == "Em Atraso" else ""
        df_atual.at[idx, "Pendências"] = nova_pendencia.strip() if nova_pendencia.strip() != "" else "Nenhuma"
        df_atual.at[idx, "Progresso (%)"] = fases_progresso[nova_fase]
        st.sidebar.success(f"Dados temporários de {eq_selecionado} modificados!")
        st.rerun()

    # Visualização Central
    st.markdown(f"### 📋 Visualização Prévia do Relatório: **{data_str}**")
    
    fig_temp = gerar_grafico(df_atual)
    st.plotly_chart(fig_temp, use_container_width=True, config={'displayModeBar': False})
    
    df_exib_temp = df_atual.drop(columns=["Progresso (%)", "icon_url"], errors='ignore')
    st.dataframe(df_exib_temp, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Botão de Salvamento Final
    if st.button("☁️ SINCRONIZAR E SALVAR ESTE DIA NO GOOGLE SHEETS", type="primary", use_container_width=True):
        with st.spinner("Conectando ao Google Sheets e salvando dados..."):
            df_historico_limpo = df_historico[df_historico["Data"] != data_str]
            df_historico_final = pd.concat([df_historico_limpo, df_atual], ignore_index=True)
            salvar_historico(df_historico_final)
        st.success(f"Relatório do dia {data_str} salvo com sucesso na sua Planilha do Google!")
