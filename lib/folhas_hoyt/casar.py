# -*- coding: utf-8 -*-
"""Casar vista x folha: coloca cada vista centralizada na area util da
folha (regra do Montar Folhas: margens e carimbo de montagem_folha.padroes;
centro = do quadro ate' a esquerda do carimbo, altura toda). Se nao couber,
avisa e posiciona mesmo assim."""
from Autodesk.Revit.DB import (
    FilteredElementCollector, Transaction, TransactionStatus, View, ViewType, Viewport, XYZ,
)

from montagem_folha import geometria, leitura

from . import eid, nome, texto

PES = geometria.PES_EM_MM

# vistas que fazem sentido casar com uma folha (legenda tem botao proprio)
TIPOS = tuple(t for t in leitura.TIPOS_COLOCAVEIS if t != ViewType.Legend)


def vistas_do_projeto(doc):
    """[(View, folha_numero_ou_vazio)] de todas as vistas colocaveis."""
    from . import vistas as _v
    saida = []
    for v in FilteredElementCollector(doc).OfClass(View).ToElements():
        try:
            if v.IsTemplate or v.ViewType not in TIPOS:
                continue
        except Exception:
            continue
        saida.append((v, _v.folha_da_vista(v)))
    saida.sort(key=lambda p: (texto(p[0].ViewType), nome(p[0]).lower()))
    return saida


def _centro_alvo(area):
    x0, y0, x1, y1 = area[u'area_centro']
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0, x1 - x0, y1 - y0


SUBIR_TITULO_CM = 2.0            # quanto o titulo da viewport sobe na folha (cm)
ESTILO_REFERENCIA = u'revisão'   # linhas de detalhe desse estilo definem o "quadro" da vista


def _sem_acento(s):
    import unicodedata
    return u''.join(c for c in unicodedata.normalize('NFD', texto(s)) if unicodedata.category(c) != 'Mn').lower()


def ajustar_recorte_as_linhas(doc, vista):
    """Encosta cada lado do recorte ATUAL da vista na linha de detalhe de estilo
    ESTILO_REFERENCIA mais proxima desse lado (a vista tem as linhas de varios
    setores; so' as que estao junto do recorte visivel contam). Lado sem linha
    por perto fica como esta'. Devolve True se achou alguma linha."""
    from Autodesk.Revit.DB import BoundingBoxXYZ, BuiltInCategory
    alvo = _sem_acento(ESTILO_REFERENCIA)
    cb = vista.CropBox
    inv = cb.Transform.Inverse
    x0, y0, x1, y1 = cb.Min.X, cb.Min.Y, cb.Max.X, cb.Max.Y
    tx, ty = 0.25 * (x1 - x0), 0.25 * (y1 - y0)    # ate' onde uma linha ainda "pertence" ao lado
    verticais, horizontais = [], []                 # x das verticais / y das horizontais (coords da vista)
    achou = False
    for el in (FilteredElementCollector(doc, vista.Id).OfCategory(BuiltInCategory.OST_Lines)
               .WhereElementIsNotElementType().ToElements()):
        try:
            if _sem_acento(nome(el.LineStyle)) != alvo:
                continue
            cv = el.GeometryCurve
            a, b = inv.OfPoint(cv.GetEndPoint(0)), inv.OfPoint(cv.GetEndPoint(1))
        except Exception:
            continue
        dx, dy = abs(b.X - a.X), abs(b.Y - a.Y)
        if dy <= 0.01 * dx and max(a.X, b.X) >= x0 and min(a.X, b.X) <= x1:
            horizontais.append((a.Y + b.Y) / 2.0)
            achou = True
        elif dx <= 0.01 * dy and max(a.Y, b.Y) >= y0 and min(a.Y, b.Y) <= y1:
            verticais.append((a.X + b.X) / 2.0)
            achou = True

    def perto(valores, ref, tol):
        c = [v for v in valores if abs(v - ref) <= tol]
        return min(c, key=lambda v: abs(v - ref)) if c else ref

    novo = BoundingBoxXYZ()
    novo.Transform = cb.Transform
    novo.Min = XYZ(perto(verticais, x0, tx), perto(horizontais, y0, ty), cb.Min.Z)
    novo.Max = XYZ(perto(verticais, x1, tx), perto(horizontais, y1, ty), cb.Max.Z)
    if achou:
        vista.CropBoxActive = True
        vista.CropBox = novo
    return achou


