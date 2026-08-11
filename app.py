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
            padding-top: 0.65rem;
            padding-bottom: 1rem;
        }

        h1 {
            margin-top: 0 !important;
            margin-bottom: 0.10rem !important;
        }

        /* ====================================================
           SIDEBAR
           ==================================================== */

        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.55rem;
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }

        section[data-testid="stSidebar"] h3 {
            font-size: 0.90rem !important;
            margin-top: 0 !important;
            margin-bottom: 0.35rem !important;
        }

        section[data-testid="stSidebar"] label {
            font-size: 0.70rem !important;
            line-height: 1rem !important;
            margin-bottom: 0.08rem !important;
        }

        /*
        Antes tínhamos margens negativas.
        Elas aproximavam os campos, mas podiam causar
        sobreposição entre multiselects.
        */

        section[data-testid="stSidebar"]
        div[data-testid="stVerticalBlock"] {
            gap: 0.30rem !important;
        }

        section[data-testid="stSidebar"] .stMultiSelect {
            margin-top: 0 !important;
            margin-bottom: 0.12rem !important;
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

        .demo-variable-title {
            font-size: 0.80rem;
            font-weight: 700;
            margin-top: 4px;
            margin-bottom: 2px;
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
        }

        .login-subtitle {
            text-align: center;
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 22px;
        }

        .login-footer {
            text-align: center;
            font-size: 11px;
            color: #9ca3af;
            margin-top: 18px;
        }

        /* ====================================================
           DIVISOR
           ==================================================== */

        .soft-divider {
            border: none;
            border-top: 1px solid rgba(120, 130, 140, 0.22);
            margin-top: 0.45rem;
            margin-bottom: 0.65rem;
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
# SELEÇÃO = 9
#
# 0 = Não
# 1 = Sim
# 9 = Não informado
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
# WRAPPERS DAS FUNÇÕES DO DATA.PY
#
# Assim tratamos Seleção = 9 no app sem alterar data.py.
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

    filtros_base = (
        filtros.copy()
    )


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

            categoria_selecao = (
                resultado[
                    "Seleção"
                ]
                .apply(
                    categorizar_selecao
                )
            )


            resultado = (
                resultado[
                    categoria_selecao.isin(
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
            "eixo": ".0%",
            "delta": "+.1%",
        }


    return {
        "rotulo": ".1f",
        "tooltip": ".1f",
        "eixo": ".1f",
        "delta": "+.1f",
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
        if pd.notna(
            valor
        )
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


    resultado = (
        base.copy()
    )


    resultado[
        "Categoria_1"
    ] = (
        temp_1[
            "Categoria"
        ].values
    )


    resultado[
        "Categoria_2"
    ] = (
        temp_2[
            "Categoria"
        ].values
    )


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

    prefixos = [
        "filtro_",
    ]


    chaves_exatas = [
        "filtro_proped",
        "filtro_ept",
    ]


    apagar = []


    for chave in st.session_state.keys():

        if (
            any(
                chave.startswith(prefixo)
                for prefixo
                in prefixos
            )
            or
            chave
            in chaves_exatas
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
# DISTRIBUIÇÃO MELHORES ESCOLAS
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
    ] = (
        temp[
            "Categoria"
        ].values
    )


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


    total = (
        resumo[
            "Escolas"
        ].sum()
    )


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


def grafico_distribuicao_top(
    distribuicao,
    titulo,
    ordem=None,
):

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


    barras = (
        alt.Chart(
            distribuicao
        )
        .mark_bar(
            color="#5D91BF"
        )
        .encode(

            x=alt.X(
                "Categoria:N",
                title=None,
                sort=ordem,
                axis=alt.Axis(
                    labelAngle=-30,
                    labelLimit=120,
                ),
            ),

            y=alt.Y(
                "Percentual:Q",
                title=None,
                axis=alt.Axis(
                    format=".0%",
                ),
            ),

            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                ),

                alt.Tooltip(
                    "Escolas:Q",
                    format=",",
                ),

                alt.Tooltip(
                    "Percentual:Q",
                    format=".1%",
                ),
            ],
        )
    )


    textos = (
        alt.Chart(
            distribuicao
        )
        .mark_text(
            dy=-6,
            fontSize=10,
        )
        .encode(

            x=alt.X(
                "Categoria:N",
                sort=ordem,
            ),

            y="Percentual:Q",

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
        height=220,
        title=alt.TitleParams(
            text=titulo,
            anchor="middle",
            fontSize=15,
        ),
    )


# ============================================================
# NOVO LAYOUT HORIZONTAL — PRINCIPAIS INDICADORES
# ============================================================

def preparar_layout_horizontal_principal(
    resultado,
    consolidado,
    anos,
    ordem_categorias,
    ano_inicial,
    ano_final,
):

    dados = pd.concat(
        [
            resultado,
            consolidado,
        ],
        ignore_index=True,
    )


    categorias = (
        ordem_categorias
        +
        [
            "Consolidado"
        ]
    )


    anos_ord = sorted(
        anos
    )


    linhas = []


    for categoria in categorias:

        temp_cat = (
            dados[
                dados[
                    "Categoria"
                ]
                == categoria
            ]
            .copy()
        )


        for i, ano in enumerate(
            anos_ord
        ):

            recorte = (
                temp_cat[
                    temp_cat[
                        "Ano"
                    ]
                    == str(
                        ano
                    )
                ]
            )


            if recorte.empty:

                continue


            n = int(
                recorte[
                    "N escolas"
                ].iloc[0]
            )


            if i == 0:

                label = (
                    f"{categoria}  "
                    f"{ano} ({n:,})"
                )

            else:

                label = (
                    f"        "
                    f"{ano} ({n:,})"
                )


            label = label.replace(
                ",",
                ".",
            )


            linhas.append(
                {
                    "Categoria":
                        categoria,

                    "Ano":
                        str(ano),

                    "Média":
                        recorte[
                            "Média"
                        ].iloc[0],

                    "N escolas":
                        n,

                    "Linha":
                        label,
                }
            )


    plot = pd.DataFrame(
        linhas
    )


    if plot.empty:

        return (
            plot,
            [],
        )


    # ========================================================
    # DELTA POR CATEGORIA
    # ========================================================

    deltas = {}


    if (
        ano_inicial is not None
        and
        ano_final is not None
    ):

        for categoria in categorias:

            rec_ini = (
                dados[
                    (
                        dados[
                            "Categoria"
                        ]
                        == categoria
                    )
                    &
                    (
                        dados[
                            "Ano"
                        ]
                        == str(
                            ano_inicial
                        )
                    )
                ]
            )


            rec_fim = (
                dados[
                    (
                        dados[
                            "Categoria"
                        ]
                        == categoria
                    )
                    &
                    (
                        dados[
                            "Ano"
                        ]
                        == str(
                            ano_final
                        )
                    )
                ]
            )


            if (
                not rec_ini.empty
                and
                not rec_fim.empty
            ):

                deltas[
                    categoria
                ] = (
                    rec_fim[
                        "Média"
                    ].iloc[0]
                    -
                    rec_ini[
                        "Média"
                    ].iloc[0]
                )


    plot[
        "Variação"
    ] = np.nan


    # Delta aparece na linha do ano mais recente.
    for categoria, delta in deltas.items():

        mask = (
            (
                plot[
                    "Categoria"
                ]
                == categoria
            )
            &
            (
                plot[
                    "Ano"
                ]
                == str(
                    ano_final
                )
            )
        )


        plot.loc[
            mask,
            "Variação",
        ] = delta


    ordem_linhas = (
        plot[
            "Linha"
        ]
        .tolist()
    )


    return (
        plot,
        ordem_linhas,
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

st.title(
    "Painel IDEB"
)


# ============================================================
# NAVEGAÇÃO
# ============================================================

if "pagina" not in st.session_state:

    st.session_state.pagina = (
        "PRINCIPAIS INDICADORES"
    )


(
    nav_1,
    nav_2,
    nav_3,
    nav_4,
    _,
) = st.columns(
    [
        1.55,
        1.05,
        1.0,
        1.25,
        3.2,
    ]
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
# FILTROS DA SIDEBAR
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
# REGRA DO INTEGRAL AGREGADO
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
        margin-top:0.55rem;
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
        margin-top:0.55rem;
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
# APLICAR FILTROS
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


    (
        c1,
        c2,
        c3,
    ) = st.columns(
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
    # GRÁFICOS DE PERFIL
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


    g1, g2, g3 = st.columns(3)


    with g1:

        st.altair_chart(
            grafico_distribuicao_top(
                dist_tipo,
                "Distribuição por Tipo de Escola",
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
            grafico_distribuicao_top(
                dist_inse,
                "Distribuição de INSE",
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
            grafico_distribuicao_top(
                dist_ppi,
                "Distribuição de PPI",
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
            ] = (
                temp[
                    "Categoria"
                ].values
            )

        except Exception:

            base_dim[
                dimensao
            ] = "Não informado"


    ranking = (
        ranking.merge(
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
    )


    st.markdown(
        f"""
        <div style="
            text-align:center;
            font-size:22px;
            font-weight:700;
            margin-top:12px;
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


    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        height=750,
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
        ">
            CRUZAMENTOS
        </div>
        """,
        unsafe_allow_html=True,
    )


    c1, c2 = st.columns(
        [
            2,
            1,
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

        ordenacao_cruz = st.selectbox(
            "Ordenação",
            [
                "Número absoluto",
                "Delta",
            ],
            key="ordenacao_cruz",
        )


    _, bloco, __ = st.columns(
        [
            1.4,
            3,
            1.4,
        ]
    )


    with bloco:

        cols = st.columns(5)


        selecao = {}


        defaults = {
            2017: False,
            2019: False,
            2021: False,
            2023: True,
            2025: True,
        }


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

        st.stop()


    opcoes = list(
        EIXOS_DISPONIVEIS.keys()
    )


    c1, c2 = st.columns(2)


    with c1:

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
        x
        for x
        in opcoes
        if x
        != variavel_1
    ]


    with c2:

        variavel_2 = st.selectbox(
            "2ª dimensão",
            opcoes_2,
            index=(
                opcoes_2.index(
                    "PPI"
                )
                if "PPI"
                in opcoes_2
                else 0
            ),
            format_func=rotulo_dimensao,
            key="cruz_var_2",
        )


    resultado_cruz = (
        media_ponderada_duas_dimensoes(
            base=df,
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


    anos_ord = sorted(
        anos_cruz
    )


    ano_final_cruz = (
        anos_ord[-1]
    )


    ano_ini_cruz = (
        anos_ord[-2]
        if len(
            anos_ord
        )
        >= 2
        else None
    )


    formatos = formatos_indicador(
        indicador_cruz
    )


    # ========================================================
    # CRIA UMA LINHA PARA CADA COMBINAÇÃO + ANO
    # ========================================================

    resultado_cruz[
        "Grupo"
    ] = (
        resultado_cruz[
            "Categoria_1"
        ].astype(str)
        +
        " | "
        +
        resultado_cruz[
            "Categoria_2"
        ].astype(str)
    )


    grupos = (
        resultado_cruz[
            "Grupo"
        ]
        .drop_duplicates()
        .tolist()
    )


    linhas = []


    for grupo in grupos:

        rec_grupo = (
            resultado_cruz[
                resultado_cruz[
                    "Grupo"
                ]
                == grupo
            ]
        )


        for i, ano in enumerate(
            anos_ord
        ):

            rec = (
                rec_grupo[
                    rec_grupo[
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


            if i == 0:

                label = (
                    f"{grupo}  "
                    f"{ano} "
                    f"({n:,})"
                )

            else:

                label = (
                    f"        "
                    f"{ano} "
                    f"({n:,})"
                )


            label = label.replace(
                ",",
                ".",
            )


            linhas.append(
                {
                    "Grupo":
                        grupo,

                    "Linha":
                        label,

                    "Ano":
                        str(ano),

                    "Média":
                        rec[
                            "Média"
                        ].iloc[0],

                    "Variação":
                        np.nan,
                }
            )


    plot_cruz = pd.DataFrame(
        linhas
    )


    if ano_ini_cruz is not None:

        for grupo in grupos:

            rec = (
                resultado_cruz[
                    resultado_cruz[
                        "Grupo"
                    ]
                    == grupo
                ]
            )


            ini = (
                rec[
                    rec[
                        "Ano"
                    ]
                    == str(
                        ano_ini_cruz
                    )
                ]
            )


            fim = (
                rec[
                    rec[
                        "Ano"
                    ]
                    == str(
                        ano_final_cruz
                    )
                ]
            )


            if (
                not ini.empty
                and
                not fim.empty
            ):

                delta = (
                    fim[
                        "Média"
                    ].iloc[0]
                    -
                    ini[
                        "Média"
                    ].iloc[0]
                )


                mask = (
                    (
                        plot_cruz[
                            "Grupo"
                        ]
                        == grupo
                    )
                    &
                    (
                        plot_cruz[
                            "Ano"
                        ]
                        == str(
                            ano_final_cruz
                        )
                    )
                )


                plot_cruz.loc[
                    mask,
                    "Variação",
                ] = delta


    ordem = (
        plot_cruz[
            "Linha"
        ]
        .tolist()
    )


    # ========================================================
    # DOIS GRÁFICOS LADO A LADO
    # ========================================================

    esquerda = (
        alt.Chart(
            plot_cruz
        )
        .mark_bar()
        .encode(

            y=alt.Y(
                "Linha:N",
                title=None,
                sort=ordem,
                axis=alt.Axis(
                    labelLimit=250,
                    labelFontSize=10,
                ),
            ),

            x=alt.X(
                "Média:Q",
                title=indicador_cruz,
                axis=alt.Axis(
                    format=formatos[
                        "eixo"
                    ],
                ),
            ),

            color=alt.Color(
                "Ano:N",
                scale=alt.Scale(
                    domain=ORDEM_ANOS_STR,
                    range=ESCALA_CORES_ANOS,
                ),
            ),
        )
        .properties(
            height=max(
                300,
                len(
                    plot_cruz
                )
                * 22,
            )
        )
    )


    texto_esquerda = (
        alt.Chart(
            plot_cruz
        )
        .mark_text(
            align="left",
            dx=4,
        )
        .encode(

            y=alt.Y(
                "Linha:N",
                sort=ordem,
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


    direita = (
        alt.Chart(
            plot_cruz[
                plot_cruz[
                    "Variação"
                ].notna()
            ]
        )
        .mark_bar(
            color=COR_DELTA
        )
        .encode(

            y=alt.Y(
                "Linha:N",
                title=None,
                sort=ordem,
                axis=None,
            ),

            x=alt.X(
                "Variação:Q",
                title=(
                    f"Δ {ano_final_cruz} "
                    f"− {ano_ini_cruz}"
                    if ano_ini_cruz
                    is not None
                    else "Variação"
                ),
            ),
        )
        .properties(
            height=max(
                300,
                len(
                    plot_cruz
                )
                * 22,
            )
        )
    )


    texto_direita = (
        alt.Chart(
            plot_cruz[
                plot_cruz[
                    "Variação"
                ].notna()
            ]
        )
        .mark_text(
            dx=alt.expr(
                "datum.Variação >= 0 "
                "? 5 : -5"
            ),
            align=alt.expr(
                "datum.Variação >= 0 "
                "? 'left' : 'right'"
            ),
        )
        .encode(

            y=alt.Y(
                "Linha:N",
                sort=ordem,
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


    grafico_cruz = (
        alt.hconcat(
            (
                esquerda
                +
                texto_esquerda
            ).properties(
                width=550
            ),

            (
                direita
                +
                texto_direita
            ).properties(
                width=300
            ),

            spacing=25,
        )
        .resolve_scale(
            y="shared"
        )
    )


    st.altair_chart(
        grafico_cruz,
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
        ">
            DEMOGRAFIA
        </div>
        """,
        unsafe_allow_html=True,
    )


    ano_demografia = st.radio(
        "Ano de referência",
        options=ANOS_PAINEL,
        index=4,
        horizontal=True,
        key="ano_demografia",
    )


    opcoes_demo = list(
        EIXOS_DISPONIVEIS.keys()
    )


    col_var, col_visual = st.columns(
        [
            1.15,
            4.85,
        ]
    )


    with col_var:

        variavel_demo = st.radio(
            "Variável das barras",
            opcoes_demo,
            index=(
                opcoes_demo.index(
                    "PPI"
                )
                if "PPI"
                in opcoes_demo
                else 0
            ),
            format_func=rotulo_dimensao,
        )


    op_comp = [
        x
        for x
        in opcoes_demo
        if x
        != variavel_demo
    ]


    with col_visual:

        variavel_comp = st.radio(
            "Composição das barras",
            op_comp,
            index=(
                op_comp.index(
                    "INSE"
                )
                if "INSE"
                in op_comp
                else 0
            ),
            horizontal=True,
            format_func=rotulo_dimensao,
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
    ] = (
        resumo[
            "Escolas"
        ]
        /
        resumo[
            "Total"
        ]
    )


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
    ] = (
        temp_cons[
            "Categoria"
        ].values
    )


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


    total_cons = (
        cons[
            "Escolas"
        ].sum()
    )


    cons[
        "Percentual"
    ] = (
        cons[
            "Escolas"
        ]
        / total_cons
    )


    cons[
        "Grupo"
    ] = "Consolidado"


    cons[
        "Total"
    ] = total_cons


    resumo = pd.concat(
        [
            resumo,
            cons,
        ],
        ignore_index=True,
    )


    ordem_barras = (
        ordem_grupos
        +
        [
            "Consolidado"
        ]
    )


    paleta = [
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


    graf_pct = (
        alt.Chart(
            resumo
        )
        .mark_bar()
        .encode(

            y=alt.Y(
                "Grupo:N",
                sort=ordem_barras,
                title=None,
            ),

            x=alt.X(
                "Percentual:Q",
                stack="normalize",
                axis=alt.Axis(
                    format=".0%",
                ),
                title=None,
            ),

            color=alt.Color(
                "Composição:N",
                scale=alt.Scale(
                    domain=ordem_comp,
                    range=paleta[
                        :len(
                            ordem_comp
                        )
                    ],
                ),
            ),

            tooltip=[
                "Grupo:N",
                "Composição:N",
                "Escolas:Q",
                alt.Tooltip(
                    "Percentual:Q",
                    format=".1%",
                ),
            ],
        )
        .properties(
            height=max(
                250,
                42
                * len(
                    ordem_barras
                ),
            )
        )
    )


    graf_n = (
        alt.Chart(
            totais
        )
        .mark_bar(
            color="#6C93B8"
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
            ),
        )
    )


    with col_visual:

        st.altair_chart(
            alt.hconcat(
                graf_pct.properties(
                    width=520
                ),
                graf_n.properties(
                    width=180
                ),
            )
            .resolve_scale(
                y="shared"
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


c1, c2, c3 = st.columns(
    [
        2,
        1,
        1,
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
    )


with c2:

    ordenacao = st.selectbox(
        "Ordenação",
        [
            "Número absoluto",
            "Delta",
        ],
    )


with c3:

    same_schools = st.toggle(
        "SAME SCHOOLS",
        value=False,
    )


# ============================================================
# ANOS
# ============================================================

_, bloco_anos, __ = st.columns(
    [
        1.4,
        3,
        1.4,
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
# DIVISOR
# ============================================================

st.markdown(
    '<hr class="soft-divider">',
    unsafe_allow_html=True,
)


# ============================================================
# VARIÁVEL DO EIXO X
# ============================================================

st.markdown(
    """
    <div style="
        text-align:center;
        font-size:0.80rem;
        font-weight:600;
        margin-bottom:0.15rem;
    ">
        Variável
    </div>
    """,
    unsafe_allow_html=True,
)


if "eixo_x" not in st.session_state:

    st.session_state[
        "eixo_x"
    ] = "Tipo de Escola"


_, bloco_eixo, __ = st.columns(
    [
        0.4,
        5.2,
        0.4,
    ]
)


with bloco_eixo:

    st.radio(
        "Variável",
        options=list(
            EIXOS_DISPONIVEIS.keys()
        ),
        horizontal=True,
        label_visibility="collapsed",
        format_func=rotulo_dimensao,
        key="eixo_x",
    )


eixo_x = (
    st.session_state[
        "eixo_x"
    ]
)


# ============================================================
# SAME SCHOOLS
# ============================================================

df_principal = (
    df.copy()
)


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


consolidado = (
    calcular_consolidado(
        df_principal,
        indicador,
        anos,
    )
)


# ============================================================
# INTEGRAL AGREGADO
# ============================================================

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

    st.stop()


# ============================================================
# ANOS MAIS RECENTES
# ============================================================

anos_ord = sorted(
    anos
)


ano_final = (
    anos_ord[-1]
)


ano_inicial = (
    anos_ord[-2]
    if len(
        anos_ord
    )
    >= 2
    else None
)


# ============================================================
# ORDEM DAS CATEGORIAS
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

        ordem_categorias = (
            categorias
        )

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

            ordem_categorias = (
                categorias
            )


for categoria in categorias:

    if categoria not in ordem_categorias:

        ordem_categorias.append(
            categoria
        )


# ============================================================
# BASE ÚNICA PARA OS DOIS GRÁFICOS
# ============================================================

plot_principal, ordem_linhas = (
    preparar_layout_horizontal_principal(
        resultado=resultado,
        consolidado=consolidado,
        anos=anos,
        ordem_categorias=ordem_categorias,
        ano_inicial=ano_inicial,
        ano_final=ano_final,
    )
)


formatos = formatos_indicador(
    indicador
)


altura = max(
    300,
    len(
        plot_principal
    )
    * 25,
)


# ============================================================
# GRÁFICO ESQUERDO — VALORES ABSOLUTOS
# ============================================================

graf_abs = (
    alt.Chart(
        plot_principal
    )
    .mark_bar()
    .encode(

        y=alt.Y(
            "Linha:N",
            sort=ordem_linhas,
            title=None,
            axis=alt.Axis(
                labelLimit=280,
                labelFontSize=10,
            ),
        ),

        x=alt.X(
            "Média:Q",
            title=indicador,
            scale=alt.Scale(
                zero=True
            ),
            axis=alt.Axis(
                format=formatos[
                    "eixo"
                ]
            ),
        ),

        color=alt.Color(
            "Ano:N",
            title="Ano",
            scale=alt.Scale(
                domain=ORDEM_ANOS_STR,
                range=ESCALA_CORES_ANOS,
            ),
        ),

        tooltip=[
            alt.Tooltip(
                "Categoria:N",
                title=rotulo_dimensao(
                    eixo_x
                ),
            ),

            alt.Tooltip(
                "Ano:N",
            ),

            alt.Tooltip(
                "N escolas:Q",
                title="Escolas",
                format=",",
            ),

            alt.Tooltip(
                "Média:Q",
                format=formatos[
                    "tooltip"
                ],
            ),
        ],
    )
    .properties(
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
)


texto_abs = (
    alt.Chart(
        plot_principal
    )
    .mark_text(
        align="left",
        dx=5,
        fontSize=10,
    )
    .encode(

        y=alt.Y(
            "Linha:N",
            sort=ordem_linhas,
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


# ============================================================
# GRÁFICO DIREITO — DELTA
# ============================================================

plot_delta = (
    plot_principal[
        plot_principal[
            "Variação"
        ].notna()
    ]
    .copy()
)


graf_delta = (
    alt.Chart(
        plot_delta
    )
    .mark_bar(
        color=COR_DELTA
    )
    .encode(

        y=alt.Y(
            "Linha:N",
            sort=ordem_linhas,
            title=None,
            axis=None,
        ),

        x=alt.X(
            "Variação:Q",
            title=(
                (
                    f"Δ {ano_final} "
                    f"− {ano_inicial}"
                )
                if ano_inicial
                is not None
                else "Variação"
            ),
            axis=alt.Axis(
                format=formatos[
                    "eixo"
                ]
            ),
        ),

        tooltip=[
            alt.Tooltip(
                "Categoria:N",
                title=rotulo_dimensao(
                    eixo_x
                ),
            ),

            alt.Tooltip(
                "Variação:Q",
                format=formatos[
                    "delta"
                ],
            ),
        ],
    )
    .properties(
        height=altura,
        title=alt.TitleParams(
            text=(
                (
                    f"Variação "
                    f"{ano_final} − "
                    f"{ano_inicial}"
                )
                if ano_inicial
                is not None
                else "Variação"
            ),
            anchor="middle",
            fontSize=17,
            fontWeight="bold",
        ),
    )
)


texto_delta = (
    alt.Chart(
        plot_delta
    )
    .mark_text(
        dx=alt.expr(
            "datum.Variação >= 0 "
            "? 5 : -5"
        ),
        align=alt.expr(
            "datum.Variação >= 0 "
            "? 'left' : 'right'"
        ),
        fontSize=10,
    )
    .encode(

        y=alt.Y(
            "Linha:N",
            sort=ordem_linhas,
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


linha_zero_delta = (
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
        color="#666666",
        strokeWidth=1,
    )
    .encode(
        x="zero:Q"
    )
)


# ============================================================
# VISÃO ÚNICA
# ============================================================

painel_graficos = (
    alt.hconcat(

        (
            graf_abs
            +
            texto_abs
        )
        .properties(
            width=600
        ),

        (
            graf_delta
            +
            texto_delta
            +
            linha_zero_delta
        )
        .properties(
            width=320
        ),

        spacing=30,
    )
    .resolve_scale(
        y="shared"
    )
)


st.altair_chart(
    painel_graficos,
    width="stretch",
)