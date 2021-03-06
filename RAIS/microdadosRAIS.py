#!/usr/bin/python

"""
Pipeline para coleta e organização de microdados da RAIS
ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/

PROJETO: Avaliação de Impactos da Infraestrura Aeroportuária | ITA & SAC

Os arquivos de microdados podem ser grandes, acima de 10 GB depois de descompactados.
Assim, este pipeline está organizado da seguinte forma:
. baixar localmente o arquivo .7z e descompactar em um diretório temporário
. limpar dados
. processar: aplicar modelo de agregação de dados
. gerar arquivos finais e enviar para persistência (dir local)
. apagar arquivos temporários
. processar próximo arquivo .7z

Código para Python 3

Algumas referências:
https://github.com/guilhermejacob/guilhermejacob.github.io/blob/master/scripts/mtps.R
https://github.com/rdahis/clean_RAIS
"""

__version__ = "1.1"
__author__ = "Mauro Zackiewicz"   # codigo
__email__ = "maurozac@gmail.com"
__copyright__ = "Copyright 2020"
__license__ = "New BSD License"
__status__ = "Experimental"


import json
import os

import numpy as np
import pandas as pd
import wget
import py7zr
import requests


UFs = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO',
    ]

ANOS = ['2017', '2010']

# Estes PATHs são do meu ambiente => use os seus aqui
PATH_TEMP = "/Users/tapirus/Desktop/ITA/dados/RAIS/temp/"
PATH_UTIL = "/Users/tapirus/Desktop/ITA/dados/RAIS/util/"
PATH_END = "/Users/tapirus/Desktop/ITA/dados/RAIS/pronto/"
PATH_UFS = "/Users/tapirus/Desktop/ITA/dados/RAIS/ufs/"
PATH_REC = "/Users/tapirus/Desktop/ITA/dados/RAIS/recortes/"


def baixar_raw(uf, ano, path_temp):
    """Baixa e descompacta arquivo de microdados da RAIS
    Retorna o path para do arquivo pronto para ser processado.

    ATENÇÃO: há variação na estrutura dos paths no ftp da RAIS,
    verifique a compatibilidade ao rodar para anos diferentes
    dos que estão aqui.
    """
    url = "ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/"
    url += ano + "/" + uf + ano + ".7z"

    filename = wget.download(url, out=path_temp)

    archive = py7zr.SevenZipFile(filename, mode='r')
    archive.extractall(path=path_temp)
    extraidos = archive.getnames()
    archive.close()
    if len(extraidos) != 1:
        print('[!] Pacote 7z fora do padrão:', uf, ano)
        return None

    os.remove(filename)

    return path_temp + extraidos[0]


# TESTE
# path = baixar_raw("AL", "2010", PATH_TEMP)


# DICT com definições para os tipos de dados
# nem todos foram incluidos pq não serão usados
CAMPOS_RAIS = {
    "2010": {
        # "CBO Ocupação 2002": str,
        "CNAE 2.0 Classe": str,
        # "CNAE 2.0 Subclasse": str,
        "Município": str,
        "Tamanho Estabelecimento": str,
        "Escolaridade após 2005": str,
        # "Faixa Etária": str,
        # "Raça Cor": str,
        # "Sexo Trabalhador": str,
        "Vl Remun Dezembro Nom": np.float64,
        "Vl Remun Média Nom": np.float64,
    },
    "2017": {
        # "CBO Ocupação 2002": str,
        "CNAE 2.0 Classe": str,
        # "CNAE 2.0 Subclasse": str,
        "Município": str,
        "Tamanho Estabelecimento": str,
        "Escolaridade após 2005": str,
        # "Faixa Etária": str,
        # "Raça Cor": str,
        # "Sexo Trabalhador": str,
        "Vl Rem Janeiro CC": np.float64,
        "Vl Rem Fevereiro CC": np.float64,
        "Vl Rem Março CC": np.float64,
        "Vl Rem Abril CC": np.float64,
        "Vl Rem Maio CC": np.float64,
        "Vl Rem Junho CC": np.float64,
        "Vl Rem Julho CC": np.float64,
        "Vl Rem Agosto CC": np.float64,
        "Vl Rem Setembro CC": np.float64,
        "Vl Rem Outubro CC": np.float64,
        "Vl Rem Novembro CC": np.float64,
        "Vl Remun Dezembro Nom": np.float64,
        "Vl Remun Média Nom": np.float64,
    }
}


