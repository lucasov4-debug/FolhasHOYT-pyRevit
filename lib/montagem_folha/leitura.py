# -*- coding: utf-8 -*-
"""Le uma folha do Revit e devolve SO' dados puros, em mm de papel.

Nada aqui fica no modelo (formatos_do_projeto cria folhas de teste e
desfaz). O mesmo dicionario serve a medicao (botao
MontarFolha, versao so-leitura) e, depois, o editor de arrastar.

Compativel com IronPython 2.7 e CPython 3 (o motor que o pyRevit usa
nesta maquina ja' surpreendeu uma vez - ver ultimo_erro.txt do
Gerenciador de Folhas): so' literais u'', nada de f-string.
"""

from Autodesk.Revit.DB import (
    BuiltInCategory,
    BuiltInParameter,
    FilteredElementCollector,
    GeometryInstance,
    Line,
    Options,
    ScheduleSheetInstance,
    Transaction,
    View,
    ViewSchedule,
    ViewSheet,
    ViewType,
    Viewport,
    XYZ,
)

from Autodesk.Revit.DB.Electrical import PanelScheduleSheetInstance, PanelScheduleView

from folhas_disciplina import titulo as _titulo

from . import geometria

PES_EM_MM = geometria.PES_EM_MM

# tipos de vista que fazem sentido arrastar para dentro de uma folha
TIPOS_COLOCAVEIS = (
    ViewType.FloorPlan, ViewType.CeilingPlan, ViewType.AreaPlan,
    ViewType.EngineeringPlan, ViewType.Section, ViewType.Elevation,
    ViewType.Detail, ViewType.ThreeD, ViewType.DraftingView, ViewType.Legend,
)


def _mm(v):
    return v * PES_EM_MM


def _id(eid):
    """ElementId -> int. `.Value` no Revit 2024+, `.IntegerValue` antes
    (o IntegerValue sai no 2026)."""
    try:
        return int(eid.Value)
    except Exception:
        return int(eid.IntegerValue)


def _ret_de(minimo, maximo):
    return geometria.ret(_mm(minimo.X), _mm(minimo.Y), _mm(maximo.X), _mm(maximo.Y))


def _texto(v):
    try:
        return u'%s' % v
    except Exception:
        return u'?'


# ------------------------------------------------------------ carimbo
def carimbo_da_folha(doc, folha):
    for inst in (FilteredElementCollector(doc, folha.Id)
                 .OfCategory(BuiltInCategory.OST_TitleBlocks)
                 .WhereElementIsNotElementType().ToElements()):
        return inst
    return None


def geometria_do_elemento(elemento, op):
    """(segmentos em mm, contagem por tipo de objeto, retorno). Desce em
    GeometryInstance (familias aninhadas) - GetInstanceGeometry ja' devolve
    em coordenadas da folha. retorno: 'None' (o Revit nao devolveu
    geometria), 'vazio' (devolveu, sem nada dentro) ou 'ok'."""
    segmentos = []
    contagem = {}

    def varrer(geo):
        if geo is None:
            return
        for obj in geo:
            nome = obj.GetType().Name
            contagem[nome] = contagem.get(nome, 0) + 1
            if isinstance(obj, GeometryInstance):
                varrer(obj.GetInstanceGeometry())
            elif isinstance(obj, Line):
                p, q = obj.GetEndPoint(0), obj.GetEndPoint(1)
                segmentos.append(((_mm(p.X), _mm(p.Y)), (_mm(q.X), _mm(q.Y))))

    geo = elemento.get_Geometry(op)
    varrer(geo)
    retorno = u'None' if geo is None else (u'ok' if contagem else u'vazio')
    return segmentos, contagem, retorno


def opcoes(vista=None, nao_visiveis=False):
    op = Options()
    if vista is not None:
        op.View = vista
    if nao_visiveis:
        op.IncludeNonVisibleObjects = True
    return op


def segmentos_do_carimbo(carimbo, folha):
    segmentos, contagem, _ = geometria_do_elemento(carimbo, opcoes(folha))
    return segmentos, contagem


def _param_mm(elemento, bip):
    try:
        p = elemento.get_Parameter(bip)
        if p is not None and p.HasValue:
            return _mm(p.AsDouble())
    except Exception:
        pass
    return None