# A linha do titulo termina no fim do texto: com a linha minima, o Revit devolve
# o contorno do titulo (logo + texto); a linha vai de onde o texto comeca ate o fim
# dele, entao e' uma fracao desse contorno (ajuste fino se sobrar/faltar).
FRACAO_LINHA = 0.81


def _padronizar_titulo(vp):
    """Titulo da viewport sempre SUBIR_TITULO_CM acima da posicao padrao (valor
    absoluto: rodar de novo nao soma) e linha ate' o fim do texto. Devolve um
    texto de diagnostico."""
    o = vp.LabelOffset
    vp.LabelOffset = XYZ(o.X, SUBIR_TITULO_CM / 30.48, o.Z)
    doc = vp.Document
    try:
        antes = vp.LabelLineLength
        vp.LabelLineLength = 0.001                       # linha minima: o contorno e' so' logo + texto
        doc.Regenerate()
        c = vp.GetLabelOutline()
        largura = c.MaximumPoint.X - c.MinimumPoint.X
        alvo = largura * FRACAO_LINHA
        vp.LabelLineLength = alvo
        doc.Regenerate()
        depois = vp.LabelLineLength
    except Exception as ex:
        return u'subiu o título, mas não ajustou a linha (%s)' % texto(ex)
    return u'linha: antes %.1f cm, contorno do título %.1f cm, pedido %.1f cm, ficou %.1f cm' % (
        antes * 30.48, largura * 30.48, alvo * 30.48, depois * 30.48)



def recentralizar_folha(doc, folha):
    """Recentraliza na area util (do tamanho ATUAL do carimbo) cada vista da
    folha (legendas nao). Chamar dentro de uma transacao. Devolve avisos."""
    avisos = []
    area = leitura.area_da_folha(doc, folha)
    if area is None:
        return [u'%s: folha sem carimbo ou sem Largura/Altura da folha (não recentralizou)' % folha.SheetNumber]
    cx, cy, larg, alt = _centro_alvo(area)
    for vid in folha.GetAllViewports():
        vp = doc.GetElement(vid)
        if doc.GetElement(vp.ViewId).ViewType == ViewType.Legend:
            continue
        d = leitura.ler_viewport(doc, vp)
        ret = d[u'recorte_folha'] or d[u'caixa']
        rx, ry = geometria.centro(ret)
        c = vp.GetBoxCenter()
        vp.SetBoxCenter(XYZ(c.X + (cx - rx) / PES, c.Y + (cy - ry) / PES, c.Z))
        if geometria.largura(ret) > larg + 0.5 or geometria.altura(ret) > alt + 0.5:
            avisos.append(u'%s: a vista não cabe na folha nova (vista %d x %d mm, área útil %d x %d mm)'
                          % (folha.SheetNumber, geometria.largura(ret), geometria.altura(ret), larg, alt))
    return avisos