def carregar_dados(path, ano, campos):
    """Importa arquivo .txt RAIS => na verdade um csv jabuticaba.
    Força consistência dos tipos de dados e elimina colunas que não serão usadas.
    Retorna DataFrame pronto para o uso.

    OBS: diferentes anos possuem diferentes campos de dados, certifique-se de
    fornecer o dict de campos correto.

    OBS2: comentar no dict de campos aqueles que não serão usados (isso diminui
    o impacto no processamento)
    """
    frame = pd.read_csv(
                path,
                encoding="ISO-8859-1",
                decimal=",",
                sep=";",
                dtype=campos[ano]
            )

    retirar = [_ for _ in frame.keys() if _ not in campos[ano].keys()]
    os.remove(path)

    return frame.drop(columns=retirar)


# TESTE
# df = carregar_dados(path, ano, CAMPOS_RAIS)
# df.shape
# fulano = df.iloc[1234]  # para ver um fulano qquer


def classes_CNAE(path_to_cnae=None):
    """
    docs:
    https://servicodados.ibge.gov.br/api/docs/cnae?versao=2#api-Classes-classesGet
    """
    if not path_to_cnae:
        url = "https://servicodados.ibge.gov.br/api/v2/cnae/classes"
        cnaes = json.loads(requests.get(url).text)
        with open(PATH_UTIL + "CNAEclasses.json", 'w', encoding='utf-8') as f:
            json.dump(cnaes, f, ensure_ascii=False, indent=2)
        return cnaes

    f = open(path_to_cnae + "CNAEclasses.json")
    cnaes = json.loads(f.read())
    f.close()

    return cnaes

# TESTE
# cnaes = classes_CNAE(PATH_UTIL)  # com arquivo CNAEclasses.json salvo em PATH_UTIL
# cnaes = classes_CNAE()  # init => baixa e salva em PATH_UTIL


def consolidar_tabela(df_limpo, ano, municipios, classes):
    """Esta tabela é a base para a estimativa de coeficentes locacionais.
    """
    col1, col2, col3, col4 = [], [], [], []
    for x in municipios:
        print(x)
        select1 = df_limpo.loc[df_limpo['Município'] == x]
        for y in classes:
            select2 = select1.loc[select1['CNAE 2.0 Classe'] == y]
            if ano == "2017":
                valor, trabalhadores, esco, tam = calcula_valores_2017(select2)
            elif ano == "2010":
                valor, trabalhadores, esco, tam = calcula_valores_2010(select2)
            else:
                valor, trabalhadores, esco, tam = 0.0, 0.0, 0.0, 0.0
            col1.append(valor)
            col2.append(trabalhadores)
            col3.append(esco)
            col4.append(tam)
    return col1, col2, col3, col4


def calcula_valores_2017(df):
    valor, trabalhadores, esco, tam = 0.0, 0.0, 0.0, 0.0
    casos = df.shape[0]
    if not casos:
        return valor, trabalhadores, esco, tam
    for index, row in df.iterrows():
        ano = [
            row['Vl Rem Janeiro CC'],
            row['Vl Rem Fevereiro CC'],
            row['Vl Rem Março CC'],
            row['Vl Rem Abril CC'],
            row['Vl Rem Maio CC'],
            row['Vl Rem Junho CC'],
            row['Vl Rem Julho CC'],
            row['Vl Rem Agosto CC'],
            row['Vl Rem Setembro CC'],
            row['Vl Rem Outubro CC'],
            row['Vl Rem Novembro CC'],
            row['Vl Remun Dezembro Nom'],
        ]
        ano = [m for m in ano if m > 0.0]  # elimina meses sem contrato
        contagem = len(ano)/12.0   # igual a 1 se trabalhou o ano inteiro, ou < 1
        trabalhadores += contagem
        # acontecem erros de digitacao ou conversão dos decimais => corrigir?
        # usando a remuneração média que normalmente vem correta
        total = row['Vl Remun Média Nom'] * len(ano)
        # acrescido de 1/3 de férias e décimo terceiro salário (proporcionais)
        # quase igual a Brene et al. (2014), exceto que ajustamos para o ano todo
        treze = row['Vl Remun Média Nom'] * len(ano)/12
        ferias = treze * 0.333
        valor += total + ferias + treze
        esco += int(row["Escolaridade após 2005"]) * contagem  # pondera pelo tempo empregado
        tam += int(row["Tamanho Estabelecimento"])

    # massa salarial e empregos são somas
    # escolaridade e tamanho do estab são médias
    esco = esco/max(1, trabalhadores)  # media ponderada
    tam = tam/casos

    return valor, trabalhadores, esco, tam