def ler_carimbo(doc, folha):
    carimbo = carimbo_da_folha(doc, folha)
    if carimbo is None:
        return None
    tipo = doc.GetElement(carimbo.GetTypeId())
    segmentos, contagem = segmentos_do_carimbo(carimbo, folha)
    caixa = carimbo.get_BoundingBox(folha)
    formatos = []
    try:
        for t in _titulo.familias_de_titulo(doc).get(tipo.Family.Name, []):
            formatos.append({u'id': _id(t.Id), u'nome': _titulo.nome_tipo(t)})
    except Exception:
        pass
    return {
        u'id': _id(carimbo.Id),
        u'familia': _texto(tipo.Family.Name) if tipo is not None else u'?',
        u'formato': _titulo.nome_tipo(tipo) if tipo is not None else u'?',
        u'formato_id': _id(tipo.Id) if tipo is not None else None,
        u'formatos': formatos,
        u'caixa': _ret_de(caixa.Min, caixa.Max) if caixa is not None else None,
        u'largura_param': _param_mm(carimbo, BuiltInParameter.SHEET_WIDTH),
        u'altura_param': _param_mm(carimbo, BuiltInParameter.SHEET_HEIGHT),
        u'segmentos': segmentos,
        u'geometria': contagem,
    }


# ------------------------------------------------------------ formatos
# Lucas (26/09/2026): o tamanho de cada folha vem dos parametros
# Largura/Altura da folha ("Dados de identidade"). Medido na v0.5: esses
# parametros NAO existem no TIPO (0 de 22) - so' na instancia do carimbo
# numa folha. Entao: uma folha de teste por tipo, le a instancia, desfaz.
_NOMES_LARGURA = (u'Largura da folha', u'Sheet Width')
_NOMES_ALTURA = (u'Altura da folha', u'Sheet Height')


def _mm_parametro(elemento, bip, nomes):
    valor = _param_mm(elemento, bip)
    if valor:
        return valor
    for nome in nomes:
        try:
            p = elemento.LookupParameter(nome)
            if p is not None and p.HasValue and p.AsDouble():
                return _mm(p.AsDouble())
        except Exception:
            continue
    return None


def area_da_folha(doc, folha):
    """area_util_padrao (mm) de uma folha que ja existe - papel pelo
    bounding box do carimbo + Largura/Altura da folha, margens e carimbo
    de padroes.py. None se a folha nao tiver carimbo ou tamanho."""
    from . import padroes
    carimbo = carimbo_da_folha(doc, folha)
    if carimbo is None:
        return None
    largura = _mm_parametro(carimbo, BuiltInParameter.SHEET_WIDTH, _NOMES_LARGURA)
    altura = _mm_parametro(carimbo, BuiltInParameter.SHEET_HEIGHT, _NOMES_ALTURA)
    caixa = carimbo.get_BoundingBox(folha)
    if not largura or not altura or caixa is None:
        return None
    try:
        familia = _texto(doc.GetElement(carimbo.GetTypeId()).Family.Name)
    except Exception:
        familia = u''
    papel = geometria.papel_do_formato(_ret_de(caixa.Min, caixa.Max), largura, altura)
    p = padroes.da_familia(familia, altura)
    return geometria.area_util_padrao(papel, p[u'margens'], p[u'carimbo'])


def formatos_do_projeto(doc, familia=None):
    """[{familia, formato, id, largura, altura, papel, erro?}] dos tipos de
    folha carregados (so' os da `familia`, se dada). largura/altura = os
    parametros da instancia; papel = retangulo mm da folha numa folha nova
    (esquerda/baixo do bounding box + largura/altura - regra medida em
    26/09/2026 nos 20 formatos bons).

    Abre e DESFAZ a propria transacao - chamar no contexto de API, sem
    transacao aberta."""
    saida = []
    transacao = Transaction(doc, u'Montar Folha - ler formatos (desfeito)')
    transacao.Start()
    try:
        for nome_familia, tipos in sorted(_titulo.familias_de_titulo(doc).items()):
            if familia is not None and nome_familia != familia:
                continue
            for tipo in tipos:
                item = {u'familia': _texto(nome_familia), u'formato': _titulo.nome_tipo(tipo),
                        u'id': _id(tipo.Id), u'largura': None, u'altura': None, u'papel': None}
                try:
                    if not tipo.IsActive:
                        tipo.Activate()
                    folha = ViewSheet.Create(doc, tipo.Id)
                    doc.Regenerate()
                    carimbo = carimbo_da_folha(doc, folha)
                    item[u'largura'] = _mm_parametro(carimbo, BuiltInParameter.SHEET_WIDTH, _NOMES_LARGURA)
                    item[u'altura'] = _mm_parametro(carimbo, BuiltInParameter.SHEET_HEIGHT, _NOMES_ALTURA)
                    caixa = carimbo.get_BoundingBox(folha)
                    if caixa is not None and item[u'largura'] and item[u'altura']:
                        item[u'papel'] = geometria.papel_do_formato(
                            _ret_de(caixa.Min, caixa.Max), item[u'largura'], item[u'altura'])
                except Exception as ex:
                    item[u'erro'] = _texto(ex)
                saida.append(item)
    finally:
        transacao.RollBack()
    return saida


