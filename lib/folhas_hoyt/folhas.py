# -*- coding: utf-8 -*-
"""Folhas: listar, duplicar (mesmos parametros + legenda), trocar a
legenda em lote, renumerar/renomear em lote."""
from Autodesk.Revit.DB import (
    BuiltInCategory, BuiltInParameter, FilteredElementCollector, ScheduleSheetInstance,
    StorageType, SubTransaction, Transaction, TransactionStatus, View, ViewSheet,
    ViewType, Viewport, XYZ,
)

from . import destaque, eid, nome, regras, texto

_PULAR = (BuiltInParameter.SHEET_NUMBER, BuiltInParameter.SHEET_NAME)


# ------------------------------------------------------------ leitura
def todas(doc):
    folhas = [f for f in FilteredElementCollector(doc).OfClass(ViewSheet).ToElements()
              if not f.IsPlaceholder]
    folhas.sort(key=lambda f: f.SheetNumber)
    return folhas


def indice(doc):
    """Carimbos e viewports de TODAS as folhas em duas passadas (um coletor
    por folha e' o que deixava as abas lentas). So' para leitura em massa:
    depois de alterar o projeto, gere de novo."""
    carimbos, vps = {}, {}
    for inst in (FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_TitleBlocks)
                 .WhereElementIsNotElementType().ToElements()):
        carimbos.setdefault(eid(inst.OwnerViewId), inst)
    for vp in FilteredElementCollector(doc).OfClass(Viewport).ToElements():
        vps.setdefault(eid(vp.SheetId), []).append(vp)
    return {u'carimbos': carimbos, u'viewports': vps, u'tipos_de_vista': {}}


def viewports_da_folha(doc, folha, idx=None):
    if idx is not None:
        return idx[u'viewports'].get(eid(folha.Id), [])
    return [doc.GetElement(vid) for vid in folha.GetAllViewports()]


def carimbo(doc, folha, idx=None):
    if idx is not None:
        return idx[u'carimbos'].get(eid(folha.Id))
    for inst in (FilteredElementCollector(doc, folha.Id)
                 .OfCategory(BuiltInCategory.OST_TitleBlocks)
                 .WhereElementIsNotElementType().ToElements()):
        return inst
    return None


def tipo_do_carimbo(doc, folha, idx=None):
    c = carimbo(doc, folha, idx)
    if c is None:
        return u''
    try:
        t = doc.GetElement(c.GetTypeId())
        return u'%s : %s' % (texto(t.FamilyName), nome(t))
    except Exception:
        return u'?'


def legendas_da_folha(doc, folha, idx=None):
    """[Viewport] das legendas colocadas na folha."""
    saida = []
    for vp in viewports_da_folha(doc, folha, idx):
        try:
            if idx is not None:
                cache = idx[u'tipos_de_vista']
                k = eid(vp.ViewId)
                if k not in cache:
                    cache[k] = doc.GetElement(vp.ViewId).ViewType
                tipo = cache[k]
            else:
                tipo = doc.GetElement(vp.ViewId).ViewType
            if tipo == ViewType.Legend:
                saida.append(vp)
        except Exception:
            continue
    return saida


def nome_legendas(doc, folha, idx=None):
    return u'; '.join(nome(doc.GetElement(vp.ViewId)) for vp in legendas_da_folha(doc, folha, idx))

def legendas_do_projeto(doc):
    saida = []
    for v in FilteredElementCollector(doc).OfClass(View).ToElements():
        try:
            if not v.IsTemplate and v.ViewType == ViewType.Legend:
                saida.append(v)
        except Exception:
            continue
    saida.sort(key=lambda v: nome(v).lower())
    return saida


# ------------------------------------------------------------ copia de parametros
def copiar_parametros(origem, destino, mapa_nomes=True):
    """Copia os parametros de instancia editaveis de origem para destino
    (mesmo nome). Devolve (copiados, pulados[nomes])."""
    copiados, pulados = 0, []
    for p in origem.Parameters:
        try:
            if p.IsReadOnly or not p.HasValue:
                continue
            try:
                if p.Definition.BuiltInParameter in _PULAR:
                    continue
            except Exception:
                pass
            nome_p = p.Definition.Name
            alvo = destino.LookupParameter(nome_p)
            if alvo is None or alvo.IsReadOnly or alvo.StorageType != p.StorageType:
                pulados.append(nome_p)
                continue
            st = p.StorageType
            if st == StorageType.String:
                alvo.Set(p.AsString() or u'')
            elif st == StorageType.Integer:
                alvo.Set(p.AsInteger())
            elif st == StorageType.Double:
                alvo.Set(p.AsDouble())
            elif st == StorageType.ElementId:
                if origem.Document.Equals(destino.Document):
                    alvo.Set(p.AsElementId())
                else:
                    pulados.append(nome_p)
                    continue
            copiados += 1
        except Exception:
            try:
                pulados.append(p.Definition.Name)
            except Exception:
                pass
    return copiados, pulados


