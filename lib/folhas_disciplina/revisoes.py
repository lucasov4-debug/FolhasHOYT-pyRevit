# -*- coding: utf-8 -*-
"""Revisoes das folhas, em lote.

Duas coisas confirmadas na API antes de escrever isto (pesquisa feita
durante o grilling do Gerenciador de Folhas, corrigindo a ideia original
da Q9):

  - "incluir/tirar uma revisão de uma folha" (a grade de baixo da tela
    nativa de Revisões) É por folha:
    ViewSheet.GetAdditionalRevisionIds()/SetAdditionalRevisionIds(). A
    lógica abaixo é a mesma já validada em produção em
    ExportarPranchas.pushbutton/script.py (classe JanelaRevisoes),
    portada para CPython3.

  - "visibilidade de nuvem/tag" (Revision.Visibility, enum
    RevisionVisibility: Hidden / CloudAndTagVisible / TagVisible) NÃO é
    por folha - é uma propriedade da própria Revisão, valendo para o
    projeto inteiro. Não existe (nem existiu) API pública para uma
    revisão aparecer numa folha e sumir em outra. Por isso o toggle aqui
    é rotulado como "projeto inteiro" na interface, nunca como "nesta
    folha" - avisar o contrário seria mentir sobre o que o botão faz.

Precisa de transação aberta por quem chama.
"""
from Autodesk.Revit.DB import (
    ElementId, FilteredElementCollector, Revision, RevisionVisibility, ViewSheet,
)
from Autodesk.Revit.UI import PostableCommand, RevitCommandId
from System.Collections.Generic import List


def revisoes_do_projeto(doc):
    """[Revision, ...] em ordem de sequência."""
    saida = []
    try:
        for rid in Revision.GetAllRevisionIds(doc):
            rev = doc.GetElement(rid)
            if rev is not None:
                saida.append(rev)
    except Exception:
        pass
    saida.sort(key=lambda r: r.SequenceNumber)
    return saida


def folhas_do_projeto(doc):
    """[ViewSheet, ...] (sem folhas-modelo), ordenadas por número."""
    saida = []
    for folha in FilteredElementCollector(doc).OfClass(ViewSheet).ToElements():
        try:
            if folha.IsTemplate:
                continue
        except Exception:
            pass
        saida.append(folha)
    saida.sort(key=lambda f: (f.SheetNumber or u"", f.Name or u""))
    return saida


def revisoes_da_folha(folha):
    """set(ElementId.IntegerValue) das revisões que a folha já tem (nuvem
    física na folha OU incluída como "additional")."""
    ids = set()
    try:
        for i in folha.GetAllRevisionIds():
            ids.add(i.IntegerValue)
    except Exception:
        pass
    return ids


def aplicar_remover_revisoes(doc, folhas, ids_revisao, adicionar):
    """Aplica (adicionar=True) ou remove (adicionar=False) as revisões
    'ids_revisao' (ElementId) nas 'folhas' dadas, via
    GetAdditionalRevisionIds/SetAdditionalRevisionIds.

    Retorna (alteradas, ignoradas, falhas) - contagens de folhas, mesma
    lógica já validada em produção no ExportarPranchas."""
    alteradas, ignoradas, falhas = 0, 0, 0
    for folha in folhas:
        try:
            atuais = [i for i in folha.GetAdditionalRevisionIds()]
            tinha = set(i.IntegerValue for i in atuais)
            mudou = False
            for rid in ids_revisao:
                if adicionar:
                    if rid.IntegerValue in tinha:
                        ignoradas += 1
                        continue
                    atuais.append(rid)
                    tinha.add(rid.IntegerValue)
                    mudou = True
                else:
                    if rid.IntegerValue not in tinha:
                        ignoradas += 1
                        continue
                    atuais = [i for i in atuais if i.IntegerValue != rid.IntegerValue]
                    tinha.discard(rid.IntegerValue)
                    mudou = True
            if not mudou:
                continue
            novos = List[ElementId]()
            for i in atuais:
                novos.Add(i)
            folha.SetAdditionalRevisionIds(novos)
            alteradas += 1
        except Exception:
            falhas += 1
    return alteradas, ignoradas, falhas


# ---- visibilidade da revisão (PROJETO INTEIRO - ver aviso no topo do arquivo) ----

VISIBILIDADE_ROTULO = {
    RevisionVisibility.CloudAndTagVisible: u"Nuvem e tag visíveis (projeto inteiro)",
    RevisionVisibility.TagVisible: u"Só a tag visível (projeto inteiro)",
    RevisionVisibility.Hidden: u"Oculta em todo o projeto",
}

VISIBILIDADE_OPCOES = (
    RevisionVisibility.CloudAndTagVisible,
    RevisionVisibility.TagVisible,
    RevisionVisibility.Hidden,
)


def definir_visibilidade(revisao, visibilidade):
    """Define Revision.Visibility - vale para TODAS as folhas do projeto
    que tiverem essa revisão, não só uma (a API não permite por folha)."""
    revisao.Visibility = visibilidade


def abrir_dialogo_revisoes_nativo(uiapp):
    """Abre a tela nativa do Revit (Gerenciar > Revisões) via comando
    postável - evita reimplementar criação/edição de revisão (número,
    data, descrição, emitido por/para), que o Revit já resolve bem."""
    id_comando = RevitCommandId.LookupPostableCommandId(
        PostableCommand.SheetIssuesOrRevisions)
    uiapp.PostCommand(id_comando)
