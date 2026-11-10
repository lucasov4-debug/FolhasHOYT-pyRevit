# -*- coding: utf-8 -*-
"""Geometria da montagem de folha - SEM Revit (testada com py -3).

Tudo em MILIMETROS de papel, com Y para cima (igual a folha do Revit).
Retangulo = tupla (x0, y0, x1, y1), sempre x0 < x1 e y0 < y1.
Segmento  = ((xa, ya), (xb, yb)).

Quem converte pes <-> mm e' o adaptador (leitura.py); quem converte
mm <-> pixel e' a Transformacao, usada pela janela.

Tres partes:
  1. retangulos (medir, mover, conter, sobrepor);
  2. encaixe (snap) de um retangulo que esta sendo arrastado nas bordas
     e centros da area util, do carimbo e das outras vistas;
  3. deteccao da area util a partir das LINHAS da familia de titulo
     (quadro + carimbo). E' a parte que ainda e' SUPOSICAO: foi escrita
     para o formato NBR 10068 (quadro com margem, carimbo no canto
     inferior direito, ou coluna inteira na direita, ou faixa inteira
     embaixo) e so' vira confiavel depois de rodar a medicao
     (MontarFolha) na familia real do Lucas.
"""

PES_EM_MM = 304.8
TOL_MM = 0.5


# ============================================================
# 1. RETANGULOS
# ============================================================
def ret(x0, y0, x1, y1):
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def largura(r):
    return r[2] - r[0]


def altura(r):
    return r[3] - r[1]


def area(r):
    return largura(r) * altura(r)