# ------------------------------------------------------------ duplicar
def deslocamento(doc, folha_origem, folha_nova):
    """XYZ que leva um ponto da folha de origem para o mesmo ponto RELATIVO ao
    carimbo da folha nova (carimbo da origem pode nao estar na origem da folha)."""
    a = carimbo(doc, folha_origem)
    b = carimbo(folha_nova.Document, folha_nova)
    if a is None or b is None:
        return XYZ(0, 0, 0)
    ba, bb = a.get_BoundingBox(folha_origem), b.get_BoundingBox(folha_nova)
    if ba is None or bb is None:
        return XYZ(0, 0, 0)
    return XYZ(bb.Min.X - ba.Min.X, bb.Min.Y - ba.Min.Y, 0)


def _legenda_para(doc, folha_origem, folha_nova, vista_destino_de=None, delta=None):
    """Poe em folha_nova as legendas de folha_origem (mesma posicao, tipo de
    viewport e rotacao). vista_destino_de(view) -> View do documento da nova
    folha (None = a mesma). Devolve (n, falhas)."""
    n, falhas = 0, []
    for vp in legendas_da_folha(doc, folha_origem):
        try:
            vista = doc.GetElement(vp.ViewId)
            if vista_destino_de is not None:
                vista = vista_destino_de(vista)
            docn = folha_nova.Document
            novo = Viewport.Create(docn, folha_nova.Id, vista.Id,
                                    vp.GetBoxCenter().Add(delta) if delta is not None else vp.GetBoxCenter())
            try:
                tipo = doc.GetElement(vp.GetTypeId())
                if docn.Equals(doc):
                    novo.ChangeTypeId(vp.GetTypeId())
                else:
                    for t in FilteredElementCollector(docn).WhereElementIsElementType().ToElements():
                        if texto(getattr(t, 'FamilyName', u'')) == u'Viewport' and nome(t) == nome(tipo):
                            novo.ChangeTypeId(t.Id)
                            break
            except Exception:
                pass
            try:
                novo.Rotation = vp.Rotation
            except Exception:
                pass
            n += 1
        except Exception as ex:
            falhas.append(u'legenda %s: %s' % (nome(doc.GetElement(vp.ViewId)), texto(ex)))
    return n, falhas


def _tabelas_para(doc, folha_origem, folha_nova, delta=None):
    n, falhas = 0, []
    for inst in FilteredElementCollector(doc, folha_origem.Id).OfClass(ScheduleSheetInstance).ToElements():
        try:
            if inst.IsTitleblockRevisionSchedule:
                continue
            ScheduleSheetInstance.Create(doc, folha_nova.Id, inst.ScheduleId,
                                         inst.Point.Add(delta) if delta is not None else inst.Point)
            n += 1
        except Exception as ex:
            falhas.append(u'tabela %s: %s' % (nome(inst), texto(ex)))
    return n, falhas


def duplicar(doc, folhas, sufixo=u'-COPIA'):
    """Cria uma folha nova para cada uma (sem vistas): mesmo carimbo,
    mesmos parametros da folha e do carimbo, legendas e tabelas na mesma
    posicao. Devolve (criadas[(origem, nova)], avisos). Uma transacao so'."""
    ocupados = set(f.SheetNumber for f in todas(doc))
    criadas, avisos = [], []
    t = Transaction(doc, u'Folhas HOYT - duplicar folhas (%d)' % len(folhas))
    t.Start()
    try:
        for f in folhas:
            sub = SubTransaction(doc)
            sub.Start()
            try:
                c = carimbo(doc, f)
                if c is None:
                    raise Exception(u'a folha não tem carimbo')
                nova = ViewSheet.Create(doc, c.GetTypeId())
                num = regras.numero_livre(f.SheetNumber, ocupados, sufixo)
                ocupados.add(num)
                nova.SheetNumber = num
                nova.Name = f.Name
                doc.Regenerate()        # o carimbo novo so' aparece depois (ver Montar Folhas)
                _ok, pul = copiar_parametros(f, nova)
                cn = carimbo(doc, nova)
                if cn is None:
                    raise Exception(u'o carimbo da folha nova não foi criado')
                _ok2, pul2 = copiar_parametros(c, cn)
                pul = pul + pul2
                doc.Regenerate()        # tamanho do carimbo copiado antes de por a legenda
                if pul:
                    avisos.append(u'%s: não copiou %s' % (num, u', '.join(sorted(set(pul)))))
                delta = deslocamento(doc, f, nova)
                _n, f1 = _legenda_para(doc, f, nova, None, delta)
                _n2, f2 = _tabelas_para(doc, f, nova, delta)
                for a in f1 + f2:
                    avisos.append(u'%s: %s' % (num, a))
                sub.Commit()
                criadas.append((f, nova))
            except Exception as ex:
                sub.RollBack()
                avisos.append(u'%s: não duplicou (%s)' % (f.SheetNumber, texto(ex)))
        t.Commit()
        destaque.registrar(doc, [n.UniqueId for _o, n in criadas])
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return criadas, avisos


