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
    EIXOS_DISPONIVEIS,
    FAIXAS_IDEB,
)


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

        .block-container {
            padding-top: 2.15rem;
            padding-bottom: 2rem;
        }

        .panel-main-title {
            display: block;
            font-size: 2.55rem;
            font-weight: 760;
            line-height: 1.22;
            color: #2f313c;
            margin: 0 0 0.90rem 0;
            padding: 0.35rem 0 0.25rem 0;
            overflow: visible;
        }

        /* Botão exclusivo para limpar filtros. */
        .st-key-limpar_todos_filtros button {
            background-color: #F8D7DA !important;
            border-color: #E8B4B8 !important;
            color: #7A2E34 !important;
        }

        .st-key-limpar_todos_filtros button:hover {
            background-color: #F3C7CB !important;
            border-color: #DFA1A6 !important;
            color: #642329 !important;
        }


        div[data-testid="stButton"] button p {
            font-size: 0.72rem !important;
            white-space: nowrap !important;
        }

        /* ====================================================
           SIDEBAR
           ==================================================== */

        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.85rem;
            padding-left: 0.70rem;
            padding-right: 0.70rem;
        }

        section[data-testid="stSidebar"] h3 {
            font-size: 0.90rem !important;
            margin-top: 0 !important;
            margin-bottom: 0.35rem !important;
        }

        section[data-testid="stSidebar"] label {
            font-size: 0.70rem !important;
            line-height: 0.95rem !important;
            margin-bottom: 0.08rem !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stVerticalBlock"] {
            gap: 0.20rem !important;
        }

        section[data-testid="stSidebar"] .stMultiSelect {
            margin-top: 0 !important;
            margin-bottom: 0.05rem !important;
        }

        section[data-testid="stSidebar"]
        div[data-baseweb="select"] {
            font-size: 0.74rem !important;
            min-height: 32px !important;
        }

        section[data-testid="stSidebar"] input {
            font-size: 0.73rem !important;
        }

        section[data-testid="stSidebar"]
        span[data-baseweb="tag"] {
            font-size: 0.68rem !important;
        }

        /* ====================================================
           LOGIN
           ==================================================== */

        .login-title {
            text-align: center;
            font-size: 34px;
            font-weight: 750;
            margin-top: 10vh;
            margin-bottom: 4px;
            line-height: 1.2;
        }

        .login-subtitle {
            text-align: center;
            font-size: 14px;
            color: #6b7280;
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
    "2017": "#D9DDE2",
    "2019": "#747A82",
    "2021": "#9AA5AD",
    "2023": "#76B7E5",
    "2025": "#1F5A96",
}


ESCALA_CORES_ANOS = [
    CORES_ANOS[ano]
    for ano in ORDEM_ANOS_STR
]


COR_DELTA = "#A67C68"


CATEGORIA_INTEGRAL_AGREGADA = (
    "Integral (Mista + 100%)"
)


ORDEM_FAIXA_IDEB = [
    "IDEB < 3",
    "3 ≤ IDEB < 4",
    "4 ≤ IDEB < 5",
    "5 ≤ IDEB ≤ 6",
    "IDEB > 6",
    "Sem resultado",
]


PALETA_DISTRIBUICOES = [
    "#4E79A7",
    "#F28E2B",
    "#59A14F",
    "#EDC948",
    "#B07AA1",
    "#76B7B2",
    "#E15759",
    "#9C755F",
    "#7F7F7F",
    "#86BCB6",
]


# Paleta exclusiva dos boxplots da aba Distribuições.
# O objetivo aqui é manter contraste entre comparações sem usar
# azul ou marrom, com cores mais esmaecidas para favorecer a
# leitura dos rótulos de média e N.
CORES_ANOS_DISTRIBUICOES = {
    "2017": "#A8CFA8",   # verde pastel
    "2019": "#CBB7DD",   # lilás pastel
    "2021": "#F1C7A5",   # pêssego pastel
    "2023": "#E7B0C0",   # rosa pastel
    "2025": "#D7D59A",   # oliva/amarelo pastel
}