def recentralizar(doc, lista_folhas):
    """Recentraliza as vistas de cada folha (uma transacao so'). Devolve
    (n_folhas, avisos)."""
    n, avisos = 0, []
    t = Transaction(doc, u'Folhas HOYT - recentralizar vistas (%d folhas)' % len(lista_folhas))
    t.Start()
    try:
        for f in lista_folhas:
            try:
                novos = recentralizar_folha(doc, f)
                avisos.extend(novos)
                if not any(u'não recentralizou' in a for a in novos):
                    n += 1
            except Exception as ex:
                avisos.append(u'%s: erro (%s)' % (f.SheetNumber, texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return n, avisos


def padronizar_titulos(doc, lista_folhas):
    """Aplica o titulo padronizado a todas as viewports (nao legendas) das
    folhas dadas. Devolve (n, avisos). Uma transacao so'."""
    n, avisos = 0, []
    t = Transaction(doc, u'Folhas HOYT - padronizar título das vistas (%d folhas)' % len(lista_folhas))
    t.Start()
    try:
        for f in lista_folhas:
            for vid in f.GetAllViewports():
                try:
                    vp = doc.GetElement(vid)
                    if doc.GetElement(vp.ViewId).ViewType == ViewType.Legend:
                        continue
                    info = _padronizar_titulo(vp)
                    if n < 3:
                        avisos.append(u'%s: %s' % (f.SheetNumber, info))    # amostra para conferir
                    n += 1
                except Exception as ex:
                    avisos.append(u'%s: %s' % (f.SheetNumber, texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return n, avisos


def posicionar(doc, pares):
    """pares = [(View, ViewSheet)] -> (colocadas, avisos). Uma transacao so'.
    Aviso para: vista ja' em outra folha (pulada), folha sem carimbo/tamanho
    (pulada), folha que ja' tem vista (pulada) e vista que nao cabe
    (colocada mesmo assim)."""
    colocadas, avisos = 0, []
    t = Transaction(doc, u'Folhas HOYT - casar vistas e folhas (%d)' % len(pares))
    t.Start()
    try:
        for vista, folha in pares:
            rotulo = u'%s → %s' % (nome(vista), folha.SheetNumber)
            try:
                if not Viewport.CanAddViewToSheet(doc, folha.Id, vista.Id):
                    avisos.append(u'%s: a vista já está em outra folha (pulada)' % rotulo)
                    continue
                outras = [vp for vp in folha.GetAllViewports()
                          if doc.GetElement(doc.GetElement(vp).ViewId).ViewType != ViewType.Legend]
                if outras:
                    avisos.append(u'%s: a folha já tem vista (pulada)' % rotulo)
                    continue
                area = leitura.area_da_folha(doc, folha)
                if area is None:
                    avisos.append(u'%s: folha sem carimbo ou sem Largura/Altura da folha (pulada)' % rotulo)
                    continue
                try:
                    if not ajustar_recorte_as_linhas(doc, vista):
                        avisos.append(u'%s: sem linhas do estilo "Revisão" - recorte mantido' % rotulo)
                except Exception as e2:
                    avisos.append(u'%s: não ajustou o recorte às linhas "Revisão" (%s)' % (rotulo, texto(e2)))
                doc.Regenerate()
                cx, cy, larg, alt = _centro_alvo(area)
                vp = Viewport.Create(doc, folha.Id, vista.Id, XYZ(cx / PES, cy / PES, 0.0))
                doc.Regenerate()
                d = leitura.ler_viewport(doc, vp)
                ret = d[u'recorte_folha'] or d[u'caixa']
                rx, ry = geometria.centro(ret)
                c = vp.GetBoxCenter()
                vp.SetBoxCenter(XYZ(c.X + (cx - rx) / PES, c.Y + (cy - ry) / PES, c.Z))
                try:
                    avisos.append(u'%s: %s' % (rotulo, _padronizar_titulo(vp)))
                except Exception as e3:
                    avisos.append(u'%s: não subiu o título da vista (%s)' % (rotulo, texto(e3)))
                colocadas += 1
                lv, av = geometria.largura(ret), geometria.altura(ret)
                if lv > larg + 0.5 or av > alt + 0.5:
                    avisos.append(u'%s: não cabe (vista %d x %d mm, área útil %d x %d mm) - '
                                  u'posicionada mesmo assim' % (rotulo, lv, av, larg, alt))
            except Exception as ex:
                avisos.append(u'%s: erro (%s)' % (rotulo, texto(ex)))
        t.Commit()
    except Exception:
        if t.GetStatus() == TransactionStatus.Started:
            t.RollBack()
        raise
    return colocadas, avisos
