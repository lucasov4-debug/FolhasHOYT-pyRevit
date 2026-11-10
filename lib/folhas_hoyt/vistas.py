# -*- coding: utf-8 -*-
"""Plantas do projeto: listar, duplicar (com/sem detalhamento), renomear."""
from Autodesk.Revit.DB import (
    BuiltInParameter, FilteredElementCollector, Transaction, TransactionStatus,
    View, ViewDuplicateOption, ViewType,
)

from . import nome, texto

TIPOS = (ViewType.FloorPlan, ViewType.CeilingPlan, ViewType.EngineeringPlan, ViewType.AreaPlan)


def listar(doc):
    saida = []
    for v in FilteredElementCollector(doc).OfClass(View).ToElements():
        try:
            if v.IsTemplate or v.ViewType not in TIPOS:
                continue
        except Exception:
            continue
        saida.append(v)
    saida.sort(key=lambda v: (texto(v.ViewType), nome(v).lower()))
    return saida


def folha_da_vista(v):
    try:
        p = v.get_Parameter(BuiltInParameter.VIEWER_SHEET_NUMBER)
        s = p.AsString() if p is not None else None
        return s if s and s != u'---' else u''
    except Exception:
        return u''


def escala(v):
    try:
        return u'1:%d' % int(v.Scale)
    except Exception:
        return u''


def duplicar(doc, views, com_detalhe):
    """(feitas, falhas) - uma transacao so' (Ctrl+Z desfaz tudo)."""
    opcao = ViewDuplicateOption.WithDetailing if com_detalhe else ViewDuplicateOption.Duplicate
    feitas, falhas = [], []
    t = Transaction(doc, u'Folhas HOYT - duplicar vistas %s' % (u'com detalhamento' if com_detalhe else u'sem detalhamento'))
    t.Start()
    try:
        for v in views:
            try:
                if not v.CanViewBeDuplicated(opcao):
                    falhas.append(u'%s: o Revit não permite duplicar assim (vista dependente?)' % nome(v))
                    continue
                novo = doc.GetElement(v.Duplicate(opcao))
                feitas.append(nome(novo))
            except Exception as ex:
                falhas.append(u'%s: %s' % (nome(v), texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return feitas, falhas


def titulo_da_pagina(v):
    """Parametro "Titulo da pagina" (Title on Sheet)."""
    try:
        p = v.get_Parameter(BuiltInParameter.VIEW_DESCRIPTION)
        return (p.AsString() or u'') if p is not None else u''
    except Exception:
        return u''


def renomear(doc, mudancas):
    """mudancas = [(View, novo_nome|None, novo_titulo|None)] -> (feitas,
    falhas). Uma transacao so'."""
    feitas, falhas = 0, []
    t = Transaction(doc, u'Folhas HOYT - renomear vistas')
    t.Start()
    try:
        for v, novo, titulo in mudancas:
            antigo = nome(v)
            if novo is not None:
                try:
                    v.Name = novo
                    feitas += 1
                except Exception as ex:
                    falhas.append(u'%s → %s: %s' % (antigo, novo, texto(ex)))
            if titulo is not None:
                try:
                    v.get_Parameter(BuiltInParameter.VIEW_DESCRIPTION).Set(titulo)
                    feitas += 1
                except Exception as ex:
                    falhas.append(u'%s: título da página (%s)' % (antigo, texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return feitas, falhas
