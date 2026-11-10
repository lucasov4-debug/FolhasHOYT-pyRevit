# -*- coding: utf-8 -*-
"""Motor que cria e gerencia folhas.

Criação em lote, duas fases, na ordem certa:

  1) planejar_numeros() - so' leitura + calculo, nenhuma escrita no
     modelo. Da o numero de cada folha do lote, ja unico contra as folhas
     que existem no projeto E contra as outras folhas do MESMO lote (nao
     basta conferir uma por uma contra o projeto - a segunda folha do
     lote tambem nao pode repetir o numero da primeira).

  2) criar_folhas() - escreve de verdade: 1 ViewSheet por linha, com o
     parametro Tag_Disciplina_<codigo> certo marcado (so' 1 por folha),
     legenda da disciplina (se configurada) e o parametro "Tipo de
     Projeto" (se configurado). Antes de criar o lote inteiro,
     checar_parametros_disciplina() cria UMA folha de sonda com o tipo de
     titulo escolhido para conferir se a familia tem o parametro de cada
     disciplina pedida - se faltar alguma, o chamador desfaz a transacao
     inteira e avisa (decisao Q16 do grilling: nunca gerar folha "muda",
     sem o carimbo certo).

Gerenciamento de folhas ja existentes (aba "Folhas", pedido em
19/09/2026): excluir_folhas, duplicar_folha (com/sem detalhamento, mesma
tecnica de vista de lib/ambientes/folhas.py:_copiar_anotacoes, reescrita
aqui porque cada ferramenta mantem seu proprio lib), trocar_tipo_titulo.

Precisa de transacao aberta por quem chama - mesma convencao de
lib/ambientes/folhas.py.
"""
from Autodesk.Revit.DB import (
    BuiltInCategory, CopyPasteOptions, ElementId, ElementTransformUtils,
    FilteredElementCollector, Transform, ViewDuplicateOption, Viewport,
    ViewSheet, XYZ,
)
from System.Collections.Generic import List

from . import disciplinas as disc
from . import numeracao


def numeros_existentes(doc):
    numeros = set()
    for folha in FilteredElementCollector(doc).OfClass(ViewSheet).ToElements():
        try:
            if folha.IsTemplate:
                continue
            numeros.add(folha.SheetNumber)
        except Exception:
            pass
    return numeros


def nomes_existentes(doc):
    nomes = set()
    for folha in FilteredElementCollector(doc).OfClass(ViewSheet).ToElements():
        try:
            if folha.IsTemplate:
                continue
            nomes.add(folha.Name)
        except Exception:
            pass
    return nomes


def nome_unico(nome, ocupados):
    """'nome', ou 'nome (2)', 'nome (3)'... - o Revit recusa nome repetido
    de folha (mesma regra de lib/ambientes/nomes.py:unico)."""
    if nome not in ocupados:
        return nome
    contador = 2
    while u"%s (%d)" % (nome, contador) in ocupados:
        contador += 1
    return u"%s (%d)" % (nome, contador)


def planejar_numeros(doc, codigo_disciplina, quantidade, padrao_disciplina):
    """([numero_1, numero_2, ...], proximo_numero_livre) - so' leitura."""
    ocupados = numeros_existentes(doc)
    prefixo = (padrao_disciplina or {}).get(u"prefixo") or codigo_disciplina
    numero_sugerido = (padrao_disciplina or {}).get(u"proximo_numero") or 101

    numeros = []
    for _ in range(quantidade):
        codigo, numero = numeracao.numero_unico(prefixo, numero_sugerido, ocupados)
        ocupados.add(codigo)
        numeros.append(codigo)
        numero_sugerido = numero + 1
    return numeros, numero_sugerido


def instancia_titulo_da_folha(doc, folha):
    """A instância do carimbo (título) colada nesta folha, ou None."""
    for instancia in (FilteredElementCollector(doc, folha.Id)
                      .OfCategory(BuiltInCategory.OST_TitleBlocks)
                      .WhereElementIsNotElementType().ToElements()):
        return instancia
    return None


def _normalizar_nome_parametro(nome):
    texto = (nome or u"").strip().lower()
    if u"(" in texto:
        texto = texto.split(u"(")[0].strip()
    return texto


def achar_parametro_por_nome(elemento, nome):
    """Parameter do elemento cujo nome bate com 'nome' (tolerante a
    maiúsculas/minúsculas e a sufixo decorativo tipo "(padrão)") - versão
    genérica de disciplinas.achar_parametro_disciplina, para parâmetros
    que não seguem o padrão Tag_Disciplina_*, como "Tipo de Projeto"."""
    alvo = _normalizar_nome_parametro(nome)
    try:
        parametros = elemento.Parameters
    except Exception:
        return None
    for p in parametros:
        try:
            if _normalizar_nome_parametro(p.Definition.Name) == alvo:
                return p
        except Exception:
            continue
    return None


