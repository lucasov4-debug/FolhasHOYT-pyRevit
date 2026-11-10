# -*- coding: utf-8 -*-
"""Regras de renomear/renumerar em lote - texto puro, sem Revit."""


def aplicar(atual, prefixo=u'', sufixo=u'', buscar=u'', trocar=u''):
    """localizar/substituir -> prefixo + resultado + sufixo."""
    t = atual
    if buscar:
        t = t.replace(buscar, trocar or u'')
    return (prefixo or u'') + t + (sufixo or u'')


def sequencia(indice, prefixo=u'', inicio=1, passo=1, digitos=0, sufixo=u''):
    n = int(inicio) + int(indice) * int(passo)
    corpo = u'%d' % n
    if digitos and int(digitos) > len(corpo):
        corpo = corpo.zfill(int(digitos))
    return (prefixo or u'') + corpo + (sufixo or u'')


def inteiro(texto, padrao):
    try:
        return int(u'%s' % texto)
    except Exception:
        return padrao


def numero_livre(base, ocupados, sufixo=u'-COPIA'):
    """base + sufixo; se existir, base + sufixo + 2, 3... (ocupados = set)."""
    cand = base + sufixo
    n = 2
    while cand in ocupados:
        cand = u'%s%s%d' % (base, sufixo, n)
        n += 1
    return cand


def conflitos(finais):
    """finais = [(chave, numero_final)] -> set dos numeros que aparecem 2+ vezes."""
    vistos, repetidos = set(), set()
    for _k, n in finais:
        if n in vistos:
            repetidos.add(n)
        vistos.add(n)
    return repetidos
