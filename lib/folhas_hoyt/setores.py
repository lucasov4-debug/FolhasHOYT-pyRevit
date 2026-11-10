# -*- coding: utf-8 -*-
"""Replica os setores (recortes) de uma planta de referencia nas outras
plantas: duplica com detalhamento, aplica o recorte, o template e a escala
da vista de referencia e nomeia "<planta> - S05".

Pedido do Lucas (15/10/2026): os pavimentos tem o mesmo X/Y, o recorte e'
retangular e os setores sao numerados da esquerda para a direita."""
from Autodesk.Revit.DB import (
    BuiltInParameter, ElementId, SubTransaction, Transaction, TransactionStatus,
    ViewDuplicateOption, XYZ,
)

from . import eid, nome, texto


def codigo(inicio, k, prefixo=u'S'):
    return u'%s%02d' % (prefixo, int(inicio) + int(k))


def caixa_no_modelo(vista):
    """(x_min, y_min, x_max, y_max) do recorte da vista em coordenadas do
    modelo (pes), ou None se a vista nao tem recorte."""
    try:
        cb = vista.CropBox
        t = cb.Transform
        a, b = t.OfPoint(cb.Min), t.OfPoint(cb.Max)
        return min(a.X, b.X), min(a.Y, b.Y), max(a.X, b.X), max(a.Y, b.Y)
    except Exception:
        return None


def ordenar_da_esquerda(refs_com_x):
    """[(View, x_min)] -> [View] da esquerda para a direita."""
    return [v for v, _x in sorted(refs_com_x, key=lambda p: p[1])]


def _aplicar_recorte(nova, ref):
    cb_ref = ref.CropBox
    rt = cb_ref.Transform
    pa, pb = rt.OfPoint(cb_ref.Min), rt.OfPoint(cb_ref.Max)
    nova.CropBoxActive = True
    cb = nova.CropBox
    inv = cb.Transform.Inverse
    a, b = inv.OfPoint(pa), inv.OfPoint(pb)
    cb.Min = XYZ(min(a.X, b.X), min(a.Y, b.Y), cb.Min.Z)
    cb.Max = XYZ(max(a.X, b.X), max(a.Y, b.Y), cb.Max.Z)
    nova.CropBox = cb


def _copiar_aparencia(nova, ref, ocultar_fora=True):
    """Template (primeiro - ele pode controlar o recorte), escala, recorte
    visivel e recorte de anotacao (ocultar_fora=True liga o recorte de anotacao:
    anotacoes fora da regiao somem)."""
    try:
        if eid(ref.ViewTemplateId) != -1:
            nova.ViewTemplateId = ref.ViewTemplateId
    except Exception:
        pass
    try:
        nova.Scale = ref.Scale
    except Exception:
        pass
    _aplicar_recorte(nova, ref)
    try:
        nova.CropBoxVisible = ref.CropBoxVisible
    except Exception:
        pass
    try:
        p = ref.get_Parameter(BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
        q = nova.get_Parameter(BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
        if p is not None and q is not None and not q.IsReadOnly:
            q.Set(1 if ocultar_fora else p.AsInteger())
    except Exception:
        pass


def replicar(doc, refs, alvos, inicio, ocultar_fora=True):
    """refs = [View] ordenadas da esquerda p/ direita; alvos = [(View, n)]
    (n = quantos setores, a partir do primeiro). Devolve (nomes criados,
    avisos). Uma transacao so'."""
    criadas, avisos = [], []
    t = Transaction(doc, u'Folhas HOYT - replicar setores (%d plantas)' % len(alvos))
    t.Start()
    try:
        for alvo, n in alvos:
            base = nome(alvo)
            for k in range(min(int(n), len(refs))):
                nome_novo = u'%s - %s' % (base, codigo(inicio, k))
                sub = SubTransaction(doc)
                sub.Start()
                try:
                    op = ViewDuplicateOption.WithDetailing
                    if not alvo.CanViewBeDuplicated(op):
                        raise Exception(u'o Revit não permite duplicar esta vista')
                    nova = doc.GetElement(alvo.Duplicate(op))
                    nova.Name = nome_novo
                    _copiar_aparencia(nova, refs[k], ocultar_fora)
                    sub.Commit()
                    criadas.append(nome_novo)
                except Exception as ex:
                    sub.RollBack()
                    avisos.append(u'%s: %s' % (nome_novo, texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return criadas, avisos
