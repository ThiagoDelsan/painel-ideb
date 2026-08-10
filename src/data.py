import re
import unicodedata

import gspread
import numpy as np
import pandas as pd
import streamlit as st

from google.oauth2.service_account import Credentials


# ============================================================
# CONFIGURAÇÕES GERAIS
# ============================================================

SPREADSHEET_ID = (
    "1z0dAZsBT2icySkTl5WEYYr76dWqBYTWtnj2jhaMosdY"
)

ABA_IDEB = "IDEB_Escolas (ENSINO MÉDIO)"
ABA_INFO = "Info_Escolas_Consolidado"


ANOS_DISPONIVEIS = [
    2017,
    2019,
    2021,
    2023,
    2025,
]


INDICADORES_DISPONIVEIS = [
    "IDEB",
    "N(LP)",
    "N(M)",
    "N",
    "Rendimento",
]


# ============================================================
# FAIXAS DO IDEB
# ============================================================

FAIXAS_IDEB = [
    "Menor que 3",
    "Entre 3 e 4",
    "Entre 4 e 5",
    "Entre 5 e 6",
    "Maior que 6",
    "Sem resultado",
]


# ============================================================
# VARIÁVEIS DISPONÍVEIS
# ============================================================

EIXOS_DISPONIVEIS = {

    "Tipo de Escola": {
        "tipo": "status",
        "coluna": "Status (do ano)",
    },

    "PPI": {
        "tipo": "coluna",
        "coluna": "Faixa PPI",
    },

    "INSE": {
        "tipo": "coluna",
        "coluna": "INSE (norm)",
    },

    "Colégio Militar": {
        "tipo": "binaria",
        "coluna": "Militar",
    },

    "Colégio com Seleção": {
        "tipo": "binaria",
        "coluna": "Seleção",
    },

    "Estado": {
        "tipo": "coluna",
        "coluna": "UF",
    },

    "Região do Brasil": {
        "tipo": "coluna",
        "coluna": "Região",
    },

    "1ª IDEB 100% integral": {
        "tipo": "coluna",
        "coluna": "1ª edição 100% integral",
    },

    "Carga horária": {
        "tipo": "carga_horaria",
    },

    "Tipo de integral": {
        "tipo": "coluna",
        "coluna": "Tipo de integral",
    },

    "Faixa IDEB 2017": {
        "tipo": "coluna",
        "coluna": "Faixa IDEB 2017",
    },

    "Faixa IDEB 2019": {
        "tipo": "coluna",
        "coluna": "Faixa IDEB 2019",
    },

    "Faixa IDEB 2021": {
        "tipo": "coluna",
        "coluna": "Faixa IDEB 2021",
    },

    "Faixa IDEB 2023": {
        "tipo": "coluna",
        "coluna": "Faixa IDEB 2023",
    },

    "Faixa IDEB 2025": {
        "tipo": "coluna",
        "coluna": "Faixa IDEB 2025",
    },
}


# ============================================================
# CONEXÃO COM GOOGLE SHEETS
# ============================================================

def conectar_google_sheets():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    credenciais = (
        Credentials.from_service_account_info(
            dict(
                st.secrets[
                    "gcp_service_account"
                ]
            ),
            scopes=scopes,
        )
    )

    cliente = gspread.authorize(
        credenciais
    )

    return cliente.open_by_key(
        SPREADSHEET_ID
    )


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def converter_numero(serie):

    serie = (
        serie.astype(str)
        .str.strip()
        .replace(
            {
                "": np.nan,
                "-": np.nan,
                "nan": np.nan,
                "None": np.nan,
            }
        )
    )

    serie = serie.str.replace(
        ",",
        ".",
        regex=False,
    )

    return pd.to_numeric(
        serie,
        errors="coerce",
    )


def padronizar_codigo_escola(serie):

    serie = (
        serie.astype(str)
        .str.strip()
        .str.replace(
            r"\.0$",
            "",
            regex=True,
        )
    )

    return serie.replace(
        {
            "": np.nan,
            "nan": np.nan,
            "None": np.nan,
        }
    )


