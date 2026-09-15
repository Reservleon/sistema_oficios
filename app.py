import datetime
import io
import sqlite3
import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Gestão de Ofícios - Secretaria de Educação de Mansidão",
    layout="wide",
)


# Conexão com o banco de dados SQLite
def conectar_bd():
    conn = sqlite3.connect("oficios_secretaria.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oficios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER,
            ano INTEGER,
            codigo_oficio TEXT,
            tema TEXT,
            setor TEXT,
            responsavel TEXT,
            data_emissao TEXT
        )
    """)
    conn.commit()
    return conn


conn = conectar_bd()


# Função para obter a sugestão do próximo número de ofício
def obter_sugestao_numero(ano_atual):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MAX(numero) FROM oficios WHERE ano = ?", (ano_atual,)
    )
    resultado = cursor.fetchone()[0]
    return 1 if resultado is None else resultado + 1


# Função para salvar o ofício no banco com verificação de duplicação
def salvar_oficio(numero, ano_atual, tema, setor, responsavel):
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM oficios WHERE numero = ? AND ano = ?",
        (numero, ano_atual),
    )
    existe = cursor.fetchone()

    if existe:
        return (
            False,
            f"❌ O número de ofício {numero}/{ano_atual} já foi cadastrado por outro usuário!",
        )

    codigo_formatado = f"OF-SEC-{ano_atual}/{numero:03d}"
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    cursor.execute(
        """
        INSERT INTO oficios (numero, ano, codigo_oficio, tema, setor, responsavel, data_emissao)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            numero,
            ano_atual,
            codigo_formatado,
            tema,
            setor,
            responsavel,
            data_hoje,
        ),
    )

    conn.commit()
    return (
        True,
        f"✅ Ofício cadastrado com sucesso! **Número: {codigo_formatado}**",
    )


# Função para remover um ofício do banco de dados
def deletar_oficio(id_oficio):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM oficios WHERE id = ?", (id_oficio,))
    conn.commit()


# Interface Gráfica (Streamlit)
st.title("Sistema de Numeração de Ofícios")
st.subheader("Secretaria de Educação de Mansidão")

ano_atual = datetime.datetime.now().year
sugestao_num = obter_sugestao_numero(ano_atual)

# Formulário de Cadastro
with st.form("form_oficio", clear_on_submit=False):
    col1, col2, col3 = st.columns([1, 2, 2])

    with col1:
        sugestao_formatada = f"{int(sugestao_num):03d}"
        numero_digitado_str = st.text_input(
            "Número do Ofício",
            value=sugestao_formatada,
            max_chars=5,
            help="O número sugere o próximo sequencial formatado (ex: 003), mas pode ser alterado manualmente.",
        )

    with col2:
        setor = st.text_input("Setor / Departamento")

    with col3:
        responsavel = st.text_input("Nome do Responsável")

    tema = st.text_area("Assunto / Tema do Ofício")

    submetido = st.form_submit_button("Registrar Ofício")

    if submetido:
        if tema and setor and responsavel and numero_digitado_str:
            if numero_digitado_str.isdigit():
                numero_convertido = int(numero_digitado_str)
                sucesso, mensagem = salvar_oficio(
                    numero_convertido, ano_atual, tema, setor, responsavel
                )

                if sucesso:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(mensagem)
            else:
                st.error(
                    "❌ Digite apenas números no campo 'Número do Ofício'."
                )
        else:
            st.warning("⚠️ Preencha todos os campos antes de registrar.")

st.divider()

# Tabela de Consulta em Tempo Real
st.subheader("📋 Ofícios Registrados")

cursor = conn.cursor()
cursor.execute(
    "SELECT id, codigo_oficio, numero, ano, tema, setor, responsavel, data_emissao FROM oficios ORDER BY id DESC"
)
registros = cursor.fetchall()

if registros:
    df = pd.DataFrame(
        registros,
        columns=[
            "ID",
            "Código",
            "Número",
            "Ano",
            "Assunto / Tema",
            "Setor",
            "Responsável",
            "Data/Hora",
        ],
    )

    col_busca, col_download = st.columns([3, 1])

    with col_busca:
        busca = st.text_input(
            "🔍 Buscar por assunto, código, responsável ou setor:"
        )

    with col_download:
        # Prepara a conversão em arquivo compatível com Excel
        csv_excel = df.drop(columns=["ID"]).to_csv(
            index=False, sep=";", encoding="utf-8-sig"
        )
        data_hoje_str = datetime.datetime.now().strftime("%Y-%m-%d")

        st.write("")  # Espaçamento para alinhar com a caixa de busca
        st.download_button(
            label="📥 Baixar Backup (Excel)",
            data=csv_excel,
            file_name=f"backup_oficios_{data_hoje_str}.csv",
            mime="text/csv",
            help="Baixa uma planilha formatada com todos os ofícios registrados.",
        )

    if busca:
        df_exibicao = df[
            df.apply(
                lambda row: row.astype(str)
                .str.contains(busca, case=False)
                .any(),
                axis=1,
            )
        ]
    else:
        df_exibicao = df

    st.dataframe(df_exibicao.drop(columns=["ID"]), width=1000)

    st.divider()

    # Área de Exclusão de Ofício
    st.subheader("🗑️ Cancelar / Remover Ofício Cadastrado")

    opcoes_oficios = {
        f"{row['Código']} - {row['Assunto / Tema']} ({row['Setor']})": row["ID"]
        for _, row in df.iterrows()
    }

    oficio_selecionado = st.selectbox(
        "Selecione o ofício que deseja remover:", list(opcoes_oficios.keys())
    )

    if st.button("❌ Confirmar Exclusão", type="primary"):
        id_para_deletar = opcoes_oficios[oficio_selecionado]
        deletar_oficio(id_para_deletar)
        st.success("Ofício removido com sucesso!")
        st.rerun()
else:
    st.info("Nenhum ofício cadastrado até o momento.")