def centro(r):
    return ((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0)


def mover(r, dx, dy):
    return (r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy)


def com_centro(r, cx, cy):
    x, y = centro(r)
    return mover(r, cx - x, cy - y)


def contem(externo, interno, tol=TOL_MM):
    return (interno[0] >= externo[0] - tol and interno[1] >= externo[1] - tol
            and interno[2] <= externo[2] + tol and interno[3] <= externo[3] + tol)


def sobrepoe(a, b, tol=TOL_MM):
    """True se as AREAS se cruzam (encostar na borda nao conta)."""
    return not (a[2] <= b[0] + tol or b[2] <= a[0] + tol
                or a[3] <= b[1] + tol or b[3] <= a[1] + tol)


def uniao(rets):
    rets = [r for r in rets if r is not None]
    if not rets:
        return None
    return (min(r[0] for r in rets), min(r[1] for r in rets),
            max(r[2] for r in rets), max(r[3] for r in rets))


def prender_dentro(r, limite):
    """(dx, dy) que traz r para dentro de limite. Se r for maior que o
    limite num eixo, alinha pela borda de baixo/esquerda (a vista nao
    cabe - quem chama avisa)."""
    def eixo(a0, a1, b0, b1):
        if a1 - a0 >= b1 - b0:
            return b0 - a0
        if a0 < b0:
            return b0 - a0
        if a1 > b1:
            return b1 - a1
        return 0.0
    return (eixo(r[0], r[2], limite[0], limite[2]),
            eixo(r[1], r[3], limite[1], limite[3]))


def lugar_livre(largura_mm, altura_mm, area_util, bloqueios, folga=6.0, passo=5.0):
    """Centro (x, y) do primeiro lugar - de cima para baixo, da esquerda
    para a direita - onde um retangulo largura x altura cabe na area util
    sem encostar (folga) em nenhum bloqueio (carimbo e outras vistas).
    None se nao couber em lugar nenhum."""
    x0, y0, x1, y1 = area_util
    if largura_mm > x1 - x0 or altura_mm > y1 - y0:
        return None
    bloq = [(b[0] - folga, b[1] - folga, b[2] + folga, b[3] + folga) for b in bloqueios or []]
    y = y1 - altura_mm
    while y >= y0 - 1e-6:
        x = x0
        while x + largura_mm <= x1 + 1e-6:
            r = (x, y, x + largura_mm, y + altura_mm)
            choque = None
            for b in bloq:
                if sobrepoe(r, b, 0.0):
                    choque = b
                    break
            if choque is None:
                return centro(r)
            x = max(x + passo, choque[2]) if choque[2] > x else x + passo
        y -= passo
    return None


def problemas(r, area_util, obstaculos, outras):
    """Lista de textos curtos do que esta errado com o retangulo r."""
    saida = []
    if area_util is not None and not contem(area_util, r):
        saida.append(u"fora da área útil")
    for ob in obstaculos or []:
        if sobrepoe(r, ob):
            saida.append(u"em cima do carimbo")
            break
    for nome, outra in outras or []:
        if sobrepoe(r, outra):
            saida.append(u"sobre %s" % nome)
    return saida


# ============================================================
# 2. ENCAIXE (snap)
# ============================================================
def alvos_de_encaixe(area_util, obstaculos, outras):
    """(alvos_x, alvos_y): listas de valores em mm onde uma borda ou o
    centro da vista arrastada 'gruda'. `outras` = retangulos das outras
    vistas (a arrastada fica de fora)."""
    xs, ys = [], []
    for r in ([area_util] if area_util else []) + list(obstaculos or []):
        xs.extend([r[0], r[2]])
        ys.extend([r[1], r[3]])
    if area_util:
        cx, cy = centro(area_util)
        xs.append(cx)
        ys.append(cy)
    for r in outras or []:
        cx, cy = centro(r)
        xs.extend([r[0], cx, r[2]])
        ys.extend([r[1], cy, r[3]])
    return xs, ys


def _melhor_encaixe(proprios, alvos, tol):
    """Menor correcao que leva um dos valores `proprios` a um `alvo`."""
    melhor = None
    for p in proprios:
        for a in alvos:
            d = a - p
            if abs(d) <= tol and (melhor is None or abs(d) < abs(melhor[0])):
                melhor = (d, a)
    return melhor


def encaixar(r, alvos_x, alvos_y, tol):
    """(r_encaixado, guias). guias = [('x', valor) | ('y', valor)] - as
    linhas-guia que a janela desenha enquanto arrasta. tol em mm (a
    janela converte os pixels de tolerancia para mm pela escala)."""
    cx, cy = centro(r)
    guias = []
    dx = dy = 0.0
    ex = _melhor_encaixe([r[0], cx, r[2]], alvos_x, tol)
    if ex is not None:
        dx = ex[0]
        guias.append(('x', ex[1]))
    ey = _melhor_encaixe([r[1], cy, r[3]], alvos_y, tol)
    if ey is not None:
        dy = ey[0]
        guias.append(('y', ey[1]))
    return mover(r, dx, dy), guias


# ============================================================
# 3. TELA (mm <-> pixel)
# ============================================================
class Transformacao(object):
    """Encaixa o retangulo da folha (mm) num canvas de W x H pixels,
    centralizado, com margem. Y do papel sobe; Y da tela desce."""

    def __init__(self, folha, largura_px, altura_px, margem_px=24.0):
        self.folha = folha
        uw = max(1.0, largura_px - 2 * margem_px)
        uh = max(1.0, altura_px - 2 * margem_px)
        self.escala = min(uw / max(largura(folha), 1e-6),
                          uh / max(altura(folha), 1e-6))   # px por mm
        self.ox = (largura_px - largura(folha) * self.escala) / 2.0
        self.oy = (altura_px - altura(folha) * self.escala) / 2.0

    def para_tela(self, x, y):
        return (self.ox + (x - self.folha[0]) * self.escala,
                self.oy + (self.folha[3] - y) * self.escala)

    def para_folha(self, px, py):
        return (self.folha[0] + (px - self.ox) / self.escala,
                self.folha[3] - (py - self.oy) / self.escala)

    def ret_para_tela(self, r):
        """(esquerda, topo, largura, altura) em pixels."""
        esq, topo = self.para_tela(r[0], r[3])
        return (esq, topo, largura(r) * self.escala, altura(r) * self.escala)

    def px_para_mm(self, px):
        return px / self.escala


# ============================================================
# 4. PAPEL + AREA UTIL - REGRA MEDIDA NAS FAMILIAS REAIS (v0.3, 26/09/2026)
# ============================================================
# O que a medicao mostrou nas familias SYNC_HID_FOLHA_R04 e SYNC_FOLHA
# PARAMETRICA_R01 (22 formatos):
#   - o Revit NAO devolve a geometria do carimbo na folha (get_Geometry =
#     None ate' em folha salva); so' abrindo a familia (EditFamily);
#   - o documento da familia mostra UM estado so' (trocar o tipo nao move
#     linha): todos os formatos desenhados juntos, presos no canto
#     INFERIOR DIREITO;
#   - o papel de cada formato = esquerda e baixo do bounding box do
#     carimbo + Largura/Altura da folha (SHEET_WIDTH/HEIGHT); o bounding
#     box passa 13-17 mm do papel pela DIREITA (algo fora do papel);
#   - margens pelas linhas: 25 esq, 10 dir e baixo, 10 em cima nos A1 e 7
#     nos A2 (NBR 10068); carimbo = coluna de linhas de 175 mm encostadas
#     na margem direita (ate' y 378,6 na HID, 480,0 na PARAMETRICA).
NBR_ESQ = 25.0


def papel_do_formato(caixa_carimbo, largura_folha, altura_folha):
    """Retangulo do papel. caixa_carimbo = bounding box da instancia na
    folha; largura/altura = parametros Largura/Altura da folha."""
    return (caixa_carimbo[0], caixa_carimbo[1],
            caixa_carimbo[0] + largura_folha, caixa_carimbo[1] + altura_folha)


def area_util_padrao(papel, margens, carimbo):
    """Area util = papel - margens - carimbo (canto inferior direito).
    margens = (esq, baixo, dir, cima); carimbo = (largura, altura). E' o
    caminho do plugin (padroes.py); area_util_por_regra so' serviu para
    medir esses numeros nas familias.

    area_centro = onde a CENTRALIZACAO acontece (Lucas, 29/09/2026): o
    quadro inteiro, da margem esquerda ate' a esquerda do carimbo, na
    altura toda - a faixa vertical do carimbo e' ignorada mesmo acima dele
    (o carimbo baixo deixa espaco livre em cima, mas a vista nao vai la')."""
    esq, baixo, dir_, cima = margens
    quadro = (papel[0] + esq, papel[1] + baixo, papel[2] - dir_, papel[3] - cima)
    cl, ca = carimbo
    carimbo_ret = (quadro[2] - cl, quadro[1], quadro[2], min(quadro[1] + ca, quadro[3]))
    coluna = carimbo_ret[3] >= quadro[3] - TOL_MM
    return {u'externo': papel, u'quadro': quadro, u'carimbo': carimbo_ret,
            u'tipo': 'coluna' if coluna else 'canto',
            u'area_centro': (quadro[0], quadro[1], carimbo_ret[0], quadro[3]),
            u'area_util': (quadro[0], quadro[1], carimbo_ret[0], quadro[3]) if coluna else quadro,
            u'obstaculos': [] if coluna else [carimbo_ret],
            u'confianca': u'alta', u'margens': tuple(margens)}


def _margem_nbr(papel):
    return 10.0 if max(largura(papel), altura(papel)) >= 840.0 else 7.0


def _moda(valores, passo=0.5):
    contagem = {}
    for v in valores:
        k = round(v / passo) * passo
        contagem[k] = contagem.get(k, 0) + 1
    if not contagem:
        return None
    return max(sorted(contagem), key=lambda k: contagem[k])


def area_util_por_regra(papel, linhas, tol=TOL_MM, busca=30.0):
    """Area util de UM formato: o papel vem do projeto
    (papel_do_formato), as margens e o carimbo das linhas da familia (nas
    mesmas coordenadas - instancia na origem). O que nao achar nas linhas
    cai na NBR 10068 e fica anotado em 'origem'.

    Retorna o mesmo dict de detectar_area_util + 'margens' (esq, baixo,
    dir, cima) e 'origem' {lado: 'familia' | 'NBR'}."""
    horiz, vert = _ortogonais(linhas, tol)
    x0, y0, x1, y1 = papel
    nbr = _margem_nbr(papel)
    origem = {}

    def escolher(lado, candidatos, padrao):
        if candidatos:
            origem[lado] = u'familia'
            return candidatos
        origem[lado] = u'NBR'
        return [padrao]

    # direita: vertical logo para dentro da borda direita que cobre boa
    # parte da altura do papel (pode passar dele: no A2 a linha e' a do A1)
    m_dir = min(escolher(u'dir', [x1 - v[0] for v in vert
                                  if tol < x1 - v[0] <= busca
                                  and min(v[2], y1) - max(v[1], y0) >= 0.5 * altura(papel)], nbr))
    xi = x1 - m_dir
    # baixo e cima: horizontais que chegam na margem direita
    chega = [h for h in horiz if abs(h[2] - xi) <= 1.0]
    m_baixo = min(escolher(u'baixo', [h[0] - y0 for h in chega if tol < h[0] - y0 <= busca], nbr))
    m_cima = min(escolher(u'cima', [y1 - h[0] for h in chega if tol < y1 - h[0] <= busca], nbr))
    # esquerda: distancia entre a borda de um formato (vertical que nasce
    # no pe' do papel) e a linha do quadro dele (nasce no pe' do quadro)
    externas = [v for v in vert if abs(v[1] - y0) <= tol]
    internas = [v for v in vert if abs(v[1] - (y0 + m_baixo)) <= tol]
    pares = [i[0] - e[0] for e in externas for i in internas if 5.0 <= i[0] - e[0] <= 40.0]
    m_esq = _moda(pares)
    if m_esq is None:
        m_esq = NBR_ESQ
        origem[u'esq'] = u'NBR'
    else:
        origem[u'esq'] = u'familia'

    quadro = (x0 + m_esq, y0 + m_baixo, x1 - m_dir, y1 - m_cima)

    # carimbo: horizontais que terminam na margem direita e comecam longe
    # da esquerda do quadro; a esquerda mais comum e' a borda do carimbo
    linhas_carimbo = [h for h in chega if quadro[1] - tol <= h[0] <= quadro[3] + tol
                      and h[1] > quadro[0] + 0.25 * largura(quadro)]
    esq_carimbo = _moda([h[1] for h in linhas_carimbo])
    carimbo, tipo = None, None
    if esq_carimbo is not None:
        mesmas = [h for h in linhas_carimbo if abs(h[1] - esq_carimbo) <= 1.0]
        if len(mesmas) >= 3:
            topo = min(max(h[0] for h in mesmas), quadro[3])
            carimbo = (esq_carimbo, quadro[1], quadro[2], topo)
            tipo = 'coluna' if topo >= quadro[3] - tol else 'canto'

    if carimbo is None:
        util, obst = quadro, []
    elif tipo == 'coluna':
        util, obst = (quadro[0], quadro[1], carimbo[0], quadro[3]), []
    else:
        util, obst = quadro, [carimbo]
    todas_da_familia = all(v == u'familia' for v in origem.values())
    confianca = u'alta' if (carimbo is not None and todas_da_familia) else (
        u'media' if carimbo is not None or todas_da_familia else u'baixa')
    return {u'externo': papel, u'quadro': quadro, u'carimbo': carimbo, u'tipo': tipo,
            u'area_util': util, u'obstaculos': obst, u'confianca': confianca,
            u'margens': (m_esq, m_baixo, m_dir, m_cima), u'origem': origem}


# ============================================================
# 5. AREA UTIL A PARTIR DAS LINHAS DO CARIMBO  (1a SUPOSICAO - nao serve
#    para as familias reais: elas nao tem os retangulos fechados)
# ============================================================
def _ortogonais(segmentos, tol=TOL_MM):
    """Separa horizontais (y, x0, x1) e verticais (x, y0, y1); descarta
    diagonais e pontos."""
    horiz, vert = [], []
    for (xa, ya), (xb, yb) in segmentos:
        if abs(ya - yb) <= tol and abs(xa - xb) > tol:
            horiz.append(((ya + yb) / 2.0, min(xa, xb), max(xa, xb)))
        elif abs(xa - xb) <= tol and abs(ya - yb) > tol:
            vert.append(((xa + xb) / 2.0, min(ya, yb), max(ya, yb)))
    return _fundir(horiz, tol), _fundir(vert, tol)


def _fundir(linhas, tol):
    """Junta linhas colineares que se tocam ou se sobrepoem."""
    saida = []
    for c, a, b in sorted(linhas):
        if saida:
            c0, a0, b0 = saida[-1]
            if abs(c - c0) <= tol and a <= b0 + tol:
                saida[-1] = (c0, a0, max(b0, b))
                continue
        saida.append((c, a, b))
    return saida


def _coberto(linhas, c, a, b, tol):
    """True se [a, b] na coordenada c e' coberto por UMA linha fundida."""
    for lc, la, lb in linhas:
        if abs(lc - c) <= tol and la <= a + tol and lb >= b - tol:
            return True
    return False


def _retangulos_longos(horiz, vert, externo, tol, fracao=0.5):
    """Retangulos fechados feitos so' de linhas longas (>= fracao do
    externo). Sao poucas - borda de corte, quadro, coluna de carimbo."""
    lh = [h for h in horiz if h[2] - h[1] >= fracao * largura(externo)]
    lv = [v for v in vert if v[2] - v[1] >= fracao * altura(externo)]
    ys = sorted(set(round(h[0], 3) for h in lh))
    xs = sorted(set(round(v[0], 3) for v in lv))
    achados = []
    for i, ya in enumerate(ys):
        for yb in ys[i + 1:]:
            for j, xa in enumerate(xs):
                for xb in xs[j + 1:]:
                    if (_coberto(horiz, ya, xa, xb, tol) and _coberto(horiz, yb, xa, xb, tol)
                            and _coberto(vert, xa, ya, yb, tol) and _coberto(vert, xb, ya, yb, tol)):
                        achados.append((xa, ya, xb, yb))
    return achados


def _achar_quadro(horiz, vert, externo, tol):
    rets = _retangulos_longos(horiz, vert, externo, tol)
    if not rets:
        return None
    por_dentro = [r for r in rets
                  if r[0] > externo[0] + 1.0 and r[1] > externo[1] + 1.0
                  and r[2] < externo[2] - 1.0 and r[3] < externo[3] - 1.0]
    return max(por_dentro or rets, key=area)


def _achar_carimbo(quadro, horiz, vert, tol):
    """(retangulo do carimbo, tipo). tipo: 'canto' | 'coluna' | 'faixa'.

    Canto/coluna: a vertical MAIS A ESQUERDA que nasce no pe' do quadro,
    e cujo topo termina numa horizontal que vai ate' a borda direita (ou
    no topo do quadro = coluna inteira). Faixa: a horizontal de largura
    inteira mais alta no terco de baixo do quadro."""
    x0, y0, x1, y1 = quadro
    candidatas = sorted(v for v in vert
                        if x0 + tol < v[0] < x1 - tol and abs(v[1] - y0) <= tol)
    for c, _, topo in candidatas:
        if topo >= y1 - tol:
            return (c, y0, x1, y1), 'coluna'
        if _coberto(horiz, topo, x0, x1, tol):
            continue        # divisoria de uma FAIXA de largura inteira
        if _coberto(horiz, topo, c, x1, tol):
            return (c, y0, x1, topo), 'canto'
    faixa = [h for h in horiz
             if y0 + tol < h[0] < y0 + 0.34 * altura(quadro)
             and h[1] <= x0 + tol and h[2] >= x1 - tol]
    if faixa:
        topo = max(h[0] for h in faixa)
        return (x0, y0, x1, topo), 'faixa'
    return None, None


def detectar_area_util(segmentos, tol=TOL_MM):
    """Le as linhas da familia de titulo (mm, coordenadas da folha).

    Retorna dict:
      externo   - envelope de todas as linhas (o papel, se houver linha
                  de corte);
      quadro    - o retangulo da margem (ou o externo, se nao achou);
      carimbo   - retangulo do carimbo ou None;
      tipo      - 'canto' | 'coluna' | 'faixa' | None;
      area_util - onde as vistas podem ficar (retangulo);
      obstaculos- retangulos proibidos DENTRO da area util (o carimbo
                  de canto - a area util fica em L);
      confianca - 'alta' (quadro + carimbo achados), 'media' (so'
                  quadro), 'baixa' (nada - usa o envelope).
    """
    horiz, vert = _ortogonais(segmentos, tol)
    todos = [(h[1], h[0], h[2], h[0]) for h in horiz] + [(v[0], v[1], v[0], v[2]) for v in vert]
    externo = uniao([ret(*t) for t in todos]) if todos else None
    if externo is None:
        return {u'externo': None, u'quadro': None, u'carimbo': None, u'tipo': None,
                u'area_util': None, u'obstaculos': [], u'confianca': u'baixa'}

    quadro = _achar_quadro(horiz, vert, externo, tol)
    if quadro is None:
        return {u'externo': externo, u'quadro': externo, u'carimbo': None, u'tipo': None,
                u'area_util': externo, u'obstaculos': [], u'confianca': u'baixa'}

    carimbo, tipo = _achar_carimbo(quadro, horiz, vert, tol)
    if carimbo is None:
        util, obst, conf = quadro, [], u'media'
    elif tipo == 'coluna':
        util, obst, conf = (quadro[0], quadro[1], carimbo[0], quadro[3]), [], u'alta'
    elif tipo == 'faixa':
        util, obst, conf = (quadro[0], carimbo[3], quadro[2], quadro[3]), [], u'alta'
    else:
        util, obst, conf = quadro, [carimbo], u'alta'
    return {u'externo': externo, u'quadro': quadro, u'carimbo': carimbo, u'tipo': tipo,
            u'area_util': util, u'obstaculos': obst, u'confianca': conf}