CORES_GRUPOS_DISTRIBUICOES = [
    "#A8CFA8",
    "#CBB7DD",
]


# ============================================================
# RÓTULOS
# ============================================================

ROTULOS_DIMENSOES = {
    "Carga horária": "Carga Horária",
    "Colégio com Seleção": "Colégio com seleção",
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
# WRAPPERS DO DATA
# ============================================================

def criar_variavel_eixo(
    df,
    eixo,
):

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


    if variavel == "Tipo de Escola":

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
        == "Tipo de Escola"
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
        == "Tipo de Escola"
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

    apagar = []


    for chave in list(
        st.session_state.keys()
    ):

        if chave.startswith(
            "filtro_"
        ):

            apagar.append(
                chave
            )


    for chave in apagar:

        st.session_state.pop(
            chave,
            None,
        )


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
            fontSize=11.5,
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
            == "Tipo de Escola"
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
            labelFontSize=10,
            titleFontSize=12,
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
            labelFontSize=11,
            titleFontSize=12,
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
            color="#76B7E5",
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
            fontSize=16,
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
            labelFontSize=10,
            titleFontSize=12,
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
            labelFontSize=11,
            titleFontSize=12,
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
            color="#76B7E5",
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
            fontSize=16,
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
            labelFontSize=10,
            titleFontSize=12,
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
            labelFontSize=11,
            titleFontSize=12,
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
            color="#4E86B8",
            opacity=0.82,
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
            labelFontSize=10,
            titleFontSize=12,
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
            labelFontSize=11,
            titleFontSize=12,
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
            color="#4E86B8",
            opacity=0.82,
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
            labelFontSize=11,
            titleFontSize=12,
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
                    labelFontSize=11,
                    titleFontSize=12,
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
            fontSize=12.5,
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
            fontSize=16,
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
            labelFontSize=11,
            titleFontSize=12,
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
                    labelFontSize=11,
                    titleFontSize=12,
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
            f"<td>{ano}</td>"
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
            f"<td>{n_considerado}</td>"
            "</tr>"
        )


    tabela_html = (
        "<div style='width:96%;max-width:1180px;margin:0.25rem auto 0;"
        "overflow-x:auto;'>"
        "<table style='width:100%;border-collapse:collapse;"
        "font-size:0.78rem;text-align:center;table-layout:fixed;'>"
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
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>Ano</th>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>Comparação</th>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>p-valor</th>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>Relevância Estatística</th>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>Diferença entre médias<br>(categoria − demais)</th>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>Teste aplicado</th>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>N considerado<br>(categoria × demais)</th>"
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
            f"<td>{ano}</td>"
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
            f"<td>{n_considerado}</td>"
            "</tr>"
        )


    tabela_html = (
        "<div style='width:90%;max-width:1040px;margin:0.25rem auto 0;"
        "overflow-x:auto;'>"
        "<table style='width:100%;border-collapse:collapse;"
        "font-size:0.78rem;text-align:center;table-layout:fixed;'>"
        "<colgroup>"
        "<col style='width:10%;'>"
        "<col style='width:13%;'>"
        "<col style='width:22%;'>"
        "<col style='width:20%;'>"
        "<col style='width:19%;'>"
        "<col style='width:16%;'>"
        "</colgroup>"
        "<thead><tr>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>"
        "Ano</th>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>"
        "p-valor</th>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>"
        "Relevância Estatística</th>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>"
        "Diferença entre médias (2 − 1)</th>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>"
        "Teste aplicado</th>"
        "<th style='padding:7px 6px;border-bottom:1px solid #D1D5DB;'>"
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


        quantidade_espacos = (
            2
            if consolidado
            else 1
        )


        tipo_sep = (
            "separador_grande"
            if consolidado
            else "separador_pequeno"
        )


        for _ in range(
            quantidade_espacos
        ):

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
        registros[-1][
            "TipoLinha"
        ].startswith(
            "separador"
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
    largura_categoria=135,
    largura_anos=100,
    largura_esquerda=360,
    largura_direita=200,
):

    formatos = formatos_indicador(
        indicador
    )


    baseline = formatos[
        "baseline"
    ]


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
                color="#D5DAE0",
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
                color="#C5CBD2",
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
            fontSize=10,
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
            align="right",
            baseline="middle",
            fontSize=9.5,
            color="#7B8498",
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x=alt.value(
                largura_anos
                - 5
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
                    domainMin=baseline,
                    zero=False,
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
            fontSize=9.5,
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
            fontSize=16,
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
            fontSize=9.5,
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
            fontSize=16,
            fontWeight="bold",
        ),
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
    largura_nivel_1=105,
    largura_nivel_2=120,
    largura_anos=95,
    largura_esquerda=320,
    largura_direita=185,
):

    formatos = formatos_indicador(
        indicador
    )


    baseline = formatos[
        "baseline"
    ]


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
                color="#D5DAE0",
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
                color="#B9C0C8",
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
            fontSize=10,
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
            fontSize=9.5,
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
            align="right",
            baseline="middle",
            fontSize=9.2,
            color="#7B8498",
        )
        .encode(

            y=escala_y(
                ordem_linhas
            ),

            x=alt.value(
                largura_anos
                - 4
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
                    domainMin=baseline,
                    zero=False,
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
            fontSize=9.2,
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
            fontSize=16,
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
            fontSize=9.2,
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
            fontSize=16,
            fontWeight="bold",
        ),
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
# CARREGAMENTO
# ============================================================

try:

    df_completo = preparar_base()


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
# NAVEGAÇÃO
# ============================================================

if "pagina" not in st.session_state:

    st.session_state.pagina = (
        "PRINCIPAIS INDICADORES"
    )


nav_1, nav_2, nav_3, nav_4 = st.columns(
    [
        1.55,
        1.00,
        1.15,
        1.35,
    ],
    gap="medium",
)


with nav_1:

    if st.button(
        "PRINCIPAIS INDICADORES",
        width="stretch",
        key="nav_principais",
    ):

        st.session_state.pagina = (
            "PRINCIPAIS INDICADORES"
        )


with nav_2:

    if st.button(
        "DEMOGRAFIA",
        width="stretch",
        key="nav_demografia",
    ):

        st.session_state.pagina = (
            "DEMOGRAFIA"
        )


with nav_3:

    if st.button(
        "DISTRIBUIÇÕES",
        width="stretch",
        key="nav_distribuicoes",
    ):

        st.session_state.pagina = (
            "DISTRIBUIÇÕES"
        )


with nav_4:

    if st.button(
        "MELHORES ESCOLAS",
        width="stretch",
        key="nav_melhores",
    ):

        st.session_state.pagina = (
            "MELHORES ESCOLAS"
        )


pagina = (
    st.session_state.pagina
)


# ============================================================
# DESTAQUE DA PÁGINA ATIVA NA NAVEGAÇÃO
# ============================================================

chave_nav_ativa = {
    "PRINCIPAIS INDICADORES": "nav_principais",
    "DEMOGRAFIA": "nav_demografia",
    "DISTRIBUIÇÕES": "nav_distribuicoes",
    "MELHORES ESCOLAS": "nav_melhores",
}.get(
    pagina
)


if chave_nav_ativa:

    st.markdown(
        f"""
        <style>
            .st-key-{chave_nav_ativa} button {{
                background-color: #DFF1E2 !important;
                border-color: #A9D5B0 !important;
                color: #245C2D !important;
                font-weight: 700 !important;
            }}

            .st-key-{chave_nav_ativa} button:hover {{
                background-color: #D3EBD7 !important;
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


# SAME SCHOOLS agora significa manter somente as escolas cuja
# classificação na coluna Transicao é diferente de "-".
df_base_filtros = df_completo.copy()


if same_schools_ativo:

    if "Transicao" not in df_base_filtros.columns:

        st.error(
            "A coluna Transicao não foi encontrada na base carregada da aba Escolas_2025."
        )
        st.stop()


    valores_same_school = (
        df_base_filtros[
            "Transicao"
        ]
        .astype("string")
        .str.strip()
    )


    df_base_filtros = (
        df_base_filtros[
            valores_same_school.notna()
            &
            valores_same_school.ne("-")
        ]
        .copy()
    )


    # Sinalização visual de que o universo SAME SCHOOLS está ativo.
    st.markdown(
        """
        <style>
            .stApp,
            [data-testid="stAppViewContainer"] {
                background-color: #EEF7FF !important;
            }

            [data-testid="stHeader"] {
                background-color: rgba(238, 247, 255, 0.94) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
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
    "Tipo de Escola"
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
                "Sim",
                *[
                    faixa
                    for faixa
                    in FAIXAS_IDEB
                    if faixa
                    != "Sem resultado"
                ],
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
    "Tipo de Escola",
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

filtro_tipo_escola = (
    filtros.get(
        "Tipo de Escola",
        [],
    )
)


mostrar_integral_agregado = (
    len(
        filtro_tipo_escola
    )
    == 0
    or
    CATEGORIA_INTEGRAL_AGREGADA
    in filtro_tipo_escola
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
# DISTRIBUIÇÕES
# ============================================================

if pagina == "DISTRIBUIÇÕES":

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:25px;
            font-weight:700;
            margin-top:8px;
            margin-bottom:8px;
        ">
            DISTRIBUIÇÕES
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
                    mostrar_integral_agregado
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
                        mostrar_integral_agregado
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
                grafico_boxplots,
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
                grafico_delta_boxplots,
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


        with col_grupo_1:

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


            categorias_grupo_2 = st.multiselect(
                "Agregado 2",
                options=opcoes_grupo_2,
                placeholder="Selecione as categorias",
                key="categorias_distrib_agregado_2",
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
                        fontSize=16,
                        subtitleFontSize=11,
                        subtitlePadding=8,
                    )
                )


                st.altair_chart(
                    grafico_agregado,
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
                    grafico_medias_agregado,
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
                        fontSize=16,
                        subtitleFontSize=11,
                        subtitlePadding=8,
                    )
                )


                st.altair_chart(
                    grafico_delta_agregado,
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
                    grafico_medias_delta_agregado,
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
            font-size:25px;
            font-weight:700;
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

    dist_tipo = preparar_distribuicao_top(
        base_dim,
        "Tipo de Escola",
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


    g1, g2, g3 = st.columns(
        3,
        gap="medium",
    )


    with g1:

        st.altair_chart(
            grafico_barra_100_top(
                dist_tipo,
                "Tipo de Escola",
                [
                    "100% Integral",
                    "Mista",
                    "Parcial/Regular",
                ],
            ),
            width="stretch",
        )


    with g2:

        st.altair_chart(
            grafico_barra_100_top(
                dist_inse,
                "INSE",
                ordenar_dimensao(
                    dist_inse[
                        "Categoria"
                    ].tolist(),
                    "INSE",
                ),
            ),
            width="stretch",
        )


    with g3:

        st.altair_chart(
            grafico_barra_100_top(
                dist_ppi,
                "PPI",
                ordenar_dimensao(
                    dist_ppi[
                        "Categoria"
                    ].tolist(),
                    "PPI",
                ),
            ),
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
        border-radius: 6px;
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
    }}

    table.tabela-melhores-escolas {{
        width: 100% !important;
        max-width: 100% !important;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 8.2px !important;
        line-height: 1.08;
        margin: 0 !important;
    }}

    table.tabela-melhores-escolas th,
    table.tabela-melhores-escolas td {{
        text-align: center !important;
        vertical-align: middle !important;
        padding: 3px 2px !important;
        border-bottom: 1px solid #ECEFF2;
        white-space: normal !important;
        overflow-wrap: anywhere;
        word-break: normal;
    }}

    table.tabela-melhores-escolas th {{
        position: sticky;
        top: 0;
        z-index: 2;
        background: #F6F7F9;
        font-size: 8.0px !important;
        font-weight: 700;
        color: #343741;
    }}

    /* Nome da escola recebe mais espaço; posição e código, menos. */
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
            font-size:25px;
            font-weight:700;
            margin-bottom:0.25rem;
        ">
            PRINCIPAIS INDICADORES
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
            == "Tipo de Escola"
            and
            not mostrar_integral_agregado
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


        dados_cruz_uma_dimensao = pd.concat(
            [
                consolidado_cruz,
                resultado_cruz,
            ],
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
                    mostrar_integral_agregado
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
            consolidado=consolidado_cruz,
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
            )
        )


    st.altair_chart(
        painel_cruz,
        width="stretch",
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
            font-size:25px;
            font-weight:700;
            margin-bottom:0.5rem;
        ">
            DEMOGRAFIA
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
        == "Tipo de Escola"
        and
        mostrar_integral_agregado
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


    composicao_selecionada_demo = None


    estado_grafico_demo = st.session_state.get(
        "grafico_demografia_interativo"
    )


    if estado_grafico_demo is not None:

        try:

            selecoes_demo = (
                estado_grafico_demo.selection
            )

        except Exception:

            selecoes_demo = (
                estado_grafico_demo.get(
                    "selection",
                    {},
                )
                if hasattr(
                    estado_grafico_demo,
                    "get",
                )
                else {}
            )


        selecao_demo_anterior = (
            selecoes_demo.get(
                "selecionar_composicao_demo",
                None,
            )
            if hasattr(
                selecoes_demo,
                "get",
            )
            else None
        )


        composicao_selecionada_demo = (
            extrair_valor_selecao_demo(
                selecao_demo_anterior,
                "Composição",
            )
        )


    if (
        composicao_selecionada_demo
        in ordem_comp
    ):

        percentuais_para_ordem = (
            resumo[
                resumo[
                    "Composição"
                ]
                == composicao_selecionada_demo
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


    resumo = pd.concat(
        [
            cons,
            resumo,
        ],
        ignore_index=True,
    )


    # ========================================================
    # ESPAÇO APÓS CONSOLIDADO
    # ========================================================

    GRUPO_ESPACO = "__espaco__"


    ordem_barras = (
        [
            "Consolidado",
            GRUPO_ESPACO,
        ]
        +
        ordem_grupos
    )


    # Linha dummy exclusiva após o Consolidado. Como as demais categorias
    # ficam em posições consecutivas, somente o Consolidado recebe o
    # afastamento adicional.
    espaco_resumo = pd.DataFrame(
        {
            "Composição": [
                ordem_comp[0]
                if ordem_comp
                else ""
            ],
            "Escolas": [
                0
            ],
            "Percentual": [
                0
            ],
            "Grupo": [
                GRUPO_ESPACO
            ],
            "Total": [
                0
            ],
        }
    )


    resumo_plot = pd.concat(
        [
            resumo,
            espaco_resumo,
        ],
        ignore_index=True,
    )


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
                    labelFontSize=11,
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
            fontSize=11.5,
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
            fontSize=16,
            fontWeight="bold",
        ),
    )


    # ========================================================
    # TOTAL DE ESCOLAS
    # ========================================================

    totais_demo = pd.concat(
        [
            pd.DataFrame(
                {
                    "Grupo": [
                        "Consolidado"
                    ],
                    "Total": [
                        total_cons
                    ],
                }
            ),
            pd.DataFrame(
                {
                    "Grupo": [
                        GRUPO_ESPACO
                    ],
                    "Total": [
                        0
                    ],
                }
            ),
            totais,
        ],
        ignore_index=True,
    )


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
            color="#6C9FCC",
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
                axis=None,
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
            fontSize=10,
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
        width=210,
        height=altura_demo,
        title=alt.TitleParams(
            text="Número de escolas",
            anchor="middle",
            fontSize=16,
            fontWeight="bold",
        ),
    )


    st.caption(
        "Clique em uma seção colorida do gráfico de percentuais para "
        "ordenar as categorias por essa composição, da maior para a menor. "
        "Dê um duplo clique para limpar a seleção."
    )


    st.altair_chart(
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
        ),
        width="stretch",
        key="grafico_demografia_interativo",
        on_select="rerun",
        selection_mode=[
            "selecionar_composicao_demo"
        ],
    )


    st.stop()
