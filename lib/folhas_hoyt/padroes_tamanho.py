# -*- coding: utf-8 -*-
"""Padrões de tamanho do usuário, independentes do documento Revit."""
import io
import json
import os

ARQUIVO = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')),
                      'FolhasHOYT', 'padroes_tamanho.json')

PADROES_FIXOS = (
    (u'A0', 84.1, 118.9),
    (u'A0_EST_1', 84.1, 142.8),
    (u'A0_EST_2', 84.1, 166.7),
)


def numero_cm(valor):
    texto = (u'%s' % valor).strip().replace(u',', u'.')
    try:
        numero = float(texto)
    except Exception:
        raise ValueError(u'Informe uma medida numérica em centímetros.')
    if not 1.0 <= numero <= 500.0:
        raise ValueError(u'A medida deve estar entre 1 e 500 cm.')
    return numero


def resolver(chave, altura_manual, largura_manual, padroes):
    """Medidas pendentes: texto manual prevalece, None preserva a atual."""
    chave = chave or u''
    if chave and chave not in padroes:
        raise ValueError(u'Padrão não encontrado.')
    altura, largura = padroes[chave] if chave else (None, None)
    if (u'%s' % (altura_manual or u'')).strip():
        altura = numero_cm(altura_manual)
    if (u'%s' % (largura_manual or u'')).strip():
        largura = numero_cm(largura_manual)
    return altura, largura


def ler(caminho=ARQUIVO):
    if not os.path.isfile(caminho):
        return []
    with io.open(caminho, 'r', encoding='utf-8') as arquivo:
        dados = json.load(arquivo)
    if not isinstance(dados, list):
        raise ValueError(u'O arquivo de padrões não contém uma lista.')
    saida, nomes = [], set([p[0].lower() for p in PADROES_FIXOS])
    for item in dados:
        try:
            nome = (u'%s' % item['nome']).strip()
            alt = numero_cm(item['altura_cm'])
            larg = numero_cm(item['largura_cm'])
            if not nome or nome.lower() in nomes:
                continue
            nomes.add(nome.lower())
            saida.append((nome, alt, larg))
        except Exception:
            continue
    return saida


def salvar(nome, altura, largura, caminho=ARQUIVO):
    nome = (u'%s' % nome).strip()
    if not nome or len(nome) > 80:
        raise ValueError(u'Informe um nome de até 80 caracteres para o padrão.')
    alt, larg = numero_cm(altura), numero_cm(largura)
    atuais = ler(caminho)
    if nome.lower() in set([p[0].lower() for p in PADROES_FIXOS] +
                           [p[0].lower() for p in atuais]):
        raise ValueError(u'Já existe um padrão com esse nome.')
    pasta = os.path.dirname(caminho)
    if not os.path.isdir(pasta):
        os.makedirs(pasta)
    dados = [dict(nome=n, altura_cm=a, largura_cm=l) for n, a, l in atuais + [(nome, alt, larg)]]
    temporario = caminho + '.tmp'
    with io.open(temporario, 'w', encoding='utf-8') as arquivo:
        arquivo.write(json.dumps(dados, ensure_ascii=False, indent=2))
    if not os.path.exists(caminho):
        os.rename(temporario, caminho)
    elif hasattr(os, 'replace'):
        os.replace(temporario, caminho)
    else:
        _substituir(temporario, caminho)
    return nome, alt, larg


def _substituir(origem, destino):
    # os.replace não existe no IronPython 2.7; .NET faz a substituição atômica.
    from System.IO import File
    File.Replace(origem, destino, None)