def _proximo_numero(num, ocupados):
    """Primeiro numero livre a partir de `num`, somando 1 aos digitos finais
    (HID-09 -> HID-10); sem digitos no fim, acrescenta -2, -3..."""
    import re
    m = re.match(r'^(.*?)(\d+)$', num)
    cand, k = num, 1
    while cand in ocupados:
        if m:
            cand = u'%s%0*d' % (m.group(1), len(m.group(2)), int(m.group(2)) + k)
        else:
            cand = u'%s-%d' % (num, k + 1)
        k += 1
    return cand


def criar(doc, simbolo, qtd, numero_inicial, nome_folha):
    """Cria `qtd` folhas em branco com o tipo de carimbo `simbolo`.
    Devolve (criadas[ViewSheet], avisos). Uma transacao so'."""
    ocupados = set(f.SheetNumber for f in todas(doc))
    criadas, avisos = [], []
    t = Transaction(doc, u'Folhas HOYT - criar folhas (%d)' % qtd)
    t.Start()
    try:
        if not simbolo.IsActive:
            simbolo.Activate()
            doc.Regenerate()
        atual = numero_inicial
        for _ in range(qtd):
            sub = SubTransaction(doc)
            sub.Start()
            try:
                num = _proximo_numero(atual, ocupados)
                nova = ViewSheet.Create(doc, simbolo.Id)
                nova.SheetNumber = num
                nova.Name = nome_folha
                ocupados.add(num)
                atual = num
                sub.Commit()
                criadas.append(nova)
            except Exception as ex:
                sub.RollBack()
                avisos.append(u'%s: não criou (%s)' % (atual, texto(ex)))
        t.Commit()
        destaque.registrar(doc, [n.UniqueId for n in criadas])
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return criadas, avisos


# parametros de instancia do carimbo que definem o tamanho da folha
PARAMS_TAMANHO = (u'Altura', u'Largura', u'Altura da folha', u'Largura da folha',
                  u'Sheet Height', u'Sheet Width')


