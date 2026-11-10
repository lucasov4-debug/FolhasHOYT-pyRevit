# -*- coding: utf-8 -*-
"""Insere uma legenda no canto superior direito interno das folhas."""
from Autodesk.Revit.DB import FilteredElementCollector, SubTransaction, Transaction, TransactionStatus, Viewport, XYZ
from montagem_folha import leitura

from . import eid, folhas, nome, texto

PES_EM_MM = 304.8
RECUO_MM = 10.0
AJUSTE_DIREITA_CM = 2.53
AJUSTE_CIMA_CM = 0.41


def _tipo_sem_titulo(doc):
    for tipo in FilteredElementCollector(doc).WhereElementIsElementType().ToElements():
        try:
            if texto(tipo.FamilyName).strip().lower() == u'viewport' and nome(tipo).strip().lower() == u'no title':
                return tipo.Id
        except Exception:
            continue
    raise Exception(u'tipo de viewport "No Title" não encontrado no projeto')


def _canto_da_folha(doc, folha):
    area = leitura.area_da_folha(doc, folha)
    if area is None:
        raise Exception(u'folha sem carimbo ou tamanho de papel válido')
    papel = area[u'externo']
    return ((papel[2] - RECUO_MM) / PES_EM_MM + AJUSTE_DIREITA_CM / 30.48,
            (papel[3] - RECUO_MM) / PES_EM_MM + AJUSTE_CIMA_CM / 30.48,
            papel)


def inserir(doc, lista_folhas, legenda):
    """Insere ou corrige a legenda escolhida; uma subtransação por folha."""
    inseridas, corrigidas, avisos = 0, 0, []
    tipo_id = _tipo_sem_titulo(doc)
    t = Transaction(doc, u'Folhas HOYT - inserir legenda em %d folhas' % len(lista_folhas))
    t.Start()
    try:
        for folha in lista_folhas:
            numero = folha.SheetNumber
            existentes = [vp for vp in folhas.legendas_da_folha(doc, folha)
                          if eid(vp.ViewId) == eid(legenda.Id)]
            if len(existentes) > 1:
                avisos.append(u'%s: há mais de uma viewport da mesma legenda; confira manualmente' % numero)
                continue
            sub = SubTransaction(doc)
            sub.Start()
            try:
                x, y, papel = _canto_da_folha(doc, folha)
                if existentes:
                    vp = existentes[0]
                else:
                    if not Viewport.CanAddViewToSheet(doc, folha.Id, legenda.Id):
                        raise Exception(u'legenda não pode ser adicionada a esta folha')
                    vp = Viewport.Create(doc, folha.Id, legenda.Id, XYZ(x, y, 0.0))
                fixa = bool(vp.Pinned)
                if fixa:
                    vp.Pinned = False
                if eid(vp.GetTypeId()) != eid(tipo_id):
                    vp.ChangeTypeId(tipo_id)
                doc.Regenerate()
                caixa = vp.GetBoxOutline()
                dx = x - caixa.MaximumPoint.X
                dy = y - caixa.MaximumPoint.Y
                c = vp.GetBoxCenter()
                vp.SetBoxCenter(XYZ(c.X + dx, c.Y + dy, c.Z))
                doc.Regenerate()
                if fixa:
                    vp.Pinned = True
                caixa = vp.GetBoxOutline()
                if (caixa.MinimumPoint.X * PES_EM_MM < papel[0] - 0.5 or
                        caixa.MinimumPoint.Y * PES_EM_MM < papel[1] - 0.5):
                    raise Exception(u'legenda excede a área da folha')
                sub.Commit()
                if existentes:
                    corrigidas += 1
                else:
                    inseridas += 1
            except Exception as ex:
                sub.RollBack()
                avisos.append(u'%s: %s' % (numero, texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return inseridas, corrigidas, avisos