def calcula_valores_2010(df):
    valor, trabalhadores, esco, tam = 0.0, 0.0, 0.0, 0.0
    casos = df.shape[0]
    if not casos:
        return valor, trabalhadores, esco, tam
    for index, row in df.iterrows():
        # dados de 2010 não estão detalhados por mês
        # padrão metodológico é usar valor para DEZEMBRO [Brene et al. (2014)]
        # caso o individuo esteja empregado em dezembro...
        if row['Vl Remun Dezembro Nom']:
            trabalhadores += 1
            # usando a remuneração média que normalmente vem correta
            total = row['Vl Remun Média Nom'] * 12
            # acrescido de 1/3 de férias e décimo terceiro salário (proporcionais)
            # quase igual a , exceto que ajustamos para o ano todo
            treze = row['Vl Remun Média Nom']
            ferias = treze * 0.333
            valor += total + ferias + treze
            esco += int(row["Escolaridade após 2005"])
            tam += int(row["Tamanho Estabelecimento"])

    # massa salarial e empregos são somas
    # escolaridade e tamanho do estab são médias
    esco = esco/max(1, trabalhadores)  # media ponderada
    tam = tam/casos

    return valor, trabalhadores, esco, tam


def pipeline_completo(uf, ano):
    """Roda todo o pipeline para uma uf/ano.
    Retorna o
    """
    print("- - -")
    lista_classes = [x['id'] for x in classes_CNAE(PATH_UTIL)]
    lista_classes.sort()  # 673 classes [completo e ordenado]

    path = baixar_raw(uf, ano, PATH_TEMP)
    if not path:
        return None
    print('\n[♫] Baixado e descompactado:', uf, ano)

    df = carregar_dados(path, ano, CAMPOS_RAIS)
    print('[♫] DataFrame carregado:', uf, ano)
    print('[◔◔] com', df.shape[0], "linhas")

    municipios = df['Município'].unique()
    municipios.sort()  # ordenados

    col1, col2, col3, col4 = consolidar_tabela(df, ano, municipios, lista_classes)

    tupla = [(x, y) for x in municipios for y in lista_classes]
    mu_index = pd.MultiIndex.from_tuples(tupla, names=['Município', 'Classe CNAE'])

    tabela_uf = pd.DataFrame(
        {
            "Valor do Trabalho (R$ nom)": col1,  # soma dos salários pagos + 13º + extras
            "Pessoal empregado": col2,  # n de empregados, pode ser fracionado
            "Escolaridade": col3,  # indice medio de escolaridade
            "Tamanho do estabelecimentos": col4, # indice medio do tamanho do estabelecimento
        },
        index = mu_index
    )

    tabela_uf.to_csv(PATH_END + uf + ano + ".csv")
    print('[♫] CSV consolidado pronto:', uf, ano)
    print('[◔◔] com', tabela_uf.shape[0], "linhas")

    return tabela_uf


# teste
# tabela_uf = pipeline_completo("AP", "2010")
# caso maximo => para fritar: > 18 milhões de linhas
# tabela_uf = pipeline_completo("SP", "2017")