def remover_linhas_vazias(df):

    if df.empty:
        return df

    mascara = df.apply(
        lambda linha: any(
            str(valor).strip()
            not in [
                "",
                "nan",
                "None",
            ]
            for valor in linha
        ),
        axis=1,
    )

    return (
        df.loc[mascara]
        .reset_index(drop=True)
    )


def normalizar_texto(valor):

    if pd.isna(valor):
        return ""

    texto = (
        str(valor)
        .strip()
        .lower()
    )

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(
            caractere
        )
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto


def valor_categorico(valor):

    if pd.isna(valor):
        return "Não informado"

    texto = str(
        valor
    ).strip()

    if texto.lower() in [
        "",
        "nan",
        "none",
    ]:
        return "Não informado"

    return texto


# ============================================================
# TIPO DE ESCOLA
# ============================================================

def classificar_status(valor):

    texto = normalizar_texto(
        valor
    )

    if not texto:

        return (
            "Outros / não informado"
        )

    if (
        "integral" in texto
        and
        "100" in texto
    ):

        return "100% Integral"

    if texto in [
        "integral",
        "integral total",
    ]:

        return "100% Integral"

    if texto in [
        "mista",
        "misto",
    ]:

        return "Mista"

    if texto in [
        "parcial/regular",
        "parcial / regular",
        "parcial",
        "regular",
    ]:

        return "Parcial/Regular"

    return (
        "Outros / não informado"
    )


# ============================================================
# VARIÁVEIS BINÁRIAS
# ============================================================

def classificar_binaria(valor):

    texto = normalizar_texto(
        valor
    )

    if texto in [
        "1",
        "1.0",
        "sim",
        "s",
        "true",
        "verdadeiro",
        "x",
    ]:

        return "Sim"

    if texto in [
        "0",
        "0.0",
        "nao",
        "não",
        "n",
        "false",
        "falso",
    ]:

        return "Não"

    if not texto:

        return "Não informado"

    return str(
        valor
    ).strip()


# ============================================================
# CARGA HORÁRIA
# ============================================================

def flag_ativa(valor):

    texto = normalizar_texto(
        valor
    )

    return texto in [
        "1",
        "1.0",
        "sim",
        "s",
        "true",
        "verdadeiro",
        "x",
    ]


def classificar_carga_horaria(
    valor_7h,
    valor_9h,
):

    tem_7h = flag_ativa(
        valor_7h
    )

    tem_9h = flag_ativa(
        valor_9h
    )

    if tem_7h and tem_9h:

        return "7h + 9h"

    if tem_7h:

        return "7h"

    if tem_9h:

        return "9h"

    return "Não se aplica"


# ============================================================
# FAIXA DO IDEB
# ============================================================

def classificar_faixa_ideb(valor):

    if pd.isna(valor):

        return "Sem resultado"

    try:

        valor = float(
            valor
        )

    except (
        TypeError,
        ValueError,
    ):

        return "Sem resultado"


    if valor < 3:

        return "Menor que 3"

    if valor < 4:

        return "Entre 3 e 4"

    if valor < 5:

        return "Entre 4 e 5"

    if valor <= 6:

        return "Entre 5 e 6"

    return "Maior que 6"


# ============================================================
# LEITURA DA ABA IDEB
# ============================================================

@st.cache_data(
    ttl=300
)
def carregar_ideb():

    planilha = (
        conectar_google_sheets()
    )

    aba = planilha.worksheet(
        ABA_IDEB
    )

    dados = (
        aba.get_all_values()
    )


    if not dados:

        return pd.DataFrame()


    cabecalho = [
        str(coluna).strip()
        for coluna
        in dados[9]
    ]


    indices_validos = [
        i
        for i, coluna
        in enumerate(
            cabecalho
        )
        if coluna
    ]


    if not indices_validos:

        raise ValueError(
            "Não foi possível identificar "
            "as colunas da aba IDEB."
        )


    ultima_coluna = max(
        indices_validos
    )


    cabecalho = cabecalho[
        :ultima_coluna + 1
    ]


    linhas = [
        linha[
            :ultima_coluna + 1
        ]
        for linha
        in dados[10:]
    ]


    df = pd.DataFrame(
        linhas,
        columns=cabecalho,
    )


    df = remover_linhas_vazias(
        df
    )


    if (
        "ID_ESCOLA"
        not in df.columns
    ):

        raise ValueError(
            "A coluna ID_ESCOLA não foi "
            "encontrada na aba IDEB."
        )


    df[
        "ID_ESCOLA"
    ] = (
        padronizar_codigo_escola(
            df[
                "ID_ESCOLA"
            ]
        )
    )


    return df


