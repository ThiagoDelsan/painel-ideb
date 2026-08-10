import re

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.data import (
    preparar_base,
    aplicar_filtros_categoricos,
    aplicar_filtro_binario_coluna,
    aplicar_filtro_participacao_ideb,
    obter_opcoes_filtro,
    media_ponderada_por_categoria,
    criar_variavel_eixo,
    EIXOS_DISPONIVEIS,
)


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
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

        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.55rem;
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }

        section[data-testid="stSidebar"] h3 {
            font-size: 0.90rem !important;
            margin-top: 0 !important;
            margin-bottom: 0.20rem !important;
        }

        section[data-testid="stSidebar"] label {
            font-size: 0.68rem !important;
            line-height: 0.85rem !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stVerticalBlock"] {
            gap: 0.08rem !important;
        }

        section[data-testid="stSidebar"] .stMultiSelect {
            margin-top: -0.10rem !important;
            margin-bottom: -0.38rem !important;
        }

        section[data-testid="stSidebar"]
        div[data-baseweb="select"] {
            font-size: 0.74rem !important;
            min-height: 31px !important;
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


ORDEM_FAIXA_IDEB = [
    "Menor que 3",
    "Entre 3 e 4",
    "Entre 4 e 5",
    "Entre 5 e 6",
    "Maior que 6",
    "Sem resultado",
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


# ============================================================
# RÓTULOS DAS DIMENSÕES
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
# FUNÇÕES AUXILIARES
# ============================================================

def calcular_consolidado(
    base,
    indicador,
    anos,
):

    peso = "Matrículas EM (total) 3/4"

    resultados = []

    for ano in anos:

        recorte = base[
            base["Ano"] == ano
        ].copy()

        recorte = recorte[
            recorte[indicador].notna()
        ].copy()

        recorte = recorte[
            recorte[peso].notna()
            &
            (
                recorte[peso] > 0
            )
        ].copy()

        if recorte.empty:
            continue

        media = np.average(
            recorte[indicador],
            weights=recorte[peso],
        )

        resultados.append(
            {
                "Ano": str(ano),
                "Categoria": "Consolidado",
                "Média": media,
                "N escolas": recorte[
                    "Cód. INEP"
                ].nunique(),
                "Matrículas": recorte[
                    peso
                ].sum(),
            }
        )

    return pd.DataFrame(
        resultados
    )


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


def filtrar_same_schools(
    base,
    indicador,
    anos,
):

    if not anos:

        return base

    peso = "Matrículas EM (total) 3/4"

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

    ids_validos = (
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
                ids_validos
            )
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )


def criar_duas_dimensoes(
    base,
    variavel_1,
    variavel_2,
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

    if variavel_1 == "Tipo de Escola":

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
            "Integral (Mista + 100%)"
        )

        resultado = pd.concat(
            [
                resultado,
                agregado,
            ],
            ignore_index=True,
        )

    if variavel_2 == "Tipo de Escola":

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
            "Integral (Mista + 100%)"
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
):

    peso = "Matrículas EM (total) 3/4"

    base_dupla = criar_duas_dimensoes(
        base,
        variavel_1,
        variavel_2,
    )

    base_dupla = (
        base_dupla[
            base_dupla[
                "Ano"
            ].isin(
                anos
            )
        ]
        .copy()
    )

    base_dupla = (
        base_dupla[
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
            "Integral (Mista + 100%)",
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
# CARREGAMENTO DA BASE
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
# CABEÇALHO
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
    col_nav_1,
    col_nav_2,
    col_nav_3,
    col_nav_4,
    col_nav_vazio,
) = st.columns(
    [
        1.55,
        1.05,
        1.0,
        1.25,
        3.2,
    ]
)


with col_nav_1:

    if st.button(
        "PRINCIPAIS INDICADORES",
        width="stretch",
    ):

        st.session_state.pagina = (
            "PRINCIPAIS INDICADORES"
        )


with col_nav_2:

    if st.button(
        "CRUZAMENTOS",
        width="stretch",
    ):

        st.session_state.pagina = (
            "CRUZAMENTOS"
        )


with col_nav_3:

    if st.button(
        "DEMOGRAFIA",
        width="stretch",
    ):

        st.session_state.pagina = (
            "DEMOGRAFIA"
        )


with col_nav_4:

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
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    "### Filtros"
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
        if nome == "Estado"
        else "Todos"
    )

    filtros[nome] = (
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
# PARTICIPAÇÃO NO IDEB
# ============================================================

st.sidebar.markdown(
    """
    <div style="
        font-size:0.71rem;
        font-weight:600;
        margin-top:7px;
        margin-bottom:-5px;
    ">
        Participação no IDEB
    </div>
    """,
    unsafe_allow_html=True,
)


filtro_ideb = {}


for ano in ANOS_PAINEL:

    filtro_ideb[ano] = (
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
        font-size:0.71rem;
        font-weight:600;
        margin-top:7px;
        margin-bottom:-5px;
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

        df = aplicar_filtro_participacao_ideb(
            df,
            ano,
            valores,
        )

    if "Propedêutido" in df.columns:

        coluna_proped = "Propedêutido"

    elif "Propedêutico" in df.columns:

        coluna_proped = "Propedêutico"

    else:

        coluna_proped = "Propedêutido"

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
        col_indicador_rank,
        col_criterio_rank,
    ) = st.columns(
        [
            2,
            1,
        ]
    )


    with col_indicador_rank:

        indicador_rank = st.selectbox(
            "Indicador",
            options=[
                "IDEB",
                "N(LP)",
                "N(M)",
                "N",
                "Rendimento",
            ],
            index=0,
            key="indicador_melhores",
        )


    with col_criterio_rank:

        criterio_rank = st.selectbox(
            "Ordenar por",
            options=[
                "Valor absoluto",
                "Variação",
            ],
            index=0,
            key="criterio_melhores",
        )


    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:0.80rem;
            font-weight:600;
            margin-top:4px;
            margin-bottom:2px;
        ">
            Anos considerados
        </div>
        """,
        unsafe_allow_html=True,
    )


    (
        _,
        bloco_anos_rank,
        __,
    ) = st.columns(
        [
            1.6,
            2.8,
            1.6,
        ]
    )


    with bloco_anos_rank:

        anos_rank = st.multiselect(
            "Anos considerados",
            options=ANOS_PAINEL,
            default=[
                2023,
                2025,
            ],
            max_selections=2,
            label_visibility="collapsed",
            key="anos_melhores",
        )


    if not anos_rank:

        st.warning(
            "Selecione pelo menos um ano."
        )

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
        ) == 2
        else None
    )


    if (
        criterio_rank == "Variação"
        and
        len(
            anos_rank
        ) < 2
    ):

        st.warning(
            "Para ordenar por variação, "
            "selecione exatamente dois anos."
        )

        st.stop()


    candidatos_nome_escola = [
        "Nome da Escola",
        "Nome da escola",
        "Nome Escola",
        "Nome escola",
        "Escola",
        "NO_ESCOLA",
        "NO_ENTIDADE",
        "Nome",
    ]


    coluna_nome_escola = None


    for candidato in candidatos_nome_escola:

        if candidato in df.columns:

            coluna_nome_escola = candidato
            break


    colunas_rank = [
        "Cód. INEP",
        "Ano",
        indicador_rank,
    ]


    if coluna_nome_escola:

        colunas_rank.append(
            coluna_nome_escola
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
                    colunas_rank
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


    if coluna_nome_escola:

        base_rank[
            "Escola_rank"
        ] = (
            base_rank[
                coluna_nome_escola
            ]
            .astype(str)
            .str.strip()
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
                subset=[
                    "Cód. INEP"
                ]
            )
            .sort_values(
                indicador_rank,
                ascending=False,
            )
            .head(20)
            .reset_index(
                drop=True
            )
        )


        titulo_ranking = (
            f"Top 20 — {indicador_rank} "
            f"em {ano_rank_final}"
        )


    else:

        base_pivot = (
            base_rank[
                [
                    "Cód. INEP",
                    "Ano",
                    indicador_rank,
                ]
            ]
            .drop_duplicates(
                subset=[
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
            not in base_pivot.columns
            or
            ano_rank_final
            not in base_pivot.columns
        ):

            st.warning(
                "Não há dados suficientes "
                "para os anos selecionados."
            )

            st.stop()


        ranking = (
            base_pivot[
                base_pivot[
                    ano_rank_inicial
                ].notna()
                &
                base_pivot[
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


        identificacao = (
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
            ranking.merge(
                identificacao,
                on="Cód. INEP",
                how="left",
            )
            .sort_values(
                "Variação",
                ascending=False,
            )
            .head(20)
            .reset_index(
                drop=True
            )
        )


        titulo_ranking = (
            f"Top 20 — Variação de "
            f"{indicador_rank}: "
            f"{ano_rank_final} − "
            f"{ano_rank_inicial}"
        )


    if ranking.empty:

        st.warning(
            "Não há escolas com resultados "
            "válidos para os filtros atuais."
        )

        st.stop()


    ranking[
        "Posição"
    ] = np.arange(
        1,
        len(
            ranking
        )
        + 1,
    )


    base_dimensoes = (
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


    for dimensao in EIXOS_DISPONIVEIS:

        try:

            temp = criar_variavel_eixo(
                base_dimensoes,
                dimensao,
            )

            base_dimensoes[
                dimensao
            ] = (
                temp[
                    "Categoria"
                ].values
            )

        except Exception:

            base_dimensoes[
                dimensao
            ] = "Não informado"


    colunas_dims = [
        "Cód. INEP",
    ] + list(
        EIXOS_DISPONIVEIS.keys()
    )


    ranking = (
        ranking.merge(
            base_dimensoes[
                colunas_dims
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
            margin-top:14px;
            margin-bottom:10px;
        ">
            {titulo_ranking}
        </div>
        """,
        unsafe_allow_html=True,
    )


    tabela_rank = pd.DataFrame()


    tabela_rank[
        "Posição"
    ] = ranking[
        "Posição"
    ]


    tabela_rank[
        "Nome"
    ] = ranking[
        "Escola_rank"
    ]


    tabela_rank[
        "Cód. INEP"
    ] = ranking[
        "Cód. INEP"
    ]


    if criterio_rank == "Valor absoluto":

        tabela_rank[
            str(
                ano_rank_final
            )
        ] = ranking[
            indicador_rank
        ]

    else:

        tabela_rank[
            str(
                ano_rank_inicial
            )
        ] = ranking[
            ano_rank_inicial
        ]


        tabela_rank[
            str(
                ano_rank_final
            )
        ] = ranking[
            ano_rank_final
        ]


        tabela_rank[
            "Variação"
        ] = ranking[
            "Variação"
        ]


    for dimensao in EIXOS_DISPONIVEIS:

        if dimensao in ranking.columns:

            tabela_rank[
                rotulo_dimensao(
                    dimensao
                )
            ] = ranking[
                dimensao
            ]


    st.dataframe(
        tabela_rank,
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
            margin-top:8px;
            margin-bottom:5px;
        ">
            CRUZAMENTOS
        </div>
        """,
        unsafe_allow_html=True,
    )


    col_ind_cruz, col_ord_cruz = (
        st.columns(
            [
                2,
                1,
            ]
        )
    )


    with col_ind_cruz:

        indicador_cruz = st.selectbox(
            "Indicador",
            options=[
                "IDEB",
                "N(LP)",
                "N(M)",
                "N",
                "Rendimento",
            ],
            key="indicador_cruz",
        )


    with col_ord_cruz:

        ordenacao_cruz = st.selectbox(
            "Ordenação",
            options=[
                "Número absoluto",
                "Delta",
            ],
            key="ordenacao_cruz",
        )


    (
        _,
        bloco_anos_cruz,
        __,
    ) = st.columns(
        [
            1.4,
            3,
            1.4,
        ]
    )


    with bloco_anos_cruz:

        cols_anos_cruz = st.columns(5)


        selecao_cruz = {}


        padrao_cruz = {
            2017: False,
            2019: False,
            2021: False,
            2023: True,
            2025: True,
        }


        for coluna, ano in zip(
            cols_anos_cruz,
            ANOS_PAINEL,
        ):

            with coluna:

                selecao_cruz[
                    ano
                ] = st.checkbox(
                    str(ano),
                    value=padrao_cruz[
                        ano
                    ],
                    key=f"cruz_ano_{ano}",
                )


    anos_cruz = [
        ano
        for ano, ativo
        in selecao_cruz.items()
        if ativo
    ]


    if not anos_cruz:

        st.warning(
            "Selecione pelo menos um ano."
        )

        st.stop()


    opcoes_cruz = list(
        EIXOS_DISPONIVEIS.keys()
    )


    (
        col_var_1,
        col_var_2,
    ) = st.columns(2)


    with col_var_1:

        variavel_1 = st.selectbox(
            "1ª dimensão",
            options=opcoes_cruz,
            index=(
                opcoes_cruz.index(
                    "INSE"
                )
                if "INSE"
                in opcoes_cruz
                else 0
            ),
            format_func=rotulo_dimensao,
            key="cruz_var_1",
        )


    opcoes_var_2 = [
        valor
        for valor
        in opcoes_cruz
        if valor
        != variavel_1
    ]


    with col_var_2:

        indice_ppi = (
            opcoes_var_2.index(
                "PPI"
            )
            if "PPI"
            in opcoes_var_2
            else 0
        )


        variavel_2 = st.selectbox(
            "2ª dimensão",
            options=opcoes_var_2,
            index=indice_ppi,
            format_func=rotulo_dimensao,
            key="cruz_var_2",
        )


    try:

        resultado_cruz = (
            media_ponderada_duas_dimensoes(
                base=df,
                indicador=indicador_cruz,
                anos=anos_cruz,
                variavel_1=variavel_1,
                variavel_2=variavel_2,
            )
        )


        consolidado_cruz = (
            calcular_consolidado(
                base=df,
                indicador=indicador_cruz,
                anos=anos_cruz,
            )
        )


    except Exception as erro:

        st.error(
            "Não foi possível preparar "
            "o cruzamento selecionado."
        )

        st.exception(
            erro
        )

        st.stop()


    if resultado_cruz.empty:

        st.warning(
            "Não há dados válidos para "
            "o cruzamento selecionado."
        )

        st.stop()


    ordem_1 = ordenar_dimensao(
        resultado_cruz[
            "Categoria_1"
        ].unique(),
        variavel_1,
    )


    ordem_2 = ordenar_dimensao(
        resultado_cruz[
            "Categoria_2"
        ].unique(),
        variavel_2,
    )


    anos_cruz_ord = sorted(
        anos_cruz
    )


    ano_cruz_final = (
        anos_cruz_ord[-1]
    )


    ano_cruz_inicial = (
        anos_cruz_ord[-2]
        if len(
            anos_cruz_ord
        ) >= 2
        else None
    )


    resultado_cruz_plot = (
        resultado_cruz[
            [
                "Ano",
                "Categoria_1",
                "Categoria_2",
                "Média",
                "N escolas",
                "Matrículas",
            ]
        ]
        .copy()
    )


    consolidado_plot = (
        consolidado_cruz.copy()
    )


    consolidado_plot[
        "Categoria_1"
    ] = "Consolidado"


    consolidado_plot[
        "Categoria_2"
    ] = "Total"


    consolidado_plot = (
        consolidado_plot[
            [
                "Ano",
                "Categoria_1",
                "Categoria_2",
                "Média",
                "N escolas",
                "Matrículas",
            ]
        ]
    )


    resultado_cruz_plot = pd.concat(
        [
            resultado_cruz_plot,
            consolidado_plot,
        ],
        ignore_index=True,
    )


    ordem_1_plot = (
        ordem_1
        +
        [
            "Consolidado"
        ]
    )


    ordem_2_plot = (
        ordem_2
        +
        [
            "Total"
        ]
    )


    if indicador_cruz == "Rendimento":

        formato_rotulo_cruz = ".1%"
        formato_tooltip_cruz = ".2%"
        formato_eixo_cruz = ".0%"

    else:

        formato_rotulo_cruz = ".2f"
        formato_tooltip_cruz = ".3f"
        formato_eixo_cruz = ".1f"


    qtd_grupos_maiores = max(
        len(
            ordem_1_plot
        ),
        1,
    )


    largura_facet = int(
        max(
            105,
            min(
                245,
                1100
                / qtd_grupos_maiores,
            )
        )
    )


    st.markdown(
        f"""
        <div style="
            text-align:center;
            font-size:23px;
            font-weight:700;
            margin-top:10px;
            margin-bottom:2px;
        ">
            Média ponderada de {indicador_cruz}
        </div>

        <div style="
            text-align:center;
            font-size:0.78rem;
            color:#70757d;
            margin-bottom:7px;
        ">
            {rotulo_dimensao(variavel_1)}
            → {rotulo_dimensao(variavel_2)}
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # GRÁFICO PRINCIPAL — LAYER PRIMEIRO, FACET DEPOIS
    # ========================================================

    base_cruz_chart = (
        alt.Chart(
            resultado_cruz_plot
        )
        .encode(

            x=alt.X(
                "Categoria_2:N",

                title=None,

                sort=ordem_2_plot,

                axis=alt.Axis(
                    labelAngle=-90,
                    labelPadding=5,
                    labelLimit=140,
                    labelFontSize=10,
                ),
            ),

            xOffset=alt.XOffset(
                "Ano:N",
                sort=ORDEM_ANOS_STR,
                scale=alt.Scale(
                    paddingInner=0.02,
                    paddingOuter=0.02,
                ),
            ),

            y=alt.Y(
                "Média:Q",

                title=indicador_cruz,

                scale=alt.Scale(
                    zero=True
                ),

                axis=alt.Axis(
                    format=formato_eixo_cruz
                ),
            ),
        )
    )


    barras_cruz = (
        base_cruz_chart
        .mark_bar()
        .encode(

            color=alt.Color(
                "Ano:N",

                title="Ano",

                scale=alt.Scale(
                    domain=ORDEM_ANOS_STR,
                    range=ESCALA_CORES_ANOS,
                ),

                sort=ORDEM_ANOS_STR,
            ),

            tooltip=[
                alt.Tooltip(
                    "Categoria_1:N",
                    title=rotulo_dimensao(
                        variavel_1
                    ),
                ),

                alt.Tooltip(
                    "Categoria_2:N",
                    title=rotulo_dimensao(
                        variavel_2
                    ),
                ),

                alt.Tooltip(
                    "Ano:N",
                    title="Ano",
                ),

                alt.Tooltip(
                    "Média:Q",
                    title="Média ponderada",
                    format=formato_tooltip_cruz,
                ),

                alt.Tooltip(
                    "N escolas:Q",
                    title="Escolas",
                    format=",",
                ),

                alt.Tooltip(
                    "Matrículas:Q",
                    title="Matrículas",
                    format=",",
                ),
            ],
        )
    )


    rotulos_cruz = (
        base_cruz_chart
        .mark_text(
            dy=-7,
            fontSize=9,
        )
        .encode(

            text=alt.Text(
                "Média:Q",
                format=formato_rotulo_cruz,
            ),
        )
    )


    camada_cruz = (
        barras_cruz
        +
        rotulos_cruz
    )


    grafico_cruz = (
        camada_cruz
        .properties(
            width=largura_facet,
            height=300,
        )
        .facet(

            column=alt.Column(
                "Categoria_1:N",

                title=None,

                sort=ordem_1_plot,

                header=alt.Header(
                    labelAngle=0,
                    labelFontSize=12,
                    labelFontWeight="bold",
                    labelPadding=10,
                    labelLimit=220,
                    title=None,
                ),
            ),

            spacing=15,
        )
        .resolve_scale(
            y="shared"
        )
    )


    st.altair_chart(
        grafico_cruz,
        width="stretch",
    )


    # ========================================================
    # DELTA
    # ========================================================

    if ano_cruz_inicial is not None:

        variacao_cruz = (
            resultado_cruz[
                resultado_cruz[
                    "Ano"
                ].isin(
                    [
                        str(
                            ano_cruz_inicial
                        ),
                        str(
                            ano_cruz_final
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
            ano_cruz_inicial
        )

        col_fim = str(
            ano_cruz_final
        )


        if (
            col_ini
            in variacao_cruz.columns
            and
            col_fim
            in variacao_cruz.columns
        ):

            variacao_cruz[
                "Variação"
            ] = (
                variacao_cruz[
                    col_fim
                ]
                -
                variacao_cruz[
                    col_ini
                ]
            )


            delta_consol = (
                consolidado_cruz[
                    consolidado_cruz[
                        "Ano"
                    ].isin(
                        [
                            str(
                                ano_cruz_inicial
                            ),
                            str(
                                ano_cruz_final
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
                col_ini
                in delta_consol.columns
                and
                col_fim
                in delta_consol.columns
            ):

                delta_consol[
                    "Variação"
                ] = (
                    delta_consol[
                        col_fim
                    ]
                    -
                    delta_consol[
                        col_ini
                    ]
                )


                delta_consol[
                    "Categoria_1"
                ] = "Consolidado"


                delta_consol[
                    "Categoria_2"
                ] = "Total"


                delta_consol = (
                    delta_consol[
                        [
                            "Categoria_1",
                            "Categoria_2",
                            "Variação",
                        ]
                    ]
                )


                variacao_cruz = pd.concat(
                    [
                        variacao_cruz[
                            [
                                "Categoria_1",
                                "Categoria_2",
                                "Variação",
                            ]
                        ],

                        delta_consol,
                    ],
                    ignore_index=True,
                )


            formato_delta_cruz = (
                "+.1%"
                if indicador_cruz
                == "Rendimento"
                else "+.2f"
            )


            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    font-size:23px;
                    font-weight:700;
                    margin-top:8px;
                    margin-bottom:2px;
                ">
                    Variação de {indicador_cruz}:
                    {ano_cruz_final} − {ano_cruz_inicial}
                </div>
                """,
                unsafe_allow_html=True,
            )


            # =================================================
            # DELTA — LAYER PRIMEIRO, FACET DEPOIS
            # =================================================

            base_delta_chart = (
                alt.Chart(
                    variacao_cruz
                )
                .encode(

                    x=alt.X(
                        "Categoria_2:N",

                        title=None,

                        sort=ordem_2_plot,

                        axis=alt.Axis(
                            labelAngle=-90,
                            labelPadding=5,
                            labelLimit=140,
                            labelFontSize=10,
                        ),
                    ),

                    y=alt.Y(
                        "Variação:Q",

                        title=(
                            f"Δ {ano_cruz_final} "
                            f"− {ano_cruz_inicial}"
                        ),
                    ),
                )
            )


            barras_delta_cruz = (
                base_delta_chart
                .mark_bar(
                    color="#9B8878"
                )
                .encode(

                    tooltip=[
                        alt.Tooltip(
                            "Categoria_1:N",
                            title=rotulo_dimensao(
                                variavel_1
                            ),
                        ),

                        alt.Tooltip(
                            "Categoria_2:N",
                            title=rotulo_dimensao(
                                variavel_2
                            ),
                        ),

                        alt.Tooltip(
                            "Variação:Q",
                            title="Variação",
                            format=formato_delta_cruz,
                        ),
                    ],
                )
            )


            rotulos_delta_cruz = (
                base_delta_chart
                .mark_text(
                    dy=alt.expr(
                        "datum['Variação'] >= 0 "
                        "? -7 : 13"
                    ),
                    fontSize=9,
                )
                .encode(

                    text=alt.Text(
                        "Variação:Q",
                        format=formato_delta_cruz,
                    ),
                )
            )


            linha_zero_cruz = (
                alt.Chart(
                    variacao_cruz
                )
                .mark_rule(
                    color="#555555",
                    strokeWidth=1,
                )
                .encode(
                    y=alt.datum(
                        0
                    )
                )
            )


            camada_delta_cruz = (
                barras_delta_cruz
                +
                rotulos_delta_cruz
                +
                linha_zero_cruz
            )


            grafico_delta_cruz = (
                camada_delta_cruz
                .properties(
                    width=largura_facet,
                    height=220,
                )
                .facet(

                    column=alt.Column(
                        "Categoria_1:N",

                        title=None,

                        sort=ordem_1_plot,

                        header=alt.Header(
                            labelAngle=0,
                            labelFontSize=12,
                            labelFontWeight="bold",
                            labelPadding=10,
                            labelLimit=220,
                            title=None,
                        ),
                    ),

                    spacing=15,
                )
                .resolve_scale(
                    y="shared"
                )
            )


            st.altair_chart(
                grafico_delta_cruz,
                width="stretch",
            )


        else:

            st.info(
                "Não há resultados válidos nos "
                "dois anos mais recentes selecionados."
            )


    else:

        st.info(
            "Selecione pelo menos dois anos "
            "para visualizar a variação."
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
            margin-top:8px;
            margin-bottom:4px;
        ">
            DEMOGRAFIA
        </div>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:0.80rem;
            font-weight:600;
            margin-bottom:-4px;
        ">
            Ano de referência
        </div>
        """,
        unsafe_allow_html=True,
    )


    (
        _,
        bloco_ano_demo,
        __,
    ) = st.columns(
        [
            1.4,
            3,
            1.4,
        ]
    )


    with bloco_ano_demo:

        ano_demografia = st.radio(
            "Ano de referência",
            options=ANOS_PAINEL,
            index=4,
            horizontal=True,
            label_visibility="collapsed",
            key="ano_demografia",
        )


    opcoes_dimensoes_demo = list(
        EIXOS_DISPONIVEIS.keys()
    )


    (
        col_variavel_demo,
        col_visual_demo,
    ) = st.columns(
        [
            1.15,
            4.85,
        ],
        gap="medium",
    )


    with col_variavel_demo:

        st.markdown(
            """
            <div class="demo-variable-title">
                Variável das barras
            </div>
            """,
            unsafe_allow_html=True,
        )


        indice_ppi = (
            opcoes_dimensoes_demo.index(
                "PPI"
            )
            if "PPI"
            in opcoes_dimensoes_demo
            else 0
        )


        variavel_demo = st.radio(
            "Variável das barras",
            options=opcoes_dimensoes_demo,
            index=indice_ppi,
            horizontal=False,
            label_visibility="collapsed",
            format_func=rotulo_dimensao,
            key="variavel_demo",
        )


    opcoes_composicao = [
        opcao
        for opcao
        in opcoes_dimensoes_demo
        if opcao
        != variavel_demo
    ]


    composicao_padrao = (
        "INSE"
        if "INSE"
        in opcoes_composicao
        else opcoes_composicao[0]
    )


    if (
        "variavel_composicao_demo"
        in st.session_state
        and
        st.session_state[
            "variavel_composicao_demo"
        ]
        not in opcoes_composicao
    ):

        st.session_state[
            "variavel_composicao_demo"
        ] = (
            composicao_padrao
        )


    indice_comp = (
        opcoes_composicao.index(
            composicao_padrao
        )
    )


    with col_visual_demo:

        st.markdown(
            """
            <div style="
                text-align:center;
                font-size:0.80rem;
                font-weight:600;
                margin-top:3px;
                margin-bottom:-3px;
            ">
                Composição das barras
            </div>
            """,
            unsafe_allow_html=True,
        )


        variavel_composicao = (
            st.radio(
                "Composição das barras",
                options=opcoes_composicao,
                index=indice_comp,
                horizontal=True,
                label_visibility="collapsed",
                format_func=rotulo_dimensao,
                key="variavel_composicao_demo",
            )
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


    if base_demo.empty:

        st.warning(
            "Não há escolas para "
            "os filtros selecionados."
        )

        st.stop()


    try:

        temp_grupo = criar_variavel_eixo(
            base_demo,
            variavel_demo,
        )


        temp_comp = criar_variavel_eixo(
            base_demo,
            variavel_composicao,
        )


        base_demo[
            "Grupo_demo"
        ] = (
            temp_grupo[
                "Categoria"
            ].values
        )


        base_demo[
            "Composicao_demo"
        ] = (
            temp_comp[
                "Categoria"
            ].values
        )


    except Exception as erro:

        st.error(
            "Não foi possível preparar "
            "a visualização."
        )

        st.exception(
            erro
        )

        st.stop()


    if variavel_demo == "Tipo de Escola":

        integral_demo = (
            base_demo[
                base_demo[
                    "Grupo_demo"
                ].isin(
                    [
                        "Mista",
                        "100% Integral",
                    ]
                )
            ]
            .copy()
        )


        integral_demo[
            "Grupo_demo"
        ] = (
            "Integral (Mista + 100%)"
        )


        base_demo = pd.concat(
            [
                base_demo,
                integral_demo,
            ],
            ignore_index=True,
        )


    ordem_grupos = ordenar_dimensao(
        base_demo[
            "Grupo_demo"
        ].unique(),
        variavel_demo,
    )


    ordem_composicao = ordenar_dimensao(
        base_demo[
            "Composicao_demo"
        ].unique(),
        variavel_composicao,
    )


    distribuicao = (
        base_demo
        .groupby(
            [
                "Grupo_demo",
                "Composicao_demo",
            ],
            as_index=False,
        )
        .agg(
            Escolas=(
                "Cód. INEP",
                "nunique",
            )
        )
        .rename(
            columns={
                "Grupo_demo":
                    "Grupo",

                "Composicao_demo":
                    "Composição",
            }
        )
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


    temp_consol = (
        criar_variavel_eixo(
            base_consolidado,
            variavel_composicao,
        )
    )


    base_consolidado[
        "Composição"
    ] = (
        temp_consol[
            "Categoria"
        ].values
    )


    consolidado_comp = (
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


    consolidado_comp[
        "Grupo"
    ] = "Consolidado"


    distribuicao = pd.concat(
        [
            distribuicao,
            consolidado_comp,
        ],
        ignore_index=True,
    )


    totais_grupos = (
        base_demo[
            [
                "Grupo_demo",
                "Cód. INEP",
            ]
        ]
        .drop_duplicates()
        .groupby(
            "Grupo_demo",
            as_index=False,
        )
        .agg(
            Total_Escolas=(
                "Cód. INEP",
                "nunique",
            )
        )
        .rename(
            columns={
                "Grupo_demo":
                    "Grupo"
            }
        )
    )


    total_consolidado = (
        base_consolidado[
            "Cód. INEP"
        ]
        .nunique()
    )


    totais = pd.concat(
        [
            totais_grupos,

            pd.DataFrame(
                {
                    "Grupo": [
                        "Consolidado"
                    ],

                    "Total_Escolas": [
                        total_consolidado
                    ],
                }
            ),
        ],
        ignore_index=True,
    )


    distribuicao = (
        distribuicao.merge(
            totais,
            on="Grupo",
            how="left",
        )
    )


    distribuicao[
        "Percentual"
    ] = (
        distribuicao[
            "Escolas"
        ]
        /
        distribuicao[
            "Total_Escolas"
        ]
    )


    mapa_ordem = {
        valor: i
        for i, valor
        in enumerate(
            ordem_composicao
        )
    }


    distribuicao[
        "_ordem"
    ] = (
        distribuicao[
            "Composição"
        ]
        .map(
            mapa_ordem
        )
        .fillna(
            len(
                ordem_composicao
            )
        )
    )


    distribuicao = (
        distribuicao
        .sort_values(
            [
                "Grupo",
                "_ordem",
            ]
        )
        .reset_index(
            drop=True
        )
    )


    distribuicao[
        "Fim"
    ] = (
        distribuicao
        .groupby(
            "Grupo"
        )[
            "Percentual"
        ]
        .cumsum()
    )


    distribuicao[
        "Início"
    ] = (
        distribuicao[
            "Fim"
        ]
        -
        distribuicao[
            "Percentual"
        ]
    )


    distribuicao[
        "Centro"
    ] = (
        (
            distribuicao[
                "Fim"
            ]
            +
            distribuicao[
                "Início"
            ]
        )
        / 2
    )


    ESPACO_DEMO = "   "


    ordem_barras_demo = (
        ordem_grupos
        +
        [
            ESPACO_DEMO,
            "Consolidado",
        ]
    )


    distribuicao = pd.concat(
        [
            distribuicao,

            pd.DataFrame(
                [
                    {
                        "Grupo":
                            ESPACO_DEMO,

                        "Composição":
                            (
                                ordem_composicao[0]
                                if ordem_composicao
                                else ""
                            ),

                        "Escolas":
                            0,

                        "Total_Escolas":
                            0,

                        "Percentual":
                            0,

                        "Início":
                            0,

                        "Fim":
                            0,

                        "Centro":
                            0,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )


    totais = pd.concat(
        [
            totais,

            pd.DataFrame(
                {
                    "Grupo": [
                        ESPACO_DEMO
                    ],

                    "Total_Escolas": [
                        0
                    ],
                }
            ),
        ],
        ignore_index=True,
    )


    paleta_demo = [
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
        "#6B6ECF",
        "#D4A6C8",
        "#A0CBE8",
        "#FFBE7D",
        "#8CD17D",
    ]


    cores_composicao = [
        paleta_demo[
            i
            % len(
                paleta_demo
            )
        ]
        for i
        in range(
            len(
                ordem_composicao
            )
        )
    ]


    altura_demo = max(
        250,
        39
        * len(
            ordem_barras_demo
        ),
    )


    with col_visual_demo:

        st.markdown(
            f"""
            <div style="
                text-align:center;
                font-size:21px;
                font-weight:700;
                margin-top:10px;
                margin-bottom:4px;
            ">
                Distribuição de
                {rotulo_dimensao(variavel_composicao)}
                por {rotulo_dimensao(variavel_demo)}
            </div>
            """,
            unsafe_allow_html=True,
        )


        barras_pct = (
            alt.Chart(
                distribuicao
            )
            .mark_bar(
                height=22
            )
            .encode(

                y=alt.Y(
                    "Grupo:N",
                    title=None,
                    sort=ordem_barras_demo,
                    axis=alt.Axis(
                        labelLimit=170,
                    ),
                ),

                x=alt.X(
                    "Fim:Q",
                    title=None,
                    scale=alt.Scale(
                        domain=[
                            0,
                            1,
                        ]
                    ),
                    axis=alt.Axis(
                        format=".0%"
                    ),
                ),

                x2="Início:Q",

                color=alt.Color(
                    "Composição:N",
                    title=rotulo_dimensao(
                        variavel_composicao
                    ),
                    scale=alt.Scale(
                        domain=ordem_composicao,
                        range=cores_composicao,
                    ),
                    legend=alt.Legend(
                        orient="bottom",
                        columns=4,
                    ),
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
                            variavel_composicao
                        ),
                    ),

                    alt.Tooltip(
                        "Escolas:Q",
                        title="Escolas",
                        format=",",
                    ),

                    alt.Tooltip(
                        "Percentual:Q",
                        title="Percentual",
                        format=".1%",
                    ),
                ],
            )
        )


        textos_pct = (
            alt.Chart(
                distribuicao
            )
            .transform_filter(
                "datum.Percentual >= 0.035"
            )
            .mark_text(
                fontSize=10
            )
            .encode(

                y=alt.Y(
                    "Grupo:N",
                    sort=ordem_barras_demo,
                ),

                x="Centro:Q",

                text=alt.Text(
                    "Percentual:Q",
                    format=".0%",
                ),
            )
        )


        grafico_pct = (
            barras_pct
            +
            textos_pct
        ).properties(
            width=500,
            height=altura_demo,
            title="Distribuição percentual",
        )


        barras_n = (
            alt.Chart(
                totais
            )
            .mark_bar(
                height=22,
                color="#6C93B8",
            )
            .encode(

                y=alt.Y(
                    "Grupo:N",
                    sort=ordem_barras_demo,
                    axis=None,
                ),

                x=alt.X(
                    "Total_Escolas:Q",
                    axis=None,
                ),
            )
        )


        textos_n = (
            alt.Chart(
                totais
            )
            .transform_filter(
                "datum.Total_Escolas > 0"
            )
            .mark_text(
                align="left",
                dx=6,
                fontWeight="bold",
            )
            .encode(

                y=alt.Y(
                    "Grupo:N",
                    sort=ordem_barras_demo,
                ),

                x="Total_Escolas:Q",

                text=alt.Text(
                    "Total_Escolas:Q",
                    format=",",
                ),
            )
        )


        grafico_n = (
            barras_n
            +
            textos_n
        ).properties(
            width=180,
            height=altura_demo,
            title="Número de escolas",
        )


        st.altair_chart(
            (
                alt.hconcat(
                    grafico_pct,
                    grafico_n,
                    spacing=18,
                )
                .resolve_scale(
                    y="shared"
                )
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


(
    col_indicador,
    col_ordenacao,
    col_same,
) = st.columns(
    [
        2,
        1,
        1,
    ]
)


with col_indicador:

    indicador = st.selectbox(
        "Indicador",
        options=[
            "IDEB",
            "N(LP)",
            "N(M)",
            "N",
            "Rendimento",
        ],
        index=0,
    )


with col_ordenacao:

    ordenacao = st.selectbox(
        "Ordenação",
        options=[
            "Número absoluto",
            "Delta",
        ],
        index=0,
    )


with col_same:

    same_schools = st.toggle(
        "SAME SCHOOLS",
        value=False,
        help=(
            "Mantém apenas escolas com resultado "
            "válido e matrícula maior que zero em "
            "todos os anos selecionados."
        ),
    )


(
    _,
    bloco_anos,
    __,
) = st.columns(
    [
        1.4,
        3,
        1.4,
    ]
)


with bloco_anos:

    cols_anos = st.columns(5)


    padrao_anos = {
        2017: False,
        2019: False,
        2021: False,
        2023: True,
        2025: True,
    }


    selecao_anos = {}


    for coluna, ano in zip(
        cols_anos,
        ANOS_PAINEL,
    ):

        with coluna:

            selecao_anos[
                ano
            ] = st.checkbox(
                str(ano),
                value=padrao_anos[
                    ano
                ],
                key=f"principal_ano_{ano}",
            )


anos = [
    ano
    for ano, ativo
    in selecao_anos.items()
    if ativo
]


if not anos:

    st.warning(
        "Selecione pelo menos um ano."
    )

    st.stop()


df_principal = (
    df.copy()
)


if same_schools:

    df_principal = (
        filtrar_same_schools(
            base=df_principal,
            indicador=indicador,
            anos=anos,
        )
    )


    n_same = (
        df_principal[
            df_principal[
                "Ano"
            ].isin(
                anos
            )
        ][
            "Cód. INEP"
        ]
        .nunique()
    )


    st.caption(
        (
            f"SAME SCHOOLS ativo: "
            f"{n_same:,} escolas presentes "
            f"em todos os anos selecionados."
        )
        .replace(
            ",",
            ".",
        )
    )


if "eixo_x" not in st.session_state:

    st.session_state.eixo_x = (
        "Tipo de Escola"
    )


eixo_x = (
    st.session_state.eixo_x
)


try:

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
            base=df_principal,
            indicador=indicador,
            anos=anos,
        )
    )


except Exception as erro:

    st.error(
        "Não foi possível preparar os dados."
    )

    st.exception(
        erro
    )

    st.stop()


if resultado.empty:

    st.warning(
        "Não há dados válidos para a "
        "configuração selecionada."
    )

    st.stop()


if indicador == "Rendimento":

    formato_rotulo = ".1%"
    formato_tooltip = ".2%"
    formato_eixo = ".0%"

else:

    formato_rotulo = ".2f"
    formato_tooltip = ".3f"
    formato_eixo = ".1f"


anos_ordenados = sorted(
    anos
)


ano_final = (
    anos_ordenados[-1]
)


ano_inicial = (
    anos_ordenados[-2]
    if len(
        anos_ordenados
    ) >= 2
    else None
)


base_variacao = pd.DataFrame()


if ano_inicial is not None:

    base_variacao = (
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
        in base_variacao.columns
        and
        str(
            ano_final
        )
        in base_variacao.columns
    ):

        base_variacao[
            "Variação"
        ] = (
            base_variacao[
                str(
                    ano_final
                )
            ]
            -
            base_variacao[
                str(
                    ano_inicial
                )
            ]
        )


delta_consolidado = pd.DataFrame()


if (
    ano_inicial is not None
    and
    not consolidado.empty
):

    consol_delta = (
        consolidado[
            consolidado[
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
        in consol_delta.columns
        and
        str(
            ano_final
        )
        in consol_delta.columns
    ):

        consol_delta[
            "Variação"
        ] = (
            consol_delta[
                str(
                    ano_final
                )
            ]
            -
            consol_delta[
                str(
                    ano_inicial
                )
            ]
        )


        delta_consolidado = (
            consol_delta[
                [
                    "Categoria",
                    "Variação",
                ]
            ]
        )


categorias_presentes = (
    resultado[
        "Categoria"
    ]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


ordem_categorias = (
    categorias_presentes.copy()
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


elif (
    ordenacao == "Delta"
    and
    "Variação"
    in base_variacao.columns
):

    ordem_categorias = (
        base_variacao
        .dropna(
            subset=[
                "Variação"
            ]
        )
        .sort_values(
            "Variação",
            ascending=False,
        )[
            "Categoria"
        ]
        .astype(str)
        .tolist()
    )


for categoria in categorias_presentes:

    if categoria not in ordem_categorias:

        ordem_categorias.append(
            categoria
        )


CATEGORIA_ESPACO = "   "


ordem_grafico = (
    ordem_categorias
    +
    [
        CATEGORIA_ESPACO,
        "Consolidado",
    ]
)


resultado_plot = pd.concat(
    [
        resultado,
        consolidado,
    ],
    ignore_index=True,
)


for ano in anos:

    resultado_plot = pd.concat(
        [
            resultado_plot,

            pd.DataFrame(
                [
                    {
                        "Ano":
                            str(ano),

                        "Categoria":
                            CATEGORIA_ESPACO,

                        "Média":
                            np.nan,

                        "N escolas":
                            np.nan,

                        "Matrículas":
                            np.nan,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )


st.markdown(
    f"""
    <div style="
        text-align:center;
        font-size:23px;
        font-weight:700;
        margin-top:8px;
        margin-bottom:2px;
    ">
        Média ponderada de {indicador}
    </div>
    """,
    unsafe_allow_html=True,
)


barras = (
    alt.Chart(
        resultado_plot
    )
    .mark_bar()
    .encode(

        x=alt.X(
            "Categoria:N",
            title=None,
            sort=ordem_grafico,
            scale=alt.Scale(
                paddingInner=0.22,
            ),
            axis=alt.Axis(
                labelAngle=0,
                labelLimit=180,
            ),
        ),

        xOffset=alt.XOffset(
            "Ano:N",
            sort=ORDEM_ANOS_STR,
        ),

        y=alt.Y(
            "Média:Q",
            title=indicador,
            scale=alt.Scale(
                zero=True
            ),
            axis=alt.Axis(
                format=formato_eixo
            ),
        ),

        color=alt.Color(
            "Ano:N",
            title="Ano",
            scale=alt.Scale(
                domain=ORDEM_ANOS_STR,
                range=ESCALA_CORES_ANOS,
            ),
            sort=ORDEM_ANOS_STR,
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
                title="Ano",
            ),

            alt.Tooltip(
                "Média:Q",
                title="Média ponderada",
                format=formato_tooltip,
            ),

            alt.Tooltip(
                "N escolas:Q",
                title="Escolas",
                format=",",
            ),

            alt.Tooltip(
                "Matrículas:Q",
                title="Matrículas",
                format=",",
            ),
        ],
    )
)


rotulos = (
    alt.Chart(
        resultado_plot
    )
    .mark_text(
        dy=-7,
        fontSize=11,
    )
    .encode(

        x=alt.X(
            "Categoria:N",
            sort=ordem_grafico,
        ),

        xOffset=alt.XOffset(
            "Ano:N",
            sort=ORDEM_ANOS_STR,
        ),

        y="Média:Q",

        text=alt.Text(
            "Média:Q",
            format=formato_rotulo,
        ),
    )
)


st.altair_chart(
    (
        barras
        +
        rotulos
    )
    .properties(
        height=300
    ),
    width="stretch",
)


st.markdown(
    """
    <div style="
        text-align:center;
        font-size:0.80rem;
        font-weight:600;
        margin-top:0;
        margin-bottom:-3px;
    ">
        Variável do eixo X
    </div>
    """,
    unsafe_allow_html=True,
)


st.radio(
    "Variável do eixo X",
    options=list(
        EIXOS_DISPONIVEIS.keys()
    ),
    horizontal=True,
    label_visibility="collapsed",
    format_func=rotulo_dimensao,
    key="eixo_x",
)


if (
    ano_inicial is not None
    and
    not base_variacao.empty
    and
    "Variação"
    in base_variacao.columns
):

    base_delta_plot = pd.concat(
        [
            base_variacao[
                [
                    "Categoria",
                    "Variação",
                ]
            ],

            delta_consolidado,

            pd.DataFrame(
                [
                    {
                        "Categoria":
                            CATEGORIA_ESPACO,

                        "Variação":
                            np.nan,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )


    formato_delta = (
        "+.1%"
        if indicador
        == "Rendimento"
        else "+.2f"
    )


    st.markdown(
        f"""
        <div style="
            text-align:center;
            font-size:23px;
            font-weight:700;
            margin-top:8px;
            margin-bottom:2px;
        ">
            Variação de {indicador}:
            {ano_final} − {ano_inicial}
        </div>
        """,
        unsafe_allow_html=True,
    )


    barras_delta = (
        alt.Chart(
            base_delta_plot
        )
        .mark_bar(
            color="#9B8878"
        )
        .encode(

            x=alt.X(
                "Categoria:N",
                title=None,
                sort=ordem_grafico,
                axis=alt.Axis(
                    labelAngle=0,
                    labelLimit=180,
                ),
            ),

            y=alt.Y(
                "Variação:Q",
                title=(
                    f"Δ {ano_final} "
                    f"− {ano_inicial}"
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
                    format=formato_delta,
                ),
            ],
        )
    )


    textos_delta = (
        alt.Chart(
            base_delta_plot
        )
        .mark_text(
            dy=alt.expr(
                "datum['Variação'] >= 0 "
                "? -7 : 13"
            ),
        )
        .encode(

            x=alt.X(
                "Categoria:N",
                sort=ordem_grafico,
            ),

            y="Variação:Q",

            text=alt.Text(
                "Variação:Q",
                format=formato_delta,
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
            color="#555555"
        )
        .encode(
            y="zero:Q"
        )
    )


    st.altair_chart(
        (
            barras_delta
            +
            textos_delta
            +
            linha_zero
        )
        .properties(
            height=220
        ),
        width="stretch",
    )


else:

    st.info(
        "Selecione pelo menos dois anos "
        "para visualizar a variação."
    )


st.markdown(
    """
    <div style="
        text-align:center;
        font-size:20px;
        font-weight:700;
        margin-top:18px;
        margin-bottom:10px;
    ">
        Base considerada em cada categoria
    </div>
    """,
    unsafe_allow_html=True,
)


categorias_tabela = (
    ordem_categorias
    +
    [
        "Consolidado"
    ]
)


html = """
<style>

.base-scroll {
    width: 100%;
    overflow-x: auto;
}

.base-table {
    width: 100%;
    min-width: 800px;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 11px;
}

.base-table th,
.base-table td {
    text-align: center;
    padding: 6px 4px;
    border-bottom: 1px solid #eceff2;
}

.base-table th {
    font-weight: 600;
    border-bottom: 1px solid #cfd4da;
}

.base-table .categoria {
    font-weight: 700;
}

.base-table .ano {
    width: 65px;
    font-weight: 600;
}

.base-table .consolidado {
    border-left: 2px solid #b8bec5;
}

</style>

<div class="base-scroll">

<table class="base-table">

<thead>

<tr>

<th rowspan="2" class="ano">
Ano
</th>
"""


for categoria in categorias_tabela:

    classe = (
        "categoria consolidado"
        if categoria
        == "Consolidado"
        else
        "categoria"
    )

    html += (
        f'<th colspan="2" '
        f'class="{classe}">'
        f'{categoria}'
        '</th>'
    )


html += """
</tr>
<tr>
"""


for categoria in categorias_tabela:

    classe = (
        ' class="consolidado"'
        if categoria
        == "Consolidado"
        else ""
    )

    html += (
        f"<th{classe}>Escolas</th>"
        "<th>Matrículas</th>"
    )


html += """
</tr>
</thead>
<tbody>
"""


for ano in anos:

    html += (
        "<tr>"
        f"<td class='ano'>{ano}</td>"
    )


    for categoria in ordem_categorias:

        recorte = (
            resultado[
                (
                    resultado[
                        "Categoria"
                    ].astype(str)
                    == categoria
                )
                &
                (
                    resultado[
                        "Ano"
                    ]
                    == str(
                        ano
                    )
                )
            ]
        )


        if recorte.empty:

            escolas = "—"
            matriculas = "—"

        else:

            escolas = (
                f"{int(recorte['N escolas'].iloc[0]):,}"
                .replace(
                    ",",
                    ".",
                )
            )


            matriculas = (
                f"{int(recorte['Matrículas'].iloc[0]):,}"
                .replace(
                    ",",
                    ".",
                )
            )


        html += (
            f"<td>{escolas}</td>"
            f"<td>{matriculas}</td>"
        )


    recorte_consol = (
        consolidado[
            consolidado[
                "Ano"
            ]
            == str(
                ano
            )
        ]
    )


    if recorte_consol.empty:

        escolas_total = "—"
        matriculas_total = "—"

    else:

        escolas_total = (
            f"{int(recorte_consol['N escolas'].iloc[0]):,}"
            .replace(
                ",",
                ".",
            )
        )


        matriculas_total = (
            f"{int(recorte_consol['Matrículas'].iloc[0]):,}"
            .replace(
                ",",
                ".",
            )
        )


    html += (
        '<td class="consolidado">'
        f'{escolas_total}'
        '</td>'
        f'<td>{matriculas_total}</td>'
    )


    html += "</tr>"


html += """
</tbody>
</table>
</div>
"""


st.html(
    html
)