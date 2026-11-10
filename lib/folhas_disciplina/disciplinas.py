# -*- coding: utf-8 -*-
"""Disciplinas do carimbo SYNC e seus parametros Tag_Disciplina_*.

A familia de titulo (unica, com todos os checkboxes - decisao confirmada
pelo Lucas em 18/09/2026, grilling do Gerenciador de Folhas) tem um
parametro por disciplina. O nome exato foge do padrao de duas formas
confirmadas na tela de Propriedades:
  1) capitalizacao livre ("Tag_Disciplina_Gas", nao "..._GAS");
  2) sufixo "(padrão)" depois do nome, em algumas capturas de tela (nem
     sempre presente).

[19/09/2026] BUG ENCONTRADO E CORRIGIDO: so' apareciam ALGUMAS
disciplinas na lista, nunca todas as ~8 da familia real. Motivo: a tela
de Propriedades de uma instancia mostra junto parametros de INSTANCIA e
de TIPO (FamilySymbol) - o Revit nao distingue visualmente os dois ali.
`instancia.Parameters` sozinho so' devolve os de instancia; os de tipo
ficavam de fora. A busca agora percorre os dois (`_parametros_de`).

CUIDADO (documentado, nao contornavel): se algum Tag_Disciplina_<codigo>
for de TIPO (nao de instancia), marca-lo com marcar_disciplina() muda
TODAS as folhas que usam aquele mesmo tipo de titulo, nao so' a folha em
edicao - e' comportamento nativo do Revit para parametro de tipo, a API
nao tem como fazer diferente. Vale testar com uma folha isolada antes de
confiar em lote.

A familia real tem MAIS disciplinas do que os 5 códigos originalmente
pedidos (AF, AF/AQ, CLI, EST tambem existem) - por isso a lista de
disciplinas disponiveis NUNCA e fixada em codigo: e sempre descoberta na
hora, lendo os parametros de uma instancia real de titulo
(disciplinas_do_elemento).

A busca de parametro e sempre por nome (nunca por posicao ou ordem na
lista) - mesma regra de "nao adivinhar propriedade" da memoria de
filtro/visibilidade.

So um checkbox marcado por folha (Q1 do grilling): marcar uma disciplina
desliga todas as outras que existirem na familia.
"""

import re

# rotulos humanos so' para as disciplinas ja conhecidas - qualquer outro
# codigo encontrado na familia (disciplinas_do_elemento) tambem funciona
# normalmente, so' aparece com o proprio codigo como rotulo (ver rotulo()).
DISCIPLINAS = (
    (u"ESG", u"Esgoto"),
    (u"HID", u"Hidrossanitário"),
    (u"GAS", u"Gás"),
    (u"ELE", u"Elétrico"),
    (u"FUR", u"Furação"),
    (u"AF", u"Água Fria"),
    (u"AF/AQ", u"Água Fria/Água Quente"),
    (u"CLI", u"Climatização"),
    (u"EST", u"Estrutura"),
)

CODIGOS = [codigo for codigo, _ in DISCIPLINAS]

# "Tag_Disciplina_ESG", "Tag_Disciplina_ESG (padrão)", "tag_disciplina_af/aq"
# ... tudo isso tem que casar. O que vem depois do codigo, entre
# parenteses, e' decoracao da tela de Propriedades - descartado.
_PADRAO_NOME = re.compile(u"^tag_disciplina_(.+?)(?:\\s*\\(.*\\))?$", re.UNICODE)


def rotulo(codigo):
    """'HID - Hidrossanitário', ou o próprio código se ainda não tiver
    rótulo humano cadastrado (disciplina nova, descoberta na família)."""
    for c, nome in DISCIPLINAS:
        if c == codigo:
            return u"%s - %s" % (c, nome)
    return codigo


def _codigo_do_nome_parametro(nome):
    """'Tag_Disciplina_AF/AQ (padrão)' -> 'AF/AQ'; None se o nome não
    seguir o padrão Tag_Disciplina_*."""
    if not nome:
        return None
    m = _PADRAO_NOME.match(nome.strip().lower())
    if not m:
        return None
    return m.group(1).strip().upper()