def definir_tipo_de_projeto(instancia_titulo, texto):
    """Preenche o parâmetro de texto "Tipo de Projeto" do carimbo, se a
    família tiver esse parâmetro e um valor tiver sido configurado na aba
    Padrões (Lucas, 19/09/2026: esse parâmetro separa as pranchas por
    tipo de projeto)."""
    if not texto:
        return
    p = achar_parametro_por_nome(instancia_titulo, u"Tipo de Projeto")
    if p is None:
        return
    try:
        p.Set(texto)
    except Exception:
        pass


def detectar_disciplinas(doc, tipo_titulo):
    """[(codigo, nome_parametro), ...] - todas as disciplinas que a
    família deste tipo de título realmente tem, descobertas criando uma
    folha de sonda e lendo os parâmetros da instância do carimbo.

    NÃO apaga a sonda nem faz commit/rollback sozinha - quem chama decide
    (normalmente um RollBack, já que isto é só para ler e popular a
    interface, a sonda nunca deve ficar no projeto)."""
    try:
        sonda = ViewSheet.Create(doc, tipo_titulo.Id)
    except Exception:
        return []
    instancia = instancia_titulo_da_folha(doc, sonda)
    if instancia is None:
        return []
    return disc.disciplinas_do_elemento(instancia)


def checar_parametros_disciplina(doc, tipo_titulo, codigos):
    """Cria uma folha de sonda com este tipo de titulo, confere se o
    parametro Tag_Disciplina_<codigo> existe na instancia do carimbo para
    cada codigo pedido, apaga a folha de sonda e devolve
    (codigos_faltando, mensagem_erro).

    Chamar isto ANTES de criar o lote de verdade, dentro da MESMA
    transacao - se vier algo faltando, o chamador desfaz tudo (RollBack)
    e avisa quais disciplinas a familia ainda nao suporta."""
    try:
        sonda = ViewSheet.Create(doc, tipo_titulo.Id)
    except Exception as ex:
        return list(codigos), u"não consegui criar uma folha de teste com este título: %s" % ex

    instancia = instancia_titulo_da_folha(doc, sonda)
    if instancia is None:
        faltando = list(codigos)
    else:
        faltando = disc.parametros_disciplina_faltando(instancia, codigos)

    try:
        doc.Delete(sonda.Id)
    except Exception:
        pass
    return faltando, None


def colocar_legenda(doc, folha, legenda_view, ponto=None):
    """Coloca a vista de legenda dada na folha - legendas (diferente de
    vistas normais) podem estar em várias folhas ao mesmo tempo, então
    isto não "rouba" a legenda de outra folha. Posição padrão é só um
    chute conservador (canto inferior esquerdo do papel) - o usuário
    arrasta depois se quiser noutro lugar."""
    if legenda_view is None:
        return False
    try:
        if not Viewport.CanAddViewToSheet(doc, folha.Id, legenda_view.Id):
            return False
        Viewport.Create(doc, folha.Id, legenda_view.Id, ponto or XYZ(0.5, 0.5, 0.0))
        return True
    except Exception:
        return False


def criar_folhas(doc, tipo_titulo, linhas, legendas_por_disciplina=None, tipo_projeto_por_disciplina=None):
    """linhas: [{'disciplina': 'HID', 'numero': 'HID-101', 'nome': '...'}, ...]
    tipo_titulo: ElementType (FamilySymbol) de titulo, ja Activate()-ado se
    precisar. legendas_por_disciplina: {'HID': View, ...} opcional -
    coloca essa legenda em toda folha daquela disciplina.
    tipo_projeto_por_disciplina: {'HID': 'texto', ...} opcional - valor a
    preencher no parâmetro de texto "Tipo de Projeto" do carimbo, POR
    disciplina (não é um valor global - Lucas, 19/09/2026).

    Retorna (criadas, falhas): criadas = [ViewSheet, ...] na mesma ordem
    de 'linhas'; falhas = [(linha, motivo), ...] das que deram problema
    (a folha ainda pode ter sido criada parcialmente - numero ou nome
    inválido não desfaz a criação da folha em si)."""
    criadas = []
    falhas = []
    for linha in linhas:
        try:
            folha = ViewSheet.Create(doc, tipo_titulo.Id)
        except Exception as ex:
            falhas.append((linha, u"não consegui criar a folha: %s" % ex))
            continue

        try:
            folha.SheetNumber = linha[u"numero"]
        except Exception as ex:
            falhas.append((linha, u"número inválido ou já usado: %s" % ex))
        try:
            folha.Name = linha[u"nome"]
        except Exception as ex:
            falhas.append((linha, u"nome inválido ou já usado: %s" % ex))

        instancia = instancia_titulo_da_folha(doc, folha)
        if instancia is not None:
            disc.marcar_disciplina(instancia, linha[u"disciplina"])
            texto_tipo_projeto = (tipo_projeto_por_disciplina or {}).get(linha[u"disciplina"])
            definir_tipo_de_projeto(instancia, texto_tipo_projeto)

        if legendas_por_disciplina:
            colocar_legenda(doc, folha, legendas_por_disciplina.get(linha[u"disciplina"]))

        criadas.append(folha)
    return criadas, falhas


# ============================================================
# GERENCIAMENTO DE FOLHAS JÁ EXISTENTES (aba "Folhas")
# ============================================================