def consolidar_uf(uf, ano):
    """Gera tabela consolidada para o territorio da uf (soma municipios).
    """
    tabela_uf = pd.read_csv(PATH_END + uf + ano + ".csv")

    municipios = tabela_uf['Município'].unique()
    municipios.sort()
    cnaes = classes_CNAE(PATH_UTIL)
    lista_classes = [x['id'] for x in cnaes]
    lista_classes.sort()  # 673 classes [completo e ordenado]

    col1 = np.array([0.0 for _ in lista_classes])
    col2 = np.array([0.000001 for _ in lista_classes])  # init para evitar NaN
    col3 = np.array([0.0 for _ in lista_classes])
    col4 = np.array([0.0 for _ in lista_classes])

    for m in municipios:
        local = tabela_uf.loc[tabela_uf["Município"] == m]
        col1 += local['Valor do Trabalho (R$ nom)'].values
        col3 = (col3*col2 + local['Escolaridade'].values*local['Pessoal empregado'].values) / (col2+local['Pessoal empregado'].values)
        col4 = (col4*col2 + local['Tamanho do estabelecimentos'].values*local['Pessoal empregado'].values) / (col2+local['Pessoal empregado'].values)
        # pessoal por ultimo para não estragar a ponderação de col3 e col4
        col2 += local['Pessoal empregado'].values

    pronto = pd.DataFrame(
        {
            "Valor do Trabalho (R$ nom)": col1,  # soma dos salários pagos + 13º + extras
            "Pessoal empregado": col2,  # n de empregados, pode ser fracionado
            "Escolaridade": col3,  # indice medio de escolaridade
            "Tamanho do estabelecimentos": col4, # indice medio do tamanho do estabelecimento
        },
        index = pd.Index(lista_classes, name="Classe CNAE")
    )

    # adiciona descricao das classes CNAE
    desc = [x['descricao'] for x in cnaes]
    pronto['Atividade Econômica'] = pd.Series(desc, index=pronto.index)

    pronto.to_csv(PATH_UFS + uf + ano + ".csv")
    print('[♫] CSV UF pronto:', uf, ano)

    return pronto


def consolidar_BR(ano):
    """Gera tabela consolidada para o territorio nacional (soma ufs).
    """
    cnaes = classes_CNAE(PATH_UTIL)
    lista_classes = [x['id'] for x in cnaes]
    lista_classes.sort()  # 673 classes [completo e ordenado]

    col1 = np.array([0.0 for _ in lista_classes])
    col2 = np.array([0.000001 for _ in lista_classes])  # init para evitar NaN
    col3 = np.array([0.0 for _ in lista_classes])
    col4 = np.array([0.0 for _ in lista_classes])

    for uf in UFs:
        local = pd.read_csv(PATH_UFS + uf + ano + ".csv")
        col1 += local['Valor do Trabalho (R$ nom)'].values
        col3 = (col3*col2 + local['Escolaridade'].values*local['Pessoal empregado'].values) / (col2+local['Pessoal empregado'].values)
        col4 = (col4*col2 + local['Tamanho do estabelecimentos'].values*local['Pessoal empregado'].values) / (col2+local['Pessoal empregado'].values)
        # pessoal por ultimo para não estragar a ponderação de col3 e col4
        col2 += local['Pessoal empregado'].values

    br = pd.DataFrame(
        {
            "Valor do Trabalho (R$ nom)": col1,  # soma dos salários pagos + 13º + extras
            "Pessoal empregado": col2,  # n de empregados, pode ser fracionado
            "Escolaridade": col3,  # indice medio de escolaridade
            "Tamanho do estabelecimentos": col4, # indice medio do tamanho do estabelecimento
        },
        index = pd.Index(lista_classes, name="Classe CNAE")
    )

    # adiciona descricao das classes CNAE
    desc = [x['descricao'] for x in cnaes]
    br['Atividade Econômica'] = pd.Series(desc, index=br.index)

    br.to_csv(PATH_UFS + "BRASIL" + ano + ".csv")
    print('[♫] CSV BR pronto:', ano)

    return br


