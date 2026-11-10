# -*- coding: utf-8 -*-
"""Leva folhas (carimbo + legenda + parametros) para outro documento aberto."""
from Autodesk.Revit.DB import (
    BuiltInCategory, CopyPasteOptions, DuplicateTypeAction, ElementId, ElementTransformUtils,
    FamilySymbol, FilteredElementCollector, IDuplicateTypeNamesHandler, SubTransaction,
    Transaction, TransactionStatus, Transform, View, ViewSheet, ViewType,
)
from System.Collections.Generic import List

from . import destaque, eid, folhas, nome, regras, texto


class _UsarDestino(IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DuplicateTypeAction.UseDestinationTypes


def _opcoes():
    op = CopyPasteOptions()
    op.SetDuplicateTypeNamesHandler(_UsarDestino())
    return op


def documentos_destino(app, doc):
    """Outros projetos abertos (nao familia, nao link)."""
    saida = []
    for d in app.Documents:
        try:
            if d.IsFamilyDocument or d.IsLinked or d.Equals(doc):
                continue
            saida.append(d)
        except Exception:
            continue
    return saida


def _tipo_de_carimbo(origem, destino, tipo):
    """FamilySymbol do carimbo no destino: o de mesmo nome de familia/tipo,
    ou copiado do documento de origem."""
    fam, tn = texto(tipo.FamilyName), nome(tipo)
    for s in (FilteredElementCollector(destino).OfCategory(BuiltInCategory.OST_TitleBlocks)
              .OfClass(FamilySymbol).ToElements()):
        if texto(s.FamilyName) == fam and nome(s) == tn:
            return s
    ids = List[ElementId]()
    ids.Add(tipo.Id)
    novos = ElementTransformUtils.CopyElements(origem, ids, destino, Transform.Identity, _opcoes())
    for i in novos:
        s = destino.GetElement(i)
        if isinstance(s, FamilySymbol):
            return s
    raise Exception(u'não consegui trazer o carimbo %s : %s' % (fam, tn))


def _legenda_no_destino(origem, destino, legenda, cache):
    chave = eid(legenda.Id)
    if chave in cache:
        return cache[chave]
    ids = List[ElementId]()
    ids.Add(legenda.Id)
    novos = ElementTransformUtils.CopyElements(origem, ids, destino, Transform.Identity, _opcoes())
    for i in novos:
        v = destino.GetElement(i)
        if isinstance(v, View) and v.ViewType == ViewType.Legend:
            cache[chave] = v
            return v
    raise Exception(u'não consegui copiar a legenda %s' % nome(legenda))


def levar(origem, destino, lista_folhas, sufixo=u'-COPIA'):
    """Cria no destino uma folha para cada folha da origem. Devolve
    (criadas[numeros], avisos). Uma transacao no destino."""
    ocupados = set(f.SheetNumber for f in folhas.todas(destino))
    cache, criadas, avisos, uids = {}, [], [], []
    t = Transaction(destino, u'Folhas HOYT - trazer folhas (%d)' % len(lista_folhas))
    t.Start()
    try:
        for f in lista_folhas:
            sub = SubTransaction(destino)
            sub.Start()
            try:
                c = folhas.carimbo(origem, f)
                if c is None:
                    raise Exception(u'a folha não tem carimbo')
                simbolo = _tipo_de_carimbo(origem, destino, origem.GetElement(c.GetTypeId()))
                if not simbolo.IsActive:
                    simbolo.Activate()
                nova = ViewSheet.Create(destino, simbolo.Id)
                num = f.SheetNumber
                if num in ocupados:
                    num = regras.numero_livre(num, ocupados, sufixo)
                ocupados.add(num)
                nova.SheetNumber = num
                nova.Name = f.Name
                destino.Regenerate()
                _o, pul = folhas.copiar_parametros(f, nova)
                cn = folhas.carimbo(destino, nova)
                if cn is None:
                    raise Exception(u'o carimbo da folha nova não foi criado')
                _o2, pul2 = folhas.copiar_parametros(c, cn)
                pul = pul + pul2
                destino.Regenerate()
                if pul:
                    avisos.append(u'%s: não copiou %s' % (num, u', '.join(sorted(set(pul)))))
                _n, falhas = folhas._legenda_para(
                    origem, f, nova, lambda v: _legenda_no_destino(origem, destino, v, cache),
                    folhas.deslocamento(origem, f, nova))
                for a in falhas:
                    avisos.append(u'%s: %s' % (num, a))
                sub.Commit()
                criadas.append(num)
                uids.append(nova.UniqueId)
            except Exception as ex:
                sub.RollBack()
                avisos.append(u'%s: não levou (%s)' % (f.SheetNumber, texto(ex)))
        t.Commit()
        destaque.registrar(destino, uids)
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return criadas, avisos