def _relativo(r, c):
    return None if r is None else geometria.mover(r, -c[0], -c[1])


def catalogo(doc, tipo_titulo):
    """(vistas, views_por_id, disciplinas, erros) - TODAS as vistas livres
    colocadas numa folha de teste (com o tipo dado) e medidas: caixa,
    recorte e rotulo relativos ao centro da caixa. disciplinas = codigos
    Tag_Disciplina_* da familia (mesma sonda do Gerenciador). Desfaz tudo.
    views_por_id guarda os View (existiam antes, continuam validos)."""
    from folhas_disciplina import criar as _criar
    vistas, views_por_id, erros, disciplinas = [], {}, [], []
    transacao = Transaction(doc, u'Montar Folha - medir vistas (desfeito)')
    transacao.Start()
    try:
        try:
            disciplinas = [codigo for codigo, _ in _criar.detectar_disciplinas(doc, tipo_titulo)]
        except Exception as ex:
            erros.append(u'disciplinas: %s' % _texto(ex))
        sonda = ViewSheet.Create(doc, tipo_titulo.Id)
        colocadas = []
        for v in vistas_colocaveis(doc, sonda):
            try:
                colocadas.append((v, Viewport.Create(doc, sonda.Id, v.Id, XYZ(0, 0, 0))))
            except Exception as ex:
                erros.append(u'%s: %s' % (_texto(v.Name), _texto(ex)))
        doc.Regenerate()
        for v, vp in colocadas:
            try:
                d = ler_viewport(doc, vp)
                c = d[u'centro']
                vistas.append({u'id': d[u'vista_id'], u'nome': d[u'nome'],
                               u'tipo_vista': d[u'tipo_vista'], u'escala': d[u'escala'],
                               u'caixa_rel': _relativo(d[u'caixa'], c),
                               u'recorte_rel': _relativo(d[u'recorte_folha'], c),
                               u'rotulo_rel': _relativo(d[u'rotulo'], c)})
                views_por_id[d[u'vista_id']] = v
            except Exception as ex:
                erros.append(u'%s: %s' % (_texto(v.Name), _texto(ex)))
        _medir_tabelas(doc, sonda, vistas, views_por_id, erros)
    finally:
        transacao.RollBack()
    return vistas, views_por_id, disciplinas, erros


def tabelas_colocaveis(doc):
    """[ViewSchedule] que fazem sentido numa folha: sem modelos de vista,
    sem as internas (revisoes, lista de folhas de sistema) e sem as de
    chave."""
    saida = []
    for v in FilteredElementCollector(doc).OfClass(ViewSchedule).ToElements():
        try:
            if v.IsTemplate or v.IsInternalKeynoteSchedule or v.IsTitleblockRevisionSchedule:
                continue
            if v.Definition.IsKeySchedule:
                continue
            saida.append(v)
        except Exception:
            continue
    saida.sort(key=lambda v: _texto(v.Name).lower())
    return saida