# ============================================================
# LEITURA DA ABA INFO ESCOLAS
# ============================================================

@st.cache_data(
    ttl=300
)
def carregar_info_escolas():

    planilha = (
        conectar_google_sheets()
    )

    aba = planilha.worksheet(
        ABA_INFO
    )

    dados = (
        aba.get_all_values()
    )


    if not dados:

        return pd.DataFrame()


    cabecalho = [
        str(coluna).strip()
        for coluna
        in dados[0]
    ]


    indices_validos = [
        i
        for i, coluna
        in enumerate(
            cabecalho
        )
        if coluna
    ]


    if not indices_validos:

        raise ValueError(
            "Não foi possível identificar "
            "as colunas da aba "
            "Info_Escolas_Consolidado."
        )


    ultima_coluna = max(
        indices_validos
    )


    cabecalho = cabecalho[
        :ultima_coluna + 1
    ]


    linhas = [
        linha[
            :ultima_coluna + 1
        ]
        for linha
        in dados[1:]
    ]


    df = pd.DataFrame(
        linhas,
        columns=cabecalho,
    )


    df = remover_linhas_vazias(
        df
    )


    # ========================================================
    # COLUNAS OBRIGATÓRIAS
    # ========================================================

    colunas_basicas = [
        "Cód. INEP",
        "Ano",
        "Matrículas EM (total) 3/4",
        "Tem IDEB",
        "Localização",
    ]


    faltantes = [
        coluna
        for coluna
        in colunas_basicas
        if coluna
        not in df.columns
    ]


    if faltantes:

        raise ValueError(
            "Colunas obrigatórias ausentes "
            "em Info_Escolas_Consolidado: "
            f"{faltantes}"
        )


    # ========================================================
    # CÓDIGO INEP
    # ========================================================

    df[
        "Cód. INEP"
    ] = (
        padronizar_codigo_escola(
            df[
                "Cód. INEP"
            ]
        )
    )


    # ========================================================
    # ANO
    # ========================================================

    df[
        "Ano"
    ] = (
        converter_numero(
            df[
                "Ano"
            ]
        )
    )


    # ========================================================
    # MATRÍCULAS
    # ========================================================

    df[
        "Matrículas EM (total) 3/4"
    ] = (
        converter_numero(
            df[
                "Matrículas EM (total) 3/4"
            ]
        )
    )


    # ========================================================
    # TEM IDEB
    # ========================================================

    df[
        "Tem IDEB"
    ] = (
        converter_numero(
            df[
                "Tem IDEB"
            ]
        )
    )


    # ========================================================
    # LOCALIZAÇÃO
    # ========================================================

    df[
        "Localização"
    ] = (
        converter_numero(
            df[
                "Localização"
            ]
        )
    )


    return df


# ============================================================
# NOMES DAS COLUNAS IDEB POR ANO
# ============================================================

def colunas_indicadores_ano(
    ano,
):

    return {

        "matematica":
            f"VL_NOTA_MATEMATICA_{ano}",

        "portugues":
            f"VL_NOTA_PORTUGUES_{ano}",

        "n":
            f"VL_NOTA_MEDIA_{ano}",

        "rendimento":
            f"VL_INDICADOR_REND_{ano}",

        "ideb":
            f"VL_OBSERVADO_{ano}",
    }


# ============================================================
# INDICADORES DE UM ANO
# ============================================================