def gerar_recorte(nome, uf, ano, ids):
    """Consolida um recorte dentro de uma UF a partir de
    uma lista de ids de municipios.
    """
    if type(ids) is not list:
        print('[!] IDs precisam ser fornecidos como lista')
        return None

    base = pd.read_csv(PATH_END + uf + ano + ".csv")

    cnaes = classes_CNAE(PATH_UTIL)
    lista_classes = [x['id'] for x in cnaes]
    lista_classes.sort()  # 673 classes [completo e ordenado]

    col1 = np.array([0.0 for _ in lista_classes])
    col2 = np.array([0.000001 for _ in lista_classes])  # init para evitar NaN
    col3 = np.array([0.0 for _ in lista_classes])
    col4 = np.array([0.0 for _ in lista_classes])

    for mun in ids:
        local = base.loc[base['Município'] == int(mun)]
        col1 += local['Valor do Trabalho (R$ nom)'].values
        col3 = (col3*col2 + local['Escolaridade'].values*local['Pessoal empregado'].values) / (col2+local['Pessoal empregado'].values)
        col4 = (col4*col2 + local['Tamanho do estabelecimentos'].values*local['Pessoal empregado'].values) / (col2+local['Pessoal empregado'].values)
        # pessoal por ultimo para não estragar a ponderação de col3 e col4
        col2 += local['Pessoal empregado'].values

    recorte = pd.DataFrame(
        {
            "Valor do Trabalho (R$ nom)": col1,  # soma dos salários pagos + 13º + extras
            "Pessoal empregado": col2,  # n de empregados, pode ser fracionado
            "Escolaridade": col3,  # indice medio de escolaridade
            "Tamanho do estabelecimentos": col4, # indice medio do tamanho do estabelecimento
        },
        index = pd.Index(lista_classes, name="Classe CNAE")
    )

    # adiciona descricao das classes CNAE
    desc = [x['descricao'] for x in cnaes]
    recorte['Atividade Econômica'] = pd.Series(desc, index=recorte.index)

    recorte.to_csv(PATH_REC + nome + ano + ".csv")
    print('[♫] CSV ' + nome + ' pronto:', ano)

    return recorte


# Testes
# recorte = gerar_recorte('Campinas', 'SP', '2017', [350950])
# recorte = gerar_recorte('Campinas', 'SP', '2010', [350950])
# recorte = gerar_recorte('SJC', 'SP', '2017', [354990])
# recorte = gerar_recorte('SJC', 'SP', '2010', [354990])


################################################################################################

# RODAR - PASSO 1
for uf in UFs:
    for ano in ANOS:
        pipeline_completo(uf, ano)

# RODAR - PASSO 2
for uf in UFs:
    for ano in ANOS:
        consolidar_uf(uf, ano)

# RODAR - PASSO 3
for ano in ANOS:
    consolidar_BR(ano)
 
# RODAR - PASSO 4
RMC = {
    "350160":"Americana",
    "350380":"Artur Nogueira",
    "350950":"Campinas",
    "351280":"Cosmópolis",
    "351515":"Engenheiro Coelho",
    "351905":"Holambra",
    "351907":"Hortolândia",
    "352050":"Indaiatuba",
    "352340":"Itatiba",
    "352470":"Jaguariúna",
    "353180":"Monte Mor",
    "353200":"Morungaba",
    "353340":"Nova Odessa",
    "353650":"Paulínia",
    "353710":"Pedreira",
    "354580":"Santa Bárbara d'Oeste",
    "354800":"Santo Antônio de Posse",
    "355240":"Sumaré",
    "355620":"Valinhos",
    "355670":"Vinhedo",
}

RMC_17 = gerar_recorte('RMC', 'SP', '2017', list(RMC.keys()))
RMC_10 = gerar_recorte('RMC', 'SP', '2010', list(RMC.keys()))


################################################################################################

"""
Range das Escalas
-----------------

Escolaridade após 2005:
1 "Analfabeto"
2 "Ate 5a Incompleto"
3 "5a Completo"
4 "6a a 9a Incompleto"
5 "9a Completo"
6 "Medio Incompleto"
7 "Medio Completo"
8 "Superior Incompleto"
9 "Superior Completo"
10 "Mestrado"
11 "Doutorado"

Tamanho do Estabelecimento:
0 "Zero"
1 "Ate 4"
2 "De 5 a 9"
3 "De 10 a 19"
4 "De 20 a 49"
5 "De 50 a 99"
6 "De 100 a 249"
7 "De 250 a 499"
8 "De 500 a 999"
9 "1000 ou mais"
"""