def _medir_tabelas(doc, sonda, vistas, views_por_id, erros):
    """Poe cada tabela na folha de teste e mede. O centro guardado de uma
    tabela e' o PONTO DE INSERCAO (canto superior esquerdo, o que o
    ScheduleSheetInstance.Create recebe); caixa_rel e' relativa a ele."""
    medidas = []
    for t in tabelas_colocaveis(doc):
        try:
            medidas.append((t, ScheduleSheetInstance.Create(doc, sonda.Id, t.Id, XYZ(0, 0, 0))))
        except Exception as ex:
            erros.append(u'tabela %s: %s' % (_texto(t.Name), _texto(ex)))
    # tabelas de painel (as do quadro de cargas): o Create nao recebe ponto,
    # entram na origem; o ponto guardado e' o canto superior esquerdo da caixa
    for p in paineis_colocaveis(doc):
        try:
            medidas.append((p, PanelScheduleSheetInstance.Create(doc, p.Id, sonda)))
        except Exception as ex:
            erros.append(u'tabela de painel %s: %s' % (_texto(p.Name), _texto(ex)))
    doc.Regenerate()
    for t, inst in medidas:
        try:
            caixa = inst.get_BoundingBox(sonda)
            x, y = ancora_da_tabela(inst, sonda)
            ponto = (_mm(x), _mm(y))
            vistas.append({u'id': _id(t.Id), u'nome': _texto(t.Name), u'tipo_vista': u'Tabela',
                           u'escala': None, u'painel': not isinstance(inst, ScheduleSheetInstance),
                           u'caixa_rel': _relativo(_ret_de(caixa.Min, caixa.Max), ponto),
                           u'recorte_rel': None, u'rotulo_rel': None})
            views_por_id[_id(t.Id)] = t
        except Exception as ex:
            erros.append(u'tabela %s: %s' % (_texto(t.Name), _texto(ex)))


def paineis_colocaveis(doc):
    """[PanelScheduleView] que ainda nao estao em nenhuma folha (uma tabela
    de painel so' entra numa folha)."""
    ocupados = set()
    for inst in FilteredElementCollector(doc).OfClass(PanelScheduleSheetInstance).ToElements():
        try:
            ocupados.add(_id(inst.ScheduleId))
        except Exception:
            continue
    saida = []
    for v in FilteredElementCollector(doc).OfClass(PanelScheduleView).ToElements():
        try:
            if v.IsPanelScheduleTemplate() or _id(v.Id) in ocupados:
                continue
            saida.append(v)
        except Exception:
            continue
    saida.sort(key=lambda v: _texto(v.Name).lower())
    return saida


def ancora_da_tabela(inst, vista_da_folha):
    """(x, y) em pes do ponto que guarda a posicao da tabela na folha:
    o ponto de insercao da tabela comum; o canto superior esquerdo da caixa
    na tabela de painel (ela nao tem ponto de insercao)."""
    if isinstance(inst, ScheduleSheetInstance):
        return inst.Point.X, inst.Point.Y
    caixa = inst.get_BoundingBox(vista_da_folha)
    return caixa.Min.X, caixa.Max.Y


def instancias_de_tabela(doc, folha):
    """Tabelas da folha (comuns e de painel), sem a de revisoes do carimbo."""
    saida = []
    for classe in (ScheduleSheetInstance, PanelScheduleSheetInstance):
        for inst in FilteredElementCollector(doc, folha.Id).OfClass(classe).ToElements():
            try:
                if isinstance(inst, ScheduleSheetInstance) and inst.IsTitleblockRevisionSchedule:
                    continue
            except Exception:
                continue
            saida.append(inst)
    return saida


def familia_em_uso(doc):
    """Nome da familia de folha mais usada nas folhas do projeto (None se
    nao houver folha) - e' a que o plugin mostra por padrao."""
    contagem = {}
    for folha in todas_as_folhas(doc):
        carimbo = carimbo_da_folha(doc, folha)
        if carimbo is None:
            continue
        try:
            nome = _texto(doc.GetElement(carimbo.GetTypeId()).Family.Name)
        except Exception:
            continue
        contagem[nome] = contagem.get(nome, 0) + 1
    if not contagem:
        return None
    return max(sorted(contagem), key=lambda n: contagem[n])