def preparar_indicadores_ano(
    df_ideb,
    ano,
):

    colunas = (
        colunas_indicadores_ano(
            ano
        )
    )


    necessarias = [
        "ID_ESCOLA",
        colunas["matematica"],
        colunas["portugues"],
        colunas["n"],
        colunas["rendimento"],
        colunas["ideb"],
    ]


    faltantes = [
        coluna
        for coluna
        in necessarias
        if coluna
        not in df_ideb.columns
    ]


    if faltantes:

        raise ValueError(
            f"Colunas ausentes para "
            f"{ano}: {faltantes}"
        )


    df = (
        df_ideb[
            necessarias
        ]
        .copy()
    )


    df[
        "ID_ESCOLA"
    ] = (
        padronizar_codigo_escola(
            df[
                "ID_ESCOLA"
            ]
        )
    )


    df = (
        df[
            df[
                "ID_ESCOLA"
            ].notna()
        ]
        .copy()
    )


    df = (
        df
        .drop_duplicates()
        .reset_index(
            drop=True
        )
    )


    duplicados = (
        df[
            df[
                "ID_ESCOLA"
            ].duplicated(
                keep=False
            )
        ]
    )


    if not duplicados.empty:

        ids = (
            duplicados[
                "ID_ESCOLA"
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Códigos duplicados na base "
            f"IDEB em {ano}: "
            f"{ids[:10]}"
        )


    # ========================================================
    # CONVERSÃO NUMÉRICA
    # ========================================================

    for coluna in [
        colunas["matematica"],
        colunas["portugues"],
        colunas["n"],
        colunas["rendimento"],
        colunas["ideb"],
    ]:

        df[
            coluna
        ] = (
            converter_numero(
                df[
                    coluna
                ]
            )
        )


    # ========================================================
    # N(LP)
    # ========================================================

    df[
        "N(LP)"
    ] = (
        10
        * (
            df[
                colunas[
                    "portugues"
                ]
            ]
            - 117
        )
        / 334
    )


    # ========================================================
    # N(M)
    # ========================================================

    df[
        "N(M)"
    ] = (
        10
        * (
            df[
                colunas[
                    "matematica"
                ]
            ]
            - 111
        )
        / 356
    )


    # ========================================================
    # N
    # ========================================================

    df[
        "N"
    ] = (
        df[
            colunas[
                "n"
            ]
        ]
    )


    # ========================================================
    # RENDIMENTO
    # ========================================================

    df[
        "Rendimento"
    ] = (
        df[
            colunas[
                "rendimento"
            ]
        ]
    )


    # ========================================================
    # IDEB
    # ========================================================

    df[
        "IDEB"
    ] = (
        df[
            colunas[
                "ideb"
            ]
        ]
    )


    df[
        "Ano"
    ] = ano


    return df[
        [
            "ID_ESCOLA",
            "Ano",
            "IDEB",
            "N(LP)",
            "N(M)",
            "N",
            "Rendimento",
        ]
    ]


# ============================================================
# BASE ANALÍTICA MULTIANO
# ============================================================

@st.cache_data(
    ttl=300
)
def preparar_base():

    df_ideb = (
        carregar_ideb()
    )

    df_info = (
        carregar_info_escolas()
    )


    # ========================================================
    # REGRA GERAL DO PAINEL
    #
    # O UNIVERSO É:
    #
    # Tem IDEB = 1
    # E
    # Localização = 1
    #
    # Essa regra é aplicada ANTES de qualquer outra operação.
    # ========================================================

    df_info = (
        df_info[
            (
                df_info[
                    "Tem IDEB"
                ]
                == 1
            )
            &
            (
                df_info[
                    "Localização"
                ]
                == 1
            )
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )


    # ========================================================
    # SEGURANÇA
    # ========================================================

    if df_info.empty:

        raise ValueError(
            "Após aplicar as regras gerais "
            "'Tem IDEB = 1' e "
            "'Localização = 1', "
            "não restaram registros na base."
        )


    bases = []


    # ========================================================
    # MONTA UMA LINHA ESCOLA × ANO
    # ========================================================

    for ano in ANOS_DISPONIVEIS:

        info_ano = (
            df_info[
                df_info[
                    "Ano"
                ]
                == ano
            ]
            .copy()
        )


        info_ano = (
            info_ano[
                info_ano[
                    "Cód. INEP"
                ].notna()
            ]
            .copy()
        )


        indicadores_ano = (
            preparar_indicadores_ano(
                df_ideb,
                ano,
            )
        )


        base_ano = (
            info_ano.merge(

                indicadores_ano,

                left_on=[
                    "Cód. INEP",
                    "Ano",
                ],

                right_on=[
                    "ID_ESCOLA",
                    "Ano",
                ],

                how="left",

                validate="many_to_one",
            )
        )


        bases.append(
            base_ano
        )


    base_final = (
        pd.concat(
            bases,
            ignore_index=True,
        )
    )


    # ========================================================
    # IDEB DE CADA EDIÇÃO COMO ATRIBUTO DA ESCOLA
    # ========================================================

    ideb_por_escola = (
        base_final[
            [
                "Cód. INEP",
                "Ano",
                "IDEB",
            ]
        ]
        .dropna(
            subset=[
                "Cód. INEP"
            ]
        )
        .drop_duplicates(
            subset=[
                "Cód. INEP",
                "Ano",
            ],
            keep="first",
        )
        .pivot(
            index="Cód. INEP",
            columns="Ano",
            values="IDEB",
        )
        .reset_index()
    )


    ideb_por_escola.columns.name = None


    # ========================================================
    # PADRONIZA NOMES DAS COLUNAS
    # ========================================================

    mapa_renomear = {}


    for coluna in ideb_por_escola.columns:

        if coluna == "Cód. INEP":
            continue

        try:

            ano_coluna = int(
                float(
                    coluna
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


        mapa_renomear[
            coluna
        ] = (
            f"IDEB_REF_{ano_coluna}"
        )


    ideb_por_escola = (
        ideb_por_escola.rename(
            columns=mapa_renomear
        )
    )


    # ========================================================
    # JUNTA OS IDEBs HISTÓRICOS
    # ========================================================

    base_final = (
        base_final.merge(
            ideb_por_escola,
            on="Cód. INEP",
            how="left",
            validate="many_to_one",
        )
    )


    # ========================================================
    # CRIA AS FAIXAS IDEB
    # ========================================================

    for ano in ANOS_DISPONIVEIS:

        coluna_origem = (
            f"IDEB_REF_{ano}"
        )

        coluna_destino = (
            f"Faixa IDEB {ano}"
        )


        if (
            coluna_origem
            in base_final.columns
        ):

            base_final[
                coluna_destino
            ] = (
                base_final[
                    coluna_origem
                ]
                .apply(
                    classificar_faixa_ideb
                )
            )


        else:

            base_final[
                coluna_destino
            ] = (
                "Sem resultado"
            )


    return base_final


# ============================================================
# CRIA VARIÁVEL CATEGÓRICA
# ============================================================

def criar_variavel_eixo(
    df,
    eixo_painel,
):

    if (
        eixo_painel
        not in EIXOS_DISPONIVEIS
    ):

        raise ValueError(
            f"Eixo inválido: "
            f"{eixo_painel}"
        )


    configuracao = (
        EIXOS_DISPONIVEIS[
            eixo_painel
        ]
    )


    tipo = (
        configuracao[
            "tipo"
        ]
    )


    base = (
        df.copy()
    )


    # ========================================================
    # TIPO DE ESCOLA
    # ========================================================

    if tipo == "status":

        coluna = (
            configuracao[
                "coluna"
            ]
        )


        if coluna not in base.columns:

            raise ValueError(
                f"A coluna '{coluna}' "
                "não foi encontrada."
            )


        base[
            "Categoria"
        ] = (
            base[
                coluna
            ]
            .apply(
                classificar_status
            )
        )


    # ========================================================
    # BINÁRIA
    # ========================================================

    elif tipo == "binaria":

        coluna = (
            configuracao[
                "coluna"
            ]
        )


        if coluna not in base.columns:

            raise ValueError(
                f"A coluna '{coluna}' "
                "não foi encontrada."
            )


        base[
            "Categoria"
        ] = (
            base[
                coluna
            ]
            .apply(
                classificar_binaria
            )
        )


    # ========================================================
    # CARGA HORÁRIA
    # ========================================================

    elif tipo == "carga_horaria":

        col_7h = (
            "Escola EMI 7h"
        )

        col_9h = (
            "Escola EMI 9h"
        )


        faltantes = [
            coluna
            for coluna
            in [
                col_7h,
                col_9h,
            ]
            if coluna
            not in base.columns
        ]


        if faltantes:

            raise ValueError(
                "Colunas necessárias para "
                "Carga horária não encontradas: "
                f"{faltantes}"
            )


        base[
            "Categoria"
        ] = (
            base.apply(
                lambda linha:
                    classificar_carga_horaria(
                        linha[
                            col_7h
                        ],
                        linha[
                            col_9h
                        ],
                    ),
                axis=1,
            )
        )


    # ========================================================
    # DEMAIS CATEGÓRICAS
    # ========================================================

    else:

        coluna = (
            configuracao[
                "coluna"
            ]
        )


        if coluna not in base.columns:

            raise ValueError(
                f"A coluna '{coluna}' "
                "não foi encontrada."
            )


        base[
            "Categoria"
        ] = (
            base[
                coluna
            ]
            .apply(
                valor_categorico
            )
        )


    return base


# ============================================================
# OPÇÕES DISPONÍVEIS NOS FILTROS
# ============================================================

def obter_opcoes_filtro(
    df,
    nome_filtro,
):

    try:

        base = (
            criar_variavel_eixo(
                df,
                nome_filtro,
            )
        )

    except ValueError:

        return []


    opcoes = (
        base[
            "Categoria"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


    # ========================================================
    # TIPO DE ESCOLA
    # ========================================================

    if (
        nome_filtro
        == "Tipo de Escola"
    ):

        if (
            "Mista" in opcoes
            or
            "100% Integral" in opcoes
        ):

            opcoes.append(
                "Integral "
                "(Mista + 100%)"
            )


        ordem = [
            "Parcial/Regular",
            "Mista",
            "100% Integral",
            "Integral "
            "(Mista + 100%)",
            "Outros / não informado",
        ]


        return [
            valor
            for valor
            in ordem
            if valor
            in opcoes
        ]


    # ========================================================
    # FAIXAS DO IDEB
    # ========================================================

    if (
        nome_filtro.startswith(
            "Faixa IDEB"
        )
    ):

        return [
            valor
            for valor
            in FAIXAS_IDEB
            if valor
            in opcoes
        ]


    return sorted(
        opcoes,
        key=lambda x: str(x),
    )


# ============================================================
# FILTRO SIM / NÃO
# ============================================================

def aplicar_filtro_binario_coluna(
    base,
    coluna,
    valores_filtro,
):

    if not valores_filtro:

        return base


    if set(
        valores_filtro
    ) == {
        "Sim",
        "Não",
    }:

        return base


    if coluna not in base.columns:

        return base


    classificacao = (
        base[
            coluna
        ]
        .apply(
            classificar_binaria
        )
    )


    return (
        base.loc[
            classificacao.isin(
                valores_filtro
            )
        ]
        .reset_index(
            drop=True
        )
    )


# ============================================================
# FILTRO PARTICIPAÇÃO NO IDEB
# ============================================================

def aplicar_filtro_participacao_ideb(
    base,
    ano,
    valores_filtro,
):

    if not valores_filtro:

        return base


    if set(
        valores_filtro
    ) == {
        "Sim",
        "Não",
    }:

        return base


    coluna_ref = (
        f"IDEB_REF_{ano}"
    )


    if (
        coluna_ref
        in base.columns
    ):

        tem_ideb = (
            base[
                coluna_ref
            ]
            .notna()
        )


        if "Sim" in valores_filtro:

            return (
                base.loc[
                    tem_ideb
                ]
                .reset_index(
                    drop=True
                )
            )


        if "Não" in valores_filtro:

            return (
                base.loc[
                    ~tem_ideb
                ]
                .reset_index(
                    drop=True
                )
            )


    escolas_com_ideb = (
        base.loc[
            (
                base[
                    "Ano"
                ]
                == ano
            )
            &
            (
                base[
                    "IDEB"
                ]
                .notna()
            ),
            "Cód. INEP",
        ]
        .dropna()
        .unique()
    )


    if "Sim" in valores_filtro:

        return (
            base[
                base[
                    "Cód. INEP"
                ]
                .isin(
                    escolas_com_ideb
                )
            ]
            .reset_index(
                drop=True
            )
        )


    if "Não" in valores_filtro:

        return (
            base[
                ~base[
                    "Cód. INEP"
                ]
                .isin(
                    escolas_com_ideb
                )
            ]
            .reset_index(
                drop=True
            )
        )


    return base


# ============================================================
# FILTROS CATEGÓRICOS
# ============================================================

def aplicar_filtros_categoricos(
    df,
    filtros,
):

    base = (
        df.copy()
    )


    for (
        nome_filtro,
        valores,
    ) in filtros.items():


        if not valores:

            continue


        temp = (
            criar_variavel_eixo(
                base,
                nome_filtro,
            )
        )


        # ====================================================
        # TIPO DE ESCOLA
        # ====================================================

        if (
            nome_filtro
            == "Tipo de Escola"
        ):

            valores_base = []


            for valor in valores:

                if (
                    valor
                    == "Integral "
                    "(Mista + 100%)"
                ):

                    valores_base.extend(
                        [
                            "Mista",
                            "100% Integral",
                        ]
                    )

                else:

                    valores_base.append(
                        valor
                    )


            valores_base = list(
                set(
                    valores_base
                )
            )


            mascara = (
                temp[
                    "Categoria"
                ]
                .isin(
                    valores_base
                )
            )


        else:

            mascara = (
                temp[
                    "Categoria"
                ]
                .isin(
                    valores
                )
            )


        base = (
            temp.loc[
                mascara
            ]
            .drop(
                columns=[
                    "Categoria"
                ]
            )
            .reset_index(
                drop=True
            )
        )


    return base


# ============================================================
# MÉDIA PONDERADA POR CATEGORIA
# ============================================================

def media_ponderada_por_categoria(
    df,
    indicador,
    anos,
    eixo_painel,
):

    if (
        indicador
        not in INDICADORES_DISPONIVEIS
    ):

        raise ValueError(
            f"Indicador inválido: "
            f"{indicador}"
        )


    base = (
        criar_variavel_eixo(
            df,
            eixo_painel,
        )
    )


    peso = (
        "Matrículas EM (total) 3/4"
    )


    # ========================================================
    # CATEGORIA AGREGADA
    # ========================================================

    if (
        eixo_painel
        == "Tipo de Escola"
    ):

        integral = (
            base[
                base[
                    "Categoria"
                ]
                .isin(
                    [
                        "Mista",
                        "100% Integral",
                    ]
                )
            ]
            .copy()
        )


        integral[
            "Categoria"
        ] = (
            "Integral "
            "(Mista + 100%)"
        )


        base = (
            pd.concat(
                [
                    base,
                    integral,
                ],
                ignore_index=True,
            )
        )


    # ========================================================
    # ANOS SELECIONADOS
    # ========================================================

    base = (
        base[
            base[
                "Ano"
            ]
            .isin(
                anos
            )
        ]
        .copy()
    )


    # ========================================================
    # INDICADOR AUSENTE
    # ========================================================

    base = (
        base[
            base[
                indicador
            ]
            .notna()
        ]
        .copy()
    )


    # ========================================================
    # PESO INVÁLIDO
    # ========================================================

    base = (
        base[
            base[
                peso
            ]
            .notna()
            &
            (
                base[
                    peso
                ]
                > 0
            )
        ]
        .copy()
    )


    if base.empty:

        return pd.DataFrame(
            columns=[
                "Ano",
                "Categoria",
                "Média",
                "N escolas",
                "Matrículas",
            ]
        )


    # ========================================================
    # PRODUTO DA MÉDIA PONDERADA
    # ========================================================

    base[
        "produto"
    ] = (
        base[
            indicador
        ]
        *
        base[
            peso
        ]
    )


    # ========================================================
    # AGREGAÇÃO
    # ========================================================

    resultado = (
        base
        .groupby(
            [
                "Ano",
                "Categoria",
            ],
            as_index=False,
        )
        .agg(

            soma_ponderada=(
                "produto",
                "sum",
            ),

            Matrículas=(
                peso,
                "sum",
            ),

            **{
                "N escolas": (
                    indicador,
                    "count",
                )
            },
        )
    )


    # ========================================================
    # MÉDIA PONDERADA
    # ========================================================

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
            "Categoria",
            "Média",
            "N escolas",
            "Matrículas",
        ]
    ]