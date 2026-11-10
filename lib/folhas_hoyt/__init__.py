# -*- coding: utf-8 -*-
"""Folhas HOYT - gerenciador de vistas e folhas (Revit 2023).

Pedido do Lucas (15/10/2026). Uma aba propria com 4 botoes:
  Vistas      - plantas: duplicar (com/sem detalhamento) e renomear em lote
  Folhas      - duplicar (-COPIA, mesmos parametros e legenda), trocar a
                legenda em lote, renumerar/renomear em lote
  Casar       - lista de vistas x lista de folhas; posiciona cada vista
                centralizada na area util (motor do Montar Folhas)
  Levar       - leva folhas (com a legenda) para outro documento aberto

Modulos: regras (texto puro), ui (WPF), vistas, folhas, casar, transferir.
IronPython 2.7 do pyRevit: so' literais u'', nada de f-string.
"""

VERSAO = u'0.3.1'


def texto(v):
    try:
        return u'%s' % v
    except Exception:
        return u'?'


def eid(elemento_id):
    """ElementId -> int (IntegerValue no 2023, Value no 2024+)."""
    try:
        return int(elemento_id.Value)
    except Exception:
        return int(elemento_id.IntegerValue)


def nome(elemento):
    """Nome de qualquer elemento (Element.Name.GetValue contorna o conflito
    de .Name em tipos de familia no IronPython)."""
    try:
        return texto(elemento.Name)
    except Exception:
        from Autodesk.Revit.DB import Element
        return texto(Element.Name.GetValue(elemento))