# ------------------------------------------------------------ vistas
def _recorte(vista):
    """Tamanho da regiao de recorte NO PAPEL (mm) e o formato dela."""
    info = {u'ativo': False, u'visivel': False, u'anotacao': None,
            u'largura': None, u'altura': None, u'curvas': None}
    try:
        info[u'ativo'] = bool(vista.CropBoxActive)
        info[u'visivel'] = bool(vista.CropBoxVisible)
    except Exception:
        return info
    try:
        p = vista.get_Parameter(BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
        info[u'anotacao'] = bool(p.AsInteger()) if p is not None else None
    except Exception:
        pass
    try:
        escala = float(vista.Scale or 1)
        cb = vista.CropBox
        info[u'largura'] = _mm(cb.Max.X - cb.Min.X) / escala
        info[u'altura'] = _mm(cb.Max.Y - cb.Min.Y) / escala
    except Exception:
        pass
    try:
        gerente = vista.GetCropRegionShapeManager()
        lacos = list(gerente.GetCropShape())
        if lacos:
            info[u'curvas'] = sum(1 for _ in lacos[0])
    except Exception:
        pass
    return info


def recorte_na_folha(vp, vista):
    """(retangulo mm, erro) da REGIAO DE RECORTE projetada na folha:
    modelo -> projecao da vista -> folha. E' o retangulo que o Lucas quer
    usar como limite (a caixa do viewport inclui anotacao fora do
    recorte - medido em 26/09/2026: +6,1 mm nas plantas 1:50, +22 x +98
    no corte)."""
    try:
        if not vista.CropBoxActive:
            return None, u'recorte desligado'
        para_folha = vp.GetProjectionToSheetTransform()
        projecoes = list(vista.GetModelToProjectionTransforms())
        m2p = projecoes[0].GetModelToProjectionTransform()
        lacos = list(vista.GetCropRegionShapeManager().GetCropShape())
        xs, ys = [], []
        for curva in lacos[0]:
            for i in (0, 1):
                p = para_folha.OfPoint(m2p.OfPoint(curva.GetEndPoint(i)))
                xs.append(_mm(p.X))
                ys.append(_mm(p.Y))
        extra = u'' if len(projecoes) == 1 else u'vista dividida (%d partes)' % len(projecoes)
        return geometria.ret(min(xs), min(ys), max(xs), max(ys)), extra or None
    except Exception as ex:
        return None, _texto(ex)


def ler_viewport(doc, vp):
    vista = doc.GetElement(vp.ViewId)
    caixa = vp.GetBoxOutline()
    c = vp.GetBoxCenter()
    rotulo = None
    try:
        lo = vp.GetLabelOutline()
        rotulo = _ret_de(lo.MinimumPoint, lo.MaximumPoint)
    except Exception:
        pass
    recorte_folha, recorte_erro = recorte_na_folha(vp, vista)
    return {
        u'recorte_folha': recorte_folha,
        u'recorte_folha_obs': recorte_erro,
        u'id': _id(vp.Id),
        u'vista_id': _id(vista.Id),
        u'nome': _texto(vista.Name),
        u'tipo_vista': _texto(vista.ViewType),
        u'escala': vista.Scale,
        u'rotacao': _texto(vp.Rotation),
        u'caixa': _ret_de(caixa.MinimumPoint, caixa.MaximumPoint),
        u'centro': (_mm(c.X), _mm(c.Y)),
        u'rotulo': rotulo,
        u'recorte': _recorte(vista),
    }


def _tabela(doc, folha, inst):
    caixa = inst.get_BoundingBox(folha)
    return {
        u'id': _id(inst.Id),
        u'nome': _texto(inst.Name),
        u'caixa': _ret_de(caixa.Min, caixa.Max) if caixa is not None else None,
        u'ponto': tuple(_mm(v) for v in ancora_da_tabela(inst, folha)),
        u'painel': not isinstance(inst, ScheduleSheetInstance),
    }


def vistas_colocaveis(doc, folha):
    """[View] que PODEM entrar nesta folha (Viewport.CanAddViewToSheet -
    vista que ja' esta' em outra folha fica de fora; legenda pode repetir)."""
    saida = []
    for v in FilteredElementCollector(doc).OfClass(View).ToElements():
        try:
            if v.IsTemplate or v.ViewType not in TIPOS_COLOCAVEIS:
                continue
            if Viewport.CanAddViewToSheet(doc, folha.Id, v.Id):
                saida.append(v)
        except Exception:
            continue
    saida.sort(key=lambda v: (_texto(v.ViewType), _texto(v.Name)))
    return saida


def vistas_livres(doc, folha):
    """[{id, nome, tipo_vista, escala}] - os dados de vistas_colocaveis."""
    return [{u'id': _id(v.Id), u'nome': _texto(v.Name),
             u'tipo_vista': _texto(v.ViewType), u'escala': v.Scale}
            for v in vistas_colocaveis(doc, folha)]


# ------------------------------------------------------------ folha
def ler_folha(doc, folha, com_livres=True):
    viewports = []
    for vp_id in folha.GetAllViewports():
        try:
            viewports.append(ler_viewport(doc, doc.GetElement(vp_id)))
        except Exception as ex:
            viewports.append({u'id': _id(vp_id), u'erro': _texto(ex)})
    tabelas = []
    for inst in instancias_de_tabela(doc, folha):
        try:
            tabelas.append(_tabela(doc, folha, inst))
        except Exception:
            continue
    carimbo = ler_carimbo(doc, folha)
    deteccao = geometria.detectar_area_util(carimbo[u'segmentos']) if carimbo else None
    return {
        u'folha': {u'id': _id(folha.Id), u'numero': _texto(folha.SheetNumber),
                   u'nome': _texto(folha.Name)},
        u'carimbo': carimbo,
        u'deteccao': deteccao,
        u'viewports': viewports,
        u'tabelas': tabelas,
        u'livres': vistas_livres(doc, folha) if com_livres else None,
    }


def todas_as_folhas(doc):
    folhas = [f for f in FilteredElementCollector(doc).OfClass(ViewSheet).ToElements()
              if not f.IsPlaceholder]
    folhas.sort(key=lambda f: f.SheetNumber)
    return folhas


# ------------------------------------------------------------ folhas que ja existem
def resumo_das_folhas(doc):
    """([{id, numero, nome, vistas}], {id: ViewSheet}) - barato: so' conta
    os viewports. Os ViewSheet ficam guardados porque construir ElementId
    a partir de inteiro nao e' portavel entre versoes do Revit."""
    resumo, por_id = [], {}
    for folha in todas_as_folhas(doc):
        fid = _id(folha.Id)
        por_id[fid] = folha
        try:
            n = len(list(folha.GetAllViewports()))
        except Exception:
            n = 0
        resumo.append({u'id': fid, u'numero': _texto(folha.SheetNumber),
                       u'nome': _texto(folha.Name), u'vistas': n})
    return resumo, por_id


def ler_para_editar(doc, folha):
    """Uma folha existente como dado puro (mm de papel, coordenadas da
    propria folha): area (area_util_padrao, ou None se a folha nao tiver
    carimbo com Largura/Altura), formato, as vistas (relativas ao centro
    da caixa - o mesmo formato do catalogo - com o centro absoluto) e as
    tabelas, que so' aparecem na previa."""
    area = area_da_folha(doc, folha)
    formato = u''
    carimbo = carimbo_da_folha(doc, folha)
    if carimbo is not None:
        try:
            formato = _titulo.nome_tipo(doc.GetElement(carimbo.GetTypeId()))
        except Exception:
            pass
    vistas, erros = [], []
    for vp_id in folha.GetAllViewports():
        try:
            vp = doc.GetElement(vp_id)
            d = ler_viewport(doc, vp)
            c = d[u'centro']
            fixada = False
            try:
                fixada = bool(vp.Pinned)
            except Exception:
                pass
            vistas.append({u'id': d[u'id'], u'nome': d[u'nome'], u'tipo_vista': d[u'tipo_vista'],
                           u'escala': d[u'escala'], u'caixa_rel': _relativo(d[u'caixa'], c),
                           u'recorte_rel': _relativo(d[u'recorte_folha'], c),
                           u'rotulo_rel': _relativo(d[u'rotulo'], c),
                           u'centro': c, u'fixada': fixada})
        except Exception as ex:
            erros.append(u'%s: %s' % (_id(vp_id), _texto(ex)))
    # tabelas entram como vistas (tipo 'Tabela'): centro = ponto de insercao,
    # id = o da instancia na folha - da' para arrastar como um viewport
    for inst in instancias_de_tabela(doc, folha):
        try:
            t = _tabela(doc, folha, inst)
            if t[u'caixa'] is None:
                continue
            fixada = False
            try:
                fixada = bool(inst.Pinned)
            except Exception:
                pass
            vistas.append({u'id': t[u'id'], u'nome': t[u'nome'], u'tipo_vista': u'Tabela',
                           u'escala': None, u'painel': t[u'painel'],
                           u'caixa_rel': _relativo(t[u'caixa'], t[u'ponto']),
                           u'recorte_rel': None, u'rotulo_rel': None,
                           u'centro': t[u'ponto'], u'fixada': fixada})
        except Exception as ex:
            erros.append(u'tabela: %s' % _texto(ex))
    return {u'id': _id(folha.Id), u'numero': _texto(folha.SheetNumber), u'nome': _texto(folha.Name),
            u'formato': formato, u'area': area, u'vistas': vistas, u'tabelas': [], u'erros': erros}
