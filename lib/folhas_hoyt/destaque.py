# -*- coding: utf-8 -*-
"""Folhas "novas" (criadas pelo plugin - duplicadas ou trazidas de outro
documento) ficam destacadas na lista da aba Folhas ate' o usuario limpar.

O Revit nao deixa colorir folha no navegador de projeto, entao a marca vive
num arquivo do usuario (%APPDATA%\\FolhasHOYT\\novas.json): {documento:
[UniqueId, ...]}. Chave do documento = caminho do arquivo (ou o titulo, se
ainda nao foi salvo)."""
import io
import json
import os

ARQUIVO = os.path.join(os.environ.get(u'APPDATA', os.path.expanduser(u'~')), u'FolhasHOYT', u'novas.json')


def _chave(doc):
    try:
        return doc.PathName or doc.Title
    except Exception:
        return u'?'


def _ler():
    try:
        with io.open(ARQUIVO, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _gravar(dados):
    try:
        pasta = os.path.dirname(ARQUIVO)
        if not os.path.isdir(pasta):
            os.makedirs(pasta)
        with io.open(ARQUIVO, 'w', encoding='utf-8') as f:
            f.write(json.dumps(dados, ensure_ascii=False, indent=1))
    except Exception:
        pass


def registrar(doc, uids):
    dados = _ler()
    atuais = set(dados.get(_chave(doc), []))
    atuais.update(uids)
    dados[_chave(doc)] = sorted(atuais)
    _gravar(dados)


def novas(doc):
    return set(_ler().get(_chave(doc), []))


def limpar(doc, uids=None):
    """Tira o destaque de `uids` (None = de todas as folhas do documento)."""
    dados = _ler()
    if uids is None:
        dados.pop(_chave(doc), None)
    else:
        dados[_chave(doc)] = sorted(set(dados.get(_chave(doc), [])) - set(uids))
    _gravar(dados)