def ajustar_tamanho(doc, padrao, lista_folhas):
    """Copia da folha `padrao` SO' o tamanho (parametros PARAMS_TAMANHO da instancia
    do carimbo) para cada folha de lista_folhas. Nao troca o tipo, nao mexe em
    mais nenhum parametro, nas vistas, legendas ou tabelas. Devolve
    (ajustadas, avisos). Uma transacao so'."""
    ajustadas, avisos = 0, []
    ref = carimbo(doc, padrao)
    if ref is None:
        return 0, [u'a folha padrão não tem carimbo']
    valores = []                                   # (nome, posicao entre homonimos, StorageType, valor)
    for nome_p in PARAMS_TAMANHO:
        for k, p in enumerate(ref.GetParameters(nome_p)):      # GetParameters: pega tambem homonimos
            if not p.HasValue:
                continue
            st = p.StorageType
            v = p.AsDouble() if st == StorageType.Double else p.AsInteger() if st == StorageType.Integer else None
            if v is not None:
                valores.append((nome_p, k, st, v))
    if not valores:
        return 0, [u'o carimbo da folha padrão não tem os parâmetros de tamanho (%s)' % u', '.join(PARAMS_TAMANHO)]
    t = Transaction(doc, u'Folhas HOYT - ajustar tamanho pela folha %s (%d)' % (padrao.SheetNumber, len(lista_folhas)))
    t.Start()
    try:
        for f in lista_folhas:
            if eid(f.Id) == eid(padrao.Id):
                continue
            c = carimbo(doc, f)
            if c is None:
                avisos.append(u'%s: a folha não tem carimbo' % f.SheetNumber)
                continue
            feitos, falhas = [], []
            for nome_p, k, st, v in valores:
                alvos_p = list(c.GetParameters(nome_p))
                q = alvos_p[k] if k < len(alvos_p) else None
                if q is None or q.IsReadOnly or q.StorageType != st:
                    falhas.append(u'"%s" (inexistente ou somente leitura)' % nome_p)
                    continue
                try:
                    q.Set(v)
                    feitos.append(nome_p)
                except Exception as ex:
                    falhas.append(u'"%s": %s' % (nome_p, texto(ex)))
            if feitos:
                # parametros somente leitura (ex.: "Altura da folha", que o carimbo calcula
                # sozinho) nao sao problema quando Altura/Largura foram gravadas
                ajustadas += 1
            else:
                avisos.append(u'%s: não ajustou - %s' % (f.SheetNumber, u'; '.join(falhas)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return ajustadas, avisos


def mover_legendas(doc, lista_folhas, dx_cm, dy_cm):
    """Desloca todas as legendas das folhas dadas (dx_cm para a direita, dy_cm
    para cima; negativo = esquerda/baixo). Devolve (legendas_movidas, avisos).
    Uma transacao so'."""
    delta = XYZ(dx_cm / 30.48, dy_cm / 30.48, 0.0)
    n, avisos = 0, []
    t = Transaction(doc, u'Folhas HOYT - mover legendas (%d folhas)' % len(lista_folhas))
    t.Start()
    try:
        for f in lista_folhas:
            for vp in legendas_da_folha(doc, f):
                try:
                    fixa = bool(vp.Pinned)
                    if fixa:
                        vp.Pinned = False
                    vp.SetBoxCenter(vp.GetBoxCenter().Add(delta))
                    if fixa:
                        vp.Pinned = True
                    n += 1
                except Exception as ex:
                    avisos.append(u'%s: não moveu a legenda (%s)' % (f.SheetNumber, texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return n, avisos


def tamanho_atual(c):
    """(altura_cm, largura_cm) do carimbo `c` (None onde o parametro nao existe)."""
    saida = []
    for nomes in ((u'Altura', u'Altura da folha', u'Sheet Height'),
                  (u'Largura', u'Largura da folha', u'Sheet Width')):
        v = None
        for n in nomes:
            p = c.LookupParameter(n)
            if p is not None and p.HasValue and p.StorageType == StorageType.Double:
                v = p.AsDouble() * 30.48
                break
        saida.append(v)
    return tuple(saida)


def definir_tamanho(doc, itens):
    """itens = [(ViewSheet, altura_cm ou None, largura_cm ou None)]: grava no
    carimbo (parametros "Altura"/"Largura" de instancia). Devolve (n, avisos).
    Uma transacao so'."""
    n, avisos = 0, []
    t = Transaction(doc, u'Folhas HOYT - tamanho das folhas (%d)' % len(itens))
    t.Start()
    try:
        for f, alt, larg in itens:
            c = carimbo(doc, f)
            if c is None:
                avisos.append(u'%s: a folha não tem carimbo' % f.SheetNumber)
                continue
            ok = False
            for valor, nomes in ((alt, (u'Altura', u'Altura da folha', u'Sheet Height')),
                                 (larg, (u'Largura', u'Largura da folha', u'Sheet Width'))):
                if valor is None:
                    continue
                gravou = False
                for nm in nomes:
                    for p in c.GetParameters(nm):
                        if not p.IsReadOnly and p.StorageType == StorageType.Double:
                            p.Set(valor / 30.48)
                            gravou = True
                    if gravou:
                        break
                if gravou:
                    ok = True
                else:
                    avisos.append(u'%s: não deu para gravar %s (inexistente ou somente leitura)' % (f.SheetNumber, nomes[0]))
            if ok:
                n += 1
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return n, avisos


def apagar(doc, lista_folhas):
    """Apaga as folhas (e o que esta nelas: viewports, tabelas, carimbo; as
    vistas continuam no projeto). Devolve (apagadas, avisos)."""
    apagadas, avisos = 0, []
    t = Transaction(doc, u'Folhas HOYT - apagar folhas (%d)' % len(lista_folhas))
    t.Start()
    try:
        for f in lista_folhas:
            sub = SubTransaction(doc)
            sub.Start()
            try:
                num = f.SheetNumber
                doc.Delete(f.Id)
                sub.Commit()
                apagadas += 1
            except Exception as ex:
                sub.RollBack()
                avisos.append(u'%s: não apagou (%s)' % (num, texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return apagadas, avisos


# ------------------------------------------------------------ trocar a legenda
def legendas_em_comum(doc, lista_folhas):
    """[(View, em_quantas_folhas)] das legendas colocadas nas folhas dadas,
    as mais comuns primeiro."""
    contagem, vistas = {}, {}
    for f in lista_folhas:
        vistos = set()
        for vp in legendas_da_folha(doc, f):
            v = doc.GetElement(vp.ViewId)
            k = eid(v.Id)
            vistas[k] = v
            if k not in vistos:
                vistos.add(k)
                contagem[k] = contagem.get(k, 0) + 1
    saida = [(vistas[k], n) for k, n in contagem.items()]
    saida.sort(key=lambda p: (-p[1], nome(p[0]).lower()))
    return saida


# Deslocamento extra (X, Y) em CENTIMETROS (a unidade que o Revit mostra ao medir
# na folha) aplicado depois do alinhamento, quando esta legenda entra. Nome em
# minusculas. Convertido para pes (unidade interna) logo abaixo.
_CM_PARA_PES = 1.0 / 30.48
AJUSTE_LEGENDA = dict(
    (k, (x * _CM_PARA_PES, y * _CM_PARA_PES)) for k, (x, y) in {
        u'san - plantas baixas - r01': (0.47, -0.03),     # direita 0,47 / desce 0,03
    }.items())


def trocar_legenda(doc, lista_folhas, antiga, nova):
    """Em cada folha troca a legenda `antiga` por `nova` (Views), no mesmo
    lugar (topo e lateral direita alinhados com os da antiga). Uma folha pode ter mais de uma legenda - so' a `antiga` muda. Devolve (trocadas, avisos)."""
    trocadas, avisos = 0, []
    if eid(antiga.Id) == eid(nova.Id):
        return 0, [u'a legenda nova é igual à que sai']
    t = Transaction(doc, u'Folhas HOYT - trocar legenda (%d folhas)' % len(lista_folhas))
    t.Start()
    try:
        for f in lista_folhas:
            alvos = [vp for vp in legendas_da_folha(doc, f) if eid(vp.ViewId) == eid(antiga.Id)]
            if not alvos:
                avisos.append(u'%s: não tem a legenda "%s"' % (f.SheetNumber, nome(antiga)))
                continue
            for antigo in alvos:
                sub = SubTransaction(doc)
                sub.Start()
                try:
                    centro = antigo.GetBoxCenter()
                    o_ant = antigo.GetBoxOutline()
                    topo, direita = o_ant.MaximumPoint.Y, o_ant.MaximumPoint.X   # nova: alinhada por cima e pela direita
                    tipo_id = antigo.GetTypeId()
                    fixa = bool(antigo.Pinned)
                    rot = antigo.Rotation
                    if fixa:
                        antigo.Pinned = False
                    doc.Delete(antigo.Id)
                    novo = Viewport.Create(doc, f.Id, nova.Id, centro)
                    try:
                        novo.ChangeTypeId(tipo_id)
                    except Exception:
                        pass
                    try:
                        novo.Rotation = rot
                    except Exception:
                        pass
                    doc.Regenerate()
                    o_novo = novo.GetBoxOutline()
                    dx, dy = direita - o_novo.MaximumPoint.X, topo - o_novo.MaximumPoint.Y
                    ex, ey = AJUSTE_LEGENDA.get(nome(nova).strip().lower(), (0.0, 0.0))
                    dx, dy = dx + ex, dy + ey
                    if abs(dx) > 1e-9 or abs(dy) > 1e-9:
                        c2 = novo.GetBoxCenter()
                        novo.SetBoxCenter(XYZ(c2.X + dx, c2.Y + dy, c2.Z))
                    if fixa:
                        novo.Pinned = True
                    sub.Commit()
                    trocadas += 1
                except Exception as ex:
                    sub.RollBack()
                    avisos.append(u'%s: não trocou (%s)' % (f.SheetNumber, texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return trocadas, avisos


# ------------------------------------------------------------ tipo de folha (carimbo)
def tipos_de_carimbo(doc):
    """[FamilySymbol] de todos os tipos de carimbo carregados, por familia/tipo."""
    from Autodesk.Revit.DB import FamilySymbol
    saida = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_TitleBlocks)
                 .OfClass(FamilySymbol).ToElements())
    saida.sort(key=lambda s: (texto(s.FamilyName).lower(), nome(s).lower()))
    return saida


def rotulo_do_tipo(simbolo):
    return u'%s : %s' % (texto(simbolo.FamilyName), nome(simbolo))


def trocar_tipo(doc, lista_folhas, simbolo):
    """Troca o tipo do carimbo (= tipo da folha) das folhas para `simbolo`.
    Os parametros da folha e do carimbo ficam como estao. Devolve (trocadas,
    avisos). Uma transacao so'."""
    trocadas, avisos = 0, []
    t = Transaction(doc, u'Folhas HOYT - trocar tipo de folha (%d)' % len(lista_folhas))
    t.Start()
    try:
        if not simbolo.IsActive:
            simbolo.Activate()
            doc.Regenerate()
        for f in lista_folhas:
            sub = SubTransaction(doc)
            sub.Start()
            try:
                c = carimbo(doc, f)
                if c is None:
                    raise Exception(u'a folha não tem carimbo')
                if eid(c.GetTypeId()) == eid(simbolo.Id):
                    sub.RollBack()
                    continue
                c.ChangeTypeId(simbolo.Id)
                sub.Commit()
                trocadas += 1
            except Exception as ex:
                sub.RollBack()
                avisos.append(u'%s: não trocou (%s)' % (f.SheetNumber, texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return trocadas, avisos


# ------------------------------------------------------------ numero da prancha
PARAM_PRANCHA = u'Número da Prancha'


def numero_prancha(folha):
    """(valor, existe) do parametro "Numero da Prancha" da folha."""
    p = folha.LookupParameter(PARAM_PRANCHA)
    if p is None:
        return u'', False
    try:
        if p.StorageType == StorageType.String:
            return p.AsString() or u'', True
        return p.AsValueString() or u'', True
    except Exception:
        return u'', True


def _gravar_prancha(folha, valor):
    p = folha.LookupParameter(PARAM_PRANCHA)
    if p is None or p.IsReadOnly:
        raise Exception(u'parâmetro "%s" não existe ou é somente leitura' % PARAM_PRANCHA)
    if p.StorageType == StorageType.String:
        p.Set(valor)
    elif p.StorageType == StorageType.Integer:
        p.Set(int(valor))
    else:
        p.SetValueString(valor)


# ------------------------------------------------------------ renumerar / renomear
def renumerar_renomear(doc, mudancas):
    """mudancas = [(ViewSheet, novo_numero, novo_nome, novo_prancha)] (None =
    nao muda). Numeros em duas passadas (troca entre folhas nao colide).
    Devolve (feitas, avisos). Uma transacao so'."""
    avisos = []
    muda_num = [(f, n) for f, n, _nm, _pr in mudancas if n is not None and n != f.SheetNumber]
    alvo_ids = set(eid(f.Id) for f, _n in muda_num)
    fixos = set(f.SheetNumber for f in todas(doc) if eid(f.Id) not in alvo_ids)
    for f, n in muda_num:
        if n in fixos:
            avisos.append(u'%s → %s: número já existe em outra folha (não alterado)' % (f.SheetNumber, n))
    repetidos = regras.conflitos([(eid(f.Id), n) for f, n in muda_num])
    for n in repetidos:
        avisos.append(u'número %s repetido no lote (não alterado)' % n)
    muda_num = [(f, n) for f, n in muda_num if n not in fixos and n not in repetidos]
    feitas = 0
    t = Transaction(doc, u'Folhas HOYT - renumerar/renomear folhas')
    t.Start()
    try:
        for i, (f, _n) in enumerate(muda_num):
            f.SheetNumber = u'HOYT_TMP_%d_%s' % (i, f.UniqueId[-6:])   # sem ~ { } [ ] | ; < > ? ` (proibidos pelo Revit)
        for f, n in muda_num:
            f.SheetNumber = n
        feitas += len(muda_num)
        for f, _n, nm, pr in mudancas:
            if nm is not None and nm != f.Name:
                try:
                    f.Name = nm
                    feitas += 1
                except Exception as ex:
                    avisos.append(u'%s: não renomeou (%s)' % (f.SheetNumber, texto(ex)))
            if pr is not None:
                try:
                    _gravar_prancha(f, pr)
                    feitas += 1
                except Exception as ex:
                    avisos.append(u'%s: %s: %s' % (f.SheetNumber, PARAM_PRANCHA, texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return feitas, avisos