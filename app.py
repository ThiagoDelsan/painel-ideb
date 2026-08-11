import hmac
import re

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
            padding-top: 1rem;
            padding-bottom: 1rem;
        }

        .panel-main-title {
            display: block;
            font-size: 2.55rem;
            font-weight: 760;
            line-height: 1.30;
            color: #2f313c;
            margin: 0 0 0.65rem 0;
            padding: 0.15rem 0 0.20rem 0;
            overflow: visible;
        }

        div[data-testid="stButton"] button p {
            font-size: 0.72rem !important;
            white-space: nowrap !important;
        }

        /* ====================================================
           SIDEBAR
           ==================================================== */

        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.55rem;
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
    "Menor que 3",
    "Entre 3 e 4",
    "Entre 4 e 5",
    "Entre 5 e 6",
    "Maior que 6",
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


# ============================================================
# RÓTULOS
# ============================================================

ROTULOS_DIMENSOES = {
    "1ª IDEB 100% integral":
        "1º IDEB 100% integral (em construção)",

    "Tipo de integral":
        "Tipo de integral (em construção)",
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
# SAME SCHOOLS
# ============================================================

def filtrar_same_schools(
    base,
    indicador,
    anos,
):

    if not anos:

        return base


    peso = (
        "Matrículas EM (total) 3/4"
    )


    elegiveis = (
        base[
            base[
                "Ano"
            ].isin(
                anos
            )
            &
            base[
                indicador
            ].notna()
            &
            base[
                peso
            ].notna()
            &
            (
                base[
                    peso
                ]
                > 0
            )
        ][
            [
                "Cód. INEP",
                "Ano",
            ]
        ]
        .drop_duplicates()
    )


    contagem = (
        elegiveis
        .groupby(
            "Cód. INEP"
        )[
            "Ano"
        ]
        .nunique()
    )


    ids = (
        contagem[
            contagem
            == len(
                anos
            )
        ]
        .index
    )


    return (
        base[
            base[
                "Cód. INEP"
            ]
            .isin(
                ids
            )
        ]
        .copy()
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
                    labelFontSize=9,
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
            fontSize=9.5,
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
        height=105,
        title=alt.TitleParams(
            text=titulo,
            anchor="middle",
            fontSize=14,
            fontWeight="bold",
        ),
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


nav_1, nav_2, nav_3, nav_4, nav_5 = st.columns(
    [
        1.55,
        1.15,
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
    ):

        st.session_state.pagina = (
            "PRINCIPAIS INDICADORES"
        )


with nav_2:

    if st.button(
        "CRUZAMENTOS",
        width="stretch",
    ):

        st.session_state.pagina = (
            "CRUZAMENTOS"
        )


with nav_3:

    if st.button(
        "DEMOGRAFIA",
        width="stretch",
    ):

        st.session_state.pagina = (
            "DEMOGRAFIA"
        )


with nav_4:

    if st.button(
        "DISTRIBUIÇÕES",
        width="stretch",
    ):

        st.session_state.pagina = (
            "DISTRIBUIÇÕES"
        )


with nav_5:

    if st.button(
        "MELHORES ESCOLAS",
        width="stretch",
    ):

        st.session_state.pagina = (
            "MELHORES ESCOLAS"
        )


pagina = (
    st.session_state.pagina
)


# ============================================================
# FILTROS
# ============================================================

st.sidebar.markdown(
    "### Filtros"
)


st.sidebar.button(
    "Limpar todos os filtros",
    width="stretch",
    on_click=limpar_todos_os_filtros,
)


filtros = {}


nomes_filtros = [
    "Tipo de Escola",
    "PPI",
    "INSE",
    "Colégio Militar",
    "Colégio com Seleção",
    "Estado",
    "Região do Brasil",
    "1ª IDEB 100% integral",
    "Carga horária",
    "Tipo de integral",
]


for nome in nomes_filtros:

    opcoes = obter_opcoes_filtro(
        df_completo,
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
# PARTICIPAÇÃO IDEB
# ============================================================

st.sidebar.markdown(
    """
    <div style="
        font-size:0.72rem;
        font-weight:600;
        margin-top:0.50rem;
        margin-bottom:0.10rem;
    ">
        Participação no IDEB
    </div>
    """,
    unsafe_allow_html=True,
)


filtro_ideb = {}


for ano in ANOS_PAINEL:

    filtro_ideb[
        ano
    ] = (
        st.sidebar.multiselect(
            f"IDEB {ano}",
            options=[
                "Sim",
                "Não",
            ],
            placeholder="Todos",
            key=f"filtro_ideb_{ano}",
        )
    )


# ============================================================
# OFERTA
# ============================================================

st.sidebar.markdown(
    """
    <div style="
        font-size:0.72rem;
        font-weight:600;
        margin-top:0.50rem;
        margin-bottom:0.10rem;
    ">
        Oferta
    </div>
    """,
    unsafe_allow_html=True,
)


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
# APLICA FILTROS
# ============================================================

try:

    df = aplicar_filtros_categoricos(
        df_completo,
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
    # TABELA COM FONTE MENOR E CENTRALIZADA
    # ========================================================

    tabela_estilizada = (
        tabela
        .style
        .set_properties(
            **{
                "text-align": "center",
                "font-size": "10px",
                "padding": "3px 5px",
            }
        )
        .set_table_styles(
            [
                {
                    "selector": "th",
                    "props": [
                        (
                            "text-align",
                            "center",
                        ),
                        (
                            "font-size",
                            "10px",
                        ),
                        (
                            "padding",
                            "3px 5px",
                        ),
                    ],
                }
            ]
        )
    )


    st.dataframe(
        tabela_estilizada,
        width="stretch",
        hide_index=True,
        height=720,
        row_height=28,
    )


    st.stop()


# ============================================================
# CRUZAMENTOS
# ============================================================

if pagina == "CRUZAMENTOS":

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:25px;
            font-weight:700;
            margin-bottom:0.25rem;
        ">
            CRUZAMENTOS
        </div>
        """,
        unsafe_allow_html=True,
    )


    same_schools_cruz = st.toggle(
        "SAME SCHOOLS",
        value=False,
        key="same_schools_cruz",
    )


    opcoes = list(
        EIXOS_DISPONIVEIS.keys()
    )


    SEM_ESCOLHA = "Sem escolha"


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

        indice_padrao_var_2 = (
            opcoes_2.index(
                "PPI"
            )
            if "PPI"
            in opcoes_2
            else 0
        )


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


    if same_schools_cruz:

        df_cruz = filtrar_same_schools(
            df_cruz,
            indicador_cruz,
            anos_cruz,
        )


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
    # Quando a 2ª dimensão está como "Sem escolha", a aba
    # Cruzamentos replica a lógica de Principais Indicadores.
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


    # Dummy para obrigar o espaço a existir na escala.
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

    barras_pct = (
        alt.Chart(
            resumo_plot[
                resumo_plot[
                    "Grupo"
                ]
                != GRUPO_ESPACO
            ]
        )
        .mark_bar(
            height=28,
        )
        .encode(

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
            fontSize=9.5,
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

    ALTURA_LINHA_DEMO = 38


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
            totais_demo[
                totais_demo[
                    "Grupo"
                ]
                != GRUPO_ESPACO
            ]
        )
        .mark_bar(
            height=28,
            color="#6C9FCC",
        )
        .encode(

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
    )


    st.stop()


# ============================================================
# PRINCIPAIS INDICADORES
# ============================================================

st.caption(
    "Médias ponderadas pelo total de matrículas "
    "de 3º e 4º ano do Ensino Médio."
)


same_schools = st.toggle(
    "SAME SCHOOLS",
    value=False,
    key="same_schools_principal",
)


c1, c2, c3 = st.columns(
    [
        1.5,
        1.5,
        1.0,
    ]
)


with c1:

    indicador = st.selectbox(
        "Indicador",
        [
            "IDEB",
            "N(LP)",
            "N(M)",
            "N",
            "Rendimento",
        ],
        key="indicador_principal",
    )


with c2:

    if "eixo_x" not in st.session_state:

        st.session_state[
            "eixo_x"
        ] = "Tipo de Escola"


    st.selectbox(
        "Variável",
        options=list(
            EIXOS_DISPONIVEIS.keys()
        ),
        format_func=rotulo_dimensao,
        key="eixo_x",
    )


with c3:

    ordenacao = st.selectbox(
        "Ordenação",
        [
            "Número absoluto",
            "Delta",
        ],
        key="ordenacao_principal",
    )


eixo_x = st.session_state[
    "eixo_x"
]


# ============================================================
# ANOS
# ============================================================

_, bloco_anos, __ = st.columns(
    [
        1.3,
        3.4,
        1.3,
    ]
)


with bloco_anos:

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
                key=f"principal_ano_{ano}",
            )


anos = [
    ano
    for ano, ativo
    in selecao.items()
    if ativo
]


if not anos:

    st.warning(
        "Selecione pelo menos um ano."
    )

    st.stop()


# ============================================================
# SAME SCHOOLS
# ============================================================

df_principal = df.copy()


if same_schools:

    df_principal = filtrar_same_schools(
        df_principal,
        indicador,
        anos,
    )


# ============================================================
# CÁLCULO
# ============================================================

resultado = (
    media_ponderada_por_categoria(
        df=df_principal,
        indicador=indicador,
        anos=anos,
        eixo_painel=eixo_x,
    )
)


consolidado = calcular_consolidado(
    df_principal,
    indicador,
    anos,
)


if (
    eixo_x
    == "Tipo de Escola"
    and
    not mostrar_integral_agregado
):

    resultado = (
        resultado[
            resultado[
                "Categoria"
            ]
            != CATEGORIA_INTEGRAL_AGREGADA
        ]
        .copy()
    )


if resultado.empty:

    st.warning(
        "Não há resultados para a configuração selecionada."
    )

    st.stop()


# ============================================================
# ANOS DE COMPARAÇÃO
# ============================================================

anos_ord = sorted(
    anos
)


ano_final = anos_ord[-1]


ano_inicial = (
    anos_ord[-2]
    if len(
        anos_ord
    )
    >= 2
    else None
)


# ============================================================
# ORDEM
# ============================================================

categorias = (
    resultado[
        "Categoria"
    ]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


if ordenacao == "Número absoluto":

    ordem_categorias = (
        resultado[
            resultado[
                "Ano"
            ]
            == str(
                ano_final
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


else:

    if ano_inicial is None:

        ordem_categorias = categorias

    else:

        pivot_ord = (
            resultado[
                resultado[
                    "Ano"
                ].isin(
                    [
                        str(
                            ano_inicial
                        ),
                        str(
                            ano_final
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
                ano_inicial
            )
            in pivot_ord.columns
            and
            str(
                ano_final
            )
            in pivot_ord.columns
        ):

            pivot_ord[
                "Delta"
            ] = (
                pivot_ord[
                    str(
                        ano_final
                    )
                ]
                -
                pivot_ord[
                    str(
                        ano_inicial
                    )
                ]
            )


            ordem_categorias = (
                pivot_ord
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

            ordem_categorias = categorias


for categoria in categorias:

    if categoria not in ordem_categorias:

        ordem_categorias.append(
            categoria
        )


# ============================================================
# PLOT PRINCIPAL
# ============================================================

dados_principal = pd.concat(
    [
        consolidado,
        resultado,
    ],
    ignore_index=True,
)


(
    plot_principal,
    labels_principal,
    labels_anos_principal,
    ordem_linhas,
) = preparar_linhas_horizontais(
    dados=dados_principal,
    anos=anos,
    categorias=ordem_categorias,
    ano_inicial=ano_inicial,
    ano_final=ano_final,
)


painel = criar_painel_horizontal(
    plot=plot_principal,
    labels_categorias=labels_principal,
    labels_anos=labels_anos_principal,
    ordem_linhas=ordem_linhas,
    indicador=indicador,
    eixo_nome=eixo_x,
    ano_inicial=ano_inicial,
    ano_final=ano_final,
)


st.altair_chart(
    painel,
    width="stretch",
)