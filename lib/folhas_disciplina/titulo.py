# -*- coding: utf-8 -*-
"""Familias e tipos (formatos de papel) de titulo de prancha carregados no
projeto - sempre detectados na hora (decisao Q6 do grilling), nunca
fixados em codigo, porque a familia pode ganhar formatos novos com o tempo
("posso querer melhorar essa folha no futuro", Lucas).

BUG JA' DOCUMENTADO NESTE REPO (ver lib/furacao/nomes.py): `.Name` explode
(ou devolve vazio) em FamilySymbol/ElementType - `Element.Name` e'
so-leitura mas `ElementType` redeclara `Name` com getter E setter, e o
binder do Python/.NET nao resolve a sobreposicao. `Family.Name` (a familia,
nao o tipo) funciona normal. A saida e' ler por reflexao
(`PropertyInfo.GetValue`), que vai direto na propriedade .NET sem passar
pelo binder - mesma tecnica de lib/furacao/nomes.py, replicada aqui sem
importar aquele pacote (cada ferramenta mantem seu lib independente)."""

import clr
from Autodesk.Revit.DB import BuiltInCategory, Element, FilteredElementCollector, View, ViewType


def _propriedade_name():
    try:
        return clr.GetClrType(Element).GetProperty(u"Name")
    except Exception:
        return None


_PROP_NAME = _propriedade_name()


def nome_tipo(tipo):
    """Nome do TIPO (formato) de titulo - nunca usar `tipo.Name` sozinho
    (ver o motivo no cabecalho do arquivo). Tenta `.Name` primeiro (funciona
    em algumas instalações/versões), cai para reflexão se não vier nada."""
    try:
        nome = tipo.Name
        if nome:
            return nome
    except Exception:
        pass
    if _PROP_NAME is not None:
        for chamar in (lambda: _PROP_NAME.GetValue(tipo, None),
                       lambda: _PROP_NAME.GetValue(tipo)):
            try:
                nome = chamar()
                if nome:
                    return nome
            except Exception:
                continue
    return u""


def familias_de_titulo(doc):
    """{nome_familia: [tipo, ...]} de todos os OST_TitleBlocks carregados,
    cada lista de tipos ordenada pelo nome do formato (A1, A2, A1-E...)."""
    agrupado = {}
    tipos = (FilteredElementCollector(doc)
             .OfCategory(BuiltInCategory.OST_TitleBlocks)
             .WhereElementIsElementType()
             .ToElements())
    for tipo in tipos:
        try:
            nome_familia = tipo.Family.Name
        except Exception:
            nome_familia = u"?"
        agrupado.setdefault(nome_familia, []).append(tipo)
    for lista in agrupado.values():
        lista.sort(key=nome_tipo)
    return agrupado


def legendas_do_projeto(doc):
    """[View, ...] - todas as vistas de Legenda do projeto, ordenadas pelo
    nome. Usadas na aba Padrões para escolher qual legenda entra em cada
    disciplina (pedido do Lucas, 19/09/2026: "adicionar legendas por
    disciplina" na criação em lote). Legenda não tem o bug do FamilySymbol
    (é uma View, não um ElementType) - `.Name` funciona normal aqui."""
    legendas = []
    for v in FilteredElementCollector(doc).OfClass(View).ToElements():
        try:
            if v.ViewType == ViewType.Legend and not v.IsTemplate:
                legendas.append(v)
        except Exception:
            continue
    legendas.sort(key=lambda v: (v.Name or u""))
    return legendas
