import hmac
import html
import itertools
import math
import re
import textwrap

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.data import (
    preparar_base,
    aplicar_filtros_categoricos as aplicar_filtros_categoricos_data,
    aplicar_filtro_binario_coluna,
    aplicar_filtro_participacao_ideb,
    obter_opcoes_filtro as obter_opcoes_filtro_data,
    media_ponderada_por_categoria,
    criar_variavel_eixo as criar_variavel_eixo_data,
    EIXOS_DISPONIVEIS as EIXOS_DISPONIVEIS_DATA,
    FAIXAS_IDEB,
)


# ============================================================
# REGISTRO CANÔNICO DE DIMENSÕES DO PAINEL
# ============================================================
#
# O app mantém os nomes de apresentação explicitamente, em vez de
# depender de uma sessão antiga ou de uma versão anterior de src/data.py.
# Isso evita que o rótulo legado "Tipo de Escola" reapareça nos
# selectboxes e garante que as duas classificações sejam sempre tratadas
# como dimensões independentes e paralelas.

EIXOS_DISPONIVEIS = {
    "Tipo de Escola por ano": {
        "tipo": "status",
        "coluna": "Status (do ano)",
    },
    "Tipo de Escola 2025": {
        "tipo": "status",
        "coluna": "Tipo de Escola 2025",
    },
}

for _nome_eixo, _config_eixo in EIXOS_DISPONIVEIS_DATA.items():
    if _nome_eixo in {
        "Tipo de Escola",
        "Tipo de Escola por ano",
        "Tipo de Escola 2025",
    }:
        continue

    EIXOS_DISPONIVEIS[_nome_eixo] = _config_eixo


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Painel IDEB",
    layout="wide",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

        :root {
            --ink-900: #243247;
            --ink-700: #42526A;
            --ink-500: #6B7A90;
            --line-200: #E3E8EF;
            --line-300: #D6DEE8;
            --surface-50: #F8FAFC;
            --surface-100: #F4F7FA;
            --blue-700: #245F9C;
            --blue-100: #EAF3FB;
        }

        html, body, [class*="css"] {
            font-family: "Segoe UI", Inter, -apple-system, BlinkMacSystemFont,
                         "Helvetica Neue", Arial, sans-serif;
        }

        .stApp {
            color: var(--ink-900);
        }

        .block-container {
            max-width: 1580px;
            padding-top: 1.35rem;
            padding-bottom: 2.6rem;
            padding-left: 2.1rem;
            padding-right: 2.1rem;
        }

        .panel-main-title {
            display: block;
            font-size: 2.15rem;
            font-weight: 760;
            line-height: 1.15;
            letter-spacing: -0.035em;
            color: var(--ink-900);
            margin: 0 0 0.85rem 0;
            padding: 0.20rem 0 0.15rem 0;
            overflow: visible;
        }

        /* Hierarquia tipográfica mais limpa. */
        h1, h2, h3, h4, h5, h6 {
            color: var(--ink-900);
            letter-spacing: -0.012em;
        }

        p, .stCaption, [data-testid="stCaptionContainer"] {
            color: var(--ink-700);
        }

        [data-testid="stCaptionContainer"] {
            font-size: 0.78rem;
            line-height: 1.35;
        }

        /* Botões: superfície neutra, borda discreta e foco claro. */
        div[data-testid="stButton"] button {
            min-height: 2.35rem;
            border-radius: 9px !important;
            border: 1px solid var(--line-300) !important;
            background: #FFFFFF;
            color: var(--ink-700);
            box-shadow: none !important;
            transition: background-color 120ms ease, border-color 120ms ease,
                        color 120ms ease;
        }

        div[data-testid="stButton"] button:hover {
            background: var(--surface-50);
            border-color: #BFCAD6 !important;
            color: var(--ink-900);
        }

        div[data-testid="stButton"] button p {
            font-size: 0.77rem !important;
            font-weight: 650;
            letter-spacing: 0.01em;
            white-space: nowrap !important;
        }

        /* Dicionário de variáveis: leitura editorial, leve e escaneável. */
        .dictionary-intro {
            max-width: 980px;
            margin: 0 auto 1.15rem auto;
            text-align: center;
            color: var(--ink-500);
            font-size: 0.91rem;
            line-height: 1.55;
        }

        .dictionary-section-title {
            max-width: 1120px;
            margin: 1.25rem auto 0.55rem auto;
            color: var(--ink-900);
            font-size: 1.03rem;
            font-weight: 720;
            letter-spacing: -0.012em;
        }

        .dictionary-table-wrap {
            max-width: 1120px;
            margin: 0 auto 0.85rem auto;
            border: 1px solid var(--line-200);
            border-radius: 12px;
            overflow: hidden;
            background: #FFFFFF;
        }

        table.dictionary-table {
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }

        table.dictionary-table th {
            background: #F6F8FB;
            color: #536278;
            text-align: left;
            font-size: 0.73rem;
            font-weight: 720;
            letter-spacing: 0.045em;
            text-transform: uppercase;
            padding: 0.72rem 0.92rem;
            border-bottom: 1px solid var(--line-200);
        }

        table.dictionary-table td {
            color: var(--ink-700);
            font-size: 0.84rem;
            line-height: 1.46;
            vertical-align: top;
            padding: 0.72rem 0.92rem;
            border-bottom: 1px solid #EDF1F5;
        }

        table.dictionary-table tr:last-child td {
            border-bottom: none;
        }

        table.dictionary-table td:first-child,
        table.dictionary-table th:first-child {
            width: 26%;
        }

        table.dictionary-table td:first-child {
            color: var(--ink-900);
            font-weight: 680;
        }

        table.dictionary-table tbody tr:nth-child(even) {
            background: #FBFCFD;
        }

        /* Botão exclusivo para limpar filtros. */
        .st-key-limpar_todos_filtros button {
            background-color: #FBE5E7 !important;
            border-color: #EEC3C7 !important;
            color: #7A2E34 !important;
        }

        .st-key-limpar_todos_filtros button:hover {
            background-color: #F7D8DB !important;
            border-color: #E4AFB4 !important;
            color: #642329 !important;
        }

        /* Campos de seleção: visual consistente e compacto. */
        div[data-baseweb="select"] > div {
            border-radius: 8px !important;
            border-color: var(--line-300) !important;
            box-shadow: none !important;
        }

        div[data-baseweb="select"] > div:hover {
            border-color: #B9C6D4 !important;
        }

        [data-testid="stSelectbox"] label,
        [data-testid="stMultiSelect"] label,
        [data-testid="stNumberInput"] label,
        [data-testid="stCheckbox"] label,
        [data-testid="stToggle"] label {
            color: var(--ink-700) !important;
            font-weight: 600 !important;
        }

        /* Tabs: menos "componente" e mais navegação editorial. */
        button[data-baseweb="tab"] {
            font-size: 0.82rem !important;
            font-weight: 650 !important;
            color: var(--ink-500) !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--ink-900) !important;
        }

        div[data-baseweb="tab-border"] {
            background-color: var(--line-200) !important;
        }

        /* Alertas mais leves visualmente. */
        [data-testid="stAlert"] {
            border-radius: 10px;
            border-width: 1px;
        }

        /* Gráficos no app: respiro e sem molduras pesadas. */
        [data-testid="stVegaLiteChart"] {
            border-radius: 10px;
        }

        /* ====================================================
           SIDEBAR
           ==================================================== */

        section[data-testid="stSidebar"] {
            border-right: 1px solid var(--line-200);
        }

        section[data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
            padding-left: 0.85rem;
            padding-right: 0.85rem;
            padding-bottom: 1.4rem;
        }

        section[data-testid="stSidebar"] h3 {
            font-size: 0.98rem !important;
            font-weight: 750 !important;
            margin-top: 0 !important;
            margin-bottom: 0.55rem !important;
            color: var(--ink-900) !important;
        }

        section[data-testid="stSidebar"] label {
            font-size: 0.76rem !important;
            line-height: 1.05rem !important;
            margin-bottom: 0.10rem !important;
            color: var(--ink-700) !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stVerticalBlock"] {
            gap: 0.24rem !important;
        }

        section[data-testid="stSidebar"] .stMultiSelect {
            margin-top: 0 !important;
            margin-bottom: 0.08rem !important;
        }

        section[data-testid="stSidebar"]
        div[data-baseweb="select"] {
            font-size: 0.78rem !important;
            min-height: 34px !important;
        }

        section[data-testid="stSidebar"] input {
            font-size: 0.77rem !important;
        }

        section[data-testid="stSidebar"]
        span[data-baseweb="tag"] {
            font-size: 0.71rem !important;
            border-radius: 6px !important;
        }

        /* ====================================================
           TRANSIÇÕES — HIERARQUIA VISUAL
           ==================================================== */

        .transitions-subtitle {
            text-align: center;
            max-width: 860px;
            margin: -0.05rem auto 1.15rem auto;
            color: var(--ink-500);
            font-size: 0.86rem;
            line-height: 1.45;
        }

        .transitions-control-caption {
            text-align: center;
            color: var(--ink-500);
            font-size: 0.73rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin: 0.15rem 0 0.45rem 0;
        }

        .transitions-context {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.55rem;
            flex-wrap: wrap;
            margin: 0.65rem auto 0.80rem auto;
        }

        .transitions-chip {
            display: inline-flex;
            align-items: center;
            min-height: 1.85rem;
            padding: 0.30rem 0.70rem;
            border-radius: 999px;
            border: 1px solid var(--line-200);
            background: rgba(248, 250, 252, 0.90);
            color: var(--ink-700);
            font-size: 0.76rem;
            font-weight: 650;
            line-height: 1;
        }

        .transitions-chip-period {
            background: #EDF4FA;
            border-color: #D3E2EF;
            color: #315C80;
            font-weight: 750;
        }

        .transitions-axis-note {
            max-width: 1100px;
            margin: 0.15rem auto 1.15rem auto;
            padding: 0.62rem 0.85rem;
            border: 1px solid var(--line-200);
            border-radius: 9px;
            background: rgba(248, 250, 252, 0.72);
            color: var(--ink-500);
            font-size: 0.76rem;
            line-height: 1.45;
            text-align: center;
        }

        .transitions-axis-note strong {
            color: var(--ink-700);
            font-weight: 700;
        }

        .transitions-section {
            max-width: 1420px;
            margin: 1.20rem auto 0.45rem auto;
            padding-top: 0.20rem;
        }

        .transitions-section-title {
            color: var(--ink-900);
            font-size: 1.02rem;
            font-weight: 760;
            letter-spacing: -0.015em;
            margin-bottom: 0.10rem;
        }

        .transitions-section-text {
            color: var(--ink-500);
            font-size: 0.77rem;
            line-height: 1.40;
            margin-bottom: 0.20rem;
        }

        /* ====================================================
           LOGIN
           ==================================================== */

        .login-title {
            text-align: center;
            font-size: 32px;
            font-weight: 760;
            letter-spacing: -0.03em;
            color: var(--ink-900);
            margin-top: 10vh;
            margin-bottom: 6px;
            line-height: 1.2;
        }

        .login-subtitle {
            text-align: center;
            font-size: 14px;
            color: var(--ink-500);
            margin-bottom: 22px;
        }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CONSTANTES
# ============================================================

ANOS_PAINEL = [
    2017,
    2019,
    2021,
    2023,
    2025,
]


ORDEM_ANOS_STR = [
    "2017",
    "2019",
    "2021",
    "2023",
    "2025",
]


CORES_ANOS = {
    "2017": "#D8DEE8",
    "2019": "#9CA7B4",
    "2021": "#7FB5AE",
    "2023": "#78B7E5",
    "2025": "#245F9C",
}


ESCALA_CORES_ANOS = [
    CORES_ANOS[ano]
    for ano in ORDEM_ANOS_STR
]


COR_DELTA = "#667E8E"


CATEGORIA_INTEGRAL_AGREGADA = (
    "Integral (Mista + 100%)"
)


ORDEM_FAIXA_IDEB = [
    "IDEB < 3",
    "3 ≤ IDEB < 4",
    "4 ≤ IDEB < 5",
    "5 ≤ IDEB < 6",
    "IDEB ≥ 6",
    "Sem resultado",
]


PALETA_DISTRIBUICOES = [
    "#4F7CAC",  # azul médio
    "#72B7B2",  # verde-água
    "#88A96B",  # verde sálvia
    "#D8B85F",  # mostarda suave
    "#A88DB7",  # lilás
    "#D99CA7",  # rosa queimado claro
    "#9F8A76",  # taupe
    "#8794A5",  # cinza azulado
    "#9FC3E2",  # azul claro
    "#B7C7A8",  # sálvia claro
]


# Paleta auxiliar da aba Distribuições.
# Os boxplots permanecem em azul, enquanto comparações entre grupos
# usam tons complementares suaves para manter boa leitura dos rótulos.
CORES_ANOS_DISTRIBUICOES = {
    "2017": "#A9C8E3",
    "2019": "#91B8D8",
    "2021": "#7DA8CB",
    "2023": "#6B98BD",
    "2025": "#5B89AF",
}

CORES_GRUPOS_DISTRIBUICOES = [
    "#78A9D1",
    "#6FAFA8",
]


# ============================================================
# RÓTULOS
# ============================================================

ROTULOS_DIMENSOES = {
    "Carga horária": "Carga Horária",
    "Colégio com Seleção": "Colégio com seleção",
}


VARIAVEIS_TIPO_ESCOLA = {
    "Tipo de Escola por ano",
    "Tipo de Escola 2025",
}


def rotulo_dimensao(nome):

    return ROTULOS_DIMENSOES.get(
        nome,
        nome,
    )


# ============================================================
# LOGIN
# ============================================================

def autenticar_usuario(
    usuario_digitado,
    senha_digitada,
):

    try:

        usuario_correto = str(
            st.secrets["auth"]["username"]
        )

        senha_correta = str(
            st.secrets["auth"]["password"]
        )

    except Exception:

        st.error(
            "As credenciais de acesso não foram "
            "configuradas corretamente nos Secrets "
            "do Streamlit."
        )

        st.stop()


    return (
        hmac.compare_digest(
            str(usuario_digitado),
            usuario_correto,
        )
        and
        hmac.compare_digest(
            str(senha_digitada),
            senha_correta,
        )
    )


def exibir_tela_login():

    st.markdown(
        """
        <div class="login-title">
            Painel IDEB
        </div>

        <div class="login-subtitle">
            Entre com suas credenciais para acessar o painel.
        </div>
        """,
        unsafe_allow_html=True,
    )


    _, col_login, __ = st.columns(
        [
            1.6,
            1.0,
            1.6,
        ]
    )


    with col_login:

        with st.form(
            "form_login",
            clear_on_submit=False,
        ):

            usuario = st.text_input(
                "Usuário",
            )

            senha = st.text_input(
                "Senha",
                type="password",
            )

            entrar = st.form_submit_button(
                "Entrar",
                width="stretch",
                type="primary",
            )


        if entrar:

            if autenticar_usuario(
                usuario,
                senha,
            ):

                st.session_state[
                    "autenticado"
                ] = True

                st.session_state[
                    "usuario_logado"
                ] = usuario

                st.rerun()

            else:

                st.error(
                    "Usuário ou senha incorretos."
                )


if "autenticado" not in st.session_state:

    st.session_state[
        "autenticado"
    ] = False


if not st.session_state[
    "autenticado"
]:

    exibir_tela_login()

    st.stop()


# ============================================================
# LOGOUT
# ============================================================

with st.sidebar:

    col_user, col_logout = st.columns(
        [
            1.35,
            0.65,
        ]
    )


    with col_user:

        st.caption(
            f"Usuário: "
            f"{st.session_state.get('usuario_logado', '')}"
        )


    with col_logout:

        if st.button(
            "Sair",
            width="stretch",
        ):

            st.session_state[
                "autenticado"
            ] = False

            st.session_state.pop(
                "usuario_logado",
                None,
            )

            st.rerun()


# ============================================================
# SELEÇÃO
# ============================================================

def categorizar_selecao(valor):

    if pd.isna(valor):

        return "Não informado"


    texto = str(valor).strip()


    if texto in {
        "1",
        "1.0",
        "Sim",
        "SIM",
        "sim",
    }:

        return "Sim"


    if texto in {
        "0",
        "0.0",
        "Não",
        "Nao",
        "NÃO",
        "NAO",
        "não",
        "nao",
    }:

        return "Não"


    if texto in {
        "9",
        "9.0",
    }:

        return "Não informado"


    return "Não informado"


# ============================================================
# TIPO DE ESCOLA — CLASSIFICAÇÃO LOCAL / COMPATIBILIDADE
# ============================================================

def _classificar_tipo_escola_painel(valor):

    if pd.isna(valor):
        return "Outros / não informado"

    texto = str(valor).strip().lower()
    texto = (
        texto
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )

    if not texto or texto in {"nan", "none"}:
        return "Outros / não informado"

    if "integral" in texto and "100" in texto:
        return "100% Integral"

    if texto in {"integral", "integral total"}:
        return "100% Integral"

    if texto in {"mista", "misto"}:
        return "Mista"

    if texto in {
        "parcial/regular",
        "parcial / regular",
        "parcial",
        "regular",
    }:
        return "Parcial/Regular"

    return "Outros / não informado"


def _garantir_tipo_escola_2025(base):
    """Garante a classificação fixa de 2025 em todas as linhas.

    A fonte prioritária é a coluna trazida de ESCOLAS_CONSOLIDADO.
    Como proteção para deploy/cache de uma versão anterior do data.py,
    lacunas podem ser preenchidas usando a própria classificação anual
    observada em 2025, que contém a mesma informação.
    """

    resultado = base.copy()

    if "Tipo de Escola 2025" not in resultado.columns:
        resultado["Tipo de Escola 2025"] = np.nan

    colunas_necessarias = {
        "Cód. INEP",
        "Ano",
        "Status (do ano)",
    }

    if not colunas_necessarias.issubset(resultado.columns):
        return resultado

    referencia_2025 = (
        resultado.loc[
            pd.to_numeric(resultado["Ano"], errors="coerce").eq(2025),
            ["Cód. INEP", "Status (do ano)"],
        ]
        .dropna(subset=["Cód. INEP"])
        .drop_duplicates(subset=["Cód. INEP"], keep="last")
        .set_index("Cód. INEP")["Status (do ano)"]
    )

    fallback = resultado["Cód. INEP"].map(referencia_2025)

    atual = resultado["Tipo de Escola 2025"]
    vazio = (
        atual.isna()
        | atual.astype(str).str.strip().str.lower().isin({"", "nan", "none"})
    )

    resultado.loc[vazio, "Tipo de Escola 2025"] = fallback.loc[vazio]

    return resultado



# ============================================================
# WRAPPERS DO DATA
# ============================================================

def criar_variavel_eixo(
    df,
    eixo,
):

    if eixo in VARIAVEIS_TIPO_ESCOLA:

        coluna = EIXOS_DISPONIVEIS[eixo]["coluna"]

        if coluna not in df.columns:
            raise ValueError(
                f"A coluna '{coluna}' não foi encontrada para a dimensão '{eixo}'."
            )

        resultado = df.copy()
        resultado["Categoria"] = resultado[coluna].apply(
            _classificar_tipo_escola_painel
        )

        return resultado


    if eixo == "Colégio com Seleção":

        resultado = pd.DataFrame(
            index=df.index
        )


        if "Seleção" in df.columns:

            resultado[
                "Categoria"
            ] = (
                df[
                    "Seleção"
                ]
                .apply(
                    categorizar_selecao
                )
            )

        else:

            resultado[
                "Categoria"
            ] = "Não informado"


        return resultado


    return criar_variavel_eixo_data(
        df,
        eixo,
    )


def obter_opcoes_filtro(
    df,
    nome,
):

    if nome in VARIAVEIS_TIPO_ESCOLA:

        try:
            temp = criar_variavel_eixo(df, nome)
        except ValueError:
            return []

        existentes = set(
            temp["Categoria"]
            .dropna()
            .astype(str)
            .tolist()
        )

        if "Mista" in existentes or "100% Integral" in existentes:
            existentes.add(CATEGORIA_INTEGRAL_AGREGADA)

        ordem = [
            "Parcial/Regular",
            "Mista",
            "100% Integral",
            CATEGORIA_INTEGRAL_AGREGADA,
            "Outros / não informado",
        ]

        return [valor for valor in ordem if valor in existentes]


    if nome == "Colégio com Seleção":

        temp = criar_variavel_eixo(
            df,
            nome,
        )


        ordem = [
            "Sim",
            "Não",
            "Não informado",
        ]


        existentes = set(
            temp[
                "Categoria"
            ]
            .dropna()
            .astype(str)
        )


        return [
            valor
            for valor
            in ordem
            if valor
            in existentes
        ]


    return obter_opcoes_filtro_data(
        df,
        nome,
    )


def aplicar_filtros_categoricos(
    df,
    filtros,
):

    filtros_base = filtros.copy()


    filtros_tipo_escola = {
        nome: filtros_base.pop(nome, [])
        for nome in VARIAVEIS_TIPO_ESCOLA
    }


    filtro_selecao = (
        filtros_base.pop(
            "Colégio com Seleção",
            [],
        )
    )


    resultado = (
        aplicar_filtros_categoricos_data(
            df,
            filtros_base,
        )
    )


    for nome_tipo, valores_tipo in filtros_tipo_escola.items():

        if not valores_tipo:
            continue

        temp_tipo = criar_variavel_eixo(resultado, nome_tipo)

        valores_base = []
        for valor in valores_tipo:
            if valor == CATEGORIA_INTEGRAL_AGREGADA:
                valores_base.extend(["Mista", "100% Integral"])
            else:
                valores_base.append(valor)

        resultado = (
            temp_tipo.loc[temp_tipo["Categoria"].isin(set(valores_base))]
            .drop(columns=["Categoria"])
            .reset_index(drop=True)
        )


    if filtro_selecao:

        if "Seleção" in resultado.columns:

            categoria = (
                resultado[
                    "Seleção"
                ]
                .apply(
                    categorizar_selecao
                )
            )


            resultado = (
                resultado[
                    categoria.isin(
                        filtro_selecao
                    )
                ]
                .copy()
            )


    return resultado


# ============================================================
# FORMATOS
# ============================================================

def formatos_indicador(
    indicador,
):

    if indicador == "Rendimento":

        return {
            "rotulo": ".1%",
            "tooltip": ".1%",
            "delta": "+.1%",
            "delta_cruz": "+.2%",
            "baseline": 0.30,
        }


    return {
        "rotulo": ".1f",
        "tooltip": ".1f",
        "delta": "+.1f",
        "delta_cruz": "+.2f",
        "baseline": 3.0,
    }


def formatar_valor_tabela(
    valor,
    indicador,
):

    if pd.isna(valor):

        return "—"


    if indicador == "Rendimento":

        return (
            f"{float(valor) * 100:.1f}%"
            .replace(
                ".",
                ",",
            )
        )


    return (
        f"{float(valor):.1f}"
        .replace(
            ".",
            ",",
        )
    )


# ============================================================
# AUXILIARES
# ============================================================

def chave_natural(valor):

    texto = str(valor)


    numeros = re.findall(
        r"-?\d+(?:[.,]\d+)?",
        texto,
    )


    if numeros:

        try:

            numero = float(
                numeros[0].replace(
                    ",",
                    ".",
                )
            )


            return (
                0,
                numero,
                texto,
            )

        except ValueError:

            pass


    return (
        1,
        0,
        texto,
    )


def ordenar_dimensao(
    valores,
    variavel,
):

    valores = [
        str(valor)
        for valor
        in valores
        if pd.notna(valor)
    ]


    if variavel in VARIAVEIS_TIPO_ESCOLA:

        ordem = [
            "Parcial/Regular",
            "Mista",
            "100% Integral",
            CATEGORIA_INTEGRAL_AGREGADA,
            "Outros / não informado",
        ]


        return [
            valor
            for valor
            in ordem
            if valor
            in valores
        ]


    if variavel.startswith(
        "Faixa IDEB"
    ):

        return [
            valor
            for valor
            in ORDEM_FAIXA_IDEB
            if valor
            in valores
        ]


    return sorted(
        list(
            dict.fromkeys(
                valores
            )
        ),
        key=chave_natural,
    )


def ordenar_dimensao_para_grafico(
    valores,
    variavel,
):

    valores_unicos = list(
        dict.fromkeys(
            str(valor)
            for valor
            in valores
            if pd.notna(valor)
        )
    )


    # PPI: usa ordem natural dos rótulos, de modo que faixas com
    # números sejam apresentadas na sequência numérica esperada.
    if variavel == "PPI":

        return sorted(
            valores_unicos,
            key=chave_natural,
        )


    # Faixa IDEB: respeita a progressão explícita das faixas.
    if str(variavel).startswith(
        "Faixa IDEB"
    ):

        ordenados = [
            valor
            for valor
            in ORDEM_FAIXA_IDEB
            if valor
            in valores_unicos
        ]

        extras = sorted(
            [
                valor
                for valor
                in valores_unicos
                if valor
                not in ordenados
            ],
            key=lambda valor: str(valor).casefold(),
        )

        return ordenados + extras


    # Demais dimensões: ordem alfabética.
    return sorted(
        valores_unicos,
        key=lambda valor: str(valor).casefold(),
    )


def ordenar_combinacoes_para_grafico(
    dados,
    variavel_1,
    variavel_2=None,
):

    if dados.empty:

        return []


    pares = (
        dados[
            [
                "Categoria_1",
                "Categoria_2",
                "Categoria",
            ]
        ]
        .drop_duplicates()
        .copy()
    )


    ordem_1 = ordenar_dimensao_para_grafico(
        pares[
            "Categoria_1"
        ],
        variavel_1,
    )

    mapa_1 = {
        valor: indice
        for indice, valor
        in enumerate(
            ordem_1
        )
    }

    pares[
        "_ordem_1"
    ] = (
        pares[
            "Categoria_1"
        ]
        .astype(str)
        .map(
            mapa_1
        )
        .fillna(999)
    )


    if variavel_2 is None:

        return (
            pares
            .sort_values(
                [
                    "_ordem_1",
                    "Categoria",
                ]
            )[
                "Categoria"
            ]
            .astype(str)
            .tolist()
        )


    ordem_2 = ordenar_dimensao_para_grafico(
        pares[
            "Categoria_2"
        ],
        variavel_2,
    )

    mapa_2 = {
        valor: indice
        for indice, valor
        in enumerate(
            ordem_2
        )
    }

    pares[
        "_ordem_2"
    ] = (
        pares[
            "Categoria_2"
        ]
        .astype(str)
        .map(
            mapa_2
        )
        .fillna(999)
    )


    return (
        pares
        .sort_values(
            [
                "_ordem_1",
                "_ordem_2",
                "Categoria",
            ]
        )[
            "Categoria"
        ]
        .astype(str)
        .tolist()
    )


# ============================================================
# POSIÇÕES DE SEGMENTOS EMPILHADOS
# ============================================================

def calcular_posicoes_empilhadas(
    dados,
    grupo,
    categoria,
    valor,
    ordem_categorias,
):

    resultado = dados.copy()


    mapa_ordem = {
        categoria_nome: indice
        for indice, categoria_nome
        in enumerate(
            ordem_categorias
        )
    }


    resultado[
        "_ordem_categoria"
    ] = (
        resultado[
            categoria
        ]
        .map(
            mapa_ordem
        )
        .fillna(
            999
        )
    )


    resultado = (
        resultado
        .sort_values(
            [
                grupo,
                "_ordem_categoria",
            ]
        )
        .copy()
    )


    resultado[
        "Fim"
    ] = (
        resultado
        .groupby(
            grupo
        )[
            valor
        ]
        .cumsum()
    )


    resultado[
        "Inicio"
    ] = (
        resultado[
            "Fim"
        ]
        -
        resultado[
            valor
        ]
    )


    resultado[
        "Centro"
    ] = (
        resultado[
            "Inicio"
        ]
        +
        resultado[
            valor
        ]
        / 2
    )


    return resultado


# ============================================================
# CONSOLIDADO
# ============================================================

def calcular_consolidado(
    base,
    indicador,
    anos,
):

    peso = (
        "Matrículas EM (total) 3/4"
    )


    resultados = []


    for ano in anos:

        recorte = (
            base[
                base[
                    "Ano"
                ]
                == ano
            ]
            .copy()
        )


        recorte = (
            recorte[
                recorte[
                    indicador
                ].notna()
                &
                recorte[
                    peso
                ].notna()
                &
                (
                    recorte[
                        peso
                    ]
                    > 0
                )
            ]
            .copy()
        )


        if recorte.empty:

            continue


        resultados.append(
            {
                "Ano":
                    str(ano),

                "Categoria":
                    "Consolidado",

                "Média":
                    np.average(
                        recorte[
                            indicador
                        ],
                        weights=recorte[
                            peso
                        ],
                    ),

                "N escolas":
                    recorte[
                        "Cód. INEP"
                    ]
                    .nunique(),

                "Matrículas":
                    recorte[
                        peso
                    ]
                    .sum(),
            }
        )


    return pd.DataFrame(
        resultados
    )


# ============================================================
# DUAS DIMENSÕES
# ============================================================

def criar_duas_dimensoes(
    base,
    variavel_1,
    variavel_2,
    incluir_integral_agregado=False,
):

    temp_1 = criar_variavel_eixo(
        base,
        variavel_1,
    )


    temp_2 = criar_variavel_eixo(
        base,
        variavel_2,
    )


    resultado = base.copy()


    resultado[
        "Categoria_1"
    ] = temp_1[
        "Categoria"
    ].values


    resultado[
        "Categoria_2"
    ] = temp_2[
        "Categoria"
    ].values


    if (
        incluir_integral_agregado
        and
        variavel_1
        in VARIAVEIS_TIPO_ESCOLA
    ):

        agregado = (
            resultado[
                resultado[
                    "Categoria_1"
                ].isin(
                    [
                        "Mista",
                        "100% Integral",
                    ]
                )
            ]
            .copy()
        )


        agregado[
            "Categoria_1"
        ] = (
            CATEGORIA_INTEGRAL_AGREGADA
        )


        resultado = pd.concat(
            [
                resultado,
                agregado,
            ],
            ignore_index=True,
        )


    if (
        incluir_integral_agregado
        and
        variavel_2
        in VARIAVEIS_TIPO_ESCOLA
    ):

        agregado = (
            resultado[
                resultado[
                    "Categoria_2"
                ].isin(
                    [
                        "Mista",
                        "100% Integral",
                    ]
                )
            ]
            .copy()
        )


        agregado[
            "Categoria_2"
        ] = (
            CATEGORIA_INTEGRAL_AGREGADA
        )


        resultado = pd.concat(
            [
                resultado,
                agregado,
            ],
            ignore_index=True,
        )


    return resultado


def media_ponderada_duas_dimensoes(
    base,
    indicador,
    anos,
    variavel_1,
    variavel_2,
    incluir_integral_agregado=False,
):

    peso = (
        "Matrículas EM (total) 3/4"
    )


    base_dupla = criar_duas_dimensoes(
        base=base,
        variavel_1=variavel_1,
        variavel_2=variavel_2,
        incluir_integral_agregado=(
            incluir_integral_agregado
        ),
    )


    base_dupla = (
        base_dupla[
            base_dupla[
                "Ano"
            ].isin(
                anos
            )
            &
            base_dupla[
                indicador
            ].notna()
            &
            base_dupla[
                peso
            ].notna()
            &
            (
                base_dupla[
                    peso
                ]
                > 0
            )
        ]
        .copy()
    )


    if base_dupla.empty:

        return pd.DataFrame(
            columns=[
                "Ano",
                "Categoria_1",
                "Categoria_2",
                "Média",
                "N escolas",
                "Matrículas",
            ]
        )


    base_dupla[
        "_produto"
    ] = (
        base_dupla[
            indicador
        ]
        *
        base_dupla[
            peso
        ]
    )


    resultado = (
        base_dupla
        .groupby(
            [
                "Ano",
                "Categoria_1",
                "Categoria_2",
            ],
            as_index=False,
        )
        .agg(

            soma_ponderada=(
                "_produto",
                "sum",
            ),

            Matrículas=(
                peso,
                "sum",
            ),

            **{
                "N escolas": (
                    "Cód. INEP",
                    "nunique",
                )
            },
        )
    )


    resultado[
        "Média"
    ] = (
        resultado[
            "soma_ponderada"
        ]
        /
        resultado[
            "Matrículas"
        ]
    )


    resultado[
        "Ano"
    ] = (
        resultado[
            "Ano"
        ]
        .astype(int)
        .astype(str)
    )


    return resultado[
        [
            "Ano",
            "Categoria_1",
            "Categoria_2",
            "Média",
            "N escolas",
            "Matrículas",
        ]
    ]


# ============================================================
# LIMPAR FILTROS
# ============================================================

def limpar_todos_os_filtros():
    """Restaura explicitamente todos os filtros globais da sidebar.

    Atribuir os valores padrão diretamente ao session_state é mais robusto
    do que apenas remover as chaves, porque widgets já renderizados podem
    manter o valor anterior no estado do frontend.
    """

    padroes = {
        "filtro_same_schools": False,
        "filtro_proped": [],
        "filtro_ept": [],
    }


    for nome in EIXOS_DISPONIVEIS.keys():

        padroes[
            f"filtro_{nome}"
        ] = []


    for ano in ANOS_PAINEL:

        padroes[
            f"filtro_ideb_{ano}"
        ] = []

        padroes[
            f"filtro_considerar_ideb_{ano}"
        ] = False


    # Remove chaves antigas/legadas de filtros para evitar que uma versão
    # anterior do painel reaplique um valor que já não pertence à interface.
    for chave in list(
        st.session_state.keys()
    ):

        if (
            chave.startswith("filtro_")
            and
            chave not in padroes
        ):

            st.session_state.pop(
                chave,
                None,
            )


    for chave, valor in padroes.items():

        st.session_state[
            chave
        ] = valor


# ============================================================
# MELHORES ESCOLAS — DISTRIBUIÇÕES
# ============================================================

def preparar_distribuicao_top(
    base,
    variavel,
    categorias_permitidas=None,
):

    temp = criar_variavel_eixo(
        base,
        variavel,
    )


    dados = base[
        [
            "Cód. INEP"
        ]
    ].copy()


    dados[
        "Categoria"
    ] = temp[
        "Categoria"
    ].values


    dados = (
        dados[
            dados[
                "Categoria"
            ].notna()
        ]
        .drop_duplicates(
            "Cód. INEP"
        )
    )


    if categorias_permitidas:

        dados = (
            dados[
                dados[
                    "Categoria"
                ].isin(
                    categorias_permitidas
                )
            ]
            .copy()
        )


    resumo = (
        dados
        .groupby(
            "Categoria",
            as_index=False,
        )
        .agg(
            Escolas=(
                "Cód. INEP",
                "nunique",
            )
        )
    )


    total = resumo[
        "Escolas"
    ].sum()


    resumo[
        "Percentual"
    ] = np.where(
        total > 0,
        resumo[
            "Escolas"
        ]
        / total,
        0,
    )


    return resumo


# ============================================================
# MELHORES ESCOLAS — BARRA ÚNICA 100%
# ============================================================

def grafico_barra_100_top(
    distribuicao,
    titulo,
    ordem=None,
):

    if distribuicao.empty:

        return (
            alt.Chart(
                pd.DataFrame(
                    {
                        "x": [
                            0
                        ]
                    }
                )
            )
            .mark_text(
                text="Sem dados"
            )
            .properties(
                height=130,
                title=titulo,
            )
        )


    if ordem is None:

        ordem = (
            distribuicao
            .sort_values(
                "Percentual",
                ascending=False,
            )[
                "Categoria"
            ]
            .tolist()
        )


    dados = distribuicao.copy()


    mapa_ordem = {
        cat: i
        for i, cat
        in enumerate(
            ordem
        )
    }


    dados[
        "_ordem"
    ] = (
        dados[
            "Categoria"
        ]
        .map(
            mapa_ordem
        )
        .fillna(
            999
        )
    )


    dados = (
        dados
        .sort_values(
            "_ordem"
        )
        .copy()
    )


    dados[
        "Fim"
    ] = dados[
        "Percentual"
    ].cumsum()


    dados[
        "Inicio"
    ] = (
        dados[
            "Fim"
        ]
        -
        dados[
            "Percentual"
        ]
    )


    dados[
        "Centro"
    ] = (
        dados[
            "Inicio"
        ]
        +
        dados[
            "Percentual"
        ]
        / 2
    )


    dados[
        "Barra"
    ] = ""


    barras = (
        alt.Chart(
            dados
        )
        .mark_bar(
            height=36,
        )
        .encode(

            y=alt.Y(
                "Barra:N",
                axis=None,
                title=None,
            ),

            x=alt.X(
                "Percentual:Q",
                stack="zero",
                title=None,
                axis=None,
                scale=alt.Scale(
                    domain=[
                        0,
                        1,
                    ]
                ),
            ),

            color=alt.Color(
                "Categoria:N",
                title=None,
                scale=alt.Scale(
                    domain=ordem,
                    range=PALETA_DISTRIBUICOES[
                        :len(
                            ordem
                        )
                    ],
                ),
                legend=alt.Legend(
                    orient="bottom",
                    direction="horizontal",
                    columns=3,
                    labelFontSize=10.5,
                    symbolSize=80,
                    title=None,
                ),
            ),

            order=alt.Order(
                "_ordem:Q"
            ),

            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title="Categoria",
                ),

                alt.Tooltip(
                    "Escolas:Q",
                    title="Escolas",
                    format="d",
                ),

                alt.Tooltip(
                    "Percentual:Q",
                    title="Percentual",
                    format=".1%",
                ),
            ],
        )
    )


    # Não mostra rótulos muito pequenos.
    dados_texto = (
        dados[
            dados[
                "Percentual"
            ]
            >= 0.05
        ]
        .copy()
    )


    textos = (
        alt.Chart(
            dados_texto
        )
        .mark_text(
            baseline="middle",
            align="center",
            fontSize=12,
        )
        .encode(

            y=alt.Y(
                "Barra:N",
                axis=None,
            ),

            x=alt.X(
                "Centro:Q",
                scale=alt.Scale(
                    domain=[
                        0,
                        1,
                    ]
                ),
            ),

            text=alt.Text(
                "Percentual:Q",
                format=".0%",
            ),
        )
    )


    return (
        barras
        +
        textos
    ).properties(
        height=125,
        title=alt.TitleParams(
            text=titulo,
            anchor="middle",
            fontSize=14,
            fontWeight="bold",
        ),
    )


# ============================================================
# DISTRIBUIÇÕES — BOXPLOTS
# ============================================================

def _rotulo_combinacao_boxplot(
    categoria_1,
    categoria_2=None,
):

    categoria_1 = str(
        categoria_1
    )


    if (
        categoria_2 is None
        or
        str(
            categoria_2
        ).strip()
        == ""
    ):

        return categoria_1


    return (
        f"{categoria_1} · "
        f"{str(categoria_2)}"
    )


def _ordenar_combinacoes_boxplot(
    dados,
    variavel_1,
    variavel_2=None,
):

    if dados.empty:

        return []


    ordem_1 = ordenar_dimensao(
        dados[
            "Categoria_1"
        ]
        .dropna()
        .astype(str)
        .unique(),
        variavel_1,
    )


    mapa_1 = {
        valor: indice
        for indice, valor
        in enumerate(
            ordem_1
        )
    }


    pares = (
        dados[
            [
                "Categoria_1",
                "Categoria_2",
                "Categoria",
            ]
        ]
        .drop_duplicates()
        .copy()
    )


    if variavel_2 is None:

        pares[
            "_ordem_1"
        ] = (
            pares[
                "Categoria_1"
            ]
            .map(
                mapa_1
            )
            .fillna(
                999
            )
        )


        return (
            pares
            .sort_values(
                [
                    "_ordem_1",
                    "Categoria",
                ]
            )[
                "Categoria"
            ]
            .astype(str)
            .tolist()
        )


    ordem_2 = ordenar_dimensao(
        dados[
            "Categoria_2"
        ]
        .dropna()
        .astype(str)
        .unique(),
        variavel_2,
    )


    mapa_2 = {
        valor: indice
        for indice, valor
        in enumerate(
            ordem_2
        )
    }


    pares[
        "_ordem_1"
    ] = (
        pares[
            "Categoria_1"
        ]
        .map(
            mapa_1
        )
        .fillna(
            999
        )
    )


    pares[
        "_ordem_2"
    ] = (
        pares[
            "Categoria_2"
        ]
        .map(
            mapa_2
        )
        .fillna(
            999
        )
    )


    return (
        pares
        .sort_values(
            [
                "_ordem_1",
                "_ordem_2",
                "Categoria",
            ]
        )[
            "Categoria"
        ]
        .astype(str)
        .tolist()
    )


def _categorizar_base_boxplot(
    base,
    variavel_1,
    variavel_2=None,
    incluir_integral_agregado=False,
):

    if base.empty:

        return pd.DataFrame(
            columns=[
                *base.columns,
                "Categoria_1",
                "Categoria_2",
                "Categoria",
            ]
        )


    if variavel_2 is None:

        temp = criar_variavel_eixo(
            base,
            variavel_1,
        )


        resultado = base.copy()


        resultado[
            "Categoria_1"
        ] = temp[
            "Categoria"
        ].values


        resultado[
            "Categoria_2"
        ] = ""


        if (
            incluir_integral_agregado
            and
            variavel_1
            in VARIAVEIS_TIPO_ESCOLA
        ):

            agregado = (
                resultado[
                    resultado[
                        "Categoria_1"
                    ].isin(
                        [
                            "Mista",
                            "100% Integral",
                        ]
                    )
                ]
                .copy()
            )


            agregado[
                "Categoria_1"
            ] = CATEGORIA_INTEGRAL_AGREGADA


            resultado = pd.concat(
                [
                    resultado,
                    agregado,
                ],
                ignore_index=True,
            )


    else:

        resultado = criar_duas_dimensoes(
            base=base,
            variavel_1=variavel_1,
            variavel_2=variavel_2,
            incluir_integral_agregado=(
                incluir_integral_agregado
            ),
        )


    resultado = (
        resultado[
            resultado[
                "Categoria_1"
            ].notna()
        ]
        .copy()
    )


    resultado[
        "Categoria_1"
    ] = (
        resultado[
            "Categoria_1"
        ]
        .astype(str)
    )


    if variavel_2 is not None:

        resultado = (
            resultado[
                resultado[
                    "Categoria_2"
                ].notna()
            ]
            .copy()
        )


        resultado[
            "Categoria_2"
        ] = (
            resultado[
                "Categoria_2"
            ]
            .astype(str)
        )


    resultado[
        "Categoria"
    ] = resultado.apply(
        lambda linha:
            _rotulo_combinacao_boxplot(
                linha[
                    "Categoria_1"
                ],
                (
                    linha[
                        "Categoria_2"
                    ]
                    if variavel_2
                    is not None
                    else None
                ),
            ),
        axis=1,
    )


    return resultado


def preparar_dados_boxplot(
    base,
    indicador,
    variavel_1,
    anos,
    variavel_2=None,
    incluir_integral_agregado=False,
):

    anos = sorted(
        list(
            dict.fromkeys(
                int(
                    ano
                )
                for ano in anos
            )
        )
    )


    recorte = (
        base[
            base[
                "Ano"
            ].isin(
                anos
            )
        ]
        .copy()
    )


    if recorte.empty:

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Ano",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Valor",
                ]
            ),
            [],
        )


    recorte[
        indicador
    ] = pd.to_numeric(
        recorte[
            indicador
        ],
        errors="coerce",
    )


    recorte = (
        recorte[
            recorte[
                indicador
            ].notna()
        ]
        .drop_duplicates(
            subset=[
                "Cód. INEP",
                "Ano",
            ],
            keep="first",
        )
        .copy()
    )


    if recorte.empty:

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Ano",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Valor",
                ]
            ),
            [],
        )


    categorizado = _categorizar_base_boxplot(
        base=recorte,
        variavel_1=variavel_1,
        variavel_2=variavel_2,
        incluir_integral_agregado=(
            incluir_integral_agregado
        ),
    )


    dados_categoria = categorizado[
        [
            "Cód. INEP",
            "Ano",
            "Categoria_1",
            "Categoria_2",
            "Categoria",
            indicador,
        ]
    ].copy()


    dados_categoria = dados_categoria.rename(
        columns={
            indicador: "Valor"
        }
    )


    ordem_categorias = _ordenar_combinacoes_boxplot(
        dados=dados_categoria,
        variavel_1=variavel_1,
        variavel_2=variavel_2,
    )


    # O Consolidado usa a base original, sem as duplicações criadas
    # para a categoria Integral (Mista + 100%).
    consolidado = recorte[
        [
            "Cód. INEP",
            "Ano",
            indicador,
        ]
    ].copy()


    consolidado = consolidado.rename(
        columns={
            indicador: "Valor"
        }
    )


    consolidado[
        "Categoria_1"
    ] = "Consolidado"


    consolidado[
        "Categoria_2"
    ] = ""


    consolidado[
        "Categoria"
    ] = "Consolidado"


    dados = pd.concat(
        [
            dados_categoria[
                [
                    "Cód. INEP",
                    "Ano",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Valor",
                ]
            ],
            consolidado[
                [
                    "Cód. INEP",
                    "Ano",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Valor",
                ]
            ],
        ],
        ignore_index=True,
    )


    dados[
        "Ano"
    ] = (
        dados[
            "Ano"
        ]
        .astype(int)
        .astype(str)
    )


    ordem = (
        ordem_categorias
        +
        [
            "Consolidado"
        ]
    )


    return (
        dados,
        ordem,
    )


def preparar_dados_delta_boxplot(
    base,
    indicador,
    variavel_1,
    ano_inicial,
    ano_final,
    variavel_2=None,
    incluir_integral_agregado=False,
):

    anos_delta = [
        int(
            ano_inicial
        ),
        int(
            ano_final
        ),
    ]


    recorte = (
        base[
            base[
                "Ano"
            ].isin(
                anos_delta
            )
        ]
        .copy()
    )


    if recorte.empty:

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Delta",
                ]
            ),
            [],
        )


    recorte[
        indicador
    ] = pd.to_numeric(
        recorte[
            indicador
        ],
        errors="coerce",
    )


    recorte = (
        recorte[
            recorte[
                indicador
            ].notna()
        ]
        .drop_duplicates(
            subset=[
                "Cód. INEP",
                "Ano",
            ],
            keep="first",
        )
        .copy()
    )


    pivot = (
        recorte[
            [
                "Cód. INEP",
                "Ano",
                indicador,
            ]
        ]
        .pivot(
            index="Cód. INEP",
            columns="Ano",
            values=indicador,
        )
    )


    if (
        ano_inicial
        not in pivot.columns
        or
        ano_final
        not in pivot.columns
    ):

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Delta",
                ]
            ),
            [],
        )


    pivot = (
        pivot[
            [
                ano_inicial,
                ano_final,
            ]
        ]
        .dropna()
        .reset_index()
    )


    if pivot.empty:

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Delta",
                ]
            ),
            [],
        )


    pivot[
        "Delta"
    ] = (
        pivot[
            ano_final
        ]
        -
        pivot[
            ano_inicial
        ]
    )


    deltas_escola = pivot[
        [
            "Cód. INEP",
            "Delta",
        ]
    ].copy()


    # As dimensões são definidas pela classificação da escola no ano
    # mais recente da comparação, seguindo a lógica do painel para a
    # composição dos grupos na comparação entre edições.
    base_final = (
        recorte[
            recorte[
                "Ano"
            ]
            == ano_final
        ]
        .merge(
            deltas_escola,
            on="Cód. INEP",
            how="inner",
            validate="one_to_one",
        )
    )


    categorizado = _categorizar_base_boxplot(
        base=base_final,
        variavel_1=variavel_1,
        variavel_2=variavel_2,
        incluir_integral_agregado=(
            incluir_integral_agregado
        ),
    )


    dados_categoria = categorizado[
        [
            "Cód. INEP",
            "Categoria_1",
            "Categoria_2",
            "Categoria",
            "Delta",
        ]
    ].copy()


    ordem_categorias = _ordenar_combinacoes_boxplot(
        dados=dados_categoria,
        variavel_1=variavel_1,
        variavel_2=variavel_2,
    )


    consolidado = deltas_escola.copy()


    consolidado[
        "Categoria_1"
    ] = "Consolidado"


    consolidado[
        "Categoria_2"
    ] = ""


    consolidado[
        "Categoria"
    ] = "Consolidado"


    dados = pd.concat(
        [
            dados_categoria,
            consolidado[
                [
                    "Cód. INEP",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Delta",
                ]
            ],
        ],
        ignore_index=True,
    )


    ordem = (
        ordem_categorias
        +
        [
            "Consolidado"
        ]
    )


    return (
        dados,
        ordem,
    )


def calcular_dominio_y_compartilhado(
    serie,
    indicador,
    delta=False,
):

    valores = (
        pd.to_numeric(
            serie,
            errors="coerce",
        )
        .replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )
        .dropna()
    )


    if valores.empty:

        return None


    minimo = float(
        valores.min()
    )

    maximo = float(
        valores.max()
    )


    # Para valores absolutos, os dois gráficos partem de zero.
    # Para deltas, zero também precisa pertencer à escala, mas
    # preservamos valores negativos quando existirem.
    if delta:

        limite_inferior = min(
            minimo,
            0.0,
        )

        limite_superior = max(
            maximo,
            0.0,
        )

    else:

        limite_inferior = 0.0

        limite_superior = max(
            maximo,
            0.0,
        )


    amplitude = (
        limite_superior
        - limite_inferior
    )


    if amplitude <= 0:

        amplitude = max(
            abs(
                limite_superior
            ),
            1.0,
        )


    margem = (
        amplitude
        * 0.06
    )


    if limite_inferior < 0:

        limite_inferior -= margem


    if limite_superior > 0:

        limite_superior += margem


    # Arredonda os limites para que os dois gráficos tenham uma
    # escala limpa e rigorosamente idêntica.
    passo = (
        0.01
        if indicador == "Rendimento"
        else 0.1
    )


    limite_inferior = (
        np.floor(
            limite_inferior
            / passo
        )
        * passo
    )

    limite_superior = (
        np.ceil(
            limite_superior
            / passo
        )
        * passo
    )


    # Rendimento absoluto é uma proporção. Quando os dados estão
    # dentro do intervalo esperado, usa 0% a 100%, o que também
    # deixa a leitura dos dois gráficos mais intuitiva.
    if (
        not delta
        and indicador == "Rendimento"
        and minimo >= 0
        and maximo <= 1
    ):

        limite_inferior = 0.0
        limite_superior = 1.0


    if limite_superior <= limite_inferior:

        limite_superior = (
            limite_inferior
            + passo
        )


    return [
        float(
            limite_inferior
        ),
        float(
            limite_superior
        ),
    ]


def criar_grafico_boxplots(
    dados,
    ordem,
    indicador,
    variavel_1,
    anos,
    variavel_2=None,
    rotulos_multilinha=False,
    dominio_y=None,
    altura=430,
):

    if dados.empty:

        return (
            alt.Chart(
                pd.DataFrame(
                    {
                        "Mensagem": [
                            "Sem dados"
                        ]
                    }
                )
            )
            .mark_text(
                fontSize=15,
            )
            .encode(
                text="Mensagem:N"
            )
            .properties(
                height=360,
            )
        )


    anos_str = [
        str(
            ano
        )
        for ano in sorted(
            anos
        )
    ]


    medias = (
        dados
        .groupby(
            [
                "Categoria",
                "Ano",
            ],
            as_index=False,
        )
        .agg(
            Média=(
                "Valor",
                "mean",
            ),
            **{
                "N escolas": (
                    "Cód. INEP",
                    "nunique",
                )
            },
        )
    )


    if indicador == "Rendimento":

        formato_eixo = ".0%"
        formato_tooltip = ".1%"

        medias[
            "Rótulo média"
        ] = medias[
            "Média"
        ].apply(
            lambda valor: (
                f"{float(valor) * 100:.1f}%"
                .replace(
                    ".",
                    ",",
                )
            )
        )

    else:

        formato_eixo = ".1f"
        formato_tooltip = ".1f"

        medias[
            "Rótulo média"
        ] = medias[
            "Média"
        ].apply(
            lambda valor: (
                f"{float(valor):.1f}"
                .replace(
                    ".",
                    ",",
                )
            )
        )


    # Na aba Distribuições o primeiro boxplot representa apenas o
    # ano mais recente selecionado. O N passa a fazer parte do eixo X,
    # deixando o rótulo sobre a caixa reservado exclusivamente à média.
    ano_referencia = (
        anos_str[-1]
        if anos_str
        else None
    )


    contagens_eixo = (
        medias[
            medias[
                "Ano"
            ]
            == ano_referencia
        ]
        .set_index(
            "Categoria"
        )[
            "N escolas"
        ]
        .to_dict()
        if ano_referencia is not None
        else {}
    )


    mapa_rotulos_eixo = {
        str(categoria): (
            f"{categoria}\nN = {int(contagens_eixo.get(categoria, 0))}"
        )
        for categoria
        in ordem
    }


    dados_plot = dados.copy()

    dados_plot[
        "Categoria eixo"
    ] = (
        dados_plot[
            "Categoria"
        ]
        .astype(str)
        .map(
            mapa_rotulos_eixo
        )
        .fillna(
            dados_plot[
                "Categoria"
            ].astype(str)
        )
    )


    medias[
        "Categoria eixo"
    ] = (
        medias[
            "Categoria"
        ]
        .astype(str)
        .map(
            mapa_rotulos_eixo
        )
        .fillna(
            medias[
                "Categoria"
            ].astype(str)
        )
    )


    ordem_eixo = [
        mapa_rotulos_eixo.get(
            str(categoria),
            str(categoria),
        )
        for categoria
        in ordem
    ]


    titulo_dimensao = rotulo_dimensao(
        variavel_1
    )


    if variavel_2 is not None:

        titulo_dimensao = (
            f"{titulo_dimensao} × "
            f"{rotulo_dimensao(variavel_2)}"
        )


    eixo_x = alt.X(
        "Categoria eixo:N",
        sort=ordem_eixo,
        title=titulo_dimensao,
        axis=alt.Axis(
            labelAngle=0,
            labelFontSize=11.5,
            titleFontSize=12.5,
            labelLimit=360,
            labelPadding=10,
            labelOverlap=False,
            labelExpr="split(datum.label, '\\n')",
        ),
    )


    escala_y = (
        alt.Scale(
            domain=dominio_y,
            zero=False,
            nice=False,
        )
        if dominio_y is not None
        else alt.Scale(
            zero=False,
        )
    )


    eixo_y = alt.Y(
        "Valor:Q",
        title=indicador,
        scale=escala_y,
        axis=alt.Axis(
            format=formato_eixo,
            labelFontSize=11.5,
            titleFontSize=12.5,
            tickCount=6,
        ),
    )


    deslocamento_ano = alt.XOffset(
        "Ano:N",
        sort=anos_str,
    )


    tamanho_caixa = max(
        20,
        46
        -
        5
        * max(
            0,
            len(
                anos_str
            )
            - 1,
        ),
    )


    caixas = (
        alt.Chart(
            dados_plot
        )
        .mark_boxplot(
            extent=1.5,
            size=tamanho_caixa,
            opacity=0.48,
            color="#78AEDA",
        )
        .encode(
            x=eixo_x,
            xOffset=deslocamento_ano,
            y=eixo_y,
            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title="Categoria",
                ),
                alt.Tooltip(
                    "Ano:N",
                    title="Ano",
                ),
            ],
        )
    )


    pontos_media = (
        alt.Chart(
            medias
        )
        .mark_point(
            shape="diamond",
            filled=True,
            size=85,
            color="#2F313C",
            stroke="white",
            strokeWidth=0.8,
        )
        .encode(
            x=alt.X(
                "Categoria eixo:N",
                sort=ordem_eixo,
            ),
            xOffset=alt.XOffset(
                "Ano:N",
                sort=anos_str,
            ),
            y=alt.Y(
                "Média:Q",
                scale=escala_y,
            ),
            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title="Categoria",
                ),
                alt.Tooltip(
                    "Ano:N",
                    title="Ano",
                ),
                alt.Tooltip(
                    "Média:Q",
                    title="Média",
                    format=formato_tooltip,
                ),
                alt.Tooltip(
                    "N escolas:Q",
                    title="N escolas",
                    format="d",
                ),
            ],
        )
    )


    rotulos_media = (
        alt.Chart(
            medias
        )
        .mark_text(
            dx=13,
            dy=-2,
            align="left",
            baseline="middle",
            fontSize=14,
            fontWeight="bold",
            color="#2F313C",
        )
        .encode(
            x=alt.X(
                "Categoria eixo:N",
                sort=ordem_eixo,
            ),
            xOffset=alt.XOffset(
                "Ano:N",
                sort=anos_str,
            ),
            y=alt.Y(
                "Média:Q",
                scale=escala_y,
            ),
            text=alt.Text(
                "Rótulo média:N"
            ),
        )
    )


    return (
        caixas
        +
        pontos_media
        +
        rotulos_media
    ).properties(
        height=altura,
        title=alt.TitleParams(
            text=(
                f"Distribuição de {indicador} por "
                f"{titulo_dimensao}"
            ),
            subtitle=(
                "O boxplot corresponde ao ano mais recente selecionado. "
                "O losango e o rótulo indicam a média; o N aparece no eixo X."
            ),
            anchor="middle",
            fontSize=17,
            subtitleFontSize=11,
            subtitlePadding=8,
        ),
    )

def criar_grafico_delta_boxplots(
    dados,
    ordem,
    indicador,
    variavel_1,
    ano_inicial,
    ano_final,
    variavel_2=None,
    rotulos_multilinha=False,
    dominio_y=None,
    altura=430,
    cores_por_categoria=False,
):

    if dados.empty:

        return (
            alt.Chart(
                pd.DataFrame(
                    {
                        "Mensagem": [
                            "Sem dados"
                        ]
                    }
                )
            )
            .mark_text(
                fontSize=15,
            )
            .encode(
                text="Mensagem:N"
            )
            .properties(
                height=360,
            )
        )


    medias = (
        dados
        .groupby(
            "Categoria",
            as_index=False,
        )
        .agg(
            Média=(
                "Delta",
                "mean",
            ),
            **{
                "N escolas": (
                    "Cód. INEP",
                    "nunique",
                )
            },
        )
    )


    if indicador == "Rendimento":

        formato_eixo = "+.0%"
        formato_tooltip = "+.1%"

        medias[
            "Rótulo média"
        ] = medias[
            "Média"
        ].apply(
            lambda valor: (
                f"{float(valor) * 100:+.1f} p.p."
                .replace(
                    ".",
                    ",",
                )
            )
        )

    else:

        formato_eixo = "+.1f"
        formato_tooltip = "+.1f"

        medias[
            "Rótulo média"
        ] = medias[
            "Média"
        ].apply(
            lambda valor: (
                f"{float(valor):+.1f}"
                .replace(
                    ".",
                    ",",
                )
            )
        )


    contagens_eixo = (
        medias
        .set_index(
            "Categoria"
        )[
            "N escolas"
        ]
        .to_dict()
    )


    mapa_rotulos_eixo = {
        str(categoria): (
            f"{categoria}\nN = {int(contagens_eixo.get(categoria, 0))}"
        )
        for categoria
        in ordem
    }


    dados_plot = dados.copy()

    dados_plot[
        "Categoria eixo"
    ] = (
        dados_plot[
            "Categoria"
        ]
        .astype(str)
        .map(
            mapa_rotulos_eixo
        )
        .fillna(
            dados_plot[
                "Categoria"
            ].astype(str)
        )
    )


    medias[
        "Categoria eixo"
    ] = (
        medias[
            "Categoria"
        ]
        .astype(str)
        .map(
            mapa_rotulos_eixo
        )
        .fillna(
            medias[
                "Categoria"
            ].astype(str)
        )
    )


    ordem_eixo = [
        mapa_rotulos_eixo.get(
            str(categoria),
            str(categoria),
        )
        for categoria
        in ordem
    ]


    titulo_dimensao = rotulo_dimensao(
        variavel_1
    )


    if variavel_2 is not None:

        titulo_dimensao = (
            f"{titulo_dimensao} × "
            f"{rotulo_dimensao(variavel_2)}"
        )


    eixo_x = alt.X(
        "Categoria eixo:N",
        sort=ordem_eixo,
        title=titulo_dimensao,
        axis=alt.Axis(
            labelAngle=0,
            labelFontSize=11.5,
            titleFontSize=12.5,
            labelLimit=360,
            labelPadding=10,
            labelOverlap=False,
            labelExpr="split(datum.label, '\\n')",
        ),
    )


    escala_y = (
        alt.Scale(
            domain=dominio_y,
            zero=False,
            nice=False,
        )
        if dominio_y is not None
        else alt.Scale(
            zero=False,
        )
    )


    eixo_y = alt.Y(
        "Delta:Q",
        title=(
            f"Delta de {indicador}"
        ),
        scale=escala_y,
        axis=alt.Axis(
            format=formato_eixo,
            labelFontSize=11.5,
            titleFontSize=12.5,
            tickCount=6,
        ),
    )


    linha_zero = (
        alt.Chart(
            pd.DataFrame(
                {
                    "Zero": [
                        0
                    ]
                }
            )
        )
        .mark_rule(
            color="#9AA0A6",
            strokeDash=[
                4,
                4,
            ],
            strokeWidth=1,
        )
        .encode(
            y=alt.Y(
                "Zero:Q",
                scale=escala_y,
            )
        )
    )


    caixas = (
        alt.Chart(
            dados_plot
        )
        .mark_boxplot(
            extent=1.5,
            size=44,
            opacity=0.48,
            color="#78AEDA",
        )
        .encode(
            x=eixo_x,
            y=eixo_y,
            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title="Categoria",
                ),
            ],
        )
    )


    pontos_media = (
        alt.Chart(
            medias
        )
        .mark_point(
            shape="diamond",
            filled=True,
            size=95,
            color="#2F313C",
            stroke="white",
            strokeWidth=0.8,
        )
        .encode(
            x=alt.X(
                "Categoria eixo:N",
                sort=ordem_eixo,
            ),
            y=alt.Y(
                "Média:Q",
                scale=escala_y,
            ),
            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title="Categoria",
                ),
                alt.Tooltip(
                    "Média:Q",
                    title="Média do delta",
                    format=formato_tooltip,
                ),
                alt.Tooltip(
                    "N escolas:Q",
                    title="N escolas",
                    format="d",
                ),
            ],
        )
    )


    rotulos_media = (
        alt.Chart(
            medias
        )
        .mark_text(
            dx=13,
            dy=-2,
            align="left",
            baseline="middle",
            fontSize=14,
            fontWeight="bold",
            color="#2F313C",
        )
        .encode(
            x=alt.X(
                "Categoria eixo:N",
                sort=ordem_eixo,
            ),
            y=alt.Y(
                "Média:Q",
                scale=escala_y,
            ),
            text=alt.Text(
                "Rótulo média:N"
            ),
        )
    )


    return (
        linha_zero
        +
        caixas
        +
        pontos_media
        +
        rotulos_media
    ).properties(
        height=altura,
        title=alt.TitleParams(
            text=(
                f"Distribuição dos deltas de {indicador} por "
                f"{titulo_dimensao} — {ano_final} − {ano_inicial}"
            ),
            subtitle=(
                "Cada delta é calculado por escola. O losango e o rótulo indicam "
                "a média; o N de escolas com delta válido aparece no eixo X."
            ),
            anchor="middle",
            fontSize=17,
            subtitleFontSize=11,
            subtitlePadding=8,
        ),
    )

def criar_grafico_barras_medias_agregado(
    dados,
    ordem,
    indicador,
    variavel,
    anos,
    rotulos_multilinha=True,
    dominio_y=None,
    altura=430,
):

    if dados.empty:

        return (
            alt.Chart(
                pd.DataFrame(
                    {
                        "Mensagem": [
                            "Sem dados"
                        ]
                    }
                )
            )
            .mark_text(
                fontSize=15,
            )
            .encode(
                text="Mensagem:N"
            )
            .properties(
                height=260,
            )
        )


    anos_str = [
        str(
            ano
        )
        for ano in sorted(
            anos
        )
    ]


    medias = (
        dados
        .groupby(
            [
                "Categoria",
                "Ano",
            ],
            as_index=False,
        )
        .agg(
            Média=(
                "Valor",
                "mean",
            ),
            **{
                "N escolas": (
                    "Cód. INEP",
                    "nunique",
                )
            },
        )
    )


    if indicador == "Rendimento":

        formato_eixo = ".0%"
        formato_tooltip = ".1%"

        medias[
            "Rótulo média"
        ] = medias[
            "Média"
        ].apply(
            lambda valor: (
                f"{float(valor) * 100:.1f}%"
                .replace(
                    ".",
                    ",",
                )
            )
        )

    else:

        formato_eixo = ".1f"
        formato_tooltip = ".1f"

        medias[
            "Rótulo média"
        ] = medias[
            "Média"
        ].apply(
            lambda valor: (
                f"{float(valor):.1f}"
                .replace(
                    ".",
                    ",",
                )
            )
        )


    ano_referencia = (
        anos_str[-1]
        if anos_str
        else None
    )


    contagens_eixo = (
        medias[
            medias[
                "Ano"
            ]
            == ano_referencia
        ]
        .set_index(
            "Categoria"
        )[
            "N escolas"
        ]
        .to_dict()
        if ano_referencia is not None
        else {}
    )


    mapa_rotulos_eixo = {
        str(categoria): (
            f"{categoria}\nN = {int(contagens_eixo.get(categoria, 0))}"
        )
        for categoria
        in ordem
    }


    medias[
        "Categoria eixo"
    ] = (
        medias[
            "Categoria"
        ]
        .astype(str)
        .map(
            mapa_rotulos_eixo
        )
        .fillna(
            medias[
                "Categoria"
            ].astype(str)
        )
    )


    ordem_eixo = [
        mapa_rotulos_eixo.get(
            str(categoria),
            str(categoria),
        )
        for categoria
        in ordem
    ]


    escala_y = (
        alt.Scale(
            domain=dominio_y,
            zero=False,
            nice=False,
        )
        if dominio_y is not None
        else alt.Scale(
            zero=True,
        )
    )


    eixo_x = alt.X(
        "Categoria eixo:N",
        sort=ordem_eixo,
        title=rotulo_dimensao(
            variavel
        ),
        axis=alt.Axis(
            labelAngle=0,
            labelFontSize=11.5,
            titleFontSize=12.5,
            labelLimit=360,
            labelPadding=10,
            labelOverlap=False,
            labelExpr="split(datum.label, '\\n')",
        ),
    )


    eixo_y = alt.Y(
        "Média:Q",
        title=f"Média de {indicador}",
        scale=escala_y,
        axis=alt.Axis(
            format=formato_eixo,
            labelFontSize=11.5,
            titleFontSize=12.5,
            tickCount=6,
        ),
    )


    barras = (
        alt.Chart(
            medias
        )
        .mark_bar(
            size=48,
            cornerRadiusTopLeft=2,
            cornerRadiusTopRight=2,
            color="#5B8DB8",
            opacity=0.88,
        )
        .encode(
            x=eixo_x,
            y=eixo_y,
            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title="Categorias",
                ),
                alt.Tooltip(
                    "Ano:N",
                    title="Ano",
                ),
                alt.Tooltip(
                    "Média:Q",
                    title="Média",
                    format=formato_tooltip,
                ),
                alt.Tooltip(
                    "N escolas:Q",
                    title="N escolas",
                    format="d",
                ),
            ],
        )
    )


    rotulos = (
        alt.Chart(
            medias
        )
        .mark_text(
            dy=-9,
            fontSize=11,
            fontWeight="bold",
            color="#2F313C",
        )
        .encode(
            x=alt.X(
                "Categoria eixo:N",
                sort=ordem_eixo,
            ),
            y=alt.Y(
                "Média:Q",
                scale=escala_y,
            ),
            text=alt.Text(
                "Rótulo média:N"
            ),
        )
    )


    return (
        barras
        +
        rotulos
    ).properties(
        height=altura,
        title=alt.TitleParams(
            text=(
                f"Médias de {indicador} — categorias agregadas de "
                f"{rotulo_dimensao(variavel)}"
            ),
            subtitle=(
                "As barras representam as mesmas médias destacadas no boxplot."
            ),
            anchor="middle",
            fontSize=15,
            subtitleFontSize=10.5,
            subtitlePadding=7,
        ),
    )

def criar_grafico_barras_medias_delta_agregado(
    dados,
    ordem,
    indicador,
    variavel,
    ano_inicial,
    ano_final,
    rotulos_multilinha=True,
    dominio_y=None,
    altura=430,
):

    if dados.empty:

        return (
            alt.Chart(
                pd.DataFrame(
                    {
                        "Mensagem": [
                            "Sem dados"
                        ]
                    }
                )
            )
            .mark_text(
                fontSize=15,
            )
            .encode(
                text="Mensagem:N"
            )
            .properties(
                height=260,
            )
        )


    medias = (
        dados
        .groupby(
            "Categoria",
            as_index=False,
        )
        .agg(
            Média=(
                "Delta",
                "mean",
            ),
            **{
                "N escolas": (
                    "Cód. INEP",
                    "nunique",
                )
            },
        )
    )


    if indicador == "Rendimento":

        formato_eixo = "+.0%"
        formato_tooltip = "+.1%"

        medias[
            "Rótulo média"
        ] = medias[
            "Média"
        ].apply(
            lambda valor: (
                f"{float(valor) * 100:+.1f} p.p."
                .replace(
                    ".",
                    ",",
                )
            )
        )

    else:

        formato_eixo = "+.1f"
        formato_tooltip = "+.1f"

        medias[
            "Rótulo média"
        ] = medias[
            "Média"
        ].apply(
            lambda valor: (
                f"{float(valor):+.1f}"
                .replace(
                    ".",
                    ",",
                )
            )
        )


    contagens_eixo = (
        medias
        .set_index(
            "Categoria"
        )[
            "N escolas"
        ]
        .to_dict()
    )


    mapa_rotulos_eixo = {
        str(categoria): (
            f"{categoria}\nN = {int(contagens_eixo.get(categoria, 0))}"
        )
        for categoria
        in ordem
    }


    medias[
        "Categoria eixo"
    ] = (
        medias[
            "Categoria"
        ]
        .astype(str)
        .map(
            mapa_rotulos_eixo
        )
        .fillna(
            medias[
                "Categoria"
            ].astype(str)
        )
    )


    ordem_eixo = [
        mapa_rotulos_eixo.get(
            str(categoria),
            str(categoria),
        )
        for categoria
        in ordem
    ]


    escala_y = (
        alt.Scale(
            domain=dominio_y,
            zero=False,
            nice=False,
        )
        if dominio_y is not None
        else alt.Scale(
            zero=False,
        )
    )


    eixo_x = alt.X(
        "Categoria eixo:N",
        sort=ordem_eixo,
        title=rotulo_dimensao(
            variavel
        ),
        axis=alt.Axis(
            labelAngle=0,
            labelFontSize=11.5,
            titleFontSize=12.5,
            labelLimit=360,
            labelPadding=10,
            labelOverlap=False,
            labelExpr="split(datum.label, '\\n')",
        ),
    )


    eixo_y = alt.Y(
        "Média:Q",
        title=f"Média do delta de {indicador}",
        scale=escala_y,
        axis=alt.Axis(
            format=formato_eixo,
            labelFontSize=11.5,
            titleFontSize=12.5,
            tickCount=6,
        ),
    )


    linha_zero = (
        alt.Chart(
            pd.DataFrame(
                {
                    "Zero": [
                        0
                    ]
                }
            )
        )
        .mark_rule(
            color="#9AA0A6",
            strokeDash=[
                4,
                4,
            ],
            strokeWidth=1,
        )
        .encode(
            y=alt.Y(
                "Zero:Q",
                scale=escala_y,
            )
        )
    )


    barras = (
        alt.Chart(
            medias
        )
        .mark_bar(
            size=48,
            cornerRadiusTopLeft=2,
            cornerRadiusTopRight=2,
            color="#5B8DB8",
            opacity=0.88,
        )
        .encode(
            x=eixo_x,
            y=eixo_y,
            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title="Categorias",
                ),
                alt.Tooltip(
                    "Média:Q",
                    title="Média do delta",
                    format=formato_tooltip,
                ),
                alt.Tooltip(
                    "N escolas:Q",
                    title="N escolas",
                    format="d",
                ),
            ],
        )
    )


    rotulos = (
        alt.Chart(
            medias
        )
        .mark_text(
            dy=-9,
            fontSize=11,
            fontWeight="bold",
            color="#2F313C",
        )
        .encode(
            x=alt.X(
                "Categoria eixo:N",
                sort=ordem_eixo,
            ),
            y=alt.Y(
                "Média:Q",
                scale=escala_y,
            ),
            text=alt.Text(
                "Rótulo média:N"
            ),
        )
    )


    return (
        linha_zero
        +
        barras
        +
        rotulos
    ).properties(
        height=altura,
        title=alt.TitleParams(
            text=(
                f"Médias dos deltas de {indicador} — categorias agregadas de "
                f"{rotulo_dimensao(variavel)} — {ano_final} − {ano_inicial}"
            ),
            subtitle=(
                "As barras representam as mesmas médias destacadas no boxplot."
            ),
            anchor="middle",
            fontSize=15,
            subtitleFontSize=10.5,
            subtitlePadding=7,
        ),
    )


# ============================================================
# DISTRIBUIÇÕES — AGREGADOS ORGANIZADOS POR ANO
# ============================================================

def _rotulo_grupo_agregado(categorias):

    categorias = [
        str(categoria)
        for categoria
        in categorias
    ]


    if not categorias:

        return "Sem categorias"


    return " + ".join(
        categorias
    )


def criar_grafico_boxplots_agregados_por_ano(
    dados,
    indicador,
    variavel,
    anos,
    categorias_grupo_1,
    categorias_grupo_2,
    dominio_y=None,
    altura=430,
):

    if dados.empty:

        return (
            alt.Chart(
                pd.DataFrame(
                    {
                        "Mensagem": [
                            "Sem dados"
                        ]
                    }
                )
            )
            .mark_text(
                fontSize=15,
            )
            .encode(
                text="Mensagem:N"
            )
            .properties(
                height=360,
            )
        )


    plot = dados.copy()


    rotulo_1 = _rotulo_grupo_agregado(
        categorias_grupo_1
    )

    rotulo_2 = _rotulo_grupo_agregado(
        categorias_grupo_2
    )


    mapa_grupos = {
        "Agregado 1": rotulo_1,
        "Agregado 2": rotulo_2,
    }


    plot[
        "Grupo"
    ] = (
        plot[
            "Categoria"
        ]
        .map(
            mapa_grupos
        )
    )


    plot = (
        plot[
            plot[
                "Grupo"
            ].notna()
        ]
        .copy()
    )


    anos_str = [
        str(ano)
        for ano
        in sorted(
            anos
        )
    ]


    ordem_grupos = [
        rotulo
        for rotulo
        in [
            rotulo_1,
            rotulo_2,
        ]
        if rotulo
        in set(
            plot[
                "Grupo"
            ].dropna()
        )
    ]


    medias = (
        plot
        .groupby(
            [
                "Ano",
                "Grupo",
            ],
            as_index=False,
        )
        .agg(
            Média=(
                "Valor",
                "mean",
            ),
            **{
                "N escolas": (
                    "Cód. INEP",
                    "nunique",
                )
            },
        )
    )


    if indicador == "Rendimento":

        formato_eixo = ".0%"
        formato_tooltip = ".1%"

        medias[
            "Rótulo média"
        ] = medias.apply(
            lambda linha: (
                f"{float(linha['Média']) * 100:.1f}%\n"
                f"N={int(linha['N escolas'])}"
            ).replace(
                ".",
                ",",
            ),
            axis=1,
        )

    else:

        formato_eixo = ".1f"
        formato_tooltip = ".1f"

        medias[
            "Rótulo média"
        ] = medias.apply(
            lambda linha: (
                f"{float(linha['Média']):.1f}\n"
                f"N={int(linha['N escolas'])}"
            ).replace(
                ".",
                ",",
            ),
            axis=1,
        )


    escala_y = (
        alt.Scale(
            domain=dominio_y,
            zero=False,
            nice=False,
        )
        if dominio_y is not None
        else alt.Scale(
            zero=False,
        )
    )


    eixo_x = alt.X(
        "Ano:N",
        sort=anos_str,
        title="Ano",
        axis=alt.Axis(
            labelAngle=0,
            labelFontSize=11.5,
            titleFontSize=12.5,
            labelPadding=8,
        ),
    )


    deslocamento_grupo = alt.XOffset(
        "Grupo:N",
        sort=ordem_grupos,
    )


    escala_grupos = alt.Scale(
        domain=ordem_grupos,
        range=CORES_GRUPOS_DISTRIBUICOES[
            :len(
                ordem_grupos
            )
        ],
    )


    cor_grupo = alt.Color(
        "Grupo:N",
        title=None,
        sort=ordem_grupos,
        scale=escala_grupos,
        legend=alt.Legend(
            orient="top",
            direction="vertical",
            columns=1,
            labelLimit=600,
            symbolSize=90,
            title=None,
        ),
    )


    caixas = (
        alt.Chart(
            plot
        )
        .mark_boxplot(
            extent=1.5,
            size=38,
            opacity=0.58,
        )
        .encode(
            x=eixo_x,
            xOffset=deslocamento_grupo,
            y=alt.Y(
                "Valor:Q",
                title=indicador,
                scale=escala_y,
                axis=alt.Axis(
                    format=formato_eixo,
                    labelFontSize=11.5,
                    titleFontSize=12.5,
                    tickCount=6,
                ),
            ),
            color=cor_grupo,
            tooltip=[
                alt.Tooltip(
                    "Ano:N",
                    title="Ano",
                ),
                alt.Tooltip(
                    "Grupo:N",
                    title="Categorias",
                ),
            ],
        )
    )


    pontos_media = (
        alt.Chart(
            medias
        )
        .mark_point(
            shape="diamond",
            filled=True,
            size=80,
            color="#2F313C",
            stroke="white",
            strokeWidth=0.8,
        )
        .encode(
            x=alt.X(
                "Ano:N",
                sort=anos_str,
            ),
            xOffset=alt.XOffset(
                "Grupo:N",
                sort=ordem_grupos,
            ),
            y=alt.Y(
                "Média:Q",
                scale=escala_y,
            ),
            tooltip=[
                alt.Tooltip(
                    "Ano:N",
                    title="Ano",
                ),
                alt.Tooltip(
                    "Grupo:N",
                    title="Categorias",
                ),
                alt.Tooltip(
                    "Média:Q",
                    title="Média",
                    format=formato_tooltip,
                ),
                alt.Tooltip(
                    "N escolas:Q",
                    title="N escolas",
                    format="d",
                ),
            ],
        )
    )


    rotulos_media = (
        alt.Chart(
            medias
        )
        .mark_text(
            dy=-18,
            fontSize=13.5,
            fontWeight="bold",
            color="#2F313C",
            lineBreak="\n",
            lineHeight=14,
        )
        .encode(
            x=alt.X(
                "Ano:N",
                sort=anos_str,
            ),
            xOffset=alt.XOffset(
                "Grupo:N",
                sort=ordem_grupos,
            ),
            y=alt.Y(
                "Média:Q",
                scale=escala_y,
            ),
            text=alt.Text(
                "Rótulo média:N"
            ),
        )
    )


    return (
        caixas
        +
        pontos_media
        +
        rotulos_media
    ).properties(
        height=altura,
        title=alt.TitleParams(
            text=(
                f"Distribuição de {indicador} — categorias agregadas de "
                f"{rotulo_dimensao(variavel)}"
            ),
            subtitle=(
                "Dentro de cada ano, a 1ª seleção aparece ao lado da 2ª seleção. "
                "O losango indica a média; o rótulo mostra a média e, na linha abaixo, o N."
            ),
            anchor="middle",
            fontSize=17,
            subtitleFontSize=11,
            subtitlePadding=8,
        ),
    )


def criar_grafico_barras_medias_agregados_por_ano(
    dados,
    indicador,
    variavel,
    anos,
    categorias_grupo_1,
    categorias_grupo_2,
    dominio_y=None,
    altura=430,
):

    if dados.empty:

        return (
            alt.Chart(
                pd.DataFrame(
                    {
                        "Mensagem": [
                            "Sem dados"
                        ]
                    }
                )
            )
            .mark_text(
                fontSize=15,
            )
            .encode(
                text="Mensagem:N"
            )
            .properties(
                height=360,
            )
        )


    plot = dados.copy()


    rotulo_1 = _rotulo_grupo_agregado(
        categorias_grupo_1
    )

    rotulo_2 = _rotulo_grupo_agregado(
        categorias_grupo_2
    )


    mapa_grupos = {
        "Agregado 1": rotulo_1,
        "Agregado 2": rotulo_2,
    }


    plot[
        "Grupo"
    ] = (
        plot[
            "Categoria"
        ]
        .map(
            mapa_grupos
        )
    )


    plot = (
        plot[
            plot[
                "Grupo"
            ].notna()
        ]
        .copy()
    )


    anos_str = [
        str(ano)
        for ano
        in sorted(
            anos
        )
    ]


    ordem_grupos = [
        rotulo
        for rotulo
        in [
            rotulo_1,
            rotulo_2,
        ]
        if rotulo
        in set(
            plot[
                "Grupo"
            ].dropna()
        )
    ]


    medias = (
        plot
        .groupby(
            [
                "Ano",
                "Grupo",
            ],
            as_index=False,
        )
        .agg(
            Média=(
                "Valor",
                "mean",
            ),
            **{
                "N escolas": (
                    "Cód. INEP",
                    "nunique",
                )
            },
        )
    )


    if indicador == "Rendimento":

        formato_eixo = ".0%"
        formato_tooltip = ".1%"

        medias[
            "Rótulo média"
        ] = medias.apply(
            lambda linha: (
                f"{float(linha['Média']) * 100:.1f}% "
                f"(N={int(linha['N escolas'])})"
            ).replace(
                ".",
                ",",
            ),
            axis=1,
        )

    else:

        formato_eixo = ".1f"
        formato_tooltip = ".1f"

        medias[
            "Rótulo média"
        ] = medias.apply(
            lambda linha: (
                f"{float(linha['Média']):.1f} "
                f"(N={int(linha['N escolas'])})"
            ).replace(
                ".",
                ",",
            ),
            axis=1,
        )


    escala_y = (
        alt.Scale(
            domain=dominio_y,
            zero=False,
            nice=False,
        )
        if dominio_y is not None
        else alt.Scale(
            zero=True,
        )
    )


    eixo_x = alt.X(
        "Ano:N",
        sort=anos_str,
        title="Ano",
        axis=alt.Axis(
            labelAngle=0,
            labelFontSize=11.5,
            titleFontSize=12.5,
            labelPadding=8,
        ),
    )


    deslocamento_grupo = alt.XOffset(
        "Grupo:N",
        sort=ordem_grupos,
    )


    escala_grupos = alt.Scale(
        domain=ordem_grupos,
        range=CORES_GRUPOS_DISTRIBUICOES[
            :len(
                ordem_grupos
            )
        ],
    )


    cor_grupo = alt.Color(
        "Grupo:N",
        title=None,
        sort=ordem_grupos,
        scale=escala_grupos,
        legend=alt.Legend(
            orient="top",
            direction="vertical",
            columns=1,
            labelLimit=600,
            symbolSize=90,
            title=None,
        ),
    )


    barras = (
        alt.Chart(
            medias
        )
        .mark_bar(
            size=44,
            cornerRadiusTopLeft=2,
            cornerRadiusTopRight=2,
        )
        .encode(
            x=eixo_x,
            xOffset=deslocamento_grupo,
            y=alt.Y(
                "Média:Q",
                title=f"Média de {indicador}",
                scale=escala_y,
                axis=alt.Axis(
                    format=formato_eixo,
                    labelFontSize=11.5,
                    titleFontSize=12.5,
                    tickCount=6,
                ),
            ),
            color=cor_grupo,
            tooltip=[
                alt.Tooltip(
                    "Ano:N",
                    title="Ano",
                ),
                alt.Tooltip(
                    "Grupo:N",
                    title="Categorias",
                ),
                alt.Tooltip(
                    "Média:Q",
                    title="Média",
                    format=formato_tooltip,
                ),
                alt.Tooltip(
                    "N escolas:Q",
                    title="N escolas",
                    format="d",
                ),
            ],
        )
    )


    rotulos = (
        alt.Chart(
            medias
        )
        .mark_text(
            dy=-10,
            fontSize=9,
            fontWeight="bold",
            color="#2F313C",
        )
        .encode(
            x=alt.X(
                "Ano:N",
                sort=anos_str,
            ),
            xOffset=alt.XOffset(
                "Grupo:N",
                sort=ordem_grupos,
            ),
            y=alt.Y(
                "Média:Q",
                scale=escala_y,
            ),
            text=alt.Text(
                "Rótulo média:N"
            ),
        )
    )


    return (
        barras
        +
        rotulos
    ).properties(
        height=altura,
        title=alt.TitleParams(
            text=(
                f"Médias de {indicador} — categorias agregadas de "
                f"{rotulo_dimensao(variavel)}"
            ),
            subtitle=(
                "As duas seleções aparecem lado a lado dentro de cada ano, "
                "na mesma ordem do boxplot."
            ),
            anchor="middle",
            fontSize=15,
            subtitleFontSize=10.5,
            subtitlePadding=7,
        ),
    )


# ============================================================
# DISTRIBUIÇÕES — AGREGAÇÃO DE CATEGORIAS
# ============================================================

def obter_categorias_agregacao(
    base,
    variavel,
):

    # As faixas de IDEB têm um domínio conhecido e fixo. Na
    # subseção Agregado, elas devem aparecer como possibilidades
    # mesmo quando alguma faixa não esteja presente no recorte
    # momentâneo produzido pelos filtros gerais. Isso também evita
    # que a lista fique vazia ao trocar para uma dimensão Faixa IDEB.
    if str(variavel).startswith(
        "Faixa IDEB"
    ):

        return [
            categoria
            for categoria
            in ORDEM_FAIXA_IDEB
            if categoria
            != "Sem resultado"
        ]


    if base.empty:

        return []


    temp = criar_variavel_eixo(
        base,
        variavel,
    )


    categorias = (
        temp[
            "Categoria"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


    return ordenar_dimensao(
        categorias,
        variavel,
    )


def preparar_dados_boxplot_agregado(
    base,
    indicador,
    variavel,
    anos,
    categorias_grupo_1,
    categorias_grupo_2,
):

    anos = sorted(
        list(
            dict.fromkeys(
                int(
                    ano
                )
                for ano in anos
            )
        )
    )


    recorte = (
        base[
            base[
                "Ano"
            ].isin(
                anos
            )
        ]
        .copy()
    )


    if recorte.empty:

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Ano",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Categoria original",
                    "Valor",
                ]
            ),
            [],
        )


    recorte[
        indicador
    ] = pd.to_numeric(
        recorte[
            indicador
        ],
        errors="coerce",
    )


    recorte = (
        recorte[
            recorte[
                indicador
            ].notna()
        ]
        .drop_duplicates(
            subset=[
                "Cód. INEP",
                "Ano",
            ],
            keep="first",
        )
        .copy()
    )


    if recorte.empty:

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Ano",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Categoria original",
                    "Valor",
                ]
            ),
            [],
        )


    temp = criar_variavel_eixo(
        recorte,
        variavel,
    )


    recorte[
        "Categoria original"
    ] = temp[
        "Categoria"
    ].values


    recorte = (
        recorte[
            recorte[
                "Categoria original"
            ].notna()
        ]
        .copy()
    )


    recorte[
        "Categoria original"
    ] = (
        recorte[
            "Categoria original"
        ]
        .astype(str)
    )


    mapa_grupos = {
        str(
            categoria
        ): "Agregado 1"
        for categoria
        in categorias_grupo_1
    }


    mapa_grupos.update(
        {
            str(
                categoria
            ): "Agregado 2"
            for categoria
            in categorias_grupo_2
        }
    )


    recorte[
        "Categoria"
    ] = (
        recorte[
            "Categoria original"
        ]
        .map(
            mapa_grupos
        )
    )


    recorte = (
        recorte[
            recorte[
                "Categoria"
            ].notna()
        ]
        .copy()
    )


    if recorte.empty:

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Ano",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Categoria original",
                    "Valor",
                ]
            ),
            [],
        )


    recorte[
        "Categoria_1"
    ] = recorte[
        "Categoria"
    ]


    recorte[
        "Categoria_2"
    ] = ""


    dados = recorte[
        [
            "Cód. INEP",
            "Ano",
            "Categoria_1",
            "Categoria_2",
            "Categoria",
            "Categoria original",
            indicador,
        ]
    ].copy()


    dados = dados.rename(
        columns={
            indicador: "Valor"
        }
    )


    dados[
        "Ano"
    ] = (
        dados[
            "Ano"
        ]
        .astype(int)
        .astype(str)
    )


    categorias_existentes = set(
        dados[
            "Categoria"
        ]
        .astype(str)
        .unique()
    )


    ordem = [
        grupo
        for grupo
        in [
            "Agregado 1",
            "Agregado 2",
        ]
        if grupo
        in categorias_existentes
    ]


    return (
        dados,
        ordem,
    )


def preparar_dados_delta_boxplot_agregado(
    base,
    indicador,
    variavel,
    ano_inicial,
    ano_final,
    categorias_grupo_1,
    categorias_grupo_2,
):

    anos_delta = [
        int(
            ano_inicial
        ),
        int(
            ano_final
        ),
    ]


    recorte = (
        base[
            base[
                "Ano"
            ].isin(
                anos_delta
            )
        ]
        .copy()
    )


    if recorte.empty:

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Categoria original",
                    "Delta",
                ]
            ),
            [],
        )


    recorte[
        indicador
    ] = pd.to_numeric(
        recorte[
            indicador
        ],
        errors="coerce",
    )


    recorte = (
        recorte[
            recorte[
                indicador
            ].notna()
        ]
        .drop_duplicates(
            subset=[
                "Cód. INEP",
                "Ano",
            ],
            keep="first",
        )
        .copy()
    )


    pivot = (
        recorte[
            [
                "Cód. INEP",
                "Ano",
                indicador,
            ]
        ]
        .pivot(
            index="Cód. INEP",
            columns="Ano",
            values=indicador,
        )
    )


    if (
        ano_inicial
        not in pivot.columns
        or
        ano_final
        not in pivot.columns
    ):

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Categoria original",
                    "Delta",
                ]
            ),
            [],
        )


    pivot = (
        pivot[
            [
                ano_inicial,
                ano_final,
            ]
        ]
        .dropna()
        .reset_index()
    )


    if pivot.empty:

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Categoria original",
                    "Delta",
                ]
            ),
            [],
        )


    pivot[
        "Delta"
    ] = (
        pivot[
            ano_final
        ]
        -
        pivot[
            ano_inicial
        ]
    )


    deltas_escola = pivot[
        [
            "Cód. INEP",
            "Delta",
        ]
    ].copy()


    # A composição dos grupos do delta usa a categoria da escola
    # no ano mais recente da comparação, em linha com a regra das
    # demais comparações do painel.
    base_final = (
        recorte[
            recorte[
                "Ano"
            ]
            == ano_final
        ]
        .merge(
            deltas_escola,
            on="Cód. INEP",
            how="inner",
            validate="one_to_one",
        )
    )


    if base_final.empty:

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Categoria original",
                    "Delta",
                ]
            ),
            [],
        )


    temp = criar_variavel_eixo(
        base_final,
        variavel,
    )


    base_final[
        "Categoria original"
    ] = temp[
        "Categoria"
    ].values


    base_final = (
        base_final[
            base_final[
                "Categoria original"
            ].notna()
        ]
        .copy()
    )


    base_final[
        "Categoria original"
    ] = (
        base_final[
            "Categoria original"
        ]
        .astype(str)
    )


    mapa_grupos = {
        str(
            categoria
        ): "Agregado 1"
        for categoria
        in categorias_grupo_1
    }


    mapa_grupos.update(
        {
            str(
                categoria
            ): "Agregado 2"
            for categoria
            in categorias_grupo_2
        }
    )


    base_final[
        "Categoria"
    ] = (
        base_final[
            "Categoria original"
        ]
        .map(
            mapa_grupos
        )
    )


    base_final = (
        base_final[
            base_final[
                "Categoria"
            ].notna()
        ]
        .copy()
    )


    if base_final.empty:

        return (
            pd.DataFrame(
                columns=[
                    "Cód. INEP",
                    "Categoria_1",
                    "Categoria_2",
                    "Categoria",
                    "Categoria original",
                    "Delta",
                ]
            ),
            [],
        )


    base_final[
        "Categoria_1"
    ] = base_final[
        "Categoria"
    ]


    base_final[
        "Categoria_2"
    ] = ""


    dados = base_final[
        [
            "Cód. INEP",
            "Categoria_1",
            "Categoria_2",
            "Categoria",
            "Categoria original",
            "Delta",
        ]
    ].copy()


    categorias_existentes = set(
        dados[
            "Categoria"
        ]
        .astype(str)
        .unique()
    )


    ordem = [
        grupo
        for grupo
        in [
            "Agregado 1",
            "Agregado 2",
        ]
        if grupo
        in categorias_existentes
    ]


    return (
        dados,
        ordem,
    )


# ============================================================
# DISTRIBUIÇÕES — TESTES ENTRE AGREGADOS
# ============================================================

def _limpar_amostra_numerica(valores):

    serie = pd.to_numeric(
        pd.Series(valores),
        errors="coerce",
    ).dropna()

    return serie.to_numpy(
        dtype=float,
    )


def _p_valor_permutacao_media(
    amostra_1,
    amostra_2,
    max_exatas=20000,
    n_permutacoes=10000,
):

    amostra_1 = _limpar_amostra_numerica(
        amostra_1
    )

    amostra_2 = _limpar_amostra_numerica(
        amostra_2
    )

    n_1 = len(
        amostra_1
    )

    n_2 = len(
        amostra_2
    )


    if n_1 < 2 or n_2 < 2:

        return np.nan


    combinado = np.concatenate(
        [
            amostra_1,
            amostra_2,
        ]
    )


    diferenca_observada = abs(
        float(
            np.mean(
                amostra_1
            )
            -
            np.mean(
                amostra_2
            )
        )
    )


    n_total = n_1 + n_2


    try:

        total_combinacoes = math.comb(
            n_total,
            n_1,
        )

    except Exception:

        total_combinacoes = max_exatas + 1


    tolerancia = 1e-12


    if total_combinacoes <= max_exatas:

        soma_total = float(
            combinado.sum()
        )

        extremos = 0
        total = 0


        for indices_grupo_1 in itertools.combinations(
            range(
                n_total
            ),
            n_1,
        ):

            soma_1 = float(
                combinado[
                    list(
                        indices_grupo_1
                    )
                ].sum()
            )

            media_1 = soma_1 / n_1
            media_2 = (
                soma_total
                - soma_1
            ) / n_2

            diferenca = abs(
                media_1
                - media_2
            )


            if (
                diferenca
                >= diferenca_observada
                - tolerancia
            ):

                extremos += 1


            total += 1


        if total == 0:

            return np.nan


        return extremos / total


    rng = np.random.default_rng(
        20260811
    )

    extremos = 0


    for _ in range(
        n_permutacoes
    ):

        permutado = rng.permutation(
            combinado
        )

        diferenca = abs(
            float(
                np.mean(
                    permutado[
                        :n_1
                    ]
                )
                -
                np.mean(
                    permutado[
                        n_1:
                    ]
                )
            )
        )


        if (
            diferenca
            >= diferenca_observada
            - tolerancia
        ):

            extremos += 1


    return (
        extremos
        + 1
    ) / (
        n_permutacoes
        + 1
    )


def _p_valor_welch(
    amostra_1,
    amostra_2,
):

    amostra_1 = _limpar_amostra_numerica(
        amostra_1
    )

    amostra_2 = _limpar_amostra_numerica(
        amostra_2
    )

    n_1 = len(
        amostra_1
    )

    n_2 = len(
        amostra_2
    )


    if n_1 < 2 or n_2 < 2:

        return np.nan


    media_1 = float(
        np.mean(
            amostra_1
        )
    )

    media_2 = float(
        np.mean(
            amostra_2
        )
    )

    variancia_1 = float(
        np.var(
            amostra_1,
            ddof=1,
        )
    )

    variancia_2 = float(
        np.var(
            amostra_2,
            ddof=1,
        )
    )


    parcela_1 = variancia_1 / n_1
    parcela_2 = variancia_2 / n_2

    erro_quadrado = (
        parcela_1
        + parcela_2
    )


    if erro_quadrado <= 0:

        return (
            1.0
            if math.isclose(
                media_1,
                media_2,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
            else 0.0
        )


    estatistica_t = (
        media_1
        - media_2
    ) / math.sqrt(
        erro_quadrado
    )


    denominador_gl = (
        (
            parcela_1 ** 2
        )
        /
        (
            n_1
            - 1
        )
        +
        (
            parcela_2 ** 2
        )
        /
        (
            n_2
            - 1
        )
    )


    if denominador_gl <= 0:

        graus_liberdade = np.inf

    else:

        graus_liberdade = (
            erro_quadrado ** 2
        ) / denominador_gl


    try:

        from scipy.stats import t as distribuicao_t

        return float(
            2
            * distribuicao_t.sf(
                abs(
                    estatistica_t
                ),
                graus_liberdade,
            )
        )

    except Exception:

        # Fallback sem SciPy. Para amostras grandes, a distribuição
        # t converge rapidamente para a normal padrão.
        return float(
            math.erfc(
                abs(
                    estatistica_t
                )
                /
                math.sqrt(
                    2
                )
            )
        )


def calcular_teste_media_agregados(
    amostra_1,
    amostra_2,
    limiar_amostra_pequena=30,
):

    amostra_1 = _limpar_amostra_numerica(
        amostra_1
    )

    amostra_2 = _limpar_amostra_numerica(
        amostra_2
    )

    n_1 = len(
        amostra_1
    )

    n_2 = len(
        amostra_2
    )


    media_1 = (
        float(
            np.mean(
                amostra_1
            )
        )
        if n_1 > 0
        else np.nan
    )

    media_2 = (
        float(
            np.mean(
                amostra_2
            )
        )
        if n_2 > 0
        else np.nan
    )

    diferenca_medias = (
        media_2
        - media_1
        if (
            pd.notna(
                media_1
            )
            and
            pd.notna(
                media_2
            )
        )
        else np.nan
    )


    if n_1 < 2 or n_2 < 2:

        return {
            "p_valor": np.nan,
            "teste": "Amostra insuficiente",
            "n_1": n_1,
            "n_2": n_2,
            "media_1": media_1,
            "media_2": media_2,
            "diferenca_medias": diferenca_medias,
        }


    if min(
        n_1,
        n_2,
    ) < limiar_amostra_pequena:

        p_valor = _p_valor_permutacao_media(
            amostra_1,
            amostra_2,
        )

        teste = (
            "Permutação bilateral da diferença de médias"
        )

    else:

        p_valor = _p_valor_welch(
            amostra_1,
            amostra_2,
        )

        teste = "t de Welch bilateral"


    return {
        "p_valor": p_valor,
        "teste": teste,
        "n_1": n_1,
        "n_2": n_2,
        "media_1": media_1,
        "media_2": media_2,
        "diferenca_medias": diferenca_medias,
    }


def calcular_p_valores_agregados_por_ano(
    dados,
    anos,
):

    resultados = []


    for ano in sorted(
        anos
    ):

        recorte_ano = (
            dados[
                dados[
                    "Ano"
                ]
                == str(
                    ano
                )
            ]
        )


        teste = calcular_teste_media_agregados(
            recorte_ano[
                recorte_ano[
                    "Categoria"
                ]
                == "Agregado 1"
            ][
                "Valor"
            ],
            recorte_ano[
                recorte_ano[
                    "Categoria"
                ]
                == "Agregado 2"
            ][
                "Valor"
            ],
        )


        teste[
            "rotulo"
        ] = str(
            ano
        )

        resultados.append(
            teste
        )


    return resultados


def calcular_p_valor_agregado_delta(
    dados_delta,
    ano_inicial,
    ano_final,
):

    teste = calcular_teste_media_agregados(
        dados_delta[
            dados_delta[
                "Categoria"
            ]
            == "Agregado 1"
        ][
            "Delta"
        ],
        dados_delta[
            dados_delta[
                "Categoria"
            ]
            == "Agregado 2"
        ][
            "Delta"
        ],
    )


    teste[
        "rotulo"
    ] = (
        f"{ano_final} − {ano_inicial}"
    )


    return [
        teste
    ]



def calcular_testes_categoria_vs_demais(
    dados,
    coluna_valor,
    ordem,
    rotulo_periodo,
):

    if dados.empty:

        return []


    base_teste = (
        dados[
            dados[
                "Categoria"
            ]
            != "Consolidado"
        ]
        .copy()
    )


    if base_teste.empty:

        return []


    base_teste[
        coluna_valor
    ] = pd.to_numeric(
        base_teste[
            coluna_valor
        ],
        errors="coerce",
    )


    base_teste = base_teste[
        base_teste[
            coluna_valor
        ].notna()
    ].copy()


    resultados = []


    categorias_existentes = set(
        base_teste[
            "Categoria"
        ]
        .astype(str)
        .unique()
    )


    for categoria in ordem:

        categoria = str(
            categoria
        )


        if (
            categoria == "Consolidado"
            or categoria not in categorias_existentes
        ):

            continue


        alvo = (
            base_teste[
                base_teste[
                    "Categoria"
                ].astype(str)
                == categoria
            ]
            .drop_duplicates(
                subset=[
                    "Cód. INEP"
                ],
                keep="first",
            )
            .copy()
        )


        ids_alvo = set(
            alvo[
                "Cód. INEP"
            ].astype(str)
        )


        demais = (
            base_teste[
                (
                    base_teste[
                        "Categoria"
                    ].astype(str)
                    != categoria
                )
                &
                (
                    ~base_teste[
                        "Cód. INEP"
                    ].astype(str)
                    .isin(
                        ids_alvo
                    )
                )
            ]
            .drop_duplicates(
                subset=[
                    "Cód. INEP"
                ],
                keep="first",
            )
            .copy()
        )


        # A categoria é enviada como grupo 2 para que a diferença
        # armazenada seja média da categoria − média das demais.
        teste = calcular_teste_media_agregados(
            demais[
                coluna_valor
            ],
            alvo[
                coluna_valor
            ],
        )


        teste[
            "rotulo"
        ] = str(
            rotulo_periodo
        )

        teste[
            "comparacao"
        ] = (
            f"{categoria} vs demais"
        )

        teste[
            "n_considerado_custom"
        ] = (
            f"{int(teste['n_2'])} × "
            f"{int(teste['n_1'])}"
        )


        resultados.append(
            teste
        )


    return resultados


def exibir_p_valores_categoria_vs_demais(
    resultados,
    indicador,
):

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:1rem;
            font-weight:700;
            margin-top:0.45rem;
            margin-bottom:0.15rem;
        ">
            Diferença de médias — categoria vs demais
        </div>
        """,
        unsafe_allow_html=True,
    )


    if not resultados:

        st.info(
            "Sem comparação disponível."
        )

        return


    linhas_html = []


    for resultado in resultados:

        p_valor = resultado[
            "p_valor"
        ]


        (
            relevancia,
            cor_fundo_relevancia,
            cor_texto_relevancia,
        ) = classificar_relevancia_estatistica(
            p_valor
        )


        teste = resultado[
            "teste"
        ]

        nome_teste = html.escape(
            nome_curto_teste_media(
                teste
            )
        )

        explicacao_teste = html.escape(
            descricao_teste_media(
                teste
            ),
            quote=True,
        )

        ano = html.escape(
            str(
                resultado.get(
                    "rotulo",
                    "",
                )
            )
        )

        comparacao = html.escape(
            str(
                resultado.get(
                    "comparacao",
                    "",
                )
            )
        )

        p_formatado = html.escape(
            formatar_p_valor(
                p_valor
            )
        )

        diferenca_formatada = html.escape(
            formatar_diferenca_medias(
                resultado.get(
                    "diferenca_medias",
                    np.nan,
                ),
                indicador,
            )
        )

        n_considerado = html.escape(
            str(
                resultado.get(
                    "n_considerado_custom",
                    (
                        f"{int(resultado['n_2'])} × "
                        f"{int(resultado['n_1'])}"
                    ),
                )
            )
        )


        if pd.notna(
            p_valor
        ) and float(
            p_valor
        ) < 0.05:

            cor_p = cor_texto_relevancia

        else:

            cor_p = "#374151"


        linhas_html.append(
            "<tr>"
            f"<td style='padding:8px 7px;border-bottom:1px solid #EEF1F5;'>{ano}</td>"
            f"<td style='text-align:left;padding-left:10px;'>{comparacao}</td>"
            "<td>"
            f"<span style='font-weight:700;color:{cor_p};'>"
            f"{p_formatado}</span>"
            "</td>"
            "<td>"
            f"<span style='display:inline-block;padding:4px 10px;"
            f"border-radius:999px;background:{cor_fundo_relevancia};"
            f"color:{cor_texto_relevancia};font-weight:700;"
            f"white-space:nowrap;'>{html.escape(relevancia)}</span>"
            "</td>"
            f"<td style='font-weight:700;'>{diferenca_formatada}</td>"
            "<td>"
            f"<span title='{explicacao_teste}' "
            "style='cursor:help;text-decoration:underline dotted;"
            "text-underline-offset:3px;'>"
            f"{nome_teste}</span>"
            "</td>"
            f"<td style='padding:8px 7px;border-bottom:1px solid #EEF1F5;'>{n_considerado}</td>"
            "</tr>"
        )


    tabela_html = (
        "<div style='width:94%;max-width:1180px;margin:0.45rem auto 0;"
        "overflow-x:auto;background:#FFFFFF;border:1px solid #E1E7EE;"
        "border-radius:10px;'>"
        "<table style='width:100%;border-collapse:collapse;"
        "font-size:0.79rem;text-align:center;table-layout:fixed;color:#42526A;'>"
        "<colgroup>"
        "<col style='width:8%;'>"
        "<col style='width:24%;'>"
        "<col style='width:10%;'>"
        "<col style='width:17%;'>"
        "<col style='width:17%;'>"
        "<col style='width:14%;'>"
        "<col style='width:10%;'>"
        "</colgroup>"
        "<thead><tr>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>Ano</th>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>Comparação</th>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>p-valor</th>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>Relevância Estatística</th>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>Diferença entre médias<br>(categoria − demais)</th>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>Teste aplicado</th>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>N considerado<br>(categoria × demais)</th>"
        "</tr></thead>"
        "<tbody>"
        + "".join(
            linhas_html
        )
        + "</tbody></table></div>"
    )


    st.markdown(
        tabela_html,
        unsafe_allow_html=True,
    )


def formatar_p_valor(
    valor,
):

    if pd.isna(
        valor
    ):

        return "—"


    valor = float(
        valor
    )


    if valor < 0.001:

        return "< 0,001"


    return (
        f"{valor:.3f}"
        .replace(
            ".",
            ",",
        )
    )


def descricao_teste_media(
    teste,
):

    descricoes = {
        "t de Welch bilateral": (
            "Teste t bilateral de Welch para comparar as médias de dois "
            "grupos independentes sem pressupor variâncias iguais. É usado "
            "quando ambos os grupos têm pelo menos 30 observações."
        ),
        "Permutação bilateral da diferença de médias": (
            "Teste bilateral de permutação da diferença de médias. É usado "
            "quando pelo menos um dos grupos tem menos de 30 observações."
        ),
        "Amostra insuficiente": (
            "Não há observações suficientes nos dois grupos para calcular "
            "um teste de diferença de médias."
        ),
    }


    return descricoes.get(
        teste,
        "Teste estatístico usado para comparar as médias dos dois grupos.",
    )


def nome_curto_teste_media(
    teste,
):

    nomes = {
        "t de Welch bilateral": "t de Welch",
        "Permutação bilateral da diferença de médias": "Permutação",
        "Amostra insuficiente": "Amostra insuficiente",
    }


    return nomes.get(
        teste,
        teste,
    )


def formatar_diferenca_medias(
    valor,
    indicador,
):

    if pd.isna(
        valor
    ):

        return "—"


    valor = float(
        valor
    )


    if indicador == "Rendimento":

        return (
            f"{valor * 100:+.1f} p.p."
            .replace(
                ".",
                ",",
            )
        )


    return (
        f"{valor:+.1f}"
        .replace(
            ".",
            ",",
        )
    )


def classificar_relevancia_estatistica(
    p_valor,
):

    if pd.isna(
        p_valor
    ):

        return (
            "Indisponível",
            "#F3F4F6",
            "#6B7280",
        )


    p_valor = float(
        p_valor
    )


    # Escala convencional de evidência estatística:
    # p < 0,001  -> evidência muito forte
    # p < 0,01   -> evidência forte
    # p < 0,05   -> evidência moderada
    # p >= 0,05  -> não estatisticamente significativa
    if p_valor < 0.001:

        return (
            "Muito forte",
            "#D1FAE5",
            "#065F46",
        )


    if p_valor < 0.01:

        return (
            "Forte",
            "#DCFCE7",
            "#166534",
        )


    if p_valor < 0.05:

        return (
            "Moderada",
            "#FEF3C7",
            "#92400E",
        )


    return (
        "Não significativa",
        "#F3F4F6",
        "#6B7280",
    )


def exibir_p_valores_agregados(
    resultados,
    indicador,
):

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:1rem;
            font-weight:700;
            margin-top:0.45rem;
            margin-bottom:0.15rem;
        ">
            Diferença de médias
        </div>
        """,
        unsafe_allow_html=True,
    )


    if not resultados:

        st.info(
            "Sem comparação disponível."
        )

        return


    linhas_html = []


    for resultado in resultados:

        p_valor = resultado[
            "p_valor"
        ]


        (
            relevancia,
            cor_fundo_relevancia,
            cor_texto_relevancia,
        ) = classificar_relevancia_estatistica(
            p_valor
        )


        teste = resultado[
            "teste"
        ]

        nome_teste = html.escape(
            nome_curto_teste_media(
                teste
            )
        )

        explicacao_teste = html.escape(
            descricao_teste_media(
                teste
            ),
            quote=True,
        )

        ano = html.escape(
            str(
                resultado.get(
                    "rotulo",
                    "",
                )
            )
        )

        p_formatado = html.escape(
            formatar_p_valor(
                p_valor
            )
        )

        n_considerado = (
            f"{int(resultado['n_1'])} × "
            f"{int(resultado['n_2'])}"
        )


        diferenca_formatada = html.escape(
            formatar_diferenca_medias(
                resultado.get(
                    "diferenca_medias",
                    np.nan,
                ),
                indicador,
            )
        )


        if pd.notna(
            p_valor
        ) and float(
            p_valor
        ) < 0.05:

            cor_p = cor_texto_relevancia

        else:

            cor_p = "#374151"


        linhas_html.append(
            "<tr>"
            f"<td style='padding:8px 7px;border-bottom:1px solid #EEF1F5;'>{ano}</td>"
            "<td>"
            f"<span style='font-weight:700;color:{cor_p};'>"
            f"{p_formatado}</span>"
            "</td>"
            "<td>"
            f"<span style='display:inline-block;padding:4px 10px;"
            f"border-radius:999px;background:{cor_fundo_relevancia};"
            f"color:{cor_texto_relevancia};font-weight:700;"
            f"white-space:nowrap;'>{html.escape(relevancia)}</span>"
            "</td>"
            f"<td style='font-weight:700;'>{diferenca_formatada}</td>"
            "<td>"
            f"<span title='{explicacao_teste}' "
            "style='cursor:help;text-decoration:underline dotted;"
            "text-underline-offset:3px;'>"
            f"{nome_teste}</span>"
            "</td>"
            f"<td style='padding:8px 7px;border-bottom:1px solid #EEF1F5;'>{n_considerado}</td>"
            "</tr>"
        )


    tabela_html = (
        "<div style='width:88%;max-width:1040px;margin:0.45rem auto 0;"
        "overflow-x:auto;background:#FFFFFF;border:1px solid #E1E7EE;"
        "border-radius:10px;'>"
        "<table style='width:100%;border-collapse:collapse;"
        "font-size:0.79rem;text-align:center;table-layout:fixed;color:#42526A;'>"
        "<colgroup>"
        "<col style='width:10%;'>"
        "<col style='width:13%;'>"
        "<col style='width:22%;'>"
        "<col style='width:20%;'>"
        "<col style='width:19%;'>"
        "<col style='width:16%;'>"
        "</colgroup>"
        "<thead><tr>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>"
        "Ano</th>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>"
        "p-valor</th>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>"
        "Relevância Estatística</th>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>"
        "Diferença entre médias (2 − 1)</th>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>"
        "Teste aplicado</th>"
        "<th style='padding:9px 7px;border-bottom:1px solid #D7DFE8;background:#F7F9FC;color:#334155;'>"
        "N considerado</th>"
        "</tr></thead>"
        "<tbody>"
        + "".join(
            linhas_html
        )
        + "</tbody></table></div>"
    )


    st.markdown(
        tabela_html,
        unsafe_allow_html=True,
    )

def _rotulo_composicao_agregado(
    categorias,
    n=None,
):

    # O rótulo base contém apenas a composição do agregado. O N é
    # acrescentado dinamicamente ao eixo X pelas funções de gráfico.
    partes = [
        str(
            categoria
        )
        for categoria
        in categorias
    ]


    return "\n".join(
        partes
    )


def rotulos_n_agregados_valores(
    dados,
    ano_referencia,
    categorias_grupo_1,
    categorias_grupo_2,
):

    contagens = (
        dados[
            dados[
                "Ano"
            ]
            == str(
                ano_referencia
            )
        ]
        .groupby(
            "Categoria"
        )[
            "Cód. INEP"
        ]
        .nunique()
        .to_dict()
    )


    return {
        "Agregado 1": _rotulo_composicao_agregado(
            categorias_grupo_1,
            contagens.get(
                "Agregado 1",
                0,
            ),
        ),
        "Agregado 2": _rotulo_composicao_agregado(
            categorias_grupo_2,
            contagens.get(
                "Agregado 2",
                0,
            ),
        ),
    }


def rotulos_n_agregados_delta(
    dados_delta,
    categorias_grupo_1,
    categorias_grupo_2,
):

    contagens = (
        dados_delta
        .groupby(
            "Categoria"
        )[
            "Cód. INEP"
        ]
        .nunique()
        .to_dict()
    )


    return {
        "Agregado 1": _rotulo_composicao_agregado(
            categorias_grupo_1,
            contagens.get(
                "Agregado 1",
                0,
            ),
        ),
        "Agregado 2": _rotulo_composicao_agregado(
            categorias_grupo_2,
            contagens.get(
                "Agregado 2",
                0,
            ),
        ),
    }


def aplicar_rotulos_n_agregados(
    dados,
    ordem,
    mapa_rotulos,
):

    plot = dados.copy()

    plot[
        "Categoria"
    ] = (
        plot[
            "Categoria"
        ]
        .map(
            mapa_rotulos
        )
        .fillna(
            plot[
                "Categoria"
            ]
        )
    )


    ordem_plot = [
        mapa_rotulos.get(
            grupo,
            grupo,
        )
        for grupo
        in ordem
    ]


    return (
        plot,
        ordem_plot,
    )


# ============================================================
# MALHA Y
# ============================================================

def escala_y(
    ordem_linhas,
):

    return alt.Y(
        "RowID:N",
        title=None,
        sort=ordem_linhas,
        scale=alt.Scale(
            paddingInner=0,
            paddingOuter=0.02,
        ),
        axis=None,
    )


# ============================================================
# PRINCIPAIS INDICADORES — PREPARAÇÃO
# ============================================================

def preparar_linhas_horizontais(
    dados,
    anos,
    categorias,
    ano_inicial,
    ano_final,
):

    anos_ord = sorted(
        anos,
        reverse=True,
    )


    registros = []

    categorias_labels = []

    anos_labels = []

    ordem = []

    contador = 0


    def adicionar_bloco(
        categoria,
        recorte_categoria,
        consolidado=False,
    ):

        nonlocal contador


        linhas_categoria = []


        for ano in anos_ord:

            rec = (
                recorte_categoria[
                    recorte_categoria[
                        "Ano"
                    ]
                    == str(
                        ano
                    )
                ]
            )


            if rec.empty:

                continue


            n = int(
                rec[
                    "N escolas"
                ].iloc[0]
            )


            texto_ano = (
                f"{ano} "
                f"({n:,})"
            ).replace(
                ",",
                ".",
            )


            row_id = (
                f"{contador:05d}"
            )


            contador += 1


            registros.append(
                {
                    "RowID":
                        row_id,

                    "TipoLinha":
                        "ano",

                    "Categoria":
                        categoria,

                    "Ano":
                        str(
                            ano
                        ),

                    "Média":
                        rec[
                            "Média"
                        ].iloc[0],

                    "N escolas":
                        n,

                    "Variação":
                        np.nan,
                }
            )


            anos_labels.append(
                {
                    "RowID":
                        row_id,

                    "AnoLabel":
                        texto_ano,
                }
            )


            ordem.append(
                row_id
            )


            linhas_categoria.append(
                row_id
            )


        if not linhas_categoria:

            return


        indice_central = (
            len(
                linhas_categoria
            )
            // 2
        )


        categorias_labels.append(
            {
                "RowID":
                    linhas_categoria[
                        indice_central
                    ],

                "CategoriaLabel":
                    categoria,
            }
        )


        if (
            ano_inicial is not None
            and
            ano_final is not None
        ):

            rec_ini = (
                recorte_categoria[
                    recorte_categoria[
                        "Ano"
                    ]
                    == str(
                        ano_inicial
                    )
                ]
            )


            rec_fim = (
                recorte_categoria[
                    recorte_categoria[
                        "Ano"
                    ]
                    == str(
                        ano_final
                    )
                ]
            )


            if (
                not rec_ini.empty
                and
                not rec_fim.empty
            ):

                delta = (
                    rec_fim[
                        "Média"
                    ].iloc[0]
                    -
                    rec_ini[
                        "Média"
                    ].iloc[0]
                )


                for registro in registros:

                    if (
                        registro[
                            "Categoria"
                        ]
                        == categoria
                        and
                        registro[
                            "Ano"
                        ]
                        == str(
                            ano_final
                        )
                    ):

                        registro[
                            "Variação"
                        ] = delta

                        break


        # Após o Consolidado mantemos duas linhas de espaço, mas apenas
        # a primeira desenha uma regra. Isso preserva o respiro visual
        # sem criar duas linhas horizontais consecutivas.
        tipos_separadores = (
            [
                "separador_grande",
                "espaco_grande",
            ]
            if consolidado
            else [
                "separador_pequeno"
            ]
        )


        for tipo_sep in tipos_separadores:

            row_sep = (
                f"{contador:05d}"
            )


            contador += 1


            registros.append(
                {
                    "RowID":
                        row_sep,

                    "TipoLinha":
                        tipo_sep,

                    "Categoria":
                        categoria,

                    "Ano":
                        None,

                    "Média":
                        np.nan,

                    "N escolas":
                        np.nan,

                    "Variação":
                        np.nan,
                }
            )


            ordem.append(
                row_sep
            )


    rec_consolidado = (
        dados[
            dados[
                "Categoria"
            ]
            == "Consolidado"
        ]
        .copy()
    )


    if not rec_consolidado.empty:

        adicionar_bloco(
            categoria="Consolidado",
            recorte_categoria=(
                rec_consolidado
            ),
            consolidado=True,
        )


    for categoria in categorias:

        if categoria == "Consolidado":

            continue


        rec = (
            dados[
                dados[
                    "Categoria"
                ]
                == categoria
            ]
            .copy()
        )


        if rec.empty:

            continue


        adicionar_bloco(
            categoria=categoria,
            recorte_categoria=rec,
            consolidado=False,
        )


    while (
        registros
        and
        (
            registros[-1][
                "TipoLinha"
            ].startswith(
                "separador"
            )
            or
            registros[-1][
                "TipoLinha"
            ]
            == "espaco_grande"
        )
    ):

        registros.pop()

        ordem.pop()


    return (
        pd.DataFrame(
            registros
        ),
        pd.DataFrame(
            categorias_labels
        ),
        pd.DataFrame(
            anos_labels
        ),
        ordem,
    )


# ============================================================
# PRINCIPAIS INDICADORES — GRÁFICO
# ============================================================

def criar_painel_horizontal(
    plot,
    labels_categorias,
    labels_anos,
    ordem_linhas,
    indicador,
    eixo_nome,
    ano_inicial,
    ano_final,
    largura_categoria=155,
    largura_anos=110,
    largura_esquerda=360,
    largura_direita=200,
    mostrar_medias=True,
    mostrar_variacoes=True,
):

    formatos = formatos_indicador(
        indicador
    )


    # Com apenas um ano não existe variação a calcular. Nesse cenário,
    # o painel força a exibição somente das médias, evitando que reste
    # qualquer eixo/linha de zero do gráfico de variações.
    if ano_inicial is None:

        mostrar_variacoes = False
        mostrar_medias = True


    # O gráfico de médias sempre parte de zero. O eixo continua oculto,
    # mas a extensão visual deixa de superdimensionar diferenças quando
    # o recorte possui médias baixas.
    baseline = 0.0


    altura = max(
        260,
        len(
            plot
        )
        * 19,
    )


    dados_sep_pequeno = (
        plot[
            plot[
                "TipoLinha"
            ]
            == "separador_pequeno"
        ]
    )


    dados_sep_grande = (
        plot[
            plot[
                "TipoLinha"
            ]
            == "separador_grande"
        ]
    )


    def regra_fina():

        return (
            alt.Chart(
                dados_sep_pequeno
            )
            .mark_rule(
                strokeWidth=0.75,
                color="#E1E6EC",
            )
            .encode(
                y=escala_y(
                    ordem_linhas
                )
            )
        )


    def regra_grande():

        return (
            alt.Chart(
                dados_sep_grande
            )
            .mark_rule(
                strokeWidth=1.15,
                color="#C9D1DA",
            )
            .encode(
                y=escala_y(
                    ordem_linhas
                )
            )
        )


    texto_categoria = (
        alt.Chart(
            labels_categorias
        )
        .mark_text(
            align="right",
            baseline="middle",
            fontSize=13.5,
            fontWeight="bold",
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x=alt.value(
                largura_categoria
                - 5
            ),

            text="CategoriaLabel:N",
        )
    )


    graf_categoria = (
        texto_categoria
        +
        regra_fina()
        +
        regra_grande()
    ).properties(
        width=largura_categoria,
        height=altura,
    )


    texto_anos = (
        alt.Chart(
            labels_anos
        )
        .mark_text(
            align="center",
            baseline="middle",
            fontSize=11,
            color="#7B8498",
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x=alt.value(
                largura_anos
                / 2
            ),

            text="AnoLabel:N",
        )
    )


    graf_anos = (
        texto_anos
        +
        regra_fina()
        +
        regra_grande()
    ).properties(
        width=largura_anos,
        height=altura,
    )


    dados_anos = (
        plot[
            plot[
                "TipoLinha"
            ]
            == "ano"
        ]
    )


    barras_abs = (
        alt.Chart(
            dados_anos
        )
        .mark_bar(
            size=19,
            clip=True,
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x=alt.X(
                "Média:Q",
                title=None,
                scale=alt.Scale(
                    domainMin=0,
                    zero=True,
                    nice=True,
                ),
                axis=alt.Axis(
                    labels=False,
                    ticks=False,
                    domain=False,
                    grid=False,
                ),
            ),

            x2=alt.datum(
                baseline
            ),

            color=alt.Color(
                "Ano:N",
                title=None,
                scale=alt.Scale(
                    domain=ORDEM_ANOS_STR,
                    range=ESCALA_CORES_ANOS,
                ),
                legend=alt.Legend(
                    orient="top",
                    direction="horizontal",
                    title=None,
                    columns=5,
                ),
            ),

            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title=rotulo_dimensao(
                        eixo_nome
                    ),
                ),

                alt.Tooltip(
                    "Ano:N",
                    title="Ano",
                ),

                alt.Tooltip(
                    "N escolas:Q",
                    title="Escolas",
                    format="d",
                ),

                alt.Tooltip(
                    "Média:Q",
                    title=indicador,
                    format=formatos[
                        "tooltip"
                    ],
                ),
            ],
        )
    )


    textos_abs = (
        alt.Chart(
            dados_anos
        )
        .mark_text(
            align="left",
            dx=4,
            fontSize=11,
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x="Média:Q",

            text=alt.Text(
                "Média:Q",
                format=formatos[
                    "rotulo"
                ],
            ),
        )
    )


    graf_abs = (
        barras_abs
        +
        textos_abs
        +
        regra_fina()
        +
        regra_grande()
    ).properties(
        width=largura_esquerda,
        height=altura,
        title=alt.TitleParams(
            text=(
                f"Média ponderada de "
                f"{indicador}"
            ),
            anchor="middle",
            fontSize=17,
            fontWeight="bold",
        ),
    )


    dados_delta = (
        plot[
            plot[
                "Variação"
            ].notna()
        ]
        .copy()
    )


    barras_delta = (
        alt.Chart(
            dados_delta
        )
        .mark_bar(
            size=19,
            color=COR_DELTA,
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x=alt.X(
                "Variação:Q",
                title=None,
                axis=alt.Axis(
                    labels=False,
                    ticks=False,
                    domain=False,
                    grid=False,
                ),
            ),

            x2=alt.datum(
                0
            ),
        )
    )


    textos_delta = (
        alt.Chart(
            dados_delta
        )
        .mark_text(
            dx=alt.expr(
                "datum.Variação >= 0 ? 4 : -4"
            ),
            align=alt.expr(
                "datum.Variação >= 0 ? 'left' : 'right'"
            ),
            fontSize=11,
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x="Variação:Q",

            text=alt.Text(
                "Variação:Q",
                format=formatos[
                    "delta"
                ],
            ),
        )
    )


    linha_zero = (
        alt.Chart(
            pd.DataFrame(
                {
                    "zero": [
                        0
                    ]
                }
            )
        )
        .mark_rule(
            color="#8A8A8A",
            strokeWidth=0.8,
        )
        .encode(
            x="zero:Q"
        )
    )


    titulo_delta = (
        (
            f"Variação "
            f"{ano_final} − "
            f"{ano_inicial}"
        )
        if ano_inicial
        is not None
        else
        "Variação"
    )


    graf_delta = (
        barras_delta
        +
        textos_delta
        +
        linha_zero
        +
        regra_fina()
        +
        regra_grande()
    ).properties(
        width=largura_direita,
        height=altura,
        title=alt.TitleParams(
            text=titulo_delta,
            anchor="middle",
            fontSize=17,
            fontWeight="bold",
        ),
    )


    # ========================================================
    # MODO APENAS VARIAÇÕES
    #
    # Mantém somente uma linha por categoria e reposiciona o nome
    # da categoria exatamente na linha da barra de variação. Os
    # separadores permanecem para preservar a hierarquia visual.
    # ========================================================

    if (
        not mostrar_medias
        and
        mostrar_variacoes
        and
        not dados_delta.empty
    ):

        tipos_delta = {
            "separador_pequeno",
            "separador_grande",
            "espaco_grande",
        }


        plot_delta_compacto = (
            plot[
                plot[
                    "Variação"
                ].notna()
                |
                plot[
                    "TipoLinha"
                ].isin(
                    tipos_delta
                )
            ]
            .copy()
        )


        ids_delta_compacto = set(
            plot_delta_compacto[
                "RowID"
            ].astype(str)
        )


        ordem_delta_compacto = [
            row_id
            for row_id in ordem_linhas
            if str(row_id)
            in ids_delta_compacto
        ]


        dados_delta_compacto = (
            plot_delta_compacto[
                plot_delta_compacto[
                    "Variação"
                ].notna()
            ]
            .copy()
        )


        labels_categoria_delta = (
            dados_delta_compacto[
                [
                    "RowID",
                    "Categoria",
                ]
            ]
            .rename(
                columns={
                    "Categoria":
                        "CategoriaLabel"
                }
            )
        )


        sep_pequeno_delta = (
            plot_delta_compacto[
                plot_delta_compacto[
                    "TipoLinha"
                ]
                == "separador_pequeno"
            ]
        )


        sep_grande_delta = (
            plot_delta_compacto[
                plot_delta_compacto[
                    "TipoLinha"
                ]
                == "separador_grande"
            ]
        )


        altura_delta = max(
            260,
            len(
                ordem_delta_compacto
            )
            * 28,
        )


        def regra_fina_delta():

            return (
                alt.Chart(
                    sep_pequeno_delta
                )
                .mark_rule(
                    strokeWidth=0.75,
                    color="#E1E6EC",
                )
                .encode(
                    y=escala_y(
                        ordem_delta_compacto
                    )
                )
            )


        def regra_grande_delta():

            return (
                alt.Chart(
                    sep_grande_delta
                )
                .mark_rule(
                    strokeWidth=1.15,
                    color="#C9D1DA",
                )
                .encode(
                    y=escala_y(
                        ordem_delta_compacto
                    )
                )
            )


        graf_categoria_delta = (
            alt.Chart(
                labels_categoria_delta
            )
            .mark_text(
                align="right",
                baseline="middle",
                fontSize=13.5,
                fontWeight="bold",
            )
            .encode(
                y=escala_y(
                    ordem_delta_compacto
                ),
                x=alt.value(
                    largura_categoria
                    - 5
                ),
                text="CategoriaLabel:N",
            )
            +
            regra_fina_delta()
            +
            regra_grande_delta()
        ).properties(
            width=largura_categoria,
            height=altura_delta,
        )


        barras_delta_compacto = (
            alt.Chart(
                dados_delta_compacto
            )
            .mark_bar(
                size=22,
                color=COR_DELTA,
            )
            .encode(
                y=escala_y(
                    ordem_delta_compacto
                ),
                x=alt.X(
                    "Variação:Q",
                    title=None,
                    axis=alt.Axis(
                        labels=False,
                        ticks=False,
                        domain=False,
                        grid=False,
                    ),
                ),
                x2=alt.datum(
                    0
                ),
            )
        )


        textos_delta_compacto = (
            alt.Chart(
                dados_delta_compacto
            )
            .mark_text(
                dx=alt.expr(
                    "datum.Variação >= 0 ? 5 : -5"
                ),
                align=alt.expr(
                    "datum.Variação >= 0 ? 'left' : 'right'"
                ),
                fontSize=11,
            )
            .encode(
                y=escala_y(
                    ordem_delta_compacto
                ),
                x="Variação:Q",
                text=alt.Text(
                    "Variação:Q",
                    format=formatos[
                        "delta"
                    ],
                ),
            )
        )


        graf_delta_compacto = (
            barras_delta_compacto
            +
            textos_delta_compacto
            +
            linha_zero
            +
            regra_fina_delta()
            +
            regra_grande_delta()
        ).properties(
            width=max(
                320,
                largura_direita
                + 100,
            ),
            height=altura_delta,
            title=alt.TitleParams(
                text=titulo_delta,
                anchor="middle",
                fontSize=17,
                fontWeight="bold",
            ),
        )


        return (
            alt.hconcat(
                graf_categoria_delta,
                graf_delta_compacto,
                spacing=0,
            )
            .resolve_scale(
                y="shared"
            )
            .configure_view(
                stroke=None
            )
        )


    # ========================================================
    # MODO APENAS MÉDIAS
    # ========================================================

    if mostrar_medias and not mostrar_variacoes:

        return (
            alt.hconcat(
                graf_categoria,
                graf_anos,
                graf_abs,
                spacing=0,
            )
            .resolve_scale(
                y="shared"
            )
            .configure_view(
                stroke=None
            )
        )


    return (
        alt.hconcat(
            graf_categoria,
            graf_anos,
            graf_abs,
            graf_delta,
            spacing=0,
        )
        .resolve_scale(
            y="shared"
        )
        .configure_view(
            stroke=None
        )
    )


# ============================================================
# CRUZAMENTOS — PREPARAÇÃO
# ============================================================

def preparar_linhas_cruzamentos(
    resultado,
    consolidado,
    anos,
    ordem_nivel_1,
    ordem_nivel_2,
    ano_inicial,
    ano_final,
):

    anos_ord = sorted(
        anos,
        reverse=True,
    )


    registros = []
    labels_nivel_1 = []
    labels_nivel_2 = []
    labels_anos = []
    ordem_linhas = []

    contador = 0


    def adicionar_ano(
        nivel_1,
        nivel_2,
        ano,
        media,
        n_escolas,
        delta=np.nan,
    ):

        nonlocal contador


        texto_ano = (
            f"{ano} "
            f"({int(n_escolas):,})"
        ).replace(
            ",",
            ".",
        )


        row_id = (
            f"{contador:06d}"
        )


        contador += 1


        registros.append(
            {
                "RowID": row_id,
                "TipoLinha": "ano",
                "Nivel1": nivel_1,
                "Nivel2": nivel_2,
                "Ano": str(ano),
                "Média": media,
                "N escolas": n_escolas,
                "Variação": delta,
            }
        )


        labels_anos.append(
            {
                "RowID": row_id,
                "AnoLabel": texto_ano,
            }
        )


        ordem_linhas.append(
            row_id
        )


        return row_id


    def adicionar_separador(
        tipo,
    ):

        nonlocal contador


        row_id = (
            f"{contador:06d}"
        )


        contador += 1


        registros.append(
            {
                "RowID": row_id,
                "TipoLinha": tipo,
                "Nivel1": None,
                "Nivel2": None,
                "Ano": None,
                "Média": np.nan,
                "N escolas": np.nan,
                "Variação": np.nan,
            }
        )


        ordem_linhas.append(
            row_id
        )


    # ========================================================
    # CONSOLIDADO
    # ========================================================

    if (
        consolidado is not None
        and
        not consolidado.empty
    ):

        linhas_cons = []


        for ano in anos_ord:

            rec = (
                consolidado[
                    consolidado[
                        "Ano"
                    ]
                    == str(
                        ano
                    )
                ]
            )


            if rec.empty:

                continue


            delta = np.nan


            if (
                ano_inicial is not None
                and
                ano
                == ano_final
            ):

                rec_ini = (
                    consolidado[
                        consolidado[
                            "Ano"
                        ]
                        == str(
                            ano_inicial
                        )
                    ]
                )


                if not rec_ini.empty:

                    delta = (
                        rec[
                            "Média"
                        ].iloc[0]
                        -
                        rec_ini[
                            "Média"
                        ].iloc[0]
                    )


            row = adicionar_ano(
                nivel_1="Consolidado",
                nivel_2="Total",
                ano=ano,
                media=rec[
                    "Média"
                ].iloc[0],
                n_escolas=rec[
                    "N escolas"
                ].iloc[0],
                delta=delta,
            )


            linhas_cons.append(
                row
            )


        if linhas_cons:

            centro = (
                len(
                    linhas_cons
                )
                // 2
            )


            labels_nivel_1.append(
                {
                    "RowID":
                        linhas_cons[
                            centro
                        ],

                    "Label":
                        "Consolidado",
                }
            )


            labels_nivel_2.append(
                {
                    "RowID":
                        linhas_cons[
                            centro
                        ],

                    "Label":
                        "Total",
                }
            )


            adicionar_separador(
                "separador_nivel_1"
            )

            adicionar_separador(
                "espaco_grande"
            )


    # ========================================================
    # DEMAIS
    # ========================================================

    for nivel_1 in ordem_nivel_1:

        base_n1 = (
            resultado[
                resultado[
                    "Categoria_1"
                ].astype(str)
                == str(
                    nivel_1
                )
            ]
            .copy()
        )


        if base_n1.empty:

            continue


        linhas_nivel_1 = []


        niveis_2_presentes = (
            base_n1[
                "Categoria_2"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )


        ordem_n2_local = [
            n2
            for n2
            in ordem_nivel_2
            if n2
            in niveis_2_presentes
        ]


        for n2_extra in niveis_2_presentes:

            if n2_extra not in ordem_n2_local:

                ordem_n2_local.append(
                    n2_extra
                )


        for idx_n2, nivel_2 in enumerate(
            ordem_n2_local
        ):

            base_n2 = (
                base_n1[
                    base_n1[
                        "Categoria_2"
                    ].astype(str)
                    == str(
                        nivel_2
                    )
                ]
                .copy()
            )


            if base_n2.empty:

                continue


            linhas_nivel_2 = []


            delta_grupo = np.nan


            if ano_inicial is not None:

                rec_ini = (
                    base_n2[
                        base_n2[
                            "Ano"
                        ]
                        == str(
                            ano_inicial
                        )
                    ]
                )


                rec_fim = (
                    base_n2[
                        base_n2[
                            "Ano"
                        ]
                        == str(
                            ano_final
                        )
                    ]
                )


                if (
                    not rec_ini.empty
                    and
                    not rec_fim.empty
                ):

                    delta_grupo = (
                        rec_fim[
                            "Média"
                        ].iloc[0]
                        -
                        rec_ini[
                            "Média"
                        ].iloc[0]
                    )


            for ano in anos_ord:

                rec = (
                    base_n2[
                        base_n2[
                            "Ano"
                        ]
                        == str(
                            ano
                        )
                    ]
                )


                if rec.empty:

                    continue


                delta_linha = (
                    delta_grupo
                    if ano
                    == ano_final
                    else np.nan
                )


                row = adicionar_ano(
                    nivel_1=nivel_1,
                    nivel_2=nivel_2,
                    ano=ano,
                    media=rec[
                        "Média"
                    ].iloc[0],
                    n_escolas=rec[
                        "N escolas"
                    ].iloc[0],
                    delta=delta_linha,
                )


                linhas_nivel_2.append(
                    row
                )

                linhas_nivel_1.append(
                    row
                )


            if linhas_nivel_2:

                labels_nivel_2.append(
                    {
                        "RowID":
                            linhas_nivel_2[
                                len(
                                    linhas_nivel_2
                                )
                                // 2
                            ],

                        "Label":
                            str(
                                nivel_2
                            ),
                    }
                )


            if idx_n2 < (
                len(
                    ordem_n2_local
                )
                - 1
            ):

                adicionar_separador(
                    "separador_nivel_2"
                )


        if linhas_nivel_1:

            labels_nivel_1.append(
                {
                    "RowID":
                        linhas_nivel_1[
                            len(
                                linhas_nivel_1
                            )
                            // 2
                        ],

                    "Label":
                        str(
                            nivel_1
                        ),
                }
            )


        adicionar_separador(
            "separador_nivel_1"
        )


    while (
        registros
        and
        registros[-1][
            "TipoLinha"
        ]
        in {
            "separador_nivel_1",
            "separador_nivel_2",
            "espaco_grande",
        }
    ):

        registros.pop()
        ordem_linhas.pop()


    return (
        pd.DataFrame(
            registros
        ),
        pd.DataFrame(
            labels_nivel_1
        ),
        pd.DataFrame(
            labels_nivel_2
        ),
        pd.DataFrame(
            labels_anos
        ),
        ordem_linhas,
    )


# ============================================================
# CRUZAMENTOS — GRÁFICO
# ============================================================

def criar_painel_cruzamentos(
    plot,
    labels_nivel_1,
    labels_nivel_2,
    labels_anos,
    ordem_linhas,
    indicador,
    variavel_1,
    variavel_2,
    ano_inicial,
    ano_final,
    largura_nivel_1=120,
    largura_nivel_2=145,
    largura_anos=110,
    largura_esquerda=320,
    largura_direita=185,
    mostrar_medias=True,
    mostrar_variacoes=True,
):

    formatos = formatos_indicador(
        indicador
    )


    # Com apenas um ano não existe variação a calcular. Nesse cenário,
    # o painel força a exibição somente das médias, evitando que reste
    # qualquer eixo/linha de zero do gráfico de variações.
    if ano_inicial is None:

        mostrar_variacoes = False
        mostrar_medias = True


    # O gráfico de médias sempre parte de zero. O eixo continua oculto,
    # mas a extensão visual deixa de superdimensionar diferenças quando
    # o recorte possui médias baixas.
    baseline = 0.0


    altura = max(
        290,
        len(
            plot
        )
        * 18,
    )


    separadores_n2 = (
        plot[
            plot[
                "TipoLinha"
            ]
            == "separador_nivel_2"
        ]
    )


    separadores_n1 = (
        plot[
            plot[
                "TipoLinha"
            ]
            == "separador_nivel_1"
        ]
    )


    def regra_n2():

        return (
            alt.Chart(
                separadores_n2
            )
            .mark_rule(
                strokeWidth=0.70,
                color="#E1E6EC",
            )
            .encode(
                y=escala_y(
                    ordem_linhas
                )
            )
        )


    def regra_n1():

        return (
            alt.Chart(
                separadores_n1
            )
            .mark_rule(
                strokeWidth=1.65,
                color="#C3CCD6",
            )
            .encode(
                y=escala_y(
                    ordem_linhas
                )
            )
        )


    texto_n1 = (
        alt.Chart(
            labels_nivel_1
        )
        .mark_text(
            align="right",
            baseline="middle",
            fontSize=13.5,
            fontWeight="bold",
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x=alt.value(
                largura_nivel_1
                - 4
            ),

            text="Label:N",
        )
    )


    graf_n1 = (
        texto_n1
        +
        regra_n1()
    ).properties(
        width=largura_nivel_1,
        height=altura,
    )


    texto_n2 = (
        alt.Chart(
            labels_nivel_2
        )
        .mark_text(
            align="right",
            baseline="middle",
            fontSize=12,
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x=alt.value(
                largura_nivel_2
                - 4
            ),

            text="Label:N",
        )
    )


    graf_n2 = (
        texto_n2
        +
        regra_n2()
        +
        regra_n1()
    ).properties(
        width=largura_nivel_2,
        height=altura,
    )


    texto_anos = (
        alt.Chart(
            labels_anos
        )
        .mark_text(
            align="center",
            baseline="middle",
            fontSize=11,
            color="#7B8498",
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x=alt.value(
                largura_anos
                / 2
            ),

            text="AnoLabel:N",
        )
    )


    graf_anos = (
        texto_anos
        +
        regra_n2()
        +
        regra_n1()
    ).properties(
        width=largura_anos,
        height=altura,
    )


    dados_anos = (
        plot[
            plot[
                "TipoLinha"
            ]
            == "ano"
        ]
        .copy()
    )


    barras_abs = (
        alt.Chart(
            dados_anos
        )
        .mark_bar(
            size=18,
            clip=True,
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x=alt.X(
                "Média:Q",
                title=None,
                scale=alt.Scale(
                    domainMin=0,
                    zero=True,
                    nice=True,
                ),
                axis=alt.Axis(
                    labels=False,
                    ticks=False,
                    domain=False,
                    grid=False,
                ),
            ),

            x2=alt.datum(
                baseline
            ),

            color=alt.Color(
                "Ano:N",
                title=None,
                scale=alt.Scale(
                    domain=ORDEM_ANOS_STR,
                    range=ESCALA_CORES_ANOS,
                ),
                legend=alt.Legend(
                    orient="top",
                    direction="horizontal",
                    title=None,
                    columns=5,
                ),
            ),
        )
    )


    texto_abs = (
        alt.Chart(
            dados_anos
        )
        .mark_text(
            align="left",
            dx=4,
            fontSize=10.2,
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x="Média:Q",

            text=alt.Text(
                "Média:Q",
                format=formatos[
                    "rotulo"
                ],
            ),
        )
    )


    graf_abs = (
        barras_abs
        +
        texto_abs
        +
        regra_n2()
        +
        regra_n1()
    ).properties(
        width=largura_esquerda,
        height=altura,
        title=alt.TitleParams(
            text=(
                f"Média ponderada de "
                f"{indicador}"
            ),
            anchor="middle",
            fontSize=17,
            fontWeight="bold",
        ),
    )


    dados_delta = (
        plot[
            plot[
                "Variação"
            ].notna()
        ]
        .copy()
    )


    barras_delta = (
        alt.Chart(
            dados_delta
        )
        .mark_bar(
            size=18,
            color=COR_DELTA,
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x=alt.X(
                "Variação:Q",
                title=None,
                axis=alt.Axis(
                    labels=False,
                    ticks=False,
                    domain=False,
                    grid=False,
                ),
            ),

            x2=alt.datum(
                0
            ),
        )
    )


    texto_delta = (
        alt.Chart(
            dados_delta
        )
        .mark_text(
            dx=alt.expr(
                "datum.Variação >= 0 ? 4 : -4"
            ),
            align=alt.expr(
                "datum.Variação >= 0 ? 'left' : 'right'"
            ),
            fontSize=10.2,
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x="Variação:Q",

            text=alt.Text(
                "Variação:Q",
                format=formatos[
                    "delta_cruz"
                ],
            ),
        )
    )


    linha_zero = (
        alt.Chart(
            pd.DataFrame(
                {
                    "zero": [
                        0
                    ]
                }
            )
        )
        .mark_rule(
            color="#888888",
            strokeWidth=0.8,
        )
        .encode(
            x="zero:Q"
        )
    )


    titulo_delta = (
        (
            f"Variação "
            f"{ano_final} − "
            f"{ano_inicial}"
        )
        if ano_inicial
        is not None
        else
        "Variação"
    )


    graf_delta = (
        barras_delta
        +
        texto_delta
        +
        linha_zero
        +
        regra_n2()
        +
        regra_n1()
    ).properties(
        width=largura_direita,
        height=altura,
        title=alt.TitleParams(
            text=titulo_delta,
            anchor="middle",
            fontSize=17,
            fontWeight="bold",
        ),
    )


    # ========================================================
    # MODO APENAS VARIAÇÕES
    #
    # Remove as linhas de anos e o gráfico de médias, mantendo uma
    # linha por combinação de categorias. Os rótulos são recalculados
    # sobre essa estrutura compacta para permanecerem alinhados.
    # ========================================================

    if (
        not mostrar_medias
        and
        mostrar_variacoes
        and
        not dados_delta.empty
    ):

        tipos_delta = {
            "separador_nivel_1",
            "separador_nivel_2",
            "espaco_grande",
        }


        plot_delta_compacto = (
            plot[
                plot[
                    "Variação"
                ].notna()
                |
                plot[
                    "TipoLinha"
                ].isin(
                    tipos_delta
                )
            ]
            .copy()
        )


        ids_delta_compacto = set(
            plot_delta_compacto[
                "RowID"
            ].astype(str)
        )


        ordem_delta_compacto = [
            row_id
            for row_id in ordem_linhas
            if str(row_id)
            in ids_delta_compacto
        ]


        dados_delta_compacto = (
            plot_delta_compacto[
                plot_delta_compacto[
                    "Variação"
                ].notna()
            ]
            .copy()
        )


        labels_n2_delta = (
            dados_delta_compacto[
                [
                    "RowID",
                    "Nivel2",
                ]
            ]
            .rename(
                columns={
                    "Nivel2":
                        "Label"
                }
            )
        )


        posicoes_delta = {
            row_id: idx
            for idx, row_id
            in enumerate(
                ordem_delta_compacto
            )
        }


        registros_n1_delta = []


        for nivel_1, grupo_n1 in (
            dados_delta_compacto
            .groupby(
                "Nivel1",
                sort=False,
            )
        ):

            rows_n1 = sorted(
                grupo_n1[
                    "RowID"
                ].astype(str).tolist(),
                key=lambda row_id:
                    posicoes_delta.get(
                        row_id,
                        10**9,
                    ),
            )


            if not rows_n1:

                continue


            registros_n1_delta.append(
                {
                    "RowID":
                        rows_n1[
                            len(
                                rows_n1
                            )
                            // 2
                        ],
                    "Label":
                        str(
                            nivel_1
                        ),
                }
            )


        labels_n1_delta = pd.DataFrame(
            registros_n1_delta
        )


        sep_n2_delta = (
            plot_delta_compacto[
                plot_delta_compacto[
                    "TipoLinha"
                ]
                == "separador_nivel_2"
            ]
        )


        sep_n1_delta = (
            plot_delta_compacto[
                plot_delta_compacto[
                    "TipoLinha"
                ]
                == "separador_nivel_1"
            ]
        )


        altura_delta = max(
            290,
            len(
                ordem_delta_compacto
            )
            * 27,
        )


        def regra_n2_delta():

            return (
                alt.Chart(
                    sep_n2_delta
                )
                .mark_rule(
                    strokeWidth=0.70,
                    color="#E1E6EC",
                )
                .encode(
                    y=escala_y(
                        ordem_delta_compacto
                    )
                )
            )


        def regra_n1_delta():

            return (
                alt.Chart(
                    sep_n1_delta
                )
                .mark_rule(
                    strokeWidth=1.65,
                    color="#C3CCD6",
                )
                .encode(
                    y=escala_y(
                        ordem_delta_compacto
                    )
                )
            )


        graf_n1_delta = (
            alt.Chart(
                labels_n1_delta
            )
            .mark_text(
                align="right",
                baseline="middle",
                fontSize=13.5,
                fontWeight="bold",
            )
            .encode(
                y=escala_y(
                    ordem_delta_compacto
                ),
                x=alt.value(
                    largura_nivel_1
                    - 4
                ),
                text="Label:N",
            )
            +
            regra_n1_delta()
        ).properties(
            width=largura_nivel_1,
            height=altura_delta,
        )


        graf_n2_delta = (
            alt.Chart(
                labels_n2_delta
            )
            .mark_text(
                align="right",
                baseline="middle",
                fontSize=12,
            )
            .encode(
                y=escala_y(
                    ordem_delta_compacto
                ),
                x=alt.value(
                    largura_nivel_2
                    - 4
                ),
                text="Label:N",
            )
            +
            regra_n2_delta()
            +
            regra_n1_delta()
        ).properties(
            width=largura_nivel_2,
            height=altura_delta,
        )


        barras_delta_compacto = (
            alt.Chart(
                dados_delta_compacto
            )
            .mark_bar(
                size=21,
                color=COR_DELTA,
            )
            .encode(
                y=escala_y(
                    ordem_delta_compacto
                ),
                x=alt.X(
                    "Variação:Q",
                    title=None,
                    axis=alt.Axis(
                        labels=False,
                        ticks=False,
                        domain=False,
                        grid=False,
                    ),
                ),
                x2=alt.datum(
                    0
                ),
            )
        )


        textos_delta_compacto = (
            alt.Chart(
                dados_delta_compacto
            )
            .mark_text(
                dx=alt.expr(
                    "datum.Variação >= 0 ? 5 : -5"
                ),
                align=alt.expr(
                    "datum.Variação >= 0 ? 'left' : 'right'"
                ),
                fontSize=11,
            )
            .encode(
                y=escala_y(
                    ordem_delta_compacto
                ),
                x="Variação:Q",
                text=alt.Text(
                    "Variação:Q",
                    format=formatos[
                        "delta_cruz"
                    ],
                ),
            )
        )


        graf_delta_compacto = (
            barras_delta_compacto
            +
            textos_delta_compacto
            +
            linha_zero
            +
            regra_n2_delta()
            +
            regra_n1_delta()
        ).properties(
            width=max(
                340,
                largura_direita
                + 120,
            ),
            height=altura_delta,
            title=alt.TitleParams(
                text=titulo_delta,
                anchor="middle",
                fontSize=17,
                fontWeight="bold",
            ),
        )


        return (
            alt.hconcat(
                graf_n1_delta,
                graf_n2_delta,
                graf_delta_compacto,
                spacing=0,
            )
            .resolve_scale(
                y="shared"
            )
            .configure_view(
                stroke=None
            )
        )


    # ========================================================
    # MODO APENAS MÉDIAS
    # ========================================================

    if mostrar_medias and not mostrar_variacoes:

        return (
            alt.hconcat(
                graf_n1,
                graf_n2,
                graf_anos,
                graf_abs,
                spacing=0,
            )
            .resolve_scale(
                y="shared"
            )
            .configure_view(
                stroke=None
            )
        )


    return (
        alt.hconcat(
            graf_n1,
            graf_n2,
            graf_anos,
            graf_abs,
            graf_delta,
            spacing=0,
        )
        .resolve_scale(
            y="shared"
        )
        .configure_view(
            stroke=None
        )
    )


# ============================================================
# HISTÓRIA DO ANO — PREPARAÇÃO E GRÁFICOS DE FÓRMULA
# ============================================================

def _filtrar_integral_resultado_historia(
    resultado,
    variavel,
    incluir_integral_agregado,
    coluna_categoria="Categoria",
):

    if resultado.empty:

        return resultado


    if (
        variavel in VARIAVEIS_TIPO_ESCOLA
        and
        not incluir_integral_agregado
        and
        coluna_categoria in resultado.columns
    ):

        return (
            resultado[
                resultado[
                    coluna_categoria
                ].astype(str)
                != CATEGORIA_INTEGRAL_AGREGADA
            ]
            .copy()
        )


    return resultado


def _resumo_historia_uma_dimensao(
    base,
    indicador,
    ano,
    variavel,
    incluir_integral_agregado,
    incluir_consolidado=False,
):

    categorias = media_ponderada_por_categoria(
        df=base,
        indicador=indicador,
        anos=[ano],
        eixo_painel=variavel,
    )


    categorias = _filtrar_integral_resultado_historia(
        categorias,
        variavel,
        incluir_integral_agregado,
    )


    if incluir_consolidado:

        consolidado = calcular_consolidado(
            base,
            indicador,
            [ano],
        )


        return pd.concat(
            [
                consolidado,
                categorias,
            ],
            ignore_index=True,
        )


    return categorias.copy()


def _ordem_historia_uma_dimensao(
    resumo_ancora,
    variavel,
    ordenacao,
    ano,
):

    categorias = (
        resumo_ancora[
            resumo_ancora[
                "Categoria"
            ].astype(str)
            != "Consolidado"
        ][
            "Categoria"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


    if ordenacao == "Ordem para gráfico":

        return ordenar_dimensao_para_grafico(
            categorias,
            variavel,
        )


    ranking = (
        resumo_ancora[
            (
                resumo_ancora[
                    "Categoria"
                ].astype(str)
                != "Consolidado"
            )
            &
            (
                resumo_ancora[
                    "Ano"
                ].astype(str)
                == str(ano)
            )
        ]
        .dropna(
            subset=[
                "Média"
            ]
        )
        .sort_values(
            "Média",
            ascending=False,
        )[
            "Categoria"
        ]
        .astype(str)
        .tolist()
    )


    for categoria in categorias:

        if categoria not in ranking:

            ranking.append(
                categoria
            )


    return ranking


def _aplicar_medias_historia_uma_dimensao(
    plot_base,
    resumo,
):

    mapa = {
        str(categoria): media
        for categoria, media
        in zip(
            resumo[
                "Categoria"
            ],
            resumo[
                "Média"
            ],
        )
        if pd.notna(
            categoria
        )
    }


    resultado = plot_base.copy()

    resultado[
        "Média"
    ] = np.nan


    mascara = (
        resultado[
            "TipoLinha"
        ]
        == "ano"
    )


    resultado.loc[
        mascara,
        "Média",
    ] = (
        resultado.loc[
            mascara,
            "Categoria",
        ]
        .astype(str)
        .map(
            mapa
        )
    )


    return resultado


def _preparar_bloco_historia_uma_dimensao(
    base,
    ano,
    variavel,
    ordenacao,
    indicadores,
    incluir_integral_agregado,
    incluir_consolidado=False,
):

    indicador_ancora = indicadores[0]


    resumos = {
        indicador: _resumo_historia_uma_dimensao(
            base=base,
            indicador=indicador,
            ano=ano,
            variavel=variavel,
            incluir_integral_agregado=(
                incluir_integral_agregado
            ),
            incluir_consolidado=(
                incluir_consolidado
            ),
        )
        for indicador
        in indicadores
    }


    resumo_ancora = resumos[
        indicador_ancora
    ]


    if resumo_ancora.empty:

        return None


    ordem_categorias = _ordem_historia_uma_dimensao(
        resumo_ancora=resumo_ancora,
        variavel=variavel,
        ordenacao=ordenacao,
        ano=ano,
    )


    (
        plot_base,
        labels_categorias,
        labels_anos,
        ordem_linhas,
    ) = preparar_linhas_horizontais(
        dados=resumo_ancora,
        anos=[ano],
        categorias=ordem_categorias,
        ano_inicial=None,
        ano_final=ano,
    )


    plots = {
        indicador: _aplicar_medias_historia_uma_dimensao(
            plot_base,
            resumo,
        )
        for indicador, resumo
        in resumos.items()
    }


    return {
        "plot_base": plot_base,
        "plots": plots,
        "labels_categorias": labels_categorias,
        "labels_anos": labels_anos,
        "ordem_linhas": ordem_linhas,
    }


def _resumo_historia_duas_dimensoes(
    base,
    indicador,
    ano,
    variavel_1,
    variavel_2,
    incluir_integral_agregado,
    incluir_consolidado=False,
):

    resultado = media_ponderada_duas_dimensoes(
        base=base,
        indicador=indicador,
        anos=[ano],
        variavel_1=variavel_1,
        variavel_2=variavel_2,
        incluir_integral_agregado=(
            incluir_integral_agregado
        ),
    )


    if incluir_consolidado:

        consolidado = calcular_consolidado(
            base,
            indicador,
            [ano],
        )

    else:

        consolidado = pd.DataFrame(
            columns=[
                "Ano",
                "Categoria",
                "Média",
                "N escolas",
                "Matrículas",
            ]
        )


    return resultado, consolidado


def _ordens_historia_duas_dimensoes(
    resultado_ancora,
    variavel_1,
    variavel_2,
    ordenacao,
    ano,
):

    ordem_nivel_1 = ordenar_dimensao(
        resultado_ancora[
            "Categoria_1"
        ]
        .dropna()
        .unique(),
        variavel_1,
    )


    ordem_nivel_2 = ordenar_dimensao(
        resultado_ancora[
            "Categoria_2"
        ]
        .dropna()
        .unique(),
        variavel_2,
    )


    if ordenacao == "Ordem para gráfico":

        ordem_nivel_1 = ordenar_dimensao_para_grafico(
            resultado_ancora[
                "Categoria_1"
            ]
            .dropna()
            .astype(str)
            .unique(),
            variavel_1,
        )


        ordem_nivel_2 = ordenar_dimensao_para_grafico(
            resultado_ancora[
                "Categoria_2"
            ]
            .dropna()
            .astype(str)
            .unique(),
            variavel_2,
        )


        return (
            ordem_nivel_1,
            ordem_nivel_2,
        )


    ranking_n1 = (
        resultado_ancora[
            resultado_ancora[
                "Ano"
            ].astype(str)
            == str(ano)
        ]
        .groupby(
            "Categoria_1",
            as_index=False,
        )[
            "Média"
        ]
        .mean()
        .sort_values(
            "Média",
            ascending=False,
        )
    )


    ordem_temp = (
        ranking_n1[
            "Categoria_1"
        ]
        .astype(str)
        .tolist()
    )


    ordem_nivel_1 = (
        ordem_temp
        +
        [
            valor
            for valor
            in ordem_nivel_1
            if valor
            not in ordem_temp
        ]
    )


    return (
        ordem_nivel_1,
        ordem_nivel_2,
    )


def _aplicar_medias_historia_duas_dimensoes(
    plot_base,
    resultado,
    consolidado,
):

    mapa = {}


    for _, linha in resultado.iterrows():

        mapa[
            (
                str(
                    linha[
                        "Categoria_1"
                    ]
                ),
                str(
                    linha[
                        "Categoria_2"
                    ]
                ),
            )
        ] = linha[
            "Média"
        ]


    if not consolidado.empty:

        mapa[
            (
                "Consolidado",
                "Total",
            )
        ] = consolidado[
            "Média"
        ].iloc[0]


    resultado_plot = plot_base.copy()

    resultado_plot[
        "Média"
    ] = np.nan


    mascara = (
        resultado_plot[
            "TipoLinha"
        ]
        == "ano"
    )


    chaves = list(
        zip(
            resultado_plot.loc[
                mascara,
                "Nivel1",
            ].astype(str),
            resultado_plot.loc[
                mascara,
                "Nivel2",
            ].astype(str),
        )
    )


    resultado_plot.loc[
        mascara,
        "Média",
    ] = [
        mapa.get(
            chave,
            np.nan,
        )
        for chave
        in chaves
    ]


    return resultado_plot


def _preparar_bloco_historia_duas_dimensoes(
    base,
    ano,
    variavel_1,
    variavel_2,
    ordenacao,
    indicadores,
    incluir_integral_agregado,
    incluir_consolidado=False,
):

    resumos = {}


    for indicador in indicadores:

        resumos[
            indicador
        ] = _resumo_historia_duas_dimensoes(
            base=base,
            indicador=indicador,
            ano=ano,
            variavel_1=variavel_1,
            variavel_2=variavel_2,
            incluir_integral_agregado=(
                incluir_integral_agregado
            ),
            incluir_consolidado=(
                incluir_consolidado
            ),
        )


    resultado_ancora, consolidado_ancora = (
        resumos[
            indicadores[0]
        ]
    )


    if resultado_ancora.empty:

        return None


    (
        ordem_nivel_1,
        ordem_nivel_2,
    ) = _ordens_historia_duas_dimensoes(
        resultado_ancora=resultado_ancora,
        variavel_1=variavel_1,
        variavel_2=variavel_2,
        ordenacao=ordenacao,
        ano=ano,
    )


    (
        plot_base,
        labels_nivel_1,
        labels_nivel_2,
        labels_anos,
        ordem_linhas,
    ) = preparar_linhas_cruzamentos(
        resultado=resultado_ancora,
        consolidado=consolidado_ancora,
        anos=[ano],
        ordem_nivel_1=ordem_nivel_1,
        ordem_nivel_2=ordem_nivel_2,
        ano_inicial=None,
        ano_final=ano,
    )


    plots = {}


    for indicador, (
        resultado,
        consolidado,
    ) in resumos.items():

        plots[
            indicador
        ] = _aplicar_medias_historia_duas_dimensoes(
            plot_base=plot_base,
            resultado=resultado,
            consolidado=consolidado,
        )


    return {
        "plot_base": plot_base,
        "plots": plots,
        "labels_nivel_1": labels_nivel_1,
        "labels_nivel_2": labels_nivel_2,
        "labels_anos": labels_anos,
        "ordem_linhas": ordem_linhas,
    }


def _grafico_parentese_formula(
    simbolo,
    altura,
    largura=34,
):

    dados = pd.DataFrame(
        {
            "simbolo": [
                simbolo
            ]
        }
    )


    # O tamanho acompanha a altura do bloco, para o parêntese
    # enquadrar visualmente todas as barras da fórmula.
    tamanho_fonte = max(
        110,
        int(
            altura
            * 0.82
        ),
    )


    return (
        alt.Chart(
            dados
        )
        .mark_text(
            fontSize=tamanho_fonte,
            fontWeight=300,
            color="#64748B",
            baseline="middle",
            align="center",
        )
        .encode(
            x=alt.value(
                largura
                / 2
            ),
            y=alt.value(
                altura
                / 2
            ),
            text="simbolo:N",
        )
        .properties(
            width=largura,
            height=altura,
        )
    )


def _grafico_simbolo_formula(
    simbolo,
    altura,
    largura=None,
):

    # Tokens compostos usados na segunda fórmula da História do Ano.
    # Os parênteses são renderizados separadamente para poderem ocupar
    # praticamente toda a altura do conjunto de barras.
    if simbolo == "= (":

        return alt.hconcat(
            _grafico_simbolo_formula(
                "=",
                altura=altura,
                largura=38,
            ),
            _grafico_parentese_formula(
                "(",
                altura=altura,
                largura=34,
            ),
            spacing=0,
        )


    if simbolo == ") ÷ 2":

        return alt.hconcat(
            _grafico_parentese_formula(
                ")",
                altura=altura,
                largura=34,
            ),
            _grafico_simbolo_formula(
                "÷ 2",
                altura=altura,
                largura=58,
            ),
            spacing=0,
        )


    if largura is None:

        largura = max(
            42,
            14 * len(str(simbolo)) + 14,
        )


    dados = pd.DataFrame(
        {
            "simbolo": [
                simbolo
            ]
        }
    )


    return (
        alt.Chart(
            dados
        )
        .mark_text(
            fontSize=27,
            fontWeight=700,
            color="#64748B",
            baseline="middle",
            align="center",
        )
        .encode(
            x=alt.value(
                largura
                / 2
            ),
            y=alt.value(
                altura
                / 2
            ),
            text="simbolo:N",
        )
        .properties(
            width=largura,
            height=altura,
        )
    )


def _grafico_metrica_historia_uma_dimensao(
    plot,
    ordem_linhas,
    indicador,
    ano,
    largura=245,
):

    formatos = formatos_indicador(
        indicador
    )


    altura = max(
        260,
        len(
            plot
        )
        * 19,
    )


    separador_pequeno = (
        plot[
            plot[
                "TipoLinha"
            ]
            == "separador_pequeno"
        ]
    )


    separador_grande = (
        plot[
            plot[
                "TipoLinha"
            ]
            == "separador_grande"
        ]
    )


    regra_fina = (
        alt.Chart(
            separador_pequeno
        )
        .mark_rule(
            strokeWidth=0.75,
            color="#E1E6EC",
        )
        .encode(
            y=escala_y(
                ordem_linhas
            )
        )
    )


    regra_grande = (
        alt.Chart(
            separador_grande
        )
        .mark_rule(
            strokeWidth=1.15,
            color="#C9D1DA",
        )
        .encode(
            y=escala_y(
                ordem_linhas
            )
        )
    )


    dados = (
        plot[
            (
                plot[
                    "TipoLinha"
                ]
                == "ano"
            )
            &
            plot[
                "Média"
            ].notna()
        ]
    )


    barras = (
        alt.Chart(
            dados
        )
        .mark_bar(
            size=19,
            clip=True,
            color=CORES_ANOS[
                str(ano)
            ],
        )
        .encode(
            y=escala_y(
                ordem_linhas
            ),
            x=alt.X(
                "Média:Q",
                title=None,
                scale=alt.Scale(
                    domainMin=0,
                    zero=True,
                    nice=True,
                ),
                axis=alt.Axis(
                    labels=False,
                    ticks=False,
                    domain=False,
                    grid=False,
                ),
            ),
            x2=alt.datum(
                0
            ),
            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title="Categoria",
                ),
                alt.Tooltip(
                    "Média:Q",
                    title=indicador,
                    format=formatos[
                        "tooltip"
                    ],
                ),
            ],
        )
    )


    textos = (
        alt.Chart(
            dados
        )
        .mark_text(
            align="left",
            dx=4,
            fontSize=11,
        )
        .encode(
            y=escala_y(
                ordem_linhas
            ),
            x="Média:Q",
            text=alt.Text(
                "Média:Q",
                format=formatos[
                    "rotulo"
                ],
            ),
        )
    )


    return (
        barras
        +
        textos
        +
        regra_fina
        +
        regra_grande
    ).properties(
        width=largura,
        height=altura,
        title=alt.TitleParams(
            text=(
                f"Média ponderada de "
                f"{indicador}"
            ),
            anchor="middle",
            fontSize=15.5,
            fontWeight="bold",
        ),
    )


def _montar_formula_historia_uma_dimensao(
    bloco,
    indicadores,
    simbolos,
    ano,
    titulo_formula,
    largura_categoria=155,
    largura_anos=105,
    largura_metrica=245,
):

    plot_base = bloco[
        "plot_base"
    ]

    ordem_linhas = bloco[
        "ordem_linhas"
    ]


    altura = max(
        260,
        len(
            plot_base
        )
        * 19,
    )


    separador_pequeno = (
        plot_base[
            plot_base[
                "TipoLinha"
            ]
            == "separador_pequeno"
        ]
    )


    separador_grande = (
        plot_base[
            plot_base[
                "TipoLinha"
            ]
            == "separador_grande"
        ]
    )


    def regra_fina():

        return (
            alt.Chart(
                separador_pequeno
            )
            .mark_rule(
                strokeWidth=0.75,
                color="#E1E6EC",
            )
            .encode(
                y=escala_y(
                    ordem_linhas
                )
            )
        )


    def regra_grande():

        return (
            alt.Chart(
                separador_grande
            )
            .mark_rule(
                strokeWidth=1.15,
                color="#C9D1DA",
            )
            .encode(
                y=escala_y(
                    ordem_linhas
                )
            )
        )


    graf_categoria = (
        alt.Chart(
            bloco[
                "labels_categorias"
            ]
        )
        .mark_text(
            align="right",
            baseline="middle",
            fontSize=13.5,
            fontWeight="bold",
        )
        .encode(
            y=escala_y(
                ordem_linhas
            ),
            x=alt.value(
                largura_categoria
                - 5
            ),
            text="CategoriaLabel:N",
        )
        +
        regra_fina()
        +
        regra_grande()
    ).properties(
        width=largura_categoria,
        height=altura,
    )


    graf_anos = (
        alt.Chart(
            bloco[
                "labels_anos"
            ]
        )
        .mark_text(
            align="center",
            baseline="middle",
            fontSize=11,
            color="#7B8498",
        )
        .encode(
            y=escala_y(
                ordem_linhas
            ),
            x=alt.value(
                largura_anos
                / 2
            ),
            text="AnoLabel:N",
        )
        +
        regra_fina()
        +
        regra_grande()
    ).properties(
        width=largura_anos,
        height=altura,
    )


    componentes = [
        graf_categoria,
        graf_anos,
    ]


    for indice, indicador in enumerate(
        indicadores
    ):

        componentes.append(
            _grafico_metrica_historia_uma_dimensao(
                plot=bloco[
                    "plots"
                ][
                    indicador
                ],
                ordem_linhas=ordem_linhas,
                indicador=indicador,
                ano=ano,
                largura=largura_metrica,
            )
        )


        if indice < len(
            simbolos
        ):

            componentes.append(
                _grafico_simbolo_formula(
                    simbolos[
                        indice
                    ],
                    altura=altura,
                )
            )


    return (
        alt.hconcat(
            *componentes,
            spacing=0,
        )
        .resolve_scale(
            y="shared"
        )
        .properties(
            title=alt.TitleParams(
                text=titulo_formula,
                anchor="middle",
                fontSize=19,
                fontWeight=700,
                color="#27364A",
            )
        )
    )


def _grafico_metrica_historia_duas_dimensoes(
    plot,
    ordem_linhas,
    indicador,
    ano,
    largura=225,
):

    formatos = formatos_indicador(
        indicador
    )


    altura = max(
        290,
        len(
            plot
        )
        * 18,
    )


    separadores_n2 = (
        plot[
            plot[
                "TipoLinha"
            ]
            == "separador_nivel_2"
        ]
    )


    separadores_n1 = (
        plot[
            plot[
                "TipoLinha"
            ]
            == "separador_nivel_1"
        ]
    )


    regra_n2 = (
        alt.Chart(
            separadores_n2
        )
        .mark_rule(
            strokeWidth=0.70,
            color="#E1E6EC",
        )
        .encode(
            y=escala_y(
                ordem_linhas
            )
        )
    )


    regra_n1 = (
        alt.Chart(
            separadores_n1
        )
        .mark_rule(
            strokeWidth=1.65,
            color="#C3CCD6",
        )
        .encode(
            y=escala_y(
                ordem_linhas
            )
        )
    )


    dados = (
        plot[
            (
                plot[
                    "TipoLinha"
                ]
                == "ano"
            )
            &
            plot[
                "Média"
            ].notna()
        ]
    )


    barras = (
        alt.Chart(
            dados
        )
        .mark_bar(
            size=18,
            clip=True,
            color=CORES_ANOS[
                str(ano)
            ],
        )
        .encode(
            y=escala_y(
                ordem_linhas
            ),
            x=alt.X(
                "Média:Q",
                title=None,
                scale=alt.Scale(
                    domainMin=0,
                    zero=True,
                    nice=True,
                ),
                axis=alt.Axis(
                    labels=False,
                    ticks=False,
                    domain=False,
                    grid=False,
                ),
            ),
            x2=alt.datum(
                0
            ),
            tooltip=[
                alt.Tooltip(
                    "Nivel1:N",
                    title="1ª dimensão",
                ),
                alt.Tooltip(
                    "Nivel2:N",
                    title="2ª dimensão",
                ),
                alt.Tooltip(
                    "Média:Q",
                    title=indicador,
                    format=formatos[
                        "tooltip"
                    ],
                ),
            ],
        )
    )


    textos = (
        alt.Chart(
            dados
        )
        .mark_text(
            align="left",
            dx=4,
            fontSize=11,
        )
        .encode(
            y=escala_y(
                ordem_linhas
            ),
            x="Média:Q",
            text=alt.Text(
                "Média:Q",
                format=formatos[
                    "rotulo"
                ],
            ),
        )
    )


    return (
        barras
        +
        textos
        +
        regra_n2
        +
        regra_n1
    ).properties(
        width=largura,
        height=altura,
        title=alt.TitleParams(
            text=(
                f"Média ponderada de "
                f"{indicador}"
            ),
            anchor="middle",
            fontSize=15.5,
            fontWeight="bold",
        ),
    )


def _montar_formula_historia_duas_dimensoes(
    bloco,
    indicadores,
    simbolos,
    ano,
    titulo_formula,
    largura_nivel_1=115,
    largura_nivel_2=135,
    largura_anos=100,
    largura_metrica=225,
):

    plot_base = bloco[
        "plot_base"
    ]

    ordem_linhas = bloco[
        "ordem_linhas"
    ]


    altura = max(
        290,
        len(
            plot_base
        )
        * 18,
    )


    separadores_n2 = (
        plot_base[
            plot_base[
                "TipoLinha"
            ]
            == "separador_nivel_2"
        ]
    )


    separadores_n1 = (
        plot_base[
            plot_base[
                "TipoLinha"
            ]
            == "separador_nivel_1"
        ]
    )


    def regra_n2():

        return (
            alt.Chart(
                separadores_n2
            )
            .mark_rule(
                strokeWidth=0.70,
                color="#E1E6EC",
            )
            .encode(
                y=escala_y(
                    ordem_linhas
                )
            )
        )


    def regra_n1():

        return (
            alt.Chart(
                separadores_n1
            )
            .mark_rule(
                strokeWidth=1.65,
                color="#C3CCD6",
            )
            .encode(
                y=escala_y(
                    ordem_linhas
                )
            )
        )


    graf_n1 = (
        alt.Chart(
            bloco[
                "labels_nivel_1"
            ]
        )
        .mark_text(
            align="right",
            baseline="middle",
            fontSize=13.5,
            fontWeight="bold",
        )
        .encode(
            y=escala_y(
                ordem_linhas
            ),
            x=alt.value(
                largura_nivel_1
                - 4
            ),
            text="Label:N",
        )
        +
        regra_n1()
    ).properties(
        width=largura_nivel_1,
        height=altura,
    )


    graf_n2 = (
        alt.Chart(
            bloco[
                "labels_nivel_2"
            ]
        )
        .mark_text(
            align="right",
            baseline="middle",
            fontSize=12,
        )
        .encode(
            y=escala_y(
                ordem_linhas
            ),
            x=alt.value(
                largura_nivel_2
                - 4
            ),
            text="Label:N",
        )
        +
        regra_n2()
        +
        regra_n1()
    ).properties(
        width=largura_nivel_2,
        height=altura,
    )


    graf_anos = (
        alt.Chart(
            bloco[
                "labels_anos"
            ]
        )
        .mark_text(
            align="center",
            baseline="middle",
            fontSize=11,
            color="#7B8498",
        )
        .encode(
            y=escala_y(
                ordem_linhas
            ),
            x=alt.value(
                largura_anos
                / 2
            ),
            text="AnoLabel:N",
        )
        +
        regra_n2()
        +
        regra_n1()
    ).properties(
        width=largura_anos,
        height=altura,
    )


    componentes = [
        graf_n1,
        graf_n2,
        graf_anos,
    ]


    for indice, indicador in enumerate(
        indicadores
    ):

        componentes.append(
            _grafico_metrica_historia_duas_dimensoes(
                plot=bloco[
                    "plots"
                ][
                    indicador
                ],
                ordem_linhas=ordem_linhas,
                indicador=indicador,
                ano=ano,
                largura=largura_metrica,
            )
        )


        if indice < len(
            simbolos
        ):

            componentes.append(
                _grafico_simbolo_formula(
                    simbolos[
                        indice
                    ],
                    altura=altura,
                )
            )


    return (
        alt.hconcat(
            *componentes,
            spacing=0,
        )
        .resolve_scale(
            y="shared"
        )
        .properties(
            title=alt.TitleParams(
                text=titulo_formula,
                anchor="middle",
                fontSize=19,
                fontWeight=700,
                color="#27364A",
            )
        )
    )



# ============================================================
# MAPA DE CALOR — TRANSIÇÃO ENTRE CATEGORIAS
# ============================================================

def _preparar_base_mapa_calor(
    base,
    indicador,
    variavel,
    ano_inicial,
    ano_final,
):

    peso = "Matrículas EM (total) 3/4"


    def preparar_ano(ano, sufixo):

        recorte = (
            base[
                base["Ano"] == ano
            ]
            .drop_duplicates("Cód. INEP")
            .copy()
        )


        if recorte.empty:

            return pd.DataFrame()


        categorias = criar_variavel_eixo(
            recorte,
            variavel,
        )


        recorte[f"Categoria_{sufixo}"] = (
            categorias["Categoria"].values
        )


        recorte[f"Indicador_{sufixo}"] = pd.to_numeric(
            recorte[indicador],
            errors="coerce",
        )


        recorte[f"Peso_{sufixo}"] = (
            pd.to_numeric(
                recorte[peso],
                errors="coerce",
            )
            .fillna(0)
            .clip(lower=0)
        )


        return recorte[
            [
                "Cód. INEP",
                f"Categoria_{sufixo}",
                f"Indicador_{sufixo}",
                f"Peso_{sufixo}",
            ]
        ].copy()


    base_inicial = preparar_ano(
        ano_inicial,
        "inicial",
    )

    base_final = preparar_ano(
        ano_final,
        "final",
    )


    if base_inicial.empty or base_final.empty:

        return pd.DataFrame()


    cruzada = base_inicial.merge(
        base_final,
        on="Cód. INEP",
        how="inner",
        validate="one_to_one",
    )


    cruzada = cruzada[
        cruzada["Categoria_inicial"].notna()
        &
        cruzada["Categoria_final"].notna()
    ].copy()


    cruzada["Categoria_inicial"] = (
        cruzada["Categoria_inicial"].astype(str)
    )

    cruzada["Categoria_final"] = (
        cruzada["Categoria_final"].astype(str)
    )


    cruzada["Delta"] = (
        cruzada["Indicador_final"]
        -
        cruzada["Indicador_inicial"]
    )


    return cruzada


def _media_ponderada_segura_mapa(
    dados,
    coluna_valor,
    coluna_peso,
):

    valores = pd.to_numeric(
        dados[coluna_valor],
        errors="coerce",
    )

    pesos = pd.to_numeric(
        dados[coluna_peso],
        errors="coerce",
    )


    validos = (
        valores.notna()
        &
        pesos.notna()
        &
        (pesos > 0)
    )


    if not validos.any():

        return np.nan


    return float(
        np.average(
            valores[validos],
            weights=pesos[validos],
        )
    )


def _valor_recorte_mapa(
    dados,
    tipo,
):

    if dados.empty:

        return np.nan


    if tipo == "media_inicial":

        return _media_ponderada_segura_mapa(
            dados,
            "Indicador_inicial",
            "Peso_inicial",
        )


    if tipo == "media_final":

        return _media_ponderada_segura_mapa(
            dados,
            "Indicador_final",
            "Peso_final",
        )


    if tipo == "delta":

        return _media_ponderada_segura_mapa(
            dados,
            "Delta",
            "Peso_final",
        )


    if tipo == "escolas":

        return float(
            dados["Cód. INEP"].nunique()
        )


    if tipo == "matriculas":

        pesos = pd.to_numeric(
            dados["Peso_final"],
            errors="coerce",
        )

        return float(
            pesos[
                pesos.notna()
                &
                (pesos > 0)
            ].sum()
        )


    return np.nan


def _formatar_valor_mapa_calor(
    valor,
    tipo,
    indicador,
):

    if pd.isna(valor):

        return "—"


    if tipo in {
        "escolas",
        "matriculas",
    }:

        return (
            f"{int(round(float(valor))):,}"
            .replace(",", ".")
        )


    if indicador == "Rendimento":

        numero = float(valor) * 100

        if tipo == "delta":

            return (
                f"{numero:+.1f} p.p."
                .replace(".", ",")
            )

        return (
            f"{numero:.1f}%"
            .replace(".", ",")
        )


    if tipo == "delta":

        return (
            f"{float(valor):+.1f}"
            .replace(".", ",")
        )


    return (
        f"{float(valor):.1f}"
        .replace(".", ",")
    )


def _montar_dados_matriz_mapa(
    base_cruzada,
    categorias,
    tipo,
    indicador,
):

    registros = []
    categorias_com_total = [
        *categorias,
        "Consolidado",
    ]


    for categoria_linha in categorias_com_total:

        for categoria_coluna in categorias_com_total:

            recorte = base_cruzada


            if categoria_linha != "Consolidado":

                recorte = recorte[
                    recorte["Categoria_inicial"]
                    == categoria_linha
                ]


            if categoria_coluna != "Consolidado":

                recorte = recorte[
                    recorte["Categoria_final"]
                    == categoria_coluna
                ]


            valor = _valor_recorte_mapa(
                recorte,
                tipo,
            )


            registros.append(
                {
                    "Linha": categoria_linha,
                    "Coluna": categoria_coluna,
                    "Valor": valor,
                    "Rotulo": _formatar_valor_mapa_calor(
                        valor,
                        tipo,
                        indicador,
                    ),
                    "Consolidado": (
                        categoria_linha == "Consolidado"
                        or
                        categoria_coluna == "Consolidado"
                    ),
                }
            )


    return pd.DataFrame(registros)


def _criar_matriz_mapa_calor(
    dados,
    categorias,
    titulo,
    subtitulo=None,
    mostrar_rotulos_linhas=True,
):

    ordem = [
        *categorias,
        "Consolidado",
    ]


    dados_normais = dados[
        ~dados["Consolidado"]
        &
        dados["Valor"].notna()
    ]


    if dados_normais.empty:

        dominio_cor = [0.0, 1.0]

    else:

        minimo = float(
            dados_normais["Valor"].min()
        )

        maximo = float(
            dados_normais["Valor"].max()
        )


        if np.isclose(minimo, maximo):

            margem = max(
                abs(minimo) * 0.05,
                0.01,
            )

            dominio_cor = [
                minimo - margem,
                maximo + margem,
            ]

        else:

            dominio_cor = [
                minimo,
                maximo,
            ]


    # Mantém as matrizes compactas o suficiente para três gráficos lado a
    # lado, sem sacrificar a leitura quando exportadas para apresentação.
    tamanho_celula = 40
    tamanho = max(
        270,
        min(
            360,
            len(ordem) * tamanho_celula,
        ),
    )


    base_chart = alt.Chart(dados)


    retangulos = (
        base_chart
        .mark_rect(
            stroke="#F8FAFC",
            strokeWidth=1.5,
        )
        .encode(
            x=alt.X(
                "Coluna:N",
                sort=ordem,
                title=None,
                axis=alt.Axis(
                    orient="top",
                    labelAngle=-35,
                    labelFontSize=10.5,
                    labelFontWeight=600,
                    labelColor="#536278",
                    labelLimit=135,
                    labelPadding=7,
                    ticks=False,
                    domain=False,
                ),
            ),
            y=alt.Y(
                "Linha:N",
                sort=ordem,
                title=None,
                axis=alt.Axis(
                    labels=mostrar_rotulos_linhas,
                    labelFontSize=10.5,
                    labelFontWeight=600,
                    labelColor="#536278",
                    labelLimit=155,
                    labelPadding=7,
                    ticks=False,
                    domain=False,
                ),
            ),
            color=alt.condition(
                "datum.Consolidado === true",
                alt.value("#E4E9EF"),
                alt.Color(
                    "Valor:Q",
                    scale=alt.Scale(
                        domain=[
                            dominio_cor[0],
                            (dominio_cor[0] + dominio_cor[1]) / 2,
                            dominio_cor[1],
                        ],
                        range=[
                            "#DDA0A0",
                            "#F3EFE9",
                            "#8CB198",
                        ],
                    ),
                    legend=None,
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "Linha:N",
                    title="Categoria — 1º ano",
                ),
                alt.Tooltip(
                    "Coluna:N",
                    title="Categoria — 2º ano",
                ),
                alt.Tooltip(
                    "Rotulo:N",
                    title="Valor",
                ),
            ],
        )
    )


    textos = (
        base_chart
        .mark_text(
            fontSize=11.2,
            fontWeight=600,
            color="#243447",
        )
        .encode(
            x=alt.X(
                "Coluna:N",
                sort=ordem,
            ),
            y=alt.Y(
                "Linha:N",
                sort=ordem,
            ),
            text="Rotulo:N",
        )
    )


    return (
        retangulos
        +
        textos
    ).properties(
        width=tamanho,
        height=tamanho,
        title=alt.TitleParams(
            text=titulo,
            subtitle=(
                [subtitulo]
                if subtitulo
                else None
            ),
            anchor="middle",
            fontSize=15.5,
            fontWeight=700,
            color="#27364A",
            subtitleFontSize=10.5,
            subtitleFontWeight=400,
            subtitleColor="#6B7A90",
            offset=10,
        ),
    )


# ============================================================
# CARREGAMENTO
# ============================================================

try:

    df_completo = preparar_base()
    df_completo = _garantir_tipo_escola_2025(df_completo)


except Exception as erro:

    st.error(
        "Não foi possível carregar os dados."
    )

    st.exception(
        erro
    )

    st.stop()


# ============================================================
# TÍTULO
# ============================================================

st.markdown(
    """
    <div class="panel-main-title">
        Painel IDEB
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# COMPATIBILIDADE DE SESSÃO — RENOME DA DIMENSÃO
# ============================================================

# Usuários que já estavam com o painel aberto podem carregar no
# session_state o nome antigo da dimensão. A migração evita que um
# selectbox permaneça apontando para uma opção que não existe mais.
for chave_dimensao in [
    "variavel_1_distribuicoes",
    "variavel_2_distribuicoes",
    "variavel_distrib_agregado",
    "cruz_var_1",
    "cruz_var_2",
    "historia_var_1",
    "historia_var_2",
    "mapa_variavel",
    "demo_variavel_barras",
    "demo_variavel_comp",
]:

    if (
        st.session_state.get(chave_dimensao)
        == "Tipo de Escola"
    ):

        st.session_state[chave_dimensao] = (
            "Tipo de Escola por ano"
        )


# ============================================================
# NAVEGAÇÃO
# ============================================================

if "pagina" not in st.session_state:

    st.session_state.pagina = (
        "PRINCIPAIS INDICADORES"
    )


nav_0, nav_1, nav_2, nav_3, nav_4, nav_5, nav_6, nav_7 = st.columns(
    [
        1.02,
        0.98,
        1.06,
        1.00,
        0.92,
        1.30,
        0.98,
        0.88,
    ],
    gap="small",
)


with nav_0:

    if st.button(
        "DICIONÁRIO",
        width="stretch",
        key="nav_dicionario",
        help=(
            "Consulte as definições dos indicadores, dimensões, filtros e "
            "variáveis de apoio usados no painel."
        ),
    ):

        st.session_state.pagina = (
            "DICIONÁRIO DE VARIÁVEIS"
        )


with nav_1:

    if st.button(
        "INDICADORES",
        width="stretch",
        key="nav_principais",
        help=(
            "Compare médias ponderadas e variações dos indicadores entre "
            "categorias, anos e diferentes recortes."
        ),
    ):

        st.session_state.pagina = (
            "PRINCIPAIS INDICADORES"
        )


with nav_2:

    if st.button(
        "DECOMPOSIÇÃO",
        width="stretch",
        key="nav_historia_ano",
        help=(
            "Entenda como os componentes de desempenho e rendimento se "
            "combinam para formar o IDEB de um ano."
        ),
    ):

        st.session_state.pagina = (
            "HISTÓRIA DO ANO"
        )


with nav_3:

    if st.button(
        "COMPOSIÇÃO",
        width="stretch",
        key="nav_demografia",
        help=(
            "Explore como escolas e matrículas se distribuem entre "
            "diferentes categorias e perfis."
        ),
    ):

        st.session_state.pagina = (
            "DEMOGRAFIA"
        )


with nav_4:

    if st.button(
        "DISPERSÃO",
        width="stretch",
        key="nav_distribuicoes",
        help=(
            "Analise a distribuição dos resultados entre escolas, compare "
            "grupos e avalie diferenças estatísticas."
        ),
    ):

        st.session_state.pagina = (
            "DISTRIBUIÇÕES"
        )


with nav_5:

    if st.button(
        "MELHORES ESCOLAS",
        width="stretch",
        key="nav_melhores",
        help=(
            "Explore as escolas com maiores resultados ou maiores variações "
            "nos indicadores selecionados."
        ),
    ):

        st.session_state.pagina = (
            "MELHORES ESCOLAS"
        )


with nav_6:

    if st.button(
        "TRANSIÇÕES",
        width="stretch",
        key="nav_mapa_calor",
        help=(
            "Veja como as escolas mudam de categoria entre dois anos e "
            "compare resultados, variações e volumes em cada trajetória."
        ),
    ):

        st.session_state.pagina = (
            "MAPA DE CALOR"
        )


with nav_7:

    if st.button(
        "INSIGHTS",
        width="stretch",
        key="nav_insights",
        help=(
            "Seção reservada para sínteses e achados analíticos do painel."
        ),
    ):

        st.session_state.pagina = (
            "INSIGHTS"
        )


pagina = (
    st.session_state.pagina
)


# ============================================================
# DESTAQUE DA PÁGINA ATIVA NA NAVEGAÇÃO
# ============================================================

chave_nav_ativa = {
    "DICIONÁRIO DE VARIÁVEIS": "nav_dicionario",
    "PRINCIPAIS INDICADORES": "nav_principais",
    "HISTÓRIA DO ANO": "nav_historia_ano",
    "DEMOGRAFIA": "nav_demografia",
    "DISTRIBUIÇÕES": "nav_distribuicoes",
    "MELHORES ESCOLAS": "nav_melhores",
    "MAPA DE CALOR": "nav_mapa_calor",
    "INSIGHTS": "nav_insights",
}.get(
    pagina
)


if chave_nav_ativa:

    st.markdown(
        f"""
        <style>
            .st-key-{chave_nav_ativa} button {{
                background-color: #E3F2E6 !important;
                border-color: #B7DABD !important;
                color: #245C2D !important;
                font-weight: 700 !important;
            }}

            .st-key-{chave_nav_ativa} button:hover {{
                background-color: #D8EDDC !important;
                border-color: #91C99B !important;
                color: #1F5127 !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# FILTROS
# ============================================================

st.sidebar.markdown(
    "### Filtros"
)


st.sidebar.button(
    "Limpar filtros",
    width="stretch",
    on_click=limpar_todos_os_filtros,
    key="limpar_todos_filtros",
)


same_schools_ativo = st.sidebar.toggle(
    "SAME SCHOOLS",
    value=False,
    key="filtro_same_schools",
)


# Seleção cumulativa (lógica E) de participação no IDEB.
# Se mais de um ano for marcado, a escola precisa ter resultado
# em TODOS os anos selecionados para permanecer no universo.
st.sidebar.markdown(
    "**Considerar apenas escolas do IDEB em:**"
)

anos_ideb_obrigatorios = []

for ano in ANOS_PAINEL:

    if st.sidebar.checkbox(
        str(ano),
        value=False,
        key=f"filtro_considerar_ideb_{ano}",
    ):

        anos_ideb_obrigatorios.append(
            ano
        )


# SAME SCHOOLS usa exclusivamente o indicador Same_Schools da aba
# ESCOLAS_CONSOLIDADO: 1 = entra no universo; 0 = não entra.
# A coluna Transicao NÃO define o universo. Ela fornece apenas as
# categorias exibidas no painel como "Categorias Same Schools".
df_base_filtros = df_completo.copy()


if same_schools_ativo:

    if "Same_Schools" not in df_base_filtros.columns:

        st.error(
            "Não foi possível carregar a coluna Same_Schools "
            "da aba ESCOLAS_CONSOLIDADO."
        )
        st.stop()


    indicador_same_schools = pd.to_numeric(
        df_base_filtros[
            "Same_Schools"
        ],
        errors="coerce",
    )


    df_base_filtros = (
        df_base_filtros[
            indicador_same_schools.eq(1)
        ]
        .copy()
    )


# Aplica os anos obrigatórios de forma sequencial. Como cada etapa
# parte do resultado da anterior, múltiplas caixas marcadas têm
# comportamento de interseção (E), e não de união (OU).
for ano in anos_ideb_obrigatorios:

    df_base_filtros = (
        aplicar_filtro_participacao_ideb(
            df_base_filtros,
            ano,
            ["Sim"],
        )
    )


# Cor única do painel e dos gráficos conforme o universo selecionado.
# SAME SCHOOLS ligado  -> azul-claro.
# SAME SCHOOLS desligado -> branco.
COR_FUNDO_PAINEL = (
    "#EEF7FF"
    if same_schools_ativo
    else "#FFFFFF"
)

COR_FUNDO_HEADER = (
    "rgba(238, 247, 255, 0.96)"
    if same_schools_ativo
    else "rgba(255, 255, 255, 0.96)"
)

COR_FUNDO_SIDEBAR = (
    "#E8F2FB"
    if same_schools_ativo
    else "#F7F9FC"
)


st.markdown(
    f"""
    <style>
        .stApp,
        [data-testid="stAppViewContainer"] {{
            background-color: {COR_FUNDO_PAINEL} !important;
        }}

        [data-testid="stHeader"] {{
            background-color: {COR_FUNDO_HEADER} !important;
            backdrop-filter: blur(8px);
        }}

        section[data-testid="stSidebar"] {{
            background-color: {COR_FUNDO_SIDEBAR} !important;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


def aplicar_fundo_grafico(grafico):
    """Padroniza o visual dos gráficos e sincroniza o fundo com SAME SCHOOLS.

    A configuração é aplicada no nível superior para que o mesmo gráfico
    mantenha tipografia, espaçamento e contraste adequados quando exportado.
    """

    return (
        grafico
        .properties(
            background=COR_FUNDO_PAINEL,
        )
        .configure_view(
            stroke=None,
        )
        .configure_axis(
            labelFont="Segoe UI",
            titleFont="Segoe UI",
            labelColor="#536278",
            titleColor="#334155",
            labelFontSize=11.5,
            titleFontSize=12.5,
            titleFontWeight=600,
            domainColor="#CBD5E1",
            domainWidth=0.8,
            tickColor="#CBD5E1",
            tickWidth=0.8,
            gridColor="#E7ECF2",
            gridOpacity=0.72,
            labelPadding=6,
            titlePadding=10,
        )
        .configure_title(
            font="Segoe UI",
            color="#27364A",
            fontSize=17,
            fontWeight=700,
            subtitleFont="Segoe UI",
            subtitleColor="#6B7A90",
            subtitleFontSize=11,
            subtitleFontWeight=400,
            subtitlePadding=7,
            offset=12,
        )
        .configure_legend(
            labelFont="Segoe UI",
            titleFont="Segoe UI",
            labelColor="#536278",
            titleColor="#334155",
            labelFontSize=11.5,
            titleFontSize=11.5,
            titleFontWeight=600,
            symbolSize=85,
        )
    )


filtros = {}


# Mantém apenas um pequeno respiro entre os grupos, sem linhas ou títulos.
def espaco_filtros_sidebar():

    st.sidebar.markdown(
        '<div style="height:0.24rem"></div>',
        unsafe_allow_html=True,
    )


# Renderização padronizada dos filtros categóricos.
def renderizar_filtro_categorico(nome):

    opcoes = obter_opcoes_filtro(
        df_base_filtros,
        nome,
    )


    placeholder = (
        "Brasil"
        if nome
        == "Estado"
        else
        "Todos"
    )


    filtros[
        nome
    ] = (
        st.sidebar.multiselect(
            rotulo_dimensao(
                nome
            ),
            options=opcoes,
            placeholder=placeholder,
            key=f"filtro_{nome}",
        )
    )


# ============================================================
# BLOCO 1 — TIPO DE ESCOLA
# ============================================================

renderizar_filtro_categorico(
    "Tipo de Escola por ano"
)

renderizar_filtro_categorico(
    "Tipo de Escola 2025"
)


# ============================================================
# BLOCO 2 — LOCALIZAÇÃO
# ============================================================

espaco_filtros_sidebar()

renderizar_filtro_categorico(
    "Região do Brasil"
)

renderizar_filtro_categorico(
    "Estado"
)


# ============================================================
# BLOCO 3 — TRAJETÓRIA / INTEGRAL
# ============================================================

espaco_filtros_sidebar()

renderizar_filtro_categorico(
    "Categorias Same Schools"
)

renderizar_filtro_categorico(
    "1º IDEB 100% integral"
)

renderizar_filtro_categorico(
    "Carga horária"
)


# ============================================================
# BLOCO 4 — PERFIL
# ============================================================

espaco_filtros_sidebar()

renderizar_filtro_categorico(
    "PPI"
)

renderizar_filtro_categorico(
    "INSE"
)


# ============================================================
# BLOCO 5 — IDEB POR EDIÇÃO
# ============================================================

espaco_filtros_sidebar()

filtro_ideb = {}


for ano in ANOS_PAINEL:

    filtro_ideb[
        ano
    ] = (
        st.sidebar.multiselect(
            f"IDEB {ano}",
            options=[
                faixa
                for faixa
                in FAIXAS_IDEB
                if faixa
                != "Sem resultado"
            ],
            placeholder="Todos",
            key=f"filtro_ideb_{ano}",
        )
    )


# ============================================================
# BLOCO 6 — OFERTA
# ============================================================

espaco_filtros_sidebar()

filtro_proped = (
    st.sidebar.multiselect(
        "Propedêutico",
        options=[
            "Sim",
            "Não",
        ],
        placeholder="Todos",
        key="filtro_proped",
    )
)


filtro_ept = (
    st.sidebar.multiselect(
        "EPT",
        options=[
            "Sim",
            "Não",
        ],
        placeholder="Todos",
        key="filtro_ept",
    )
)


# ============================================================
# BLOCO 7 — CARACTERÍSTICAS DA ESCOLA
# ============================================================

espaco_filtros_sidebar()

renderizar_filtro_categorico(
    "Colégio Militar"
)

renderizar_filtro_categorico(
    "Colégio com Seleção"
)


# ============================================================
# FILTROS ADICIONAIS
#
# Caso novos filtros categóricos sejam adicionados futuramente à
# lista abaixo e não tenham sido organizados nos blocos anteriores,
# eles aparecem ao final, conforme a regra do painel.
# ============================================================

filtros_categoricos_existentes = [
    "Tipo de Escola por ano",
    "Tipo de Escola 2025",
    "PPI",
    "INSE",
    "Colégio Militar",
    "Colégio com Seleção",
    "Estado",
    "Região do Brasil",
    "1º IDEB 100% integral",
    "Carga horária",
    "Categorias Same Schools",
]


filtros_ja_renderizados = set(
    filtros.keys()
)


filtros_adicionais = [
    nome
    for nome
    in filtros_categoricos_existentes
    if nome
    not in filtros_ja_renderizados
]


if filtros_adicionais:

    espaco_filtros_sidebar()


    for nome in filtros_adicionais:

        renderizar_filtro_categorico(
            nome
        )


# ============================================================
# INTEGRAL AGREGADO
# ============================================================

def mostrar_integral_agregado_para(*variaveis):
    """Controla a categoria agregada de forma independente para cada
    variável de Tipo de Escola.

    Se o respectivo filtro estiver vazio, a categoria agregada pode ser
    exibida. Se o filtro estiver preenchido, ela só aparece quando tiver
    sido selecionada explicitamente.
    """

    for variavel in variaveis:

        if variavel not in VARIAVEIS_TIPO_ESCOLA:

            continue


        valores = filtros.get(
            variavel,
            [],
        )


        if (
            valores
            and
            CATEGORIA_INTEGRAL_AGREGADA
            not in valores
        ):

            return False


    return True


# Mantido como referência para trechos genéricos que trabalham apenas
# com a classificação anual. Os pontos que conhecem a dimensão escolhida
# usam mostrar_integral_agregado_para(...).
mostrar_integral_agregado = mostrar_integral_agregado_para(
    "Tipo de Escola por ano"
)


# ============================================================
# APLICA FILTROS
# ============================================================

try:

    df = aplicar_filtros_categoricos(
        df_base_filtros,
        filtros,
    )


    for ano, valores in filtro_ideb.items():

        df = (
            aplicar_filtro_participacao_ideb(
                df,
                ano,
                valores,
            )
        )


    if "Propedêutido" in df.columns:

        coluna_proped = (
            "Propedêutido"
        )

    elif "Propedêutico" in df.columns:

        coluna_proped = (
            "Propedêutico"
        )

    else:

        coluna_proped = (
            "Propedêutido"
        )


    df = aplicar_filtro_binario_coluna(
        df,
        coluna_proped,
        filtro_proped,
    )


    df = aplicar_filtro_binario_coluna(
        df,
        "EPT",
        filtro_ept,
    )


except Exception as erro:

    st.error(
        "Não foi possível aplicar os filtros."
    )

    st.exception(
        erro
    )

    st.stop()


# ============================================================
# DICIONÁRIO DE VARIÁVEIS
# ============================================================

def _tabela_dicionario_html(linhas):
    corpo = []

    for variavel, explicacao in linhas:
        corpo.append(
            "<tr>"
            f"<td>{html.escape(str(variavel))}</td>"
            f"<td>{html.escape(str(explicacao))}</td>"
            "</tr>"
        )

    return (
        '<div class="dictionary-table-wrap">'
        '<table class="dictionary-table">'
        '<thead><tr><th>Variável</th><th>O que representa no painel</th></tr></thead>'
        '<tbody>'
        + "".join(corpo)
        + '</tbody></table></div>'
    )


if pagina == "DICIONÁRIO DE VARIÁVEIS":

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:23px;
            font-weight:750;
            letter-spacing:-0.02em;
            color:#27364A;
            margin-bottom:0.25rem;
        ">
            DICIONÁRIO DE VARIÁVEIS
        </div>
        <div class="dictionary-intro">
            Versão preliminar das definições usadas no painel. O objetivo é
            tornar explícito o significado de cada indicador, dimensão e filtro
            para facilitar a leitura e a validação das análises.
        </div>
        """,
        unsafe_allow_html=True,
    )


    indicadores_dicionario = [
        (
            "IDEB",
            "Índice de Desenvolvimento da Educação Básica. No painel, corresponde ao produto entre N e Rendimento.",
        ),
        (
            "N(LP)",
            "Nota padronizada de Língua Portuguesa, convertida para a escala utilizada no cálculo do IDEB.",
        ),
        (
            "N(M)",
            "Nota padronizada de Matemática, convertida para a escala utilizada no cálculo do IDEB.",
        ),
        (
            "N",
            "Nota média padronizada de desempenho, calculada como a média aritmética simples entre N(LP) e N(M).",
        ),
        (
            "Rendimento",
            "Componente de rendimento/fluxo escolar utilizado no cálculo do IDEB.",
        ),
    ]


    dimensoes_dicionario = [
        (
            "Tipo de Escola por ano",
            "Classificação da escola em cada edição analisada: Parcial/Regular, Mista ou 100% Integral. A categoria agregada Integral (Mista + 100%) reúne Mistas e 100% Integrais.",
        ),
        (
            "Tipo de Escola 2025",
            "Classificação fixa da escola em 2025, aplicada também aos anos anteriores. Permite acompanhar ao longo do tempo o mesmo grupo definido pela situação da escola em 2025.",
        ),
        (
            "PPI",
            "Faixa PPI registrada para a escola, utilizada para segmentar o perfil racial dos estudantes.",
        ),
        (
            "INSE",
            "Faixa do Indicador de Nível Socioeconômico associada à escola.",
        ),
        (
            "Colégio Militar",
            "Indica se a escola está classificada como colégio militar na base.",
        ),
        (
            "Colégio com Seleção",
            "Indica se a escola possui processo de seleção de estudantes segundo a classificação disponível na base.",
        ),
        (
            "Estado",
            "Unidade da Federação (UF) da escola.",
        ),
        (
            "Região do Brasil",
            "Região geográfica do Brasil à qual pertence a escola.",
        ),
        (
            "1º IDEB 100% integral",
            "Primeira edição do IDEB em que a escola aparece classificada como 100% Integral.",
        ),
        (
            "Carga Horária",
            "Classificação de carga horária construída a partir dos registros de escola EMI 7h e EMI 9h: 7h, 9h, 7h + 9h ou Não se aplica.",
        ),
        (
            "Categorias Same Schools",
            "Categoria de trajetória da escola usada nas análises Same Schools, indicando transições entre classificações de tipo de escola.",
        ),
    ]


    for ano in ANOS_PAINEL:
        dimensoes_dicionario.append(
            (
                f"Faixa IDEB {ano}",
                (
                    f"Faixa do IDEB da escola em {ano}: IDEB < 3; 3 ≤ IDEB < 4; "
                    "4 ≤ IDEB < 5; 5 ≤ IDEB < 6; IDEB ≥ 6; ou Sem resultado."
                ),
            )
        )


    filtros_dicionario = [
        (
            "SAME SCHOOLS",
            "Quando ativado, restringe a análise às escolas marcadas na base consolidada como pertencentes ao conjunto Same Schools.",
        ),
        (
            "Considerar apenas escolas do IDEB em [ano]",
            "Mantém apenas escolas com resultado de IDEB no ano marcado. Quando vários anos são marcados, as condições são aplicadas simultaneamente (lógica E).",
        ),
        (
            "Propedêutico",
            "Permite filtrar as escolas conforme a marcação de oferta propedêutica disponível na base.",
        ),
        (
            "EPT",
            "Permite filtrar as escolas conforme a marcação de EPT disponível na base.",
        ),
    ]


    apoio_dicionario = [
        (
            "Ano",
            "Edição do IDEB considerada na análise. O painel trabalha com 2017, 2019, 2021, 2023 e 2025.",
        ),
        (
            "Matrículas",
            "Total de matrículas do Ensino Médio utilizado nas análises de volume e como peso das médias ponderadas do painel.",
        ),
        (
            "Nº de escolas",
            "Contagem de escolas consideradas em cada recorte após a aplicação das regras e filtros ativos.",
        ),
    ]


    st.markdown(
        '<div class="dictionary-section-title">Indicadores de resultado</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        _tabela_dicionario_html(indicadores_dicionario),
        unsafe_allow_html=True,
    )


    st.markdown(
        '<div class="dictionary-section-title">Dimensões de análise</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        _tabela_dicionario_html(dimensoes_dicionario),
        unsafe_allow_html=True,
    )


    st.markdown(
        '<div class="dictionary-section-title">Filtros complementares</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        _tabela_dicionario_html(filtros_dicionario),
        unsafe_allow_html=True,
    )


    st.markdown(
        '<div class="dictionary-section-title">Variáveis de apoio</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        _tabela_dicionario_html(apoio_dicionario),
        unsafe_allow_html=True,
    )


# ============================================================
# INSIGHTS — RACIONAL DE AGREGADOS EM DOIS NÍVEIS
# ============================================================

def obter_combinacoes_insights(
    base,
    dimensao_1,
    dimensao_2=None,
):
    """Retorna categorias ou combinações efetivamente observadas no recorte."""

    if base.empty:
        return []


    categorias_1 = criar_variavel_eixo(
        base,
        dimensao_1,
    )[
        "Categoria"
    ]


    # Quando a 2ª dimensão está vazia, cada opção dos agregados é
    # simplesmente uma categoria da 1ª dimensão. Mantemos o formato
    # de tupla para preservar a mesma estrutura interna usada no modo
    # de duas dimensões.
    if dimensao_2 is None:

        temp = pd.DataFrame(
            {
                "Nivel_1": categorias_1,
            },
            index=base.index,
        )

        temp = (
            temp[
                temp["Nivel_1"].notna()
            ]
            .astype(
                {
                    "Nivel_1": str,
                }
            )
            .drop_duplicates()
        )

        if temp.empty:
            return []

        ordem_1 = ordenar_dimensao(
            temp["Nivel_1"].unique().tolist(),
            dimensao_1,
        )

        indice_1 = {
            valor: posicao
            for posicao, valor
            in enumerate(ordem_1)
        }

        combinacoes = [
            (str(linha.Nivel_1), None)
            for linha
            in temp.itertuples(index=False)
        ]

        combinacoes.sort(
            key=lambda item: (
                indice_1.get(item[0], 10**6),
                item[0],
            )
        )

        return combinacoes


    categorias_2 = criar_variavel_eixo(
        base,
        dimensao_2,
    )[
        "Categoria"
    ]


    temp = pd.DataFrame(
        {
            "Nivel_1": categorias_1,
            "Nivel_2": categorias_2,
        },
        index=base.index,
    )


    temp = (
        temp[
            temp["Nivel_1"].notna()
            &
            temp["Nivel_2"].notna()
        ]
        .astype(
            {
                "Nivel_1": str,
                "Nivel_2": str,
            }
        )
        .drop_duplicates()
    )


    if temp.empty:
        return []


    ordem_1 = ordenar_dimensao(
        temp["Nivel_1"].unique().tolist(),
        dimensao_1,
    )


    ordem_2 = ordenar_dimensao(
        temp["Nivel_2"].unique().tolist(),
        dimensao_2,
    )


    indice_1 = {
        valor: posicao
        for posicao, valor
        in enumerate(ordem_1)
    }


    indice_2 = {
        valor: posicao
        for posicao, valor
        in enumerate(ordem_2)
    }


    combinacoes = [
        (
            str(linha.Nivel_1),
            str(linha.Nivel_2),
        )
        for linha
        in temp.itertuples(index=False)
    ]


    combinacoes.sort(
        key=lambda item: (
            indice_1.get(item[0], 10**6),
            indice_2.get(item[1], 10**6),
            item[0],
            item[1],
        )
    )


    return combinacoes



def rotulo_combinacao_insights(
    combinacao,
    dimensao_1,
    dimensao_2=None,
):

    nivel_1, nivel_2 = combinacao

    if dimensao_2 is None or nivel_2 is None:
        return (
            f"{rotulo_dimensao(dimensao_1)}: {nivel_1}"
        )

    return (
        f"{rotulo_dimensao(dimensao_1)}: {nivel_1}  ·  "
        f"{rotulo_dimensao(dimensao_2)}: {nivel_2}"
    )


def _html_resumo_agregado_insights(
    titulo,
    combinacoes,
    dimensao_1,
    dimensao_2,
):

    if not combinacoes:
        conteudo = (
            '<span style="color:#8290A3;">'
            'Nenhuma combinação selecionada.'
            '</span>'
        )

    else:
        itens = []

        for combinacao in combinacoes:
            itens.append(
                '<div style="margin:0.26rem 0;">'
                + html.escape(
                    rotulo_combinacao_insights(
                        combinacao,
                        dimensao_1,
                        dimensao_2,
                    )
                )
                + '</div>'
            )

        conteudo = "".join(itens)


    return f"""
        <div style="
            border:1px solid #E2E8F0;
            border-radius:12px;
            background:#FBFCFE;
            padding:0.9rem 1rem;
            min-height:104px;
        ">
            <div style="
                font-size:0.83rem;
                font-weight:700;
                color:#42526A;
                margin-bottom:0.45rem;
            ">{html.escape(titulo)}</div>
            <div style="
                font-size:0.82rem;
                line-height:1.45;
                color:#5D6B7E;
            ">{conteudo}</div>
        </div>
    """


# ============================================================
# INSIGHTS
# ============================================================

if pagina == "INSIGHTS":

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:23px;
            font-weight:750;
            letter-spacing:-0.02em;
            color:#27364A;
            margin-bottom:0.20rem;
        ">
            INSIGHTS
        </div>
        <div style="
            text-align:center;
            font-size:0.91rem;
            color:#6B7A90;
            margin-bottom:1.15rem;
        ">
            Construa grupos comparáveis a partir de uma dimensão ou de combinações de duas dimensões.
        </div>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        "### Racional de Agregado 1 vs Agregado 2"
    )


    st.caption(
        "Selecione uma dimensão e, se desejar, uma segunda. Com a 2ª dimensão em "
        "<vazio>, os agregados usam apenas as categorias da 1ª dimensão. Quando "
        "duas dimensões são escolhidas, cada opção representa uma combinação "
        "efetivamente observada no universo atualmente filtrado. A mesma opção "
        "não pode pertencer aos dois grupos."
    )


    opcoes_dimensoes_insights = list(
        EIXOS_DISPONIVEIS.keys()
    )


    col_dim_1, col_dim_2 = st.columns(2)


    with col_dim_1:

        dimensao_1_insights = st.selectbox(
            "1ª dimensão",
            options=opcoes_dimensoes_insights,
            index=(
                opcoes_dimensoes_insights.index(
                    "INSE"
                )
                if "INSE" in opcoes_dimensoes_insights
                else 0
            ),
            format_func=rotulo_dimensao,
            key="insights_dimensao_1",
        )


    SEM_ESCOLHA_INSIGHTS = "<vazio>"


    # Migração única da versão anterior: a 2ª dimensão passa a iniciar
    # vazia também para sessões que já estavam abertas antes desta mudança.
    if not st.session_state.get(
        "_insights_dimensao_2_v41_inicializada",
        False,
    ):
        st.session_state[
            "insights_dimensao_2"
        ] = SEM_ESCOLHA_INSIGHTS
        st.session_state[
            "_insights_dimensao_2_v41_inicializada"
        ] = True


    opcoes_dimensao_2_insights = [
        SEM_ESCOLHA_INSIGHTS,
        *[
            dimensao
            for dimensao
            in opcoes_dimensoes_insights
            if dimensao
            != dimensao_1_insights
        ],
    ]


    with col_dim_2:

        # Se a 1ª dimensão mudar para o valor que estava selecionado na
        # 2ª, removemos o estado antigo antes de recriar o selectbox.
        # O valor <vazio> permanece sempre válido.
        if (
            "insights_dimensao_2"
            in st.session_state
            and
            st.session_state[
                "insights_dimensao_2"
            ]
            not in opcoes_dimensao_2_insights
        ):

            st.session_state.pop(
                "insights_dimensao_2",
                None,
            )


        dimensao_2_insights_selecionada = st.selectbox(
            "2ª dimensão",
            options=opcoes_dimensao_2_insights,
            index=0,
            format_func=(
                lambda valor:
                    SEM_ESCOLHA_INSIGHTS
                    if valor == SEM_ESCOLHA_INSIGHTS
                    else rotulo_dimensao(valor)
            ),
            key="insights_dimensao_2",
        )


    dimensao_2_insights = (
        None
        if dimensao_2_insights_selecionada
        == SEM_ESCOLHA_INSIGHTS
        else dimensao_2_insights_selecionada
    )


    dimensoes_ativas_insights = (
        dimensao_1_insights,
        dimensao_2_insights,
    )


    if (
        st.session_state.get(
            "_insights_dimensoes_agregado_ativas"
        )
        != dimensoes_ativas_insights
    ):

        st.session_state.pop(
            "insights_agregado_1",
            None,
        )

        st.session_state.pop(
            "insights_agregado_2",
            None,
        )

        st.session_state.pop(
            "insights_agregado_2_selecionar_resto",
            None,
        )

        st.session_state[
            "_insights_dimensoes_agregado_ativas"
        ] = dimensoes_ativas_insights


    combinacoes_insights = obter_combinacoes_insights(
        df,
        dimensao_1_insights,
        dimensao_2_insights,
    )


    if not combinacoes_insights:

        st.info(
            "Não há categorias ou combinações disponíveis para as dimensões selecionadas no recorte atual."
        )

    else:

        for chave_grupo in [
            "insights_agregado_1",
            "insights_agregado_2",
        ]:

            if chave_grupo in st.session_state:

                st.session_state[chave_grupo] = [
                    combinacao
                    for combinacao
                    in st.session_state[chave_grupo]
                    if combinacao
                    in combinacoes_insights
                ]


        selecao_previa_insights_2 = st.session_state.get(
            "insights_agregado_2",
            [],
        )


        selecionar_resto_insights = bool(
            st.session_state.get(
                "insights_agregado_2_selecionar_resto",
                False,
            )
        )


        col_ag_insights_1, col_ag_insights_2 = st.columns(2)


        with col_ag_insights_1:

            if selecionar_resto_insights:

                opcoes_insights_1 = list(
                    combinacoes_insights
                )

            else:

                opcoes_insights_1 = [
                    combinacao
                    for combinacao
                    in combinacoes_insights
                    if combinacao
                    not in selecao_previa_insights_2
                ]


            agregado_insights_1 = st.multiselect(
                "Agregado 1",
                options=opcoes_insights_1,
                format_func=lambda combinacao: rotulo_combinacao_insights(
                    combinacao,
                    dimensao_1_insights,
                    dimensao_2_insights,
                ),
                placeholder=(
                    "Selecione as categorias"
                    if dimensao_2_insights is None
                    else "Selecione as combinações"
                ),
                key="insights_agregado_1",
            )


        with col_ag_insights_2:

            opcoes_insights_2 = [
                combinacao
                for combinacao
                in combinacoes_insights
                if combinacao
                not in agregado_insights_1
            ]


            if selecionar_resto_insights:

                st.session_state[
                    "insights_agregado_2"
                ] = list(
                    opcoes_insights_2
                )

            elif "insights_agregado_2" in st.session_state:

                st.session_state[
                    "insights_agregado_2"
                ] = [
                    combinacao
                    for combinacao
                    in st.session_state[
                        "insights_agregado_2"
                    ]
                    if combinacao
                    in opcoes_insights_2
                ]


            agregado_insights_2 = st.multiselect(
                "Agregado 2",
                options=opcoes_insights_2,
                format_func=lambda combinacao: rotulo_combinacao_insights(
                    combinacao,
                    dimensao_1_insights,
                    dimensao_2_insights,
                ),
                placeholder=(
                    "Selecione as categorias"
                    if dimensao_2_insights is None
                    else "Selecione as combinações"
                ),
                key="insights_agregado_2",
                disabled=selecionar_resto_insights,
            )


            selecionar_resto_insights = st.checkbox(
                "Selecionar todo o resto",
                key="insights_agregado_2_selecionar_resto",
                help=(
                    "Inclui automaticamente no Agregado 2 todas as opções "
                    "que não foram selecionadas no Agregado 1."
                ),
            )


        sobreposicao_insights = set(
            agregado_insights_1
        ).intersection(
            agregado_insights_2
        )


        if sobreposicao_insights:

            st.error(
                "A mesma combinação não pode fazer parte dos dois agregados."
            )

        else:

            st.markdown(
                "#### Composição definida"
            )


            resumo_1, resumo_2 = st.columns(2)


            with resumo_1:

                st.markdown(
                    _html_resumo_agregado_insights(
                        "Agregado 1",
                        agregado_insights_1,
                        dimensao_1_insights,
                        dimensao_2_insights,
                    ),
                    unsafe_allow_html=True,
                )


            with resumo_2:

                st.markdown(
                    _html_resumo_agregado_insights(
                        "Agregado 2",
                        agregado_insights_2,
                        dimensao_1_insights,
                        dimensao_2_insights,
                    ),
                    unsafe_allow_html=True,
                )


# ============================================================
# DISTRIBUIÇÕES
# ============================================================

if pagina == "DISTRIBUIÇÕES":

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:23px;
            font-weight:750;
            letter-spacing:-0.02em;
            color:#27364A;
            margin-top:8px;
            margin-bottom:8px;
        ">
            DISPERSÃO
        </div>
        """,
        unsafe_allow_html=True,
    )


    tab_todos_distrib, tab_agregado_distrib = st.tabs(
        [
            "Todos",
            "Agregado",
        ]
    )


    # ========================================================
    # SUBSEÇÃO — TODOS
    # ========================================================

    def render_distribuicoes_todos():



        _, col_incluir_consolidado_distrib, __ = st.columns(
            [
                2.6,
                1.4,
                2.6,
            ]
        )


        with col_incluir_consolidado_distrib:

            incluir_consolidado_distrib = st.toggle(
                "Incluir Consolidado",
                value=False,
                key="distrib_incluir_consolidado",
                help=(
                    "Inclui o Consolidado nos boxplots e nas distribuições de delta."
                ),
            )


        opcoes_distribuicoes = list(
            EIXOS_DISPONIVEIS.keys()
        )


        SEM_ESCOLHA_DISTRIB = "<vazio>"


        dist_1, dist_2, dist_3, dist_4 = st.columns(
            [
                1.15,
                1.25,
                1.25,
                1.0,
            ]
        )


        with dist_1:

            indicador_distribuicoes = st.selectbox(
                "Indicador",
                [
                    "IDEB",
                    "N(LP)",
                    "N(M)",
                    "N",
                    "Rendimento",
                ],
                key="indicador_distribuicoes",
            )


        with dist_2:

            variavel_1_distribuicoes = st.selectbox(
                "1ª dimensão",
                options=opcoes_distribuicoes,
                index=(
                    opcoes_distribuicoes.index(
                        "INSE"
                    )
                    if "INSE"
                    in opcoes_distribuicoes
                    else 0
                ),
                format_func=rotulo_dimensao,
                key="variavel_1_distribuicoes",
            )


        opcoes_2_distribuicoes = [
            SEM_ESCOLHA_DISTRIB,
            *[
                item
                for item
                in opcoes_distribuicoes
                if item
                != variavel_1_distribuicoes
            ],
        ]


        with dist_3:

            # A 2ª dimensão começa sem seleção. O usuário pode
            # adicionar uma segunda camada quando desejar.
            indice_padrao_var_2_distrib = 0


            variavel_2_distribuicoes = st.selectbox(
                "2ª dimensão",
                options=opcoes_2_distribuicoes,
                index=indice_padrao_var_2_distrib,
                format_func=(
                    lambda valor:
                        SEM_ESCOLHA_DISTRIB
                        if valor
                        == SEM_ESCOLHA_DISTRIB
                        else rotulo_dimensao(
                            valor
                        )
                ),
                key="variavel_2_distribuicoes",
            )


        with dist_4:

            ordenacao_distribuicoes = st.selectbox(
                "Ordenação",
                [
                    "Número absoluto",
                    "Delta",
                    "Ordem para gráfico",
                ],
                key="ordenacao_distribuicoes",
            )


        variavel_2_boxplot = (
            None
            if variavel_2_distribuicoes
            == SEM_ESCOLHA_DISTRIB
            else variavel_2_distribuicoes
        )


        _, bloco_distrib_anos, __ = st.columns(
            [
                1.3,
                3.4,
                1.3,
            ]
        )


        with bloco_distrib_anos:

            cols_distrib = st.columns(5)


            defaults_distrib = {
                2017: False,
                2019: False,
                2021: False,
                2023: True,
                2025: True,
            }


            selecao_distrib = {}


            for col, ano in zip(
                cols_distrib,
                ANOS_PAINEL,
            ):

                with col:

                    selecao_distrib[
                        ano
                    ] = st.checkbox(
                        str(
                            ano
                        ),
                        value=defaults_distrib[
                            ano
                        ],
                        key=f"distrib_ano_{ano}",
                    )


        anos_distribuicoes = [
            ano
            for ano, ativo
            in selecao_distrib.items()
            if ativo
        ]


        if not anos_distribuicoes:

            st.warning(
                "Selecione pelo menos um ano."
            )

            return


        anos_distribuicoes = sorted(
            anos_distribuicoes
        )


        ano_final_distrib = (
            anos_distribuicoes[-1]
        )


        ano_inicial_distrib = (
            anos_distribuicoes[-2]
            if len(
                anos_distribuicoes
            )
            >= 2
            else None
        )


        df_distribuicoes = df.copy()


        # ====================================================
        # PREPARA VALORES ABSOLUTOS
        # ====================================================

        try:

            dados_boxplot, ordem_padrao_boxplot = preparar_dados_boxplot(
                base=df_distribuicoes,
                indicador=indicador_distribuicoes,
                variavel_1=variavel_1_distribuicoes,
                variavel_2=variavel_2_boxplot,
                anos=[
                    ano_final_distrib
                ],
                incluir_integral_agregado=(
                    mostrar_integral_agregado_para(
                        variavel_1_distribuicoes,
                        variavel_2_boxplot,
                    )
                ),
            )


        except Exception as erro:

            st.error(
                "Não foi possível preparar as distribuições."
            )

            st.exception(
                erro
            )

            return


        # ====================================================
        # PREPARA DELTAS
        # ====================================================

        dados_delta_boxplot = pd.DataFrame()
        ordem_padrao_delta = []


        if ano_inicial_distrib is not None:

            try:

                (
                    dados_delta_boxplot,
                    ordem_padrao_delta,
                ) = preparar_dados_delta_boxplot(
                    base=df_distribuicoes,
                    indicador=indicador_distribuicoes,
                    variavel_1=variavel_1_distribuicoes,
                    variavel_2=variavel_2_boxplot,
                    ano_inicial=ano_inicial_distrib,
                    ano_final=ano_final_distrib,
                    incluir_integral_agregado=(
                        mostrar_integral_agregado_para(
                            variavel_1_distribuicoes,
                            variavel_2_boxplot,
                        )
                    ),
                )


            except Exception as erro:

                st.error(
                    "Não foi possível preparar os deltas das distribuições."
                )

                st.exception(
                    erro
                )

                return


        # Consolidado é opcional e começa oculto por padrão.
        if not incluir_consolidado_distrib:

            dados_boxplot = (
                dados_boxplot[
                    dados_boxplot["Categoria"].astype(str)
                    != "Consolidado"
                ]
                .copy()
            )


            if not dados_delta_boxplot.empty:

                dados_delta_boxplot = (
                    dados_delta_boxplot[
                        dados_delta_boxplot["Categoria"].astype(str)
                        != "Consolidado"
                    ]
                    .copy()
                )


        # ====================================================
        # ORDENAÇÃO
        # ====================================================

        ordem_base = [
            categoria
            for categoria
            in ordem_padrao_boxplot
            if categoria
            != "Consolidado"
        ]


        if ordenacao_distribuicoes == "Número absoluto":

            ranking_distribuicoes = (
                dados_boxplot[
                    (
                        dados_boxplot[
                            "Ano"
                        ]
                        == str(
                            ano_final_distrib
                        )
                    )
                    &
                    (
                        dados_boxplot[
                            "Categoria"
                        ]
                        != "Consolidado"
                    )
                ]
                .groupby(
                    "Categoria",
                    as_index=False,
                )
                .agg(
                    Valor_ordem=(
                        "Valor",
                        "mean",
                    )
                )
                .sort_values(
                    "Valor_ordem",
                    ascending=False,
                )
            )


            ordem_rank = (
                ranking_distribuicoes[
                    "Categoria"
                ]
                .astype(str)
                .tolist()
            )


        elif (
            ordenacao_distribuicoes == "Delta"
            and
            ano_inicial_distrib is not None
            and
            not dados_delta_boxplot.empty
        ):

            ranking_distribuicoes = (
                dados_delta_boxplot[
                    dados_delta_boxplot[
                        "Categoria"
                    ]
                    != "Consolidado"
                ]
                .groupby(
                    "Categoria",
                    as_index=False,
                )
                .agg(
                    Valor_ordem=(
                        "Delta",
                        "mean",
                    )
                )
                .sort_values(
                    "Valor_ordem",
                    ascending=False,
                )
            )


            ordem_rank = (
                ranking_distribuicoes[
                    "Categoria"
                ]
                .astype(str)
                .tolist()
            )


        elif ordenacao_distribuicoes == "Ordem para gráfico":

            dados_ordem_grafico = (
                dados_boxplot[
                    dados_boxplot[
                        "Categoria"
                    ]
                    != "Consolidado"
                ]
                .copy()
            )

            ordem_rank = ordenar_combinacoes_para_grafico(
                dados=dados_ordem_grafico,
                variavel_1=variavel_1_distribuicoes,
                variavel_2=variavel_2_boxplot,
            )


        else:

            ordem_rank = ordem_base.copy()


        ordem_boxplot = (
            ordem_rank
            +
            [
                categoria
                for categoria
                in ordem_base
                if categoria
                not in ordem_rank
            ]
        )


        if (
            "Consolidado"
            in dados_boxplot[
                "Categoria"
            ].astype(str).unique()
        ):

            ordem_boxplot.append(
                "Consolidado"
            )


        categorias_delta_existentes = set(
            dados_delta_boxplot[
                "Categoria"
            ]
            .astype(str)
            .unique()
        ) if not dados_delta_boxplot.empty else set()


        ordem_delta_boxplot = [
            categoria
            for categoria
            in ordem_boxplot
            if categoria
            in categorias_delta_existentes
            and categoria
            != "Consolidado"
        ]


        for categoria in ordem_padrao_delta:

            if (
                categoria
                != "Consolidado"
                and
                categoria
                in categorias_delta_existentes
                and
                categoria
                not in ordem_delta_boxplot
            ):

                ordem_delta_boxplot.append(
                    categoria
                )


        if "Consolidado" in categorias_delta_existentes:

            ordem_delta_boxplot.append(
                "Consolidado"
            )


        # ====================================================
        # GRÁFICO 1 — VALORES ABSOLUTOS
        # ====================================================

        st.markdown(
            "#### Distribuições dos valores"
        )


        caption_valores = (
            f"O boxplot mostra a distribuição entre escolas em {ano_final_distrib}, "
            "o ano mais recente selecionado. O losango representa a média e o N "
            "de escolas aparece no eixo X. "
            f"Ordenação: {ordenacao_distribuicoes}."
        )




        st.caption(
            caption_valores
        )


        if dados_boxplot.empty:

            st.info(
                "Não há dados disponíveis para a combinação selecionada."
            )

        else:

            grafico_boxplots = criar_grafico_boxplots(
                dados=dados_boxplot,
                ordem=ordem_boxplot,
                indicador=indicador_distribuicoes,
                variavel_1=variavel_1_distribuicoes,
                variavel_2=variavel_2_boxplot,
                anos=[
                    ano_final_distrib
                ],
            )


            st.altair_chart(
                    aplicar_fundo_grafico(
                        grafico_boxplots
                    ),
                theme=None,
                width="stretch",
            )


            testes_todos_valores = calcular_testes_categoria_vs_demais(
                dados=dados_boxplot,
                coluna_valor="Valor",
                ordem=ordem_boxplot,
                rotulo_periodo=str(
                    ano_final_distrib
                ),
            )


            exibir_p_valores_categoria_vs_demais(
                testes_todos_valores,
                indicador=indicador_distribuicoes,
            )


        # ====================================================
        # GRÁFICO 2 — DELTAS
        # ====================================================

        st.markdown(
            "#### Distribuições dos deltas"
        )


        if ano_inicial_distrib is None:

            st.info(
                "Selecione pelo menos dois anos para visualizar "
                "a distribuição dos deltas."
            )

            return


        st.caption(
            f"Delta calculado como {ano_final_distrib} − "
            f"{ano_inicial_distrib}. Quando mais de dois anos estão "
            "selecionados, são usadas as duas edições mais recentes. "
            f"As dimensões de cada escola são consideradas em "
            f"{ano_final_distrib}."
        )


        if dados_delta_boxplot.empty:

            st.info(
                "Não há escolas com resultados válidos nos dois anos "
                "mais recentes selecionados para calcular os deltas."
            )

        else:

            grafico_delta_boxplots = criar_grafico_delta_boxplots(
                dados=dados_delta_boxplot,
                ordem=ordem_delta_boxplot,
                indicador=indicador_distribuicoes,
                variavel_1=variavel_1_distribuicoes,
                variavel_2=variavel_2_boxplot,
                ano_inicial=ano_inicial_distrib,
                ano_final=ano_final_distrib,
            )


            st.altair_chart(
                    aplicar_fundo_grafico(
                        grafico_delta_boxplots
                    ),
                theme=None,
                width="stretch",
            )


            testes_todos_delta = calcular_testes_categoria_vs_demais(
                dados=dados_delta_boxplot,
                coluna_valor="Delta",
                ordem=ordem_delta_boxplot,
                rotulo_periodo=(
                    f"{ano_final_distrib} − {ano_inicial_distrib}"
                ),
            )


            exibir_p_valores_categoria_vs_demais(
                testes_todos_delta,
                indicador=indicador_distribuicoes,
            )


    # ========================================================
    # SUBSEÇÃO — AGREGADO
    # ========================================================

    def render_distribuicoes_agregado():



        opcoes_agregado = list(
            EIXOS_DISPONIVEIS.keys()
        )


        ag_1, ag_2 = st.columns(
            [
                1.0,
                1.35,
            ]
        )


        with ag_1:

            indicador_agregado = st.selectbox(
                "Indicador",
                [
                    "IDEB",
                    "N(LP)",
                    "N(M)",
                    "N",
                    "Rendimento",
                ],
                key="indicador_distrib_agregado",
            )


        with ag_2:

            variavel_agregado = st.selectbox(
                "Dimensão",
                options=opcoes_agregado,
                index=(
                    opcoes_agregado.index(
                        "INSE"
                    )
                    if "INSE"
                    in opcoes_agregado
                    else 0
                ),
                format_func=rotulo_dimensao,
                key="variavel_distrib_agregado",
            )


        _, bloco_agregado_anos, __ = st.columns(
            [
                1.3,
                3.4,
                1.3,
            ]
        )


        with bloco_agregado_anos:

            cols_agregado = st.columns(5)


            defaults_agregado = {
                2017: False,
                2019: False,
                2021: False,
                2023: True,
                2025: True,
            }


            selecao_agregado_anos = {}


            for col, ano in zip(
                cols_agregado,
                ANOS_PAINEL,
            ):

                with col:

                    selecao_agregado_anos[
                        ano
                    ] = st.checkbox(
                        str(
                            ano
                        ),
                        value=defaults_agregado[
                            ano
                        ],
                        key=f"agregado_ano_{ano}",
                    )


        anos_agregado = [
            ano
            for ano, ativo
            in selecao_agregado_anos.items()
            if ativo
        ]


        if not anos_agregado:

            st.warning(
                "Selecione pelo menos um ano."
            )

            return


        anos_agregado = sorted(
            anos_agregado
        )


        ano_final_agregado = anos_agregado[-1]


        ano_inicial_agregado = (
            anos_agregado[-2]
            if len(
                anos_agregado
            )
            >= 2
            else None
        )


        # As listas mostram as categorias atômicas da dimensão.
        # Categorias compostas já existentes no painel, como
        # "Integral (Mista + 100%)", não são adicionadas aqui para
        # evitar sobreposição de escolas entre os dois agregados.
        categorias_agregado = obter_categorias_agregacao(
            df,
            variavel_agregado,
        )


        if not categorias_agregado:

            st.info(
                "Não há categorias disponíveis para a dimensão selecionada."
            )

            return


        # Ao mudar a dimensão, limpa as escolhas dos dois agregados.
        if (
            st.session_state.get(
                "_dimensao_distrib_agregado_ativa"
            )
            != variavel_agregado
        ):

            st.session_state.pop(
                "categorias_distrib_agregado_1",
                None,
            )

            st.session_state.pop(
                "categorias_distrib_agregado_2",
                None,
            )

            st.session_state.pop(
                "agregado_2_selecionar_resto",
                None,
            )

            st.session_state[
                "_dimensao_distrib_agregado_ativa"
            ] = variavel_agregado


        # Também remove da sessão categorias que tenham desaparecido
        # por causa dos filtros gerais do painel.
        for chave_grupo in [
            "categorias_distrib_agregado_1",
            "categorias_distrib_agregado_2",
        ]:

            if chave_grupo in st.session_state:

                st.session_state[
                    chave_grupo
                ] = [
                    valor
                    for valor
                    in st.session_state[
                        chave_grupo
                    ]
                    if valor
                    in categorias_agregado
                ]


        selecao_previa_1 = st.session_state.get(
            "categorias_distrib_agregado_1",
            [],
        )


        selecao_previa_2 = st.session_state.get(
            "categorias_distrib_agregado_2",
            [],
        )


        # Segurança extra: caso exista uma sobreposição vinda de um
        # estado antigo da sessão, o Agregado 1 tem precedência.
        sobreposicao_previa = set(
            selecao_previa_1
        ).intersection(
            selecao_previa_2
        )


        if sobreposicao_previa:

            st.session_state[
                "categorias_distrib_agregado_2"
            ] = [
                valor
                for valor
                in selecao_previa_2
                if valor
                not in sobreposicao_previa
            ]

            selecao_previa_2 = st.session_state[
                "categorias_distrib_agregado_2"
            ]


        st.markdown(
            "#### Composição dos agregados"
        )


        st.caption(
            "Escolha livremente quais categorias entram em cada agregado. "
            "Não é necessário utilizar todas as categorias. Uma categoria "
            "selecionada em um agregado fica indisponível no outro."
        )


        col_grupo_1, col_grupo_2 = st.columns(2)


        selecionar_resto_agregado = bool(
            st.session_state.get(
                "agregado_2_selecionar_resto",
                False,
            )
        )


        with col_grupo_1:

            # Quando o Agregado 2 representa automaticamente todo o resto,
            # o Agregado 1 precisa continuar livre para receber qualquer
            # categoria. Caso contrário, preservamos a regra de impedir
            # sobreposição entre os dois grupos.
            if selecionar_resto_agregado:

                opcoes_grupo_1 = list(
                    categorias_agregado
                )

            else:

                opcoes_grupo_1 = [
                    categoria
                    for categoria
                    in categorias_agregado
                    if categoria
                    not in selecao_previa_2
                ]


            categorias_grupo_1 = st.multiselect(
                "Agregado 1",
                options=opcoes_grupo_1,
                placeholder="Selecione as categorias",
                key="categorias_distrib_agregado_1",
            )


        with col_grupo_2:

            opcoes_grupo_2 = [
                categoria
                for categoria
                in categorias_agregado
                if categoria
                not in categorias_grupo_1
            ]


            if selecionar_resto_agregado:

                st.session_state[
                    "categorias_distrib_agregado_2"
                ] = list(
                    opcoes_grupo_2
                )

            elif (
                "categorias_distrib_agregado_2"
                in st.session_state
            ):

                st.session_state[
                    "categorias_distrib_agregado_2"
                ] = [
                    categoria
                    for categoria
                    in st.session_state[
                        "categorias_distrib_agregado_2"
                    ]
                    if categoria
                    in opcoes_grupo_2
                ]


            categorias_grupo_2 = st.multiselect(
                "Agregado 2",
                options=opcoes_grupo_2,
                placeholder="Selecione as categorias",
                key="categorias_distrib_agregado_2",
                disabled=selecionar_resto_agregado,
            )


            selecionar_resto_agregado = st.checkbox(
                "Selecionar todo o resto",
                key="agregado_2_selecionar_resto",
                help=(
                    "Inclui automaticamente no Agregado 2 todas as "
                    "categorias que não foram selecionadas no Agregado 1."
                ),
            )


        sobreposicao = set(
            categorias_grupo_1
        ).intersection(
            categorias_grupo_2
        )


        if sobreposicao:

            st.error(
                "A mesma categoria não pode fazer parte dos dois agregados."
            )

            return


        if (
            not categorias_grupo_1
            or
            not categorias_grupo_2
        ):

            st.info(
                "Selecione pelo menos uma categoria em cada agregado "
                "para gerar os gráficos."
            )

            return


        composicao_1 = " + ".join(
            str(
                categoria
            )
            for categoria
            in categorias_grupo_1
        )


        composicao_2 = " + ".join(
            str(
                categoria
            )
            for categoria
            in categorias_grupo_2
        )


        st.caption(
            f"Agregado 1: {composicao_1}  |  "
            f"Agregado 2: {composicao_2}"
        )


        df_agregado = df.copy()


        # ====================================================
        # VALORES ABSOLUTOS
        # ====================================================

        try:

            (
                dados_agregado,
                ordem_padrao_agregado,
            ) = preparar_dados_boxplot_agregado(
                base=df_agregado,
                indicador=indicador_agregado,
                variavel=variavel_agregado,
                anos=anos_agregado,
                categorias_grupo_1=categorias_grupo_1,
                categorias_grupo_2=categorias_grupo_2,
            )


        except Exception as erro:

            st.error(
                "Não foi possível preparar as distribuições agregadas."
            )

            st.exception(
                erro
            )

            return


        # ====================================================
        # DELTAS
        # ====================================================

        dados_delta_agregado = pd.DataFrame()
        ordem_padrao_delta_agregado = []


        if ano_inicial_agregado is not None:

            try:

                (
                    dados_delta_agregado,
                    ordem_padrao_delta_agregado,
                ) = preparar_dados_delta_boxplot_agregado(
                    base=df_agregado,
                    indicador=indicador_agregado,
                    variavel=variavel_agregado,
                    ano_inicial=ano_inicial_agregado,
                    ano_final=ano_final_agregado,
                    categorias_grupo_1=categorias_grupo_1,
                    categorias_grupo_2=categorias_grupo_2,
                )


            except Exception as erro:

                st.error(
                    "Não foi possível preparar os deltas agregados."
                )

                st.exception(
                    erro
                )

                return


        # ====================================================
        # ORDEM FIXA DOS DOIS AGREGADOS
        # ====================================================

        # Nesta subseção a ordem é intencionalmente fixa para que
        # Agregado 1 apareça sempre antes de Agregado 2.
        categorias_existentes_agregado = set(
            dados_agregado[
                "Categoria"
            ]
            .astype(str)
            .unique()
        ) if not dados_agregado.empty else set()


        ordem_agregado = [
            grupo
            for grupo
            in [
                "Agregado 1",
                "Agregado 2",
            ]
            if grupo
            in categorias_existentes_agregado
        ]


        categorias_delta_agregado = set(
            dados_delta_agregado[
                "Categoria"
            ]
            .astype(str)
            .unique()
        ) if not dados_delta_agregado.empty else set()


        ordem_delta_agregado = [
            grupo
            for grupo
            in [
                "Agregado 1",
                "Agregado 2",
            ]
            if grupo
            in categorias_delta_agregado
        ]


        # ====================================================
        # GRÁFICO 1 — VALORES ABSOLUTOS AGREGADOS
        # ====================================================

        st.markdown(
            "#### Distribuições dos valores"
        )


        caption_agregado = (
            f"O primeiro gráfico usa apenas {ano_final_agregado}, o ano mais recente "
            "selecionado. Cada boxplot reúne todas as escolas pertencentes às "
            "categorias incluídas no respectivo agregado."
        )




        st.caption(
            caption_agregado
        )


        if dados_agregado.empty:

            st.info(
                "Não há dados disponíveis para os agregados selecionados."
            )

        else:

            testes_agregado_valores = (
                calcular_p_valores_agregados_por_ano(
                    dados_agregado,
                    anos_agregado,
                )
            )


            # O primeiro gráfico usa exclusivamente o ano mais recente
            # selecionado. Os demais anos continuam disponíveis para a
            # tabela estatística e para a definição do delta.
            dados_agregado_ultimo = (
                dados_agregado[
                    dados_agregado[
                        "Ano"
                    ]
                    == str(
                        ano_final_agregado
                    )
                ]
                .copy()
            )


            mapa_rotulos_agregado = rotulos_n_agregados_valores(
                dados_agregado_ultimo,
                ano_final_agregado,
                categorias_grupo_1,
                categorias_grupo_2,
            )


            (
                dados_agregado_plot,
                ordem_agregado_plot,
            ) = aplicar_rotulos_n_agregados(
                dados_agregado_ultimo,
                ordem_agregado,
                mapa_rotulos_agregado,
            )


            dominio_y_agregado = calcular_dominio_y_compartilhado(
                dados_agregado_plot[
                    "Valor"
                ],
                indicador_agregado,
                delta=False,
            )


            col_boxplot_agregado, col_medias_agregado = st.columns(
                [
                    1.00,
                    1.00,
                ],
                gap="medium",
            )


            with col_boxplot_agregado:

                grafico_agregado = criar_grafico_boxplots(
                    dados=dados_agregado_plot,
                    ordem=ordem_agregado_plot,
                    indicador=indicador_agregado,
                    variavel_1=variavel_agregado,
                    variavel_2=None,
                    anos=[
                        ano_final_agregado
                    ],
                    rotulos_multilinha=True,
                    dominio_y=dominio_y_agregado,
                    altura=430,
                )


                grafico_agregado = grafico_agregado.properties(
                    title=alt.TitleParams(
                        text=(
                            f"Distribuição de {indicador_agregado} — "
                            f"categorias agregadas de "
                            f"{rotulo_dimensao(variavel_agregado)} — "
                            f"{ano_final_agregado}"
                        ),
                        subtitle=(
                            "O gráfico mostra apenas o ano mais recente selecionado. "
                            "O losango e o rótulo indicam a média; o N aparece no eixo X."
                        ),
                        anchor="middle",
                        fontSize=17,
                        subtitleFontSize=11,
                        subtitlePadding=8,
                    )
                )


                st.altair_chart(
                        aplicar_fundo_grafico(
                            grafico_agregado
                        ),
                    theme=None,
                    width="stretch",
                )


            with col_medias_agregado:

                grafico_medias_agregado = (
                    criar_grafico_barras_medias_agregado(
                        dados=dados_agregado_plot,
                        ordem=ordem_agregado_plot,
                        indicador=indicador_agregado,
                        variavel=variavel_agregado,
                        anos=[
                            ano_final_agregado
                        ],
                        rotulos_multilinha=True,
                        dominio_y=dominio_y_agregado,
                        altura=430,
                    )
                )


                st.altair_chart(
                        aplicar_fundo_grafico(
                            grafico_medias_agregado
                        ),
                    theme=None,
                    width="stretch",
                )


            exibir_p_valores_agregados(
                testes_agregado_valores,
                indicador=indicador_agregado,
            )


        # ====================================================
        # GRÁFICO 2 — DELTAS AGREGADOS
        # ====================================================

        st.markdown(
            "#### Distribuições dos deltas"
        )


        if ano_inicial_agregado is None:

            st.info(
                "Selecione pelo menos dois anos para visualizar "
                "a distribuição dos deltas."
            )

            return


        st.caption(
            f"Delta calculado como {ano_final_agregado} − "
            f"{ano_inicial_agregado}. Quando mais de dois anos estão "
            "selecionados, são usadas as duas edições mais recentes. "
            f"A categoria usada para definir o agregado de cada escola é "
            f"a observada em {ano_final_agregado}."
        )


        if dados_delta_agregado.empty:

            st.info(
                "Não há escolas com resultados válidos nos dois anos "
                "mais recentes selecionados para calcular os deltas."
            )

        else:

            mapa_rotulos_delta_agregado = rotulos_n_agregados_delta(
                dados_delta_agregado,
                categorias_grupo_1,
                categorias_grupo_2,
            )


            (
                dados_delta_agregado_plot,
                ordem_delta_agregado_plot,
            ) = aplicar_rotulos_n_agregados(
                dados_delta_agregado,
                ordem_delta_agregado,
                mapa_rotulos_delta_agregado,
            )


            testes_agregado_delta = calcular_p_valor_agregado_delta(
                dados_delta_agregado,
                ano_inicial_agregado,
                ano_final_agregado,
            )


            # ====================================================
            # BLOCO 2 — DELTAS
            #
            # Boxplot e gráfico de médias ficam lado a lado.
            # A tabela de testes aparece abaixo dos dois gráficos.
            # ====================================================

            dominio_y_delta_agregado = calcular_dominio_y_compartilhado(
                dados_delta_agregado_plot[
                    "Delta"
                ],
                indicador_agregado,
                delta=True,
            )


            col_boxplot_delta_ag, col_medias_delta_ag = st.columns(
                [
                    1.00,
                    1.00,
                ],
                gap="medium",
            )


            with col_boxplot_delta_ag:

                grafico_delta_agregado = criar_grafico_delta_boxplots(
                    dados=dados_delta_agregado_plot,
                    ordem=ordem_delta_agregado_plot,
                    indicador=indicador_agregado,
                    variavel_1=variavel_agregado,
                    variavel_2=None,
                    ano_inicial=ano_inicial_agregado,
                    ano_final=ano_final_agregado,
                    rotulos_multilinha=True,
                    dominio_y=dominio_y_delta_agregado,
                    altura=430,
                    cores_por_categoria=True,
                )


                grafico_delta_agregado = grafico_delta_agregado.properties(
                    title=alt.TitleParams(
                        text=(
                            f"Distribuição dos deltas de {indicador_agregado} — "
                            f"categorias agregadas de "
                            f"{rotulo_dimensao(variavel_agregado)} — "
                            f"{ano_final_agregado} − {ano_inicial_agregado}"
                        ),
                        subtitle=(
                            "Cada delta é calculado por escola. O eixo mostra "
                            "diretamente as categorias de cada agregado. O losango "
                            "e o rótulo indicam a média; o N de escolas com delta "
                            "válido aparece no eixo X."
                        ),
                        anchor="middle",
                        fontSize=17,
                        subtitleFontSize=11,
                        subtitlePadding=8,
                    )
                )


                st.altair_chart(
                        aplicar_fundo_grafico(
                            grafico_delta_agregado
                        ),
                    theme=None,
                    width="stretch",
                )


            with col_medias_delta_ag:

                grafico_medias_delta_agregado = (
                    criar_grafico_barras_medias_delta_agregado(
                        dados=dados_delta_agregado_plot,
                        ordem=ordem_delta_agregado_plot,
                        indicador=indicador_agregado,
                        variavel=variavel_agregado,
                        ano_inicial=ano_inicial_agregado,
                        ano_final=ano_final_agregado,
                        rotulos_multilinha=True,
                        dominio_y=dominio_y_delta_agregado,
                        altura=430,
                    )
                )


                st.altair_chart(
                        aplicar_fundo_grafico(
                            grafico_medias_delta_agregado
                        ),
                    theme=None,
                    width="stretch",
                )


            exibir_p_valores_agregados(
                testes_agregado_delta,
                indicador=indicador_agregado,
            )


    with tab_todos_distrib:

        render_distribuicoes_todos()


    with tab_agregado_distrib:

        render_distribuicoes_agregado()


    st.stop()


# ============================================================
# MELHORES ESCOLAS
# ============================================================

if pagina == "MELHORES ESCOLAS":

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:23px;
            font-weight:750;
            letter-spacing:-0.02em;
            color:#27364A;
            margin-top:8px;
            margin-bottom:8px;
        ">
            MELHORES ESCOLAS
        </div>
        """,
        unsafe_allow_html=True,
    )


    c1, c2, c3 = st.columns(
        [
            1.8,
            1.1,
            1.1,
        ]
    )


    with c1:

        indicador_rank = st.selectbox(
            "Indicador",
            [
                "IDEB",
                "N(LP)",
                "N(M)",
                "N",
                "Rendimento",
            ],
            key="indicador_melhores",
        )


    with c2:

        criterio_rank = st.selectbox(
            "Ordenar por",
            [
                "Valor absoluto",
                "Variação",
            ],
            key="criterio_melhores",
        )


    with c3:

        quantidade_rank = st.selectbox(
            "Quantidade de escolas",
            list(
                range(
                    10,
                    101,
                    10,
                )
            ),
            index=1,
            format_func=lambda x: (
                f"{x} melhores escolas"
            ),
        )


    _, bloco_rank, __ = st.columns(
        [
            1.6,
            2.8,
            1.6,
        ]
    )


    with bloco_rank:

        anos_rank = st.multiselect(
            "Anos considerados",
            options=ANOS_PAINEL,
            default=[
                2023,
                2025,
            ],
            max_selections=2,
        )


    if not anos_rank:

        st.stop()


    anos_rank = sorted(
        anos_rank
    )


    ano_rank_final = (
        anos_rank[-1]
    )


    ano_rank_inicial = (
        anos_rank[0]
        if len(
            anos_rank
        )
        == 2
        else None
    )


    if (
        criterio_rank
        == "Variação"
        and
        len(
            anos_rank
        )
        < 2
    ):

        st.warning(
            "Para ordenar por variação, "
            "selecione dois anos."
        )

        st.stop()


    candidatos_nome = [
        "Nome da Escola",
        "Nome da escola",
        "Nome Escola",
        "Escola",
        "NO_ESCOLA",
        "NO_ENTIDADE",
        "Nome",
    ]


    coluna_nome = None


    for candidato in candidatos_nome:

        if candidato in df.columns:

            coluna_nome = candidato

            break


    colunas = [
        "Cód. INEP",
        "Ano",
        indicador_rank,
    ]


    if coluna_nome:

        colunas.append(
            coluna_nome
        )


    base_rank = (
        df[
            df[
                "Ano"
            ].isin(
                anos_rank
            )
        ][
            list(
                dict.fromkeys(
                    colunas
                )
            )
        ]
        .copy()
    )


    base_rank[
        indicador_rank
    ] = pd.to_numeric(
        base_rank[
            indicador_rank
        ],
        errors="coerce",
    )


    if coluna_nome:

        base_rank[
            "Escola_rank"
        ] = (
            base_rank[
                coluna_nome
            ]
            .astype(str)
        )

    else:

        base_rank[
            "Escola_rank"
        ] = (
            base_rank[
                "Cód. INEP"
            ]
            .astype(str)
        )


    if criterio_rank == "Valor absoluto":

        ranking = (
            base_rank[
                (
                    base_rank[
                        "Ano"
                    ]
                    == ano_rank_final
                )
                &
                base_rank[
                    indicador_rank
                ].notna()
            ]
            .drop_duplicates(
                "Cód. INEP"
            )
            .sort_values(
                indicador_rank,
                ascending=False,
            )
            .head(
                quantidade_rank
            )
            .reset_index(
                drop=True
            )
        )


        titulo_rank = (
            f"Top {quantidade_rank} — "
            f"{indicador_rank} em "
            f"{ano_rank_final}"
        )


    else:

        pivot = (
            base_rank[
                [
                    "Cód. INEP",
                    "Ano",
                    indicador_rank,
                ]
            ]
            .drop_duplicates(
                [
                    "Cód. INEP",
                    "Ano",
                ]
            )
            .pivot(
                index="Cód. INEP",
                columns="Ano",
                values=indicador_rank,
            )
            .reset_index()
        )


        if (
            ano_rank_inicial
            not in pivot.columns
            or
            ano_rank_final
            not in pivot.columns
        ):

            st.stop()


        ranking = (
            pivot[
                pivot[
                    ano_rank_inicial
                ].notna()
                &
                pivot[
                    ano_rank_final
                ].notna()
            ]
            .copy()
        )


        ranking[
            "Variação"
        ] = (
            ranking[
                ano_rank_final
            ]
            -
            ranking[
                ano_rank_inicial
            ]
        )


        nomes = (
            base_rank[
                base_rank[
                    "Ano"
                ]
                == ano_rank_final
            ][
                [
                    "Cód. INEP",
                    "Escola_rank",
                ]
            ]
            .drop_duplicates(
                "Cód. INEP"
            )
        )


        ranking = (
            ranking
            .merge(
                nomes,
                on="Cód. INEP",
                how="left",
            )
            .sort_values(
                "Variação",
                ascending=False,
            )
            .head(
                quantidade_rank
            )
            .reset_index(
                drop=True
            )
        )


        titulo_rank = (
            f"Top {quantidade_rank} — "
            f"Variação de {indicador_rank}: "
            f"{ano_rank_final} − "
            f"{ano_rank_inicial}"
        )


    ranking[
        "Posição"
    ] = np.arange(
        1,
        len(
            ranking
        )
        + 1,
    )


    base_dim = (
        df[
            (
                df[
                    "Ano"
                ]
                == ano_rank_final
            )
            &
            (
                df[
                    "Cód. INEP"
                ].isin(
                    ranking[
                        "Cód. INEP"
                    ]
                )
            )
        ]
        .drop_duplicates(
            "Cód. INEP"
        )
        .copy()
    )


    # ========================================================
    # DISTRIBUIÇÕES TOP
    # ========================================================

    dist_tipo_ano = preparar_distribuicao_top(
        base_dim,
        "Tipo de Escola por ano",
        [
            "100% Integral",
            "Parcial/Regular",
            "Mista",
        ],
    )


    dist_tipo_2025 = preparar_distribuicao_top(
        base_dim,
        "Tipo de Escola 2025",
        [
            "100% Integral",
            "Parcial/Regular",
            "Mista",
        ],
    )


    dist_inse = preparar_distribuicao_top(
        base_dim,
        "INSE",
    )


    dist_ppi = preparar_distribuicao_top(
        base_dim,
        "PPI",
    )


    g1, g2, g3, g4 = st.columns(
        4,
        gap="medium",
    )


    with g1:

        st.altair_chart(
            aplicar_fundo_grafico(
                grafico_barra_100_top(
                    dist_tipo_ano,
                    "Tipo de Escola por ano",
                    [
                        "100% Integral",
                        "Mista",
                        "Parcial/Regular",
                    ],
                )
            ),
            theme=None,
            width="stretch",
        )


    with g2:

        st.altair_chart(
            aplicar_fundo_grafico(
                grafico_barra_100_top(
                    dist_tipo_2025,
                    "Tipo de Escola 2025",
                    [
                        "100% Integral",
                        "Mista",
                        "Parcial/Regular",
                    ],
                )
            ),
            theme=None,
            width="stretch",
        )


    with g3:

        st.altair_chart(
            aplicar_fundo_grafico(
                grafico_barra_100_top(
                    dist_inse,
                    "INSE",
                    ordenar_dimensao(
                        dist_inse[
                            "Categoria"
                        ].tolist(),
                        "INSE",
                    ),
                )
            ),
            theme=None,
            width="stretch",
        )


    with g4:

        st.altair_chart(
            aplicar_fundo_grafico(
                grafico_barra_100_top(
                    dist_ppi,
                    "PPI",
                    ordenar_dimensao(
                        dist_ppi[
                            "Categoria"
                        ].tolist(),
                        "PPI",
                    ),
                )
            ),
            theme=None,
            width="stretch",
        )


    # Respiro entre as legendas dos gráficos e a tabela.
    st.markdown(
        "<div style='height:18px'></div>",
        unsafe_allow_html=True,
    )


    # ========================================================
    # DIMENSÕES DA TABELA
    # ========================================================

    for dimensao in EIXOS_DISPONIVEIS:

        try:

            temp = criar_variavel_eixo(
                base_dim,
                dimensao,
            )


            base_dim[
                dimensao
            ] = temp[
                "Categoria"
            ].values

        except Exception:

            base_dim[
                dimensao
            ] = "Não informado"


    ranking = ranking.merge(
        base_dim[
            [
                "Cód. INEP"
            ]
            +
            list(
                EIXOS_DISPONIVEIS.keys()
            )
        ],
        on="Cód. INEP",
        how="left",
    )


    st.markdown(
        f"""
        <div style="
            text-align:center;
            font-size:22px;
            font-weight:700;
            margin-top:10px;
            margin-bottom:8px;
        ">
            {titulo_rank}
        </div>
        """,
        unsafe_allow_html=True,
    )


    tabela = pd.DataFrame()


    tabela[
        "Posição"
    ] = ranking[
        "Posição"
    ]


    tabela[
        "Nome"
    ] = ranking[
        "Escola_rank"
    ]


    tabela[
        "Cód. INEP"
    ] = ranking[
        "Cód. INEP"
    ]


    if criterio_rank == "Valor absoluto":

        tabela[
            str(
                ano_rank_final
            )
        ] = (
            ranking[
                indicador_rank
            ]
            .apply(
                lambda x:
                formatar_valor_tabela(
                    x,
                    indicador_rank,
                )
            )
        )


    else:

        for ano in [
            ano_rank_inicial,
            ano_rank_final,
        ]:

            tabela[
                str(
                    ano
                )
            ] = (
                ranking[
                    ano
                ]
                .apply(
                    lambda x:
                    formatar_valor_tabela(
                        x,
                        indicador_rank,
                    )
                )
            )


        tabela[
            "Variação"
        ] = (
            ranking[
                "Variação"
            ]
            .apply(
                lambda x:
                formatar_valor_tabela(
                    x,
                    indicador_rank,
                )
            )
        )


    for dimensao in EIXOS_DISPONIVEIS:

        if dimensao in ranking.columns:

            tabela[
                rotulo_dimensao(
                    dimensao
                )
            ] = ranking[
                dimensao
            ]


    # ========================================================
    # TABELA COMPACTA, CENTRALIZADA E SEM LINHAS VAZIAS
    # ========================================================

    # Mantém apenas as linhas efetivamente existentes no ranking.
    tabela = (
        tabela
        .dropna(
            how="all"
        )
        .reset_index(
            drop=True
        )
    )


    # st.dataframe não oferece controle consistente de alinhamento e
    # tamanho de fonte entre versões do Streamlit. Para esta tabela,
    # usamos HTML responsivo: todas as células ficam centralizadas,
    # a fonte é menor e a largura total é comprimida para caber na tela
    # sem rolagem horizontal.
    tabela_html = tabela.to_html(
        index=False,
        escape=True,
        classes="tabela-melhores-escolas",
        border=0,
    )


    # IMPORTANTE: o HTML precisa chegar ao Markdown sem recuo à esquerda.
    # Caso contrário, o Markdown interpreta as tags como bloco de código
    # e exibe literalmente <div>, <table> etc.
    html_tabela = textwrap.dedent(
        f"""\
<style>
    .melhores-tabela-wrap {{
        width: 100%;
        max-height: 720px;
        overflow-y: auto;
        overflow-x: hidden;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
    }}

    table.tabela-melhores-escolas {{
        width: 100% !important;
        max-width: 100% !important;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 9.0px !important;
        line-height: 1.08;
        margin: 0 !important;
    }}

    table.tabela-melhores-escolas th,
    table.tabela-melhores-escolas td {{
        text-align: center !important;
        vertical-align: middle !important;
        padding: 5px 3px !important;
        border-bottom: 1px solid #ECEFF2;
        white-space: normal !important;
        overflow-wrap: anywhere;
        word-break: normal;
    }}

    table.tabela-melhores-escolas th {{
        position: sticky;
        top: 0;
        z-index: 2;
        background: #F4F7FA;
        font-size: 8.8px !important;
        font-weight: 700;
        color: #343741;
    }}

    /* Nome da escola recebe mais espaço; posição e código, menos. */
    table.tabela-melhores-escolas tbody tr:nth-child(even) {{
        background: #FAFBFC;
    }}

    table.tabela-melhores-escolas tbody tr:hover {{
        background: #F1F6FA;
    }}

    table.tabela-melhores-escolas th:nth-child(1),
    table.tabela-melhores-escolas td:nth-child(1) {{
        width: 4.5%;
    }}

    table.tabela-melhores-escolas th:nth-child(2),
    table.tabela-melhores-escolas td:nth-child(2) {{
        width: 15%;
    }}

    table.tabela-melhores-escolas th:nth-child(3),
    table.tabela-melhores-escolas td:nth-child(3) {{
        width: 7%;
    }}
</style>
<div class="melhores-tabela-wrap">
{tabela_html}
</div>
"""
    )

    st.markdown(
        html_tabela,
        unsafe_allow_html=True,
    )


    st.stop()


# ============================================================
# PRINCIPAIS INDICADORES
# ============================================================

if pagina == "PRINCIPAIS INDICADORES":

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:23px;
            font-weight:750;
            letter-spacing:-0.02em;
            color:#27364A;
            margin-bottom:0.25rem;
        ">
            INDICADORES
        </div>
        """,
        unsafe_allow_html=True,
    )




    opcoes = list(
        EIXOS_DISPONIVEIS.keys()
    )


    SEM_ESCOLHA = "<vazio>"


    c1, c2, c3, c4 = st.columns(
        [
            1.25,
            1.25,
            1.25,
            1.0,
        ]
    )


    with c1:

        indicador_cruz = st.selectbox(
            "Indicador",
            [
                "IDEB",
                "N(LP)",
                "N(M)",
                "N",
                "Rendimento",
            ],
            key="indicador_cruz",
        )


    with c2:

        variavel_1 = st.selectbox(
            "1ª dimensão",
            opcoes,
            index=(
                opcoes.index(
                    "INSE"
                )
                if "INSE"
                in opcoes
                else 0
            ),
            format_func=rotulo_dimensao,
            key="cruz_var_1",
        )


    opcoes_2 = [
        SEM_ESCOLHA,
        *[
            item
            for item
            in opcoes
            if item
            != variavel_1
        ],
    ]


    with c3:

        # A 2ª dimensão começa como <vazio> por padrão.
        indice_padrao_var_2 = 0


        variavel_2 = st.selectbox(
            "2ª dimensão",
            opcoes_2,
            index=indice_padrao_var_2,
            format_func=(
                lambda valor:
                    SEM_ESCOLHA
                    if valor == SEM_ESCOLHA
                    else rotulo_dimensao(
                        valor
                    )
            ),
            key="cruz_var_2",
        )


    with c4:

        ordenacao_cruz = st.selectbox(
            "Ordenação",
            [
                "Número absoluto",
                "Delta",
                "Ordem para gráfico",
            ],
            key="ordenacao_cruz",
        )


    _, bloco_cruz_anos, __ = st.columns(
        [
            1.3,
            3.4,
            1.3,
        ]
    )


    with bloco_cruz_anos:

        cols = st.columns(5)


        defaults = {
            2017: False,
            2019: False,
            2021: False,
            2023: True,
            2025: True,
        }


        selecao = {}


        for col, ano in zip(
            cols,
            ANOS_PAINEL,
        ):

            with col:

                selecao[
                    ano
                ] = st.checkbox(
                    str(ano),
                    value=defaults[
                        ano
                    ],
                    key=f"cruz_ano_{ano}",
                )


    anos_cruz = [
        ano
        for ano, ativo
        in selecao.items()
        if ativo
    ]


    if not anos_cruz:

        st.warning(
            "Selecione pelo menos um ano."
        )

        st.stop()


    df_cruz = df.copy()


    consolidado_cruz = (
        calcular_consolidado(
            df_cruz,
            indicador_cruz,
            anos_cruz,
        )
    )


    anos_ord_cruz = sorted(
        anos_cruz
    )


    ano_final_cruz = (
        anos_ord_cruz[-1]
    )


    ano_ini_cruz = (
        anos_ord_cruz[-2]
        if len(
            anos_ord_cruz
        )
        >= 2
        else None
    )


    # ========================================================
    # CONTROLES DE APRESENTAÇÃO
    #
    # Os dois controles são mutuamente exclusivos: o usuário pode
    # exibir os dois gráficos, apenas médias ou apenas variações.
    # ========================================================

    if (
        "cruz_ocultar_medias"
        not in st.session_state
    ):

        st.session_state[
            "cruz_ocultar_medias"
        ] = False


    if (
        "cruz_ocultar_variacoes"
        not in st.session_state
    ):

        st.session_state[
            "cruz_ocultar_variacoes"
        ] = False


    if ano_ini_cruz is None:

        st.session_state[
            "cruz_ocultar_medias"
        ] = False

        st.session_state[
            "cruz_ocultar_variacoes"
        ] = False


    def ao_alterar_ocultar_medias():

        if st.session_state.get(
            "cruz_ocultar_medias",
            False,
        ):

            st.session_state[
                "cruz_ocultar_variacoes"
            ] = False


    def ao_alterar_ocultar_variacoes():

        if st.session_state.get(
            "cruz_ocultar_variacoes",
            False,
        ):

            st.session_state[
                "cruz_ocultar_medias"
            ] = False


    if "cruz_incluir_consolidado" not in st.session_state:

        st.session_state[
            "cruz_incluir_consolidado"
        ] = False


    (
        col_apres_esq,
        col_ocultar_medias,
        col_ocultar_variacoes,
        col_incluir_consolidado,
        col_apres_dir,
    ) = st.columns(
        [
            1.0,
            1.8,
            1.8,
            1.55,
            1.0,
        ]
    )


    with col_ocultar_medias:

        ocultar_medias_cruz = st.toggle(
            "Ocultar gráfico de médias",
            key="cruz_ocultar_medias",
            disabled=(
                ano_ini_cruz
                is None
            ),
            help=(
                "Exibe somente as variações entre os dois anos mais recentes selecionados."
            ),
            on_change=ao_alterar_ocultar_medias,
        )


    with col_ocultar_variacoes:

        ocultar_variacoes_cruz = st.toggle(
            "Ocultar gráfico de variações",
            key="cruz_ocultar_variacoes",
            disabled=(
                ano_ini_cruz
                is None
            ),
            help=(
                "Exibe somente o gráfico de médias ponderadas."
            ),
            on_change=ao_alterar_ocultar_variacoes,
        )


    with col_incluir_consolidado:

        incluir_consolidado_cruz = st.toggle(
            "Incluir Consolidado",
            key="cruz_incluir_consolidado",
            help=(
                "Adiciona o resultado consolidado acima das categorias."
            ),
        )


    # ========================================================
    # UMA DIMENSÃO
    #
    # Quando a 2ª dimensão está como "<vazio>", o painel
    # utiliza apenas a 1ª dimensão.
    # ========================================================

    if variavel_2 == SEM_ESCOLHA:

        resultado_cruz = (
            media_ponderada_por_categoria(
                df=df_cruz,
                indicador=indicador_cruz,
                anos=anos_cruz,
                eixo_painel=variavel_1,
            )
        )


        if (
            variavel_1
            in VARIAVEIS_TIPO_ESCOLA
            and
            not mostrar_integral_agregado_para(variavel_1)
        ):

            resultado_cruz = (
                resultado_cruz[
                    resultado_cruz[
                        "Categoria"
                    ]
                    != CATEGORIA_INTEGRAL_AGREGADA
                ]
                .copy()
            )


        if resultado_cruz.empty:

            st.warning(
                "Não há resultados para a configuração selecionada."
            )

            st.stop()


        categorias_cruz = (
            resultado_cruz[
                "Categoria"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )


        if ordenacao_cruz == "Número absoluto":

            ordem_categorias_cruz = (
                resultado_cruz[
                    resultado_cruz[
                        "Ano"
                    ]
                    == str(
                        ano_final_cruz
                    )
                ]
                .dropna(
                    subset=[
                        "Média"
                    ]
                )
                .sort_values(
                    "Média",
                    ascending=False,
                )[
                    "Categoria"
                ]
                .astype(str)
                .tolist()
            )


        elif ordenacao_cruz == "Ordem para gráfico":

            ordem_categorias_cruz = ordenar_dimensao_para_grafico(
                categorias_cruz,
                variavel_1,
            )


        else:

            if ano_ini_cruz is None:

                ordem_categorias_cruz = (
                    categorias_cruz
                )

            else:

                pivot_ord_cruz = (
                    resultado_cruz[
                        resultado_cruz[
                            "Ano"
                        ].isin(
                            [
                                str(
                                    ano_ini_cruz
                                ),
                                str(
                                    ano_final_cruz
                                ),
                            ]
                        )
                    ]
                    .pivot(
                        index="Categoria",
                        columns="Ano",
                        values="Média",
                    )
                    .reset_index()
                )


                if (
                    str(
                        ano_ini_cruz
                    )
                    in pivot_ord_cruz.columns
                    and
                    str(
                        ano_final_cruz
                    )
                    in pivot_ord_cruz.columns
                ):

                    pivot_ord_cruz[
                        "Delta"
                    ] = (
                        pivot_ord_cruz[
                            str(
                                ano_final_cruz
                            )
                        ]
                        -
                        pivot_ord_cruz[
                            str(
                                ano_ini_cruz
                            )
                        ]
                    )


                    ordem_categorias_cruz = (
                        pivot_ord_cruz
                        .sort_values(
                            "Delta",
                            ascending=False,
                        )[
                            "Categoria"
                        ]
                        .astype(str)
                        .tolist()
                    )

                else:

                    ordem_categorias_cruz = (
                        categorias_cruz
                    )


        for categoria in categorias_cruz:

            if (
                categoria
                not in ordem_categorias_cruz
            ):

                ordem_categorias_cruz.append(
                    categoria
                )


        partes_cruz_uma_dimensao = [
            resultado_cruz
        ]


        if incluir_consolidado_cruz:

            partes_cruz_uma_dimensao.insert(
                0,
                consolidado_cruz,
            )


        dados_cruz_uma_dimensao = pd.concat(
            partes_cruz_uma_dimensao,
            ignore_index=True,
        )


        (
            plot_cruz,
            labels_cruz,
            labels_anos_cruz,
            ordem_linhas_cruz,
        ) = preparar_linhas_horizontais(
            dados=dados_cruz_uma_dimensao,
            anos=anos_cruz,
            categorias=ordem_categorias_cruz,
            ano_inicial=ano_ini_cruz,
            ano_final=ano_final_cruz,
        )


        painel_cruz = criar_painel_horizontal(
            plot=plot_cruz,
            labels_categorias=labels_cruz,
            labels_anos=labels_anos_cruz,
            ordem_linhas=ordem_linhas_cruz,
            indicador=indicador_cruz,
            eixo_nome=variavel_1,
            ano_inicial=ano_ini_cruz,
            ano_final=ano_final_cruz,
            mostrar_medias=(
                not ocultar_medias_cruz
            ),
            mostrar_variacoes=(
                not ocultar_variacoes_cruz
            ),
        )


    # ========================================================
    # DUAS DIMENSÕES
    # ========================================================

    else:

        resultado_cruz = (
            media_ponderada_duas_dimensoes(
                base=df_cruz,
                indicador=indicador_cruz,
                anos=anos_cruz,
                variavel_1=variavel_1,
                variavel_2=variavel_2,
                incluir_integral_agregado=(
                    mostrar_integral_agregado_para(
                        variavel_1,
                        variavel_2,
                    )
                ),
            )
        )


        if resultado_cruz.empty:

            st.warning(
                "Não há dados para essa combinação."
            )

            st.stop()


        ordem_nivel_1 = ordenar_dimensao(
            resultado_cruz[
                "Categoria_1"
            ]
            .dropna()
            .unique(),
            variavel_1,
        )


        ordem_nivel_2 = ordenar_dimensao(
            resultado_cruz[
                "Categoria_2"
            ]
            .dropna()
            .unique(),
            variavel_2,
        )


        if ordenacao_cruz == "Número absoluto":

            ranking_n1 = (
                resultado_cruz[
                    resultado_cruz[
                        "Ano"
                    ]
                    == str(
                        ano_final_cruz
                    )
                ]
                .groupby(
                    "Categoria_1",
                    as_index=False,
                )[
                    "Média"
                ]
                .mean()
                .sort_values(
                    "Média",
                    ascending=False,
                )
            )


            ordem_temp = (
                ranking_n1[
                    "Categoria_1"
                ]
                .astype(str)
                .tolist()
            )


            ordem_nivel_1 = (
                ordem_temp
                +
                [
                    x
                    for x
                    in ordem_nivel_1
                    if x
                    not in ordem_temp
                ]
            )


        elif (
            ordenacao_cruz
            == "Delta"
            and
            ano_ini_cruz
            is not None
        ):

            pivot_delta = (
                resultado_cruz[
                    resultado_cruz[
                        "Ano"
                    ].isin(
                        [
                            str(
                                ano_ini_cruz
                            ),
                            str(
                                ano_final_cruz
                            ),
                        ]
                    )
                ]
                .pivot(
                    index=[
                        "Categoria_1",
                        "Categoria_2",
                    ],
                    columns="Ano",
                    values="Média",
                )
                .reset_index()
            )


            col_ini = str(
                ano_ini_cruz
            )


            col_fim = str(
                ano_final_cruz
            )


            if (
                col_ini
                in pivot_delta.columns
                and
                col_fim
                in pivot_delta.columns
            ):

                pivot_delta[
                    "Delta"
                ] = (
                    pivot_delta[
                        col_fim
                    ]
                    -
                    pivot_delta[
                        col_ini
                    ]
                )


                ranking_n1 = (
                    pivot_delta
                    .groupby(
                        "Categoria_1",
                        as_index=False,
                    )[
                        "Delta"
                    ]
                    .mean()
                    .sort_values(
                        "Delta",
                        ascending=False,
                    )
                )


                ordem_temp = (
                    ranking_n1[
                        "Categoria_1"
                    ]
                    .astype(str)
                    .tolist()
                )


                ordem_nivel_1 = (
                    ordem_temp
                    +
                    [
                        x
                        for x
                        in ordem_nivel_1
                        if x
                        not in ordem_temp
                    ]
                )


        elif ordenacao_cruz == "Ordem para gráfico":

            ordem_nivel_1 = ordenar_dimensao_para_grafico(
                resultado_cruz[
                    "Categoria_1"
                ]
                .dropna()
                .astype(str)
                .unique(),
                variavel_1,
            )

            ordem_nivel_2 = ordenar_dimensao_para_grafico(
                resultado_cruz[
                    "Categoria_2"
                ]
                .dropna()
                .astype(str)
                .unique(),
                variavel_2,
            )


        (
            plot_cruz,
            labels_n1,
            labels_n2,
            labels_anos_cruz,
            ordem_linhas_cruz,
        ) = preparar_linhas_cruzamentos(
            resultado=resultado_cruz,
            consolidado=(
                consolidado_cruz
                if incluir_consolidado_cruz
                else consolidado_cruz.iloc[0:0].copy()
            ),
            anos=anos_cruz,
            ordem_nivel_1=ordem_nivel_1,
            ordem_nivel_2=ordem_nivel_2,
            ano_inicial=ano_ini_cruz,
            ano_final=ano_final_cruz,
        )


        painel_cruz = (
            criar_painel_cruzamentos(
                plot=plot_cruz,
                labels_nivel_1=labels_n1,
                labels_nivel_2=labels_n2,
                labels_anos=labels_anos_cruz,
                ordem_linhas=ordem_linhas_cruz,
                indicador=indicador_cruz,
                variavel_1=variavel_1,
                variavel_2=variavel_2,
                ano_inicial=ano_ini_cruz,
                ano_final=ano_final_cruz,
                mostrar_medias=(
                    not ocultar_medias_cruz
                ),
                mostrar_variacoes=(
                    not ocultar_variacoes_cruz
                ),
            )
        )


    # Centraliza a composição do painel (média ponderada + variação).
    col_princ_esq, col_princ_centro, col_princ_dir = st.columns(
        [0.7, 8.6, 0.7]
    )


    with col_princ_centro:

        st.altair_chart(
            aplicar_fundo_grafico(
                painel_cruz
            ),
            theme=None,
            width="stretch",
        )


    st.stop()


# ============================================================
# HISTÓRIA DO ANO
# ============================================================

if pagina == "HISTÓRIA DO ANO":

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:23px;
            font-weight:750;
            letter-spacing:-0.02em;
            color:#27364A;
            margin-bottom:0.25rem;
        ">
            DECOMPOSIÇÃO
        </div>
        """,
        unsafe_allow_html=True,
    )


    opcoes_historia = list(
        EIXOS_DISPONIVEIS.keys()
    )


    SEM_ESCOLHA_HISTORIA = "<vazio>"


    h1, h2, h3, h4 = st.columns(
        [
            1.35,
            1.35,
            1.10,
            0.95,
        ]
    )


    with h1:

        historia_var_1 = st.selectbox(
            "1ª dimensão",
            opcoes_historia,
            index=(
                opcoes_historia.index(
                    "INSE"
                )
                if "INSE"
                in opcoes_historia
                else 0
            ),
            format_func=rotulo_dimensao,
            key="historia_var_1",
        )


    opcoes_historia_2 = [
        SEM_ESCOLHA_HISTORIA,
        *[
            item
            for item
            in opcoes_historia
            if item
            != historia_var_1
        ],
    ]


    with h2:

        historia_var_2 = st.selectbox(
            "2ª dimensão",
            opcoes_historia_2,
            index=0,
            format_func=(
                lambda valor:
                    SEM_ESCOLHA_HISTORIA
                    if valor
                    == SEM_ESCOLHA_HISTORIA
                    else rotulo_dimensao(
                        valor
                    )
            ),
            key="historia_var_2",
        )


    with h3:

        historia_ordenacao = st.selectbox(
            "Ordenação",
            [
                "Número absoluto",
                "Ordem para gráfico",
            ],
            key="historia_ordenacao",
        )


    with h4:

        historia_ano = st.selectbox(
            "Ano",
            options=ANOS_PAINEL,
            index=(
                len(
                    ANOS_PAINEL
                )
                - 1
            ),
            key="historia_ano",
        )


    _, col_hist_consolidado, __ = st.columns(
        [
            2.6,
            1.4,
            2.6,
        ]
    )


    with col_hist_consolidado:

        incluir_consolidado_historia = st.toggle(
            "Incluir Consolidado",
            value=False,
            key="historia_incluir_consolidado",
            help=(
                "Adiciona o resultado consolidado como primeira categoria nas duas fórmulas."
            ),
        )


    df_historia = df.copy()


    indicadores_etapa_1 = [
        "IDEB",
        "N",
        "Rendimento",
    ]


    indicadores_etapa_2 = [
        "N",
        "N(LP)",
        "N(M)",
    ]


    if (
        historia_var_2
        == SEM_ESCOLHA_HISTORIA
    ):

        bloco_historia_1 = (
            _preparar_bloco_historia_uma_dimensao(
                base=df_historia,
                ano=historia_ano,
                variavel=historia_var_1,
                ordenacao=historia_ordenacao,
                indicadores=(
                    indicadores_etapa_1
                ),
                incluir_integral_agregado=(
                    mostrar_integral_agregado_para(
                        historia_var_1
                    )
                ),
                incluir_consolidado=(
                    incluir_consolidado_historia
                ),
            )
        )


        bloco_historia_2 = (
            _preparar_bloco_historia_uma_dimensao(
                base=df_historia,
                ano=historia_ano,
                variavel=historia_var_1,
                ordenacao=historia_ordenacao,
                indicadores=(
                    indicadores_etapa_2
                ),
                incluir_integral_agregado=(
                    mostrar_integral_agregado_para(
                        historia_var_1
                    )
                ),
                incluir_consolidado=(
                    incluir_consolidado_historia
                ),
            )
        )


        if (
            bloco_historia_1 is None
            or
            bloco_historia_2 is None
        ):

            st.warning(
                "Não há resultados para a configuração selecionada."
            )

            st.stop()


        formula_historia_1 = (
            _montar_formula_historia_uma_dimensao(
                bloco=bloco_historia_1,
                indicadores=(
                    indicadores_etapa_1
                ),
                simbolos=[
                    "=",
                    "×",
                ],
                ano=historia_ano,
                titulo_formula=(
                    "IDEB = N × Rendimento"
                ),
            )
        )


        formula_historia_2 = (
            _montar_formula_historia_uma_dimensao(
                bloco=bloco_historia_2,
                indicadores=(
                    indicadores_etapa_2
                ),
                simbolos=[
                    "= (",
                    "+",
                    ") ÷ 2",
                ],
                ano=historia_ano,
                titulo_formula=[
                    "          N(LP) + N(M)",
                    "N =       ─────────────",
                    "                 2",
                ],
            )
        )


    else:

        bloco_historia_1 = (
            _preparar_bloco_historia_duas_dimensoes(
                base=df_historia,
                ano=historia_ano,
                variavel_1=historia_var_1,
                variavel_2=historia_var_2,
                ordenacao=historia_ordenacao,
                indicadores=(
                    indicadores_etapa_1
                ),
                incluir_integral_agregado=(
                    mostrar_integral_agregado_para(
                        historia_var_1,
                        historia_var_2,
                    )
                ),
                incluir_consolidado=(
                    incluir_consolidado_historia
                ),
            )
        )


        bloco_historia_2 = (
            _preparar_bloco_historia_duas_dimensoes(
                base=df_historia,
                ano=historia_ano,
                variavel_1=historia_var_1,
                variavel_2=historia_var_2,
                ordenacao=historia_ordenacao,
                indicadores=(
                    indicadores_etapa_2
                ),
                incluir_integral_agregado=(
                    mostrar_integral_agregado_para(
                        historia_var_1,
                        historia_var_2,
                    )
                ),
                incluir_consolidado=(
                    incluir_consolidado_historia
                ),
            )
        )


        if (
            bloco_historia_1 is None
            or
            bloco_historia_2 is None
        ):

            st.warning(
                "Não há resultados para a configuração selecionada."
            )

            st.stop()


        formula_historia_1 = (
            _montar_formula_historia_duas_dimensoes(
                bloco=bloco_historia_1,
                indicadores=(
                    indicadores_etapa_1
                ),
                simbolos=[
                    "=",
                    "×",
                ],
                ano=historia_ano,
                titulo_formula=(
                    "IDEB = N × Rendimento"
                ),
            )
        )


        formula_historia_2 = (
            _montar_formula_historia_duas_dimensoes(
                bloco=bloco_historia_2,
                indicadores=(
                    indicadores_etapa_2
                ),
                simbolos=[
                    "= (",
                    "+",
                    ") ÷ 2",
                ],
                ano=historia_ano,
                titulo_formula=[
                    "          N(LP) + N(M)",
                    "N =       ─────────────",
                    "                 2",
                ],
            )
        )


    painel_historia_ano = (
        alt.vconcat(
            formula_historia_1,
            formula_historia_2,
            spacing=38,
        )
        .resolve_scale(
            y="independent"
        )
    )


    col_hist_esq, col_hist_centro, col_hist_dir = st.columns(
        [
            0.35,
            9.30,
            0.35,
        ]
    )


    with col_hist_centro:

        st.altair_chart(
            aplicar_fundo_grafico(
                painel_historia_ano
            ),
            theme=None,
            width="stretch",
        )


# ============================================================
# MAPA DE CALOR
# ============================================================

if pagina == "MAPA DE CALOR":

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:23px;
            font-weight:750;
            letter-spacing:-0.02em;
            color:#27364A;
            margin-bottom:0.25rem;
        ">
            TRANSIÇÕES
        </div>
        <div class="transitions-subtitle">
            Acompanhe como as escolas mudam de categoria entre dois anos e
            compare resultados, variações e volumes em cada trajetória.
        </div>
        """,
        unsafe_allow_html=True,
    )


    opcoes_mapa = list(
        EIXOS_DISPONIVEIS.keys()
    )


    st.markdown(
        '<div class="transitions-control-caption">Configuração da análise</div>',
        unsafe_allow_html=True,
    )


    mapa_lateral_esq, mapa_c1, mapa_c2, mapa_lateral_dir = st.columns(
        [
            0.45,
            1.35,
            1.65,
            0.45,
        ],
        gap="large",
    )


    with mapa_c1:

        indicador_mapa = st.selectbox(
            "Indicador",
            [
                "IDEB",
                "N(LP)",
                "N(M)",
                "N",
                "Rendimento",
            ],
            key="mapa_indicador",
        )


    with mapa_c2:

        variavel_mapa = st.selectbox(
            "Dimensão",
            options=opcoes_mapa,
            index=(
                opcoes_mapa.index("INSE")
                if "INSE" in opcoes_mapa
                else 0
            ),
            format_func=rotulo_dimensao,
            key="mapa_variavel",
        )


    st.markdown(
        '<div class="transitions-control-caption" style="margin-top:0.30rem;">Anos da comparação</div>',
        unsafe_allow_html=True,
    )


    _, bloco_mapa_anos, __ = st.columns(
        [
            1.15,
            4.7,
            1.15,
        ]
    )


    with bloco_mapa_anos:

        cols_mapa_anos = st.columns(5)

        defaults_mapa = {
            2017: False,
            2019: False,
            2021: False,
            2023: True,
            2025: True,
        }

        selecao_mapa = {}


        for col, ano in zip(
            cols_mapa_anos,
            ANOS_PAINEL,
        ):

            with col:

                selecao_mapa[ano] = st.checkbox(
                    str(ano),
                    value=defaults_mapa[ano],
                    key=f"mapa_ano_{ano}",
                )


    anos_mapa = sorted(
        [
            ano
            for ano, ativo
            in selecao_mapa.items()
            if ativo
        ]
    )


    if len(anos_mapa) != 2:

        st.warning(
            "Selecione exatamente dois anos para construir as matrizes."
        )

        st.stop()


    ano_inicial_mapa, ano_final_mapa = anos_mapa


    base_mapa = _preparar_base_mapa_calor(
        base=df,
        indicador=indicador_mapa,
        variavel=variavel_mapa,
        ano_inicial=ano_inicial_mapa,
        ano_final=ano_final_mapa,
    )


    if base_mapa.empty:

        st.info(
            "Não há escolas presentes nos dois anos para a configuração selecionada."
        )

        st.stop()


    categorias_mapa = ordenar_dimensao_para_grafico(
        pd.concat(
            [
                base_mapa["Categoria_inicial"],
                base_mapa["Categoria_final"],
            ],
            ignore_index=True,
        ).dropna().astype(str).unique(),
        variavel_mapa,
    )


    if not categorias_mapa:

        st.info(
            "Não há categorias disponíveis para a dimensão selecionada."
        )

        st.stop()


    rotulo_variavel_mapa = rotulo_dimensao(
        variavel_mapa
    )


    st.markdown(
        f"""
        <div class="transitions-context">
            <span class="transitions-chip transitions-chip-period">
                {ano_inicial_mapa} &nbsp;→&nbsp; {ano_final_mapa}
            </span>
            <span class="transitions-chip">{html.escape(rotulo_variavel_mapa)}</span>
            <span class="transitions-chip">{html.escape(indicador_mapa)}</span>
        </div>
        <div class="transitions-axis-note">
            <strong>Linhas:</strong> {html.escape(rotulo_variavel_mapa)} em {ano_inicial_mapa}
            &nbsp;&nbsp;·&nbsp;&nbsp;
            <strong>Colunas:</strong> {html.escape(rotulo_variavel_mapa)} em {ano_final_mapa}
            &nbsp;&nbsp;·&nbsp;&nbsp;
            verde indica valores relativamente maiores e vermelho valores menores dentro de cada matriz.
            As margens de <strong>Consolidado</strong> permanecem em cinza.
        </div>
        """,
        unsafe_allow_html=True,
    )


    especificacoes_mapa = [
        (
            "media_inicial",
            f"{indicador_mapa} · {ano_inicial_mapa}",
            "Média ponderada por matrículas",
        ),
        (
            "media_final",
            f"{indicador_mapa} · {ano_final_mapa}",
            "Média ponderada por matrículas",
        ),
        (
            "delta",
            f"Variação · {ano_final_mapa} − {ano_inicial_mapa}",
            f"Média da variação de {indicador_mapa}",
        ),
        (
            "escolas",
            "Escolas",
            "Total de escolas no recorte",
        ),
        (
            "matriculas",
            f"Matrículas · {ano_final_mapa}",
            f"Total de matrículas em {ano_final_mapa}",
        ),
    ]


    graficos_mapa = []


    for indice_matriz, (
        tipo_mapa,
        titulo_mapa,
        subtitulo_mapa,
    ) in enumerate(especificacoes_mapa, start=1):

        dados_matriz = _montar_dados_matriz_mapa(
            base_cruzada=base_mapa,
            categorias=categorias_mapa,
            tipo=tipo_mapa,
            indicador=indicador_mapa,
        )


        # Em cada linha de matrizes, os rótulos das linhas aparecem
        # somente na primeira matriz. Como todas usam a mesma ordem,
        # isso reduz ruído sem perder informação.
        mostrar_rotulos = indice_matriz in {
            1,
            4,
        }


        grafico_matriz = _criar_matriz_mapa_calor(
            dados=dados_matriz,
            categorias=categorias_mapa,
            titulo=titulo_mapa,
            subtitulo=subtitulo_mapa,
            mostrar_rotulos_linhas=mostrar_rotulos,
        )


        graficos_mapa.append(
            grafico_matriz
        )


    st.markdown(
        """
        <div class="transitions-section">
            <div class="transitions-section-title">Desempenho e variação</div>
            <div class="transitions-section-text">
                Compare o resultado no início e no fim do período e observe a variação
                das escolas em cada combinação de categorias.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # Primeira linha: as três matrizes de desempenho lado a lado.
    mapa_top_1, mapa_top_2, mapa_top_3 = st.columns(
        [
            1,
            1,
            1,
        ],
        gap="medium",
    )


    for indice, (
        coluna,
        grafico,
    ) in enumerate(
        zip(
            [
                mapa_top_1,
                mapa_top_2,
                mapa_top_3,
            ],
            graficos_mapa[:3],
        ),
        start=1,
    ):

        with coluna:

            st.altair_chart(
                aplicar_fundo_grafico(
                    grafico
                ),
                theme=None,
                width="stretch",
                key=f"mapa_calor_matriz_{indice}",
            )


    st.markdown(
        """
        <div class="transitions-section" style="margin-top:1.65rem;">
            <div class="transitions-section-title">Volume do recorte</div>
            <div class="transitions-section-text">
                Dimensione cada trajetória pelo número de escolas e pelo volume de matrículas.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # Segunda linha: as matrizes de volume lado a lado e centralizadas,
    # usando a mesma largura relativa das matrizes da linha superior.
    mapa_inf_esq, mapa_inf_1, mapa_inf_2, mapa_inf_dir = st.columns(
        [
            0.45,
            1,
            1,
            0.45,
        ],
        gap="medium",
    )


    for indice, (
        coluna,
        grafico,
    ) in enumerate(
        zip(
            [
                mapa_inf_1,
                mapa_inf_2,
            ],
            graficos_mapa[3:],
        ),
        start=4,
    ):

        with coluna:

            st.altair_chart(
                aplicar_fundo_grafico(
                    grafico
                ),
                theme=None,
                width="stretch",
                key=f"mapa_calor_matriz_{indice}",
            )


    st.markdown(
        f"""
        <div class="transitions-axis-note" style="margin-top:1.35rem; margin-bottom:0.2rem;">
            As médias são ponderadas por matrículas. A matriz de matrículas utiliza as matrículas
            de {ano_final_mapa}. A escala de cores é calculada separadamente em cada matriz,
            sempre desconsiderando a linha e a coluna de Consolidado.
        </div>
        """,
        unsafe_allow_html=True,
    )


    st.stop()


# ============================================================
# DEMOGRAFIA
# ============================================================

if pagina == "DEMOGRAFIA":

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:23px;
            font-weight:750;
            letter-spacing:-0.02em;
            color:#27364A;
            margin-bottom:0.5rem;
        ">
            COMPOSIÇÃO
        </div>
        """,
        unsafe_allow_html=True,
    )


    d1, d2, d3 = st.columns(
        [
            1,
            1.4,
            1.4,
        ]
    )


    with d1:

        ano_demografia = st.selectbox(
            "Ano de referência",
            options=ANOS_PAINEL,
            index=4,
            key="ano_demografia",
        )


    opcoes_demo = list(
        EIXOS_DISPONIVEIS.keys()
    )


    with d2:

        variavel_demo = st.selectbox(
            "Variável das barras",
            options=opcoes_demo,
            index=(
                opcoes_demo.index(
                    "PPI"
                )
                if "PPI"
                in opcoes_demo
                else 0
            ),
            format_func=rotulo_dimensao,
            key="demo_variavel_barras",
        )


    op_comp = [
        x
        for x
        in opcoes_demo
        if x
        != variavel_demo
    ]


    with d3:

        variavel_comp = st.selectbox(
            "Composição das barras",
            options=op_comp,
            index=(
                op_comp.index(
                    "INSE"
                )
                if "INSE"
                in op_comp
                else 0
            ),
            format_func=rotulo_dimensao,
            key="demo_variavel_comp",
        )


    # ========================================================
    # CONTROLES DE EXIBIÇÃO
    #
    # Um único par de botões controla simultaneamente os gráficos
    # de escolas e de matrículas. Como em Principais Indicadores,
    # impedimos que os dois tipos de gráfico sejam ocultados ao
    # mesmo tempo.
    # ========================================================

    if "demo_ocultar_distribuicao" not in st.session_state:

        st.session_state[
            "demo_ocultar_distribuicao"
        ] = False


    if "demo_ocultar_totais" not in st.session_state:

        st.session_state[
            "demo_ocultar_totais"
        ] = False


    def ao_alterar_ocultar_distribuicao_demo():

        if st.session_state.get(
            "demo_ocultar_distribuicao",
            False,
        ):

            st.session_state[
                "demo_ocultar_totais"
            ] = False


    def ao_alterar_ocultar_totais_demo():

        if st.session_state.get(
            "demo_ocultar_totais",
            False,
        ):

            st.session_state[
                "demo_ocultar_distribuicao"
            ] = False


    (
        col_demo_ctrl_esq,
        col_demo_ocultar_distribuicao,
        col_demo_ocultar_totais,
        col_demo_incluir_consolidado,
        col_demo_ctrl_dir,
    ) = st.columns(
        [
            1.0,
            1.8,
            1.8,
            1.55,
            1.0,
        ]
    )


    with col_demo_ocultar_distribuicao:

        ocultar_distribuicao_demo = st.toggle(
            "Ocultar gráfico de distribuição",
            key="demo_ocultar_distribuicao",
            help=(
                "Oculta o gráfico percentual tanto em Escolas quanto "
                "em Matrículas, mantendo apenas os gráficos de totais."
            ),
            on_change=ao_alterar_ocultar_distribuicao_demo,
        )


    with col_demo_ocultar_totais:

        ocultar_totais_demo = st.toggle(
            "Ocultar gráfico de totais",
            key="demo_ocultar_totais",
            help=(
                "Oculta os gráficos de totais tanto em Escolas quanto "
                "em Matrículas, mantendo apenas as distribuições."
            ),
            on_change=ao_alterar_ocultar_totais_demo,
        )


    with col_demo_incluir_consolidado:

        incluir_consolidado_demo = st.toggle(
            "Incluir Consolidado",
            value=False,
            key="demo_incluir_consolidado",
            help=(
                "Inclui a barra consolidada nos blocos de Escolas e Matrículas."
            ),
        )


    base_demo = (
        df[
            df[
                "Ano"
            ]
            == ano_demografia
        ]
        .drop_duplicates(
            "Cód. INEP"
        )
        .copy()
    )


    temp_g = criar_variavel_eixo(
        base_demo,
        variavel_demo,
    )


    temp_c = criar_variavel_eixo(
        base_demo,
        variavel_comp,
    )


    base_demo[
        "Grupo"
    ] = temp_g[
        "Categoria"
    ].values


    base_demo[
        "Composição"
    ] = temp_c[
        "Categoria"
    ].values


    if (
        variavel_demo
        in VARIAVEIS_TIPO_ESCOLA
        and
        mostrar_integral_agregado_para(variavel_demo)
    ):

        temp = (
            base_demo[
                base_demo[
                    "Grupo"
                ].isin(
                    [
                        "Mista",
                        "100% Integral",
                    ]
                )
            ]
            .copy()
        )


        temp[
            "Grupo"
        ] = (
            CATEGORIA_INTEGRAL_AGREGADA
        )


        base_demo = pd.concat(
            [
                base_demo,
                temp,
            ],
            ignore_index=True,
        )


    ordem_grupos = ordenar_dimensao(
        base_demo[
            "Grupo"
        ].unique(),
        variavel_demo,
    )


    ordem_comp = ordenar_dimensao(
        base_demo[
            "Composição"
        ].unique(),
        variavel_comp,
    )


    resumo = (
        base_demo
        .groupby(
            [
                "Grupo",
                "Composição",
            ],
            as_index=False,
        )
        .agg(
            Escolas=(
                "Cód. INEP",
                "nunique",
            )
        )
    )


    totais = (
        resumo
        .groupby(
            "Grupo",
            as_index=False,
        )[
            "Escolas"
        ]
        .sum()
        .rename(
            columns={
                "Escolas":
                    "Total"
            }
        )
    )


    resumo = resumo.merge(
        totais,
        on="Grupo",
    )


    resumo[
        "Percentual"
    ] = np.where(
        resumo[
            "Total"
        ]
        > 0,
        resumo[
            "Escolas"
        ]
        /
        resumo[
            "Total"
        ],
        0,
    )


    # ========================================================
    # RESUMO DE MATRÍCULAS PARA A ORDENAÇÃO COMPARTILHADA
    #
    # Este resumo é calculado antes da renderização dos dois blocos
    # para que um clique em Escolas possa ordenar Matrículas e um
    # clique em Matrículas possa ordenar Escolas. O bloco completo
    # de Matrículas continua sendo construído abaixo.
    # ========================================================

    coluna_matriculas_demo = (
        "Matrículas EM (total) 3/4"
    )


    base_demo_matriculas_ordem = base_demo.copy()


    base_demo_matriculas_ordem[
        "Matrículas"
    ] = (
        pd.to_numeric(
            base_demo_matriculas_ordem[
                coluna_matriculas_demo
            ],
            errors="coerce",
        )
        .fillna(0)
        .clip(lower=0)
    )


    resumo_matriculas_ordem = (
        base_demo_matriculas_ordem
        .groupby(
            [
                "Grupo",
                "Composição",
            ],
            as_index=False,
        )
        .agg(
            Matrículas=(
                "Matrículas",
                "sum",
            )
        )
    )


    totais_matriculas_ordem = (
        resumo_matriculas_ordem
        .groupby(
            "Grupo",
            as_index=False,
        )[
            "Matrículas"
        ]
        .sum()
        .rename(
            columns={
                "Matrículas":
                    "Total"
            }
        )
    )


    resumo_matriculas_ordem = resumo_matriculas_ordem.merge(
        totais_matriculas_ordem,
        on="Grupo",
    )


    resumo_matriculas_ordem[
        "Percentual"
    ] = np.where(
        resumo_matriculas_ordem[
            "Total"
        ]
        > 0,
        resumo_matriculas_ordem[
            "Matrículas"
        ]
        /
        resumo_matriculas_ordem[
            "Total"
        ],
        0,
    )


    # ========================================================
    # ORDENAÇÃO INTERATIVA POR SEÇÃO DA BARRA
    #
    # O gráfico registra a categoria de composição clicada. No
    # rerun seguinte, os grupos (exceto Consolidado) são ordenados
    # do maior para o menor percentual nessa categoria.
    # ========================================================

    def extrair_valor_selecao_demo(objeto, campo):

        if objeto is None:

            return None


        if hasattr(
            objeto,
            "items",
        ):

            try:

                itens = list(
                    objeto.items()
                )

            except Exception:

                itens = []


            for chave, valor in itens:

                if str(
                    chave
                ) == campo:

                    if isinstance(
                        valor,
                        (list, tuple),
                    ):

                        return (
                            valor[0]
                            if valor
                            else None
                        )


                    return valor


            for _, valor in itens:

                encontrado = extrair_valor_selecao_demo(
                    valor,
                    campo,
                )


                if encontrado is not None:

                    return encontrado


        if isinstance(
            objeto,
            (list, tuple),
        ):

            for item in objeto:

                encontrado = extrair_valor_selecao_demo(
                    item,
                    campo,
                )


                if encontrado is not None:

                    return encontrado


        return None


    def obter_composicao_selecionada_demo(
        chave_estado,
        nome_selecao,
    ):

        estado = st.session_state.get(
            chave_estado
        )


        if estado is None:

            return None


        try:

            selecoes = estado.selection

        except Exception:

            selecoes = (
                estado.get(
                    "selection",
                    {},
                )
                if hasattr(
                    estado,
                    "get",
                )
                else {}
            )


        selecao = (
            selecoes.get(
                nome_selecao,
                None,
            )
            if hasattr(
                selecoes,
                "get",
            )
            else None
        )


        return extrair_valor_selecao_demo(
            selecao,
            "Composição",
        )


    composicao_selecionada_escolas = (
        obter_composicao_selecionada_demo(
            "grafico_demografia_interativo",
            "selecionar_composicao_demo",
        )
    )


    composicao_selecionada_matriculas = (
        obter_composicao_selecionada_demo(
            "grafico_demografia_matriculas_interativo",
            "selecionar_composicao_matriculas_demo",
        )
    )


    selecao_escolas_anterior = st.session_state.get(
        "_demo_selecao_escolas_anterior"
    )


    selecao_matriculas_anterior = st.session_state.get(
        "_demo_selecao_matriculas_anterior"
    )


    mudou_selecao_escolas = (
        composicao_selecionada_escolas
        != selecao_escolas_anterior
    )


    mudou_selecao_matriculas = (
        composicao_selecionada_matriculas
        != selecao_matriculas_anterior
    )


    # O gráfico que mudou no último rerun passa a ser a referência
    # de ordenação para os DOIS blocos. Assim, ao clicar em Escolas,
    # Matrículas segue a ordem de Escolas; ao clicar em Matrículas,
    # Escolas segue a ordem de Matrículas.
    if (
        mudou_selecao_escolas
        and
        not mudou_selecao_matriculas
    ):

        st.session_state[
            "_demo_fonte_ordenacao"
        ] = "escolas"

        st.session_state[
            "_demo_composicao_ordenacao"
        ] = composicao_selecionada_escolas


    elif (
        mudou_selecao_matriculas
        and
        not mudou_selecao_escolas
    ):

        st.session_state[
            "_demo_fonte_ordenacao"
        ] = "matriculas"

        st.session_state[
            "_demo_composicao_ordenacao"
        ] = composicao_selecionada_matriculas


    elif (
        mudou_selecao_escolas
        and
        mudou_selecao_matriculas
    ):

        # Caso raro em que os dois estados mudam no mesmo rerun:
        # prioriza a seleção válida não vazia; se ambas existirem,
        # Matrículas fica como a interação mais abaixo na página.
        if composicao_selecionada_matriculas is not None:

            st.session_state[
                "_demo_fonte_ordenacao"
            ] = "matriculas"

            st.session_state[
                "_demo_composicao_ordenacao"
            ] = composicao_selecionada_matriculas

        else:

            st.session_state[
                "_demo_fonte_ordenacao"
            ] = "escolas"

            st.session_state[
                "_demo_composicao_ordenacao"
            ] = composicao_selecionada_escolas


    st.session_state[
        "_demo_selecao_escolas_anterior"
    ] = composicao_selecionada_escolas


    st.session_state[
        "_demo_selecao_matriculas_anterior"
    ] = composicao_selecionada_matriculas


    fonte_ordenacao_demo = st.session_state.get(
        "_demo_fonte_ordenacao"
    )


    composicao_ordenacao_demo = st.session_state.get(
        "_demo_composicao_ordenacao"
    )


    if composicao_ordenacao_demo not in ordem_comp:

        fonte_ordenacao_demo = None
        composicao_ordenacao_demo = None

        st.session_state[
            "_demo_fonte_ordenacao"
        ] = None

        st.session_state[
            "_demo_composicao_ordenacao"
        ] = None


    if composicao_ordenacao_demo in ordem_comp:

        if fonte_ordenacao_demo == "matriculas":

            resumo_referencia_ordenacao = (
                resumo_matriculas_ordem
            )

        else:

            resumo_referencia_ordenacao = resumo


        percentuais_para_ordem = (
            resumo_referencia_ordenacao[
                resumo_referencia_ordenacao[
                    "Composição"
                ]
                == composicao_ordenacao_demo
            ]
            .groupby(
                "Grupo"
            )[
                "Percentual"
            ]
            .sum()
            .to_dict()
        )


        ordem_original_demo = {
            grupo: indice
            for indice, grupo
            in enumerate(
                ordem_grupos
            )
        }


        ordem_grupos = sorted(
            ordem_grupos,
            key=lambda grupo: (
                -float(
                    percentuais_para_ordem.get(
                        grupo,
                        0,
                    )
                ),
                ordem_original_demo.get(
                    grupo,
                    9999,
                ),
            ),
        )


    # ========================================================
    # CONSOLIDADO
    # ========================================================

    base_consolidado = (
        df[
            df[
                "Ano"
            ]
            == ano_demografia
        ]
        .drop_duplicates(
            "Cód. INEP"
        )
        .copy()
    )


    temp_cons = criar_variavel_eixo(
        base_consolidado,
        variavel_comp,
    )


    base_consolidado[
        "Composição"
    ] = temp_cons[
        "Categoria"
    ].values


    cons = (
        base_consolidado
        .groupby(
            "Composição",
            as_index=False,
        )
        .agg(
            Escolas=(
                "Cód. INEP",
                "nunique",
            )
        )
    )


    total_cons = int(
        cons[
            "Escolas"
        ].sum()
    )


    cons[
        "Percentual"
    ] = np.where(
        total_cons > 0,
        cons[
            "Escolas"
        ]
        / total_cons,
        0,
    )


    cons[
        "Grupo"
    ] = "Consolidado"


    cons[
        "Total"
    ] = total_cons


    # ========================================================
    # CONSOLIDADO OPCIONAL / ESPAÇAMENTO
    # ========================================================

    GRUPO_ESPACO = "__espaco__"


    if incluir_consolidado_demo:

        resumo = pd.concat(
            [
                cons,
                resumo,
            ],
            ignore_index=True,
        )


        ordem_barras = (
            [
                "Consolidado",
                GRUPO_ESPACO,
            ]
            +
            ordem_grupos
        )


        espaco_resumo = pd.DataFrame(
            {
                "Composição": [
                    ordem_comp[0]
                    if ordem_comp
                    else ""
                ],
                "Escolas": [0],
                "Percentual": [0],
                "Grupo": [GRUPO_ESPACO],
                "Total": [0],
            }
        )


        resumo_plot = pd.concat(
            [
                resumo,
                espaco_resumo,
            ],
            ignore_index=True,
        )

    else:

        ordem_barras = list(ordem_grupos)
        resumo_plot = resumo.copy()


    resumo_plot = calcular_posicoes_empilhadas(
        dados=resumo_plot,
        grupo="Grupo",
        categoria="Composição",
        valor="Percentual",
        ordem_categorias=ordem_comp,
    )


    # ========================================================
    # PERCENTUAIS
    # ========================================================

    selecao_composicao_demo = alt.selection_point(
        name="selecionar_composicao_demo",
        fields=[
            "Composição"
        ],
        on="click",
        clear="dblclick",
        toggle=False,
    )


    barras_pct = (
        alt.Chart(
            resumo_plot
        )
        .mark_bar(
            height=24,
        )
        .encode(

            # A linha dummy permanece no domínio do eixo Y, mas fica
            # invisível. Isso cria um afastamento exclusivamente depois
            # do Consolidado, sem aumentar o espaço entre as demais barras.
            opacity=alt.condition(
                alt.datum.Grupo
                == GRUPO_ESPACO,
                alt.value(0),
                alt.value(1),
            ),

            y=alt.Y(
                "Grupo:N",
                sort=ordem_barras,
                title=None,
                axis=alt.Axis(
                    labelExpr=(
                        f"datum.label == "
                        f"'{GRUPO_ESPACO}' "
                        f"? '' : datum.label"
                    ),
                    labelFontSize=11.5,
                    labelLimit=175,
                    ticks=False,
                    domain=False,
                ),
            ),

            x=alt.X(
                "Percentual:Q",
                stack="zero",
                title=None,
                axis=None,
                scale=alt.Scale(
                    domain=[
                        0,
                        1,
                    ]
                ),
            ),

            color=alt.Color(
                "Composição:N",
                title=rotulo_dimensao(
                    variavel_comp
                ),
                scale=alt.Scale(
                    domain=ordem_comp,
                    range=PALETA_DISTRIBUICOES[
                        :len(
                            ordem_comp
                        )
                    ],
                ),
            ),

            order=alt.Order(
                "_ordem_categoria:Q"
            ),

            tooltip=[
                alt.Tooltip(
                    "Grupo:N",
                    title=rotulo_dimensao(
                        variavel_demo
                    ),
                ),

                alt.Tooltip(
                    "Composição:N",
                    title=rotulo_dimensao(
                        variavel_comp
                    ),
                ),

                alt.Tooltip(
                    "Escolas:Q",
                    title="Escolas",
                    format="d",
                ),

                alt.Tooltip(
                    "Percentual:Q",
                    title="Percentual",
                    format=".1%",
                ),
            ],
        )
    )


    # ========================================================
    # RÓTULOS CENTRALIZADOS
    #
    # 5% foi usado como corte visual.
    # ========================================================

    dados_texto_pct = (
        resumo_plot[
            (
                resumo_plot[
                    "Grupo"
                ]
                != GRUPO_ESPACO
            )
            &
            (
                resumo_plot[
                    "Percentual"
                ]
                >= 0.05
            )
        ]
        .copy()
    )


    texto_pct = (
        alt.Chart(
            dados_texto_pct
        )
        .mark_text(
            align="center",
            baseline="middle",
            fontSize=12,
        )
        .encode(

            y=alt.Y(
                "Grupo:N",
                sort=ordem_barras,
            ),

            x=alt.X(
                "Centro:Q",
                scale=alt.Scale(
                    domain=[
                        0,
                        1,
                    ]
                ),
            ),

            text=alt.Text(
                "Percentual:Q",
                format=".0%",
            ),
        )
    )


    # ========================================================
    # ALTURA / ESPAÇAMENTO VERTICAL
    #
    # As categorias regulares ficam mais próximas entre si.
    # O Consolidado continua visualmente separado porque há
    # uma categoria dummy (GRUPO_ESPACO) logo após ele.
    # ========================================================

    ALTURA_LINHA_DEMO = 30


    altura_demo = max(
        240,
        len(
            ordem_barras
        )
        * ALTURA_LINHA_DEMO,
    )


    graf_pct = (
        barras_pct
        +
        texto_pct
    ).add_params(
        selecao_composicao_demo
    ).properties(
        width=520,
        height=altura_demo,
        title=alt.TitleParams(
            text=(
                f"Distribuição de "
                f"{rotulo_dimensao(variavel_comp)}"
            ),
            anchor="middle",
            fontSize=17,
            fontWeight="bold",
        ),
    )


    # ========================================================
    # TOTAL DE ESCOLAS
    # ========================================================

    if incluir_consolidado_demo:

        totais_demo = pd.concat(
            [
                pd.DataFrame(
                    {
                        "Grupo": ["Consolidado"],
                        "Total": [total_cons],
                    }
                ),
                pd.DataFrame(
                    {
                        "Grupo": [GRUPO_ESPACO],
                        "Total": [0],
                    }
                ),
                totais,
            ],
            ignore_index=True,
        )

    else:

        totais_demo = totais.copy()


    totais_demo[
        "Total"
    ] = (
        pd.to_numeric(
            totais_demo[
                "Total"
            ],
            errors="coerce",
        )
        .fillna(
            0
        )
        .astype(int)
    )


    barras_n = (
        alt.Chart(
            totais_demo
        )
        .mark_bar(
            height=24,
            color="#5F91BD",
        )
        .encode(

            opacity=alt.condition(
                alt.datum.Grupo
                == GRUPO_ESPACO,
                alt.value(0),
                alt.value(1),
            ),

            y=alt.Y(
                "Grupo:N",
                sort=ordem_barras,
                axis=(
                    alt.Axis(
                        labelExpr=(
                            f"datum.label == "
                            f"'{GRUPO_ESPACO}' "
                            f"? '' : datum.label"
                        ),
                        labelFontSize=11.5,
                        labelLimit=175,
                        ticks=False,
                        domain=False,
                    )
                    if ocultar_distribuicao_demo
                    else None
                ),
            ),

            x=alt.X(
                "Total:Q",
                title=None,
                axis=None,
            ),

            tooltip=[
                alt.Tooltip(
                    "Grupo:N",
                    title=rotulo_dimensao(
                        variavel_demo
                    ),
                ),

                alt.Tooltip(
                    "Total:Q",
                    title="Escolas",
                    format="d",
                ),
            ],
        )
    )


    texto_n = (
        alt.Chart(
            totais_demo[
                totais_demo[
                    "Grupo"
                ]
                != GRUPO_ESPACO
            ]
        )
        .mark_text(
            align="left",
            dx=6,
            fontSize=11,
            fontWeight="bold",
        )
        .encode(

            y=alt.Y(
                "Grupo:N",
                sort=ordem_barras,
            ),

            x="Total:Q",

            # Sem separador de milhar.
            text=alt.Text(
                "Total:Q",
                format="d",
            ),
        )
    )


    graf_n = (
        barras_n
        +
        texto_n
    ).properties(
        width=(
            520
            if ocultar_distribuicao_demo
            else 210
        ),
        height=altura_demo,
        title=alt.TitleParams(
            text="Número de escolas",
            anchor="middle",
            fontSize=17,
            fontWeight="bold",
        ),
    )


    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:18px;
            font-weight:700;
            color:#334155;
            margin-top:0.25rem;
            margin-bottom:0.2rem;
        ">
            Escolas
        </div>
        """,
        unsafe_allow_html=True,
    )


    st.caption(
        "Clique em uma seção colorida do gráfico de percentuais para "
        "ordenar as categorias por essa composição, da maior para a menor. "
        "A mesma ordem será aplicada aos gráficos de Escolas e Matrículas. "
        "Dê um duplo clique para limpar a seleção."
    )


    # Centraliza a composição dos dois gráficos de Demografia.
    col_demo_esq, col_demo_centro, col_demo_dir = st.columns(
        [0.9, 8.2, 0.9]
    )


    with col_demo_centro:

        if ocultar_distribuicao_demo:

            grafico_demografia_completo = graf_n
            grafico_demo_interativo = False


        elif ocultar_totais_demo:

            grafico_demografia_completo = graf_pct
            grafico_demo_interativo = True


        else:

            grafico_demografia_completo = (
                alt.hconcat(
                    graf_pct,
                    graf_n,
                    spacing=20,
                )
                .resolve_scale(
                    y="shared"
                )
                .configure_view(
                    stroke=None
                )
            )

            grafico_demo_interativo = True


        if grafico_demo_interativo:

            st.altair_chart(
                aplicar_fundo_grafico(
                    grafico_demografia_completo
                ),
                theme=None,
                width="stretch",
                key="grafico_demografia_interativo",
                on_select="rerun",
                selection_mode=[
                    "selecionar_composicao_demo"
                ],
            )

        else:

            st.altair_chart(
                aplicar_fundo_grafico(
                    grafico_demografia_completo
                ),
                theme=None,
                width="stretch",
                key="grafico_demografia_totais",
            )


    # ========================================================
    # DEMOGRAFIA — MATRÍCULAS
    # ========================================================

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:18px;
            font-weight:700;
            color:#334155;
            margin-top:1.25rem;
            margin-bottom:0.2rem;
        ">
            Matrículas
        </div>
        """,
        unsafe_allow_html=True,
    )


    st.caption(
        "Os percentuais abaixo representam a distribuição das matrículas. "
        "Clique em uma seção colorida para ordenar as categorias por essa "
        "composição, da maior para a menor. A mesma ordem será aplicada aos "
        "gráficos de Escolas e Matrículas. Dê um duplo clique para limpar."
    )


    # A coluna de matrículas já foi definida acima para permitir
    # a ordenação compartilhada entre os dois blocos.
    base_demo_matriculas = base_demo.copy()

    base_demo_matriculas[
        "Matrículas"
    ] = (
        pd.to_numeric(
            base_demo_matriculas[
                coluna_matriculas_demo
            ],
            errors="coerce",
        )
        .fillna(0)
        .clip(lower=0)
    )


    resumo_matriculas = (
        base_demo_matriculas
        .groupby(
            [
                "Grupo",
                "Composição",
            ],
            as_index=False,
        )
        .agg(
            Matrículas=(
                "Matrículas",
                "sum",
            )
        )
    )


    totais_matriculas = (
        resumo_matriculas
        .groupby(
            "Grupo",
            as_index=False,
        )[
            "Matrículas"
        ]
        .sum()
        .rename(
            columns={
                "Matrículas":
                    "Total"
            }
        )
    )


    resumo_matriculas = resumo_matriculas.merge(
        totais_matriculas,
        on="Grupo",
    )


    resumo_matriculas[
        "Percentual"
    ] = np.where(
        resumo_matriculas[
            "Total"
        ]
        > 0,
        resumo_matriculas[
            "Matrículas"
        ]
        /
        resumo_matriculas[
            "Total"
        ],
        0,
    )


    # A ordem das categorias é única para os dois blocos.
    # Ela foi definida acima a partir do último gráfico clicado
    # (Escolas ou Matrículas).
    ordem_grupos_matriculas = list(
        ordem_grupos
    )


    base_consolidado_matriculas = base_consolidado.copy()

    base_consolidado_matriculas[
        "Matrículas"
    ] = (
        pd.to_numeric(
            base_consolidado_matriculas[
                coluna_matriculas_demo
            ],
            errors="coerce",
        )
        .fillna(0)
        .clip(lower=0)
    )


    cons_matriculas = (
        base_consolidado_matriculas
        .groupby(
            "Composição",
            as_index=False,
        )
        .agg(
            Matrículas=(
                "Matrículas",
                "sum",
            )
        )
    )


    total_cons_matriculas = float(
        cons_matriculas[
            "Matrículas"
        ].sum()
    )


    cons_matriculas[
        "Percentual"
    ] = np.where(
        total_cons_matriculas > 0,
        cons_matriculas[
            "Matrículas"
        ]
        / total_cons_matriculas,
        0,
    )

    cons_matriculas[
        "Grupo"
    ] = "Consolidado"

    cons_matriculas[
        "Total"
    ] = total_cons_matriculas


    if incluir_consolidado_demo:

        resumo_matriculas = pd.concat(
            [
                cons_matriculas,
                resumo_matriculas,
            ],
            ignore_index=True,
        )


        ordem_barras_matriculas = (
            [
                "Consolidado",
                GRUPO_ESPACO,
            ]
            +
            ordem_grupos_matriculas
        )


        espaco_matriculas = pd.DataFrame(
            {
                "Composição": [
                    ordem_comp[0]
                    if ordem_comp
                    else ""
                ],
                "Matrículas": [0],
                "Percentual": [0],
                "Grupo": [GRUPO_ESPACO],
                "Total": [0],
            }
        )


        resumo_matriculas_plot = pd.concat(
            [
                resumo_matriculas,
                espaco_matriculas,
            ],
            ignore_index=True,
        )

    else:

        ordem_barras_matriculas = list(
            ordem_grupos_matriculas
        )

        resumo_matriculas_plot = (
            resumo_matriculas.copy()
        )


    resumo_matriculas_plot = calcular_posicoes_empilhadas(
        dados=resumo_matriculas_plot,
        grupo="Grupo",
        categoria="Composição",
        valor="Percentual",
        ordem_categorias=ordem_comp,
    )


    selecao_composicao_matriculas = alt.selection_point(
        name="selecionar_composicao_matriculas_demo",
        fields=[
            "Composição"
        ],
        on="click",
        clear="dblclick",
        toggle=False,
    )


    barras_pct_matriculas = (
        alt.Chart(
            resumo_matriculas_plot
        )
        .mark_bar(
            height=24,
        )
        .encode(
            opacity=alt.condition(
                alt.datum.Grupo
                == GRUPO_ESPACO,
                alt.value(0),
                alt.value(1),
            ),
            y=alt.Y(
                "Grupo:N",
                sort=ordem_barras_matriculas,
                title=None,
                axis=alt.Axis(
                    labelExpr=(
                        f"datum.label == "
                        f"'{GRUPO_ESPACO}' "
                        f"? '' : datum.label"
                    ),
                    labelFontSize=11.5,
                    labelLimit=175,
                    ticks=False,
                    domain=False,
                ),
            ),
            x=alt.X(
                "Percentual:Q",
                stack="zero",
                title=None,
                axis=None,
                scale=alt.Scale(
                    domain=[
                        0,
                        1,
                    ]
                ),
            ),
            color=alt.Color(
                "Composição:N",
                title=rotulo_dimensao(
                    variavel_comp
                ),
                scale=alt.Scale(
                    domain=ordem_comp,
                    range=PALETA_DISTRIBUICOES[
                        :len(
                            ordem_comp
                        )
                    ],
                ),
            ),
            order=alt.Order(
                "_ordem_categoria:Q"
            ),
            tooltip=[
                alt.Tooltip(
                    "Grupo:N",
                    title=rotulo_dimensao(
                        variavel_demo
                    ),
                ),
                alt.Tooltip(
                    "Composição:N",
                    title=rotulo_dimensao(
                        variavel_comp
                    ),
                ),
                alt.Tooltip(
                    "Matrículas:Q",
                    title="Matrículas",
                    format=".0f",
                ),
                alt.Tooltip(
                    "Percentual:Q",
                    title="Percentual",
                    format=".1%",
                ),
            ],
        )
    )


    dados_texto_pct_matriculas = (
        resumo_matriculas_plot[
            (
                resumo_matriculas_plot[
                    "Grupo"
                ]
                != GRUPO_ESPACO
            )
            &
            (
                resumo_matriculas_plot[
                    "Percentual"
                ]
                >= 0.05
            )
        ]
        .copy()
    )


    texto_pct_matriculas = (
        alt.Chart(
            dados_texto_pct_matriculas
        )
        .mark_text(
            align="center",
            baseline="middle",
            fontSize=12,
        )
        .encode(
            y=alt.Y(
                "Grupo:N",
                sort=ordem_barras_matriculas,
            ),
            x=alt.X(
                "Centro:Q",
                scale=alt.Scale(
                    domain=[
                        0,
                        1,
                    ]
                ),
            ),
            text=alt.Text(
                "Percentual:Q",
                format=".0%",
            ),
        )
    )


    altura_demo_matriculas = max(
        240,
        len(
            ordem_barras_matriculas
        )
        * ALTURA_LINHA_DEMO,
    )


    graf_pct_matriculas = (
        barras_pct_matriculas
        +
        texto_pct_matriculas
    ).add_params(
        selecao_composicao_matriculas
    ).properties(
        width=520,
        height=altura_demo_matriculas,
        title=alt.TitleParams(
            text=(
                f"Distribuição de "
                f"{rotulo_dimensao(variavel_comp)}"
            ),
            anchor="middle",
            fontSize=17,
            fontWeight="bold",
        ),
    )


    if incluir_consolidado_demo:

        totais_demo_matriculas = pd.concat(
            [
                pd.DataFrame(
                    {
                        "Grupo": ["Consolidado"],
                        "Total": [total_cons_matriculas],
                    }
                ),
                pd.DataFrame(
                    {
                        "Grupo": [GRUPO_ESPACO],
                        "Total": [0],
                    }
                ),
                totais_matriculas,
            ],
            ignore_index=True,
        )

    else:

        totais_demo_matriculas = (
            totais_matriculas.copy()
        )


    totais_demo_matriculas[
        "Total"
    ] = (
        pd.to_numeric(
            totais_demo_matriculas[
                "Total"
            ],
            errors="coerce",
        )
        .fillna(0)
        .round()
        .astype(int)
    )


    barras_n_matriculas = (
        alt.Chart(
            totais_demo_matriculas
        )
        .mark_bar(
            height=24,
            color="#5F91BD",
        )
        .encode(
            opacity=alt.condition(
                alt.datum.Grupo
                == GRUPO_ESPACO,
                alt.value(0),
                alt.value(1),
            ),
            y=alt.Y(
                "Grupo:N",
                sort=ordem_barras_matriculas,
                axis=(
                    alt.Axis(
                        labelExpr=(
                            f"datum.label == "
                            f"'{GRUPO_ESPACO}' "
                            f"? '' : datum.label"
                        ),
                        labelFontSize=11.5,
                        labelLimit=175,
                        ticks=False,
                        domain=False,
                    )
                    if ocultar_distribuicao_demo
                    else None
                ),
            ),
            x=alt.X(
                "Total:Q",
                title=None,
                axis=None,
            ),
            tooltip=[
                alt.Tooltip(
                    "Grupo:N",
                    title=rotulo_dimensao(
                        variavel_demo
                    ),
                ),
                alt.Tooltip(
                    "Total:Q",
                    title="Matrículas",
                    format="d",
                ),
            ],
        )
    )


    texto_n_matriculas = (
        alt.Chart(
            totais_demo_matriculas[
                totais_demo_matriculas[
                    "Grupo"
                ]
                != GRUPO_ESPACO
            ]
        )
        .mark_text(
            align="left",
            dx=6,
            fontSize=11,
            fontWeight="bold",
        )
        .encode(
            y=alt.Y(
                "Grupo:N",
                sort=ordem_barras_matriculas,
            ),
            x="Total:Q",
            text=alt.Text(
                "Total:Q",
                format="d",
            ),
        )
    )


    graf_n_matriculas = (
        barras_n_matriculas
        +
        texto_n_matriculas
    ).properties(
        width=(
            520
            if ocultar_distribuicao_demo
            else 210
        ),
        height=altura_demo_matriculas,
        title=alt.TitleParams(
            text="Número de matrículas",
            anchor="middle",
            fontSize=17,
            fontWeight="bold",
        ),
    )


    col_demo_mat_esq, col_demo_mat_centro, col_demo_mat_dir = st.columns(
        [0.9, 8.2, 0.9]
    )


    with col_demo_mat_centro:

        if ocultar_distribuicao_demo:

            grafico_demografia_matriculas = (
                graf_n_matriculas
            )

            grafico_matriculas_interativo = False


        elif ocultar_totais_demo:

            grafico_demografia_matriculas = (
                graf_pct_matriculas
            )

            grafico_matriculas_interativo = True


        else:

            grafico_demografia_matriculas = (
                alt.hconcat(
                    graf_pct_matriculas,
                    graf_n_matriculas,
                    spacing=20,
                )
                .resolve_scale(
                    y="shared"
                )
                .configure_view(
                    stroke=None
                )
            )

            grafico_matriculas_interativo = True


        if grafico_matriculas_interativo:

            st.altair_chart(
                aplicar_fundo_grafico(
                    grafico_demografia_matriculas
                ),
                theme=None,
                width="stretch",
                key="grafico_demografia_matriculas_interativo",
                on_select="rerun",
                selection_mode=[
                    "selecionar_composicao_matriculas_demo"
                ],
            )

        else:

            st.altair_chart(
                aplicar_fundo_grafico(
                    grafico_demografia_matriculas
                ),
                theme=None,
                width="stretch",
                key="grafico_demografia_matriculas_totais",
            )



    st.stop()