def _parametros_de(elemento):
    """Todos os parâmetros a considerar - da instância E do próprio tipo
    (FamilySymbol), porque a tela de Propriedades mistura os dois sob o
    mesmo grupo "Texto" e a família real usa as duas formas. `elemento`
    aqui é sempre uma INSTÂNCIA (FamilyInstance); `.Symbol` dá o tipo."""
    vistos_ids = set()
    fontes = [elemento]
    try:
        tipo = elemento.Symbol
        if tipo is not None:
            fontes.append(tipo)
    except Exception:
        pass
    for fonte in fontes:
        try:
            parametros = fonte.Parameters
        except Exception:
            continue
        for p in parametros:
            try:
                chave = p.Id.IntegerValue
            except Exception:
                chave = id(p)
            if chave in vistos_ids:
                continue
            vistos_ids.add(chave)
            yield p


def achar_parametro_disciplina(elemento, codigo):
    """O Parameter Tag_Disciplina_<codigo> do elemento (instância OU tipo -
    comparando pelo código extraído do nome, tolera "(padrão)" e
    maiúsculas/minúsculas), ou None se a família ainda não tiver esse
    parâmetro (família desatualizada - ver parametros_disciplina_faltando)."""
    alvo = (codigo or u"").strip().upper()
    for p in _parametros_de(elemento):
        try:
            nome = p.Definition.Name
        except Exception:
            continue
        if _codigo_do_nome_parametro(nome) == alvo:
            return p
    return None


def disciplinas_do_elemento(elemento):
    """[(codigo, nome_parametro_original), ...] - TODAS as disciplinas que
    esta instância de título realmente tem (instância + tipo), na ordem
    em que os parâmetros aparecem. Não filtra pelos códigos conhecidos:
    mostra tudo que a família tiver hoje - nunca esconder uma disciplina
    que a família já suporta."""
    achadas = []
    vistos = set()
    for p in _parametros_de(elemento):
        try:
            nome = p.Definition.Name
        except Exception:
            continue
        codigo = _codigo_do_nome_parametro(nome)
        if codigo is None or codigo in vistos:
            continue
        vistos.add(codigo)
        achadas.append((codigo, nome))
    return achadas


def disciplina_marcada(elemento):
    """Código da disciplina marcada (valor 1) nesta instância de título, ou
    None se nenhuma estiver marcada - usado para mostrar a disciplina de
    uma folha já criada (aba Revisões/Folhas), sem supor uma lista fixa
    de códigos possíveis."""
    for p in _parametros_de(elemento):
        try:
            nome = p.Definition.Name
        except Exception:
            continue
        codigo = _codigo_do_nome_parametro(nome)
        if codigo is None:
            continue
        try:
            if p.AsInteger() == 1:
                return codigo
        except Exception:
            continue
    return None


def parametros_disciplina_faltando(elemento, codigos):
    """[codigo, ...] das disciplinas pedidas cujo parâmetro
    Tag_Disciplina_<código> não existe no elemento - usado para BLOQUEAR a
    criação do lote com aviso claro (decisão Q16 do grilling) em vez de
    gerar folha "muda", sem o carimbo certo."""
    faltando = []
    for codigo in codigos:
        if achar_parametro_disciplina(elemento, codigo) is None:
            faltando.append(codigo)
    return faltando


def marcar_disciplina(instancia_titulo, codigo_escolhido, todos_codigos=None):
    """Só 1 checkbox marcado por folha: o escolhido vira Sim/True, os
    outros que existirem na família viram Não/False. Sem 'todos_codigos'
    dado, descobre sozinho quais disciplinas a instância tem.

    ATENÇÃO: se o parâmetro de alguma disciplina for de TIPO (não de
    instância), isto muda TODAS as folhas que usam o mesmo tipo de
    título - limitação do Revit, não deste plugin."""
    if todos_codigos is None:
        todos_codigos = [c for c, _ in disciplinas_do_elemento(instancia_titulo)]
    for codigo in todos_codigos:
        p = achar_parametro_disciplina(instancia_titulo, codigo)
        if p is None:
            continue
        try:
            p.Set(1 if codigo == codigo_escolhido else 0)
        except Exception:
            pass