def excluir_folhas(doc, folhas):
    """Apaga as folhas dadas. As vistas que estavam colocadas nelas NÃO
    são apagadas - só ficam sem folha (o Revit não apaga conteúdo junto).
    Retorna (apagadas, falhas)."""
    apagadas = 0
    falhas = []
    for folha in folhas:
        try:
            doc.Delete(folha.Id)
            apagadas += 1
        except Exception as ex:
            falhas.append((folha, str(ex)))
    return apagadas, falhas


def trocar_tipo_titulo(doc, folhas, novo_tipo_id):
    """Troca o tipo do título (carimbo) das folhas dadas para novo_tipo_id
    via Element.ChangeTypeId - o Revit preserva os parâmetros de
    instância compatíveis entre os dois tipos. Retorna (trocadas, falhas)
    - falhas = [(folha, motivo), ...]."""
    trocadas = 0
    falhas = []
    for folha in folhas:
        instancia = instancia_titulo_da_folha(doc, folha)
        if instancia is None:
            falhas.append((folha, u"folha sem título"))
            continue
        try:
            instancia.ChangeTypeId(novo_tipo_id)
            trocadas += 1
        except Exception as ex:
            falhas.append((folha, str(ex)))
    return trocadas, falhas


def _copiar_anotacoes_soltas(doc, folha_origem, folha_nova):
    """Copia da folha de origem tudo que NÃO é viewport nem título -
    textos, linhas de detalhe, legendas, símbolos soltos. Mesma ideia de
    lib/ambientes/folhas.py:_copiar_anotacoes, reescrita aqui (cada
    ferramenta mantém seu próprio lib, sem importar entre pacotes)."""
    ids = List[ElementId]()
    for elemento in FilteredElementCollector(doc, folha_origem.Id).ToElements():
        try:
            if isinstance(elemento, Viewport):
                continue
            categoria = elemento.Category
            if categoria is None:
                continue
            if categoria.Id.IntegerValue == int(BuiltInCategory.OST_TitleBlocks):
                continue
        except Exception:
            continue
        ids.Add(elemento.Id)
    if ids.Count == 0:
        return
    try:
        ElementTransformUtils.CopyElements(
            folha_origem, ids, folha_nova, Transform.Identity, CopyPasteOptions())
    except Exception:
        pass


def duplicar_folha(doc, folha_origem, novo_numero, novo_nome, com_detalhamento):
    """Cria uma folha nova com o MESMO tipo de título da folha de origem,
    duplicando (com ou sem detalhamento, ViewDuplicateOption nativo) cada
    vista colocada nela e recolocando na mesma posição. "Com
    detalhamento" também copia anotações soltas da folha (textos, linhas,
    legendas).

    Retorna (folha_nova, avisos) - avisos = [texto, ...] de vistas que não
    puderam ser duplicadas/recolocadas (a folha ainda sai criada mesmo
    assim, só sem aquela vista)."""
    instancia_origem = instancia_titulo_da_folha(doc, folha_origem)
    if instancia_origem is None:
        return None, [u"a folha de origem não tem título - não dá para saber que tipo de título usar."]
    tipo_id = instancia_origem.GetTypeId()

    try:
        nova = ViewSheet.Create(doc, tipo_id)
    except Exception as ex:
        return None, [u"não consegui criar a folha: %s" % ex]
    try:
        nova.SheetNumber = novo_numero
    except Exception as ex:
        return nova, [u"número inválido ou já usado: %s" % ex]
    try:
        nova.Name = novo_nome
    except Exception as ex:
        return nova, [u"nome inválido ou já usado: %s" % ex]

    opcao = ViewDuplicateOption.WithDetailing if com_detalhamento else ViewDuplicateOption.Duplicate
    avisos = []
    for viewport in (FilteredElementCollector(doc, folha_origem.Id)
                     .OfClass(Viewport).ToElements()):
        vista_original = doc.GetElement(viewport.ViewId)
        if vista_original is None:
            continue
        nome_vista = getattr(vista_original, u"Name", u"?")
        try:
            if not vista_original.CanViewBeDuplicated(opcao):
                avisos.append(u"a vista \"%s\" não pode ser duplicada." % nome_vista)
                continue
            novo_id = vista_original.Duplicate(opcao)
        except Exception as ex:
            avisos.append(u"a vista \"%s\" não pôde ser duplicada: %s" % (nome_vista, ex))
            continue

        vista_nova = doc.GetElement(novo_id)
        try:
            centro = viewport.GetBoxCenter()
            if not Viewport.CanAddViewToSheet(doc, nova.Id, vista_nova.Id):
                avisos.append(u"a cópia da vista \"%s\" não coube na folha nova." % nome_vista)
                continue
            Viewport.Create(doc, nova.Id, vista_nova.Id, centro)
        except Exception as ex:
            avisos.append(u"não consegui posicionar a cópia da vista \"%s\": %s" % (nome_vista, ex))

    if com_detalhamento:
        _copiar_anotacoes_soltas(doc, folha_origem, nova)

    return nova, avisos
