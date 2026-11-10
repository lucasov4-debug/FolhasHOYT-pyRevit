# -*- coding: utf-8 -*-
"""Aba Casar vistas e folhas da janela Folhas HOYT.

Cada folha tem um campo "Vista": o clique abre um dropdown (Popup) com busca
por nome e a lista das vistas disponiveis; escolhida a vista, a proxima folha
e' selecionada. "Posicionar" poe cada vista centralizada na area util."""
from System.Windows import RoutedEventHandler
from System.Windows.Controls import Button
from System.Windows.Input import Key

from . import casar, eid, folhas, nome, ui, vistas

SEM_VISTA = u'— escolher —'


def montar(janela, doc, erro, api):
    """Liga a aba; devolve recarregar()."""
    def f(n):
        return janela.FindName(u'c_' + n)

    grade = f(u'grade_f')
    views, sheets = {}, {}
    nomes_v, rotulos_v, ja_em_folha = {}, {}, {}   # lidos ao carregar (a tela nao toca na API)
    itens_f = []
    pares = {}                  # chave da folha -> chave da vista
    estado = {u'folha': None}   # folha cujo dropdown esta aberto

    def recarregar():
        views.clear()
        sheets.clear()
        nomes_v.clear()
        rotulos_v.clear()
        ja_em_folha.clear()
        del itens_f[:]
        idx = folhas.indice(doc)
        for v, em_folha in casar.vistas_do_projeto(doc):
            k = eid(v.Id)
            views[k] = v
            nomes_v[k] = nome(v)
            rotulos_v[k] = u'%s   ·   %s %s%s' % (nome(v), u'%s' % v.ViewType, vistas.escala(v),
                                                  (u'   ·   já em ' + em_folha) if em_folha else u'')
            ja_em_folha[k] = bool(em_folha)
        for s in folhas.todas(doc):
            k = eid(s.Id)
            sheets[k] = s
            n = len(folhas.viewports_da_folha(doc, s, idx)) - len(folhas.legendas_da_folha(doc, s, idx))
            itens_f.append(ui.item(Chave=k, Numero=s.SheetNumber, NomeFolha=s.Name, Vistas=n, VistaTxt=SEM_VISTA,
                                   Busca=(s.SheetNumber + u' ' + s.Name).lower()))
        for k in [k for k, v in pares.items() if k not in sheets or v not in views]:
            del pares[k]
        mostrar()

    def mostrar():
        t = f(u'filtro_f').Text.strip().lower()
        so_vazias = bool(f(u'sem_vista').IsChecked)
        for i in itens_f:
            k = ui.campo(i, u'Chave')
            ui.definir(i, u'VistaTxt', nomes_v[pares[k]] if k in pares else SEM_VISTA)
        visiveis = [i for i in itens_f
                    if (not t or t in ui.campo(i, u'Busca'))
                    and not (so_vazias and ui.campo(i, u'Vistas') and ui.campo(i, u'Chave') not in pares)]
        grade.ItemsSource = ui.lista(visiveis)
        f(u'pares').Text = ui.plural(len(pares), u'vista escolhida', u'vistas escolhidas')

    def status(t):
        f(u'status').Text = t

    # ------------------------------------------------ dropdown
    def opcoes():
        t = f(u'busca').Text.strip().lower()
        usadas = set(v for k, v in pares.items() if k != estado[u'folha'])
        ocultar = bool(f(u'ocultar').IsChecked)
        itens = [ui.item(Chave=None, Texto=u'(nenhuma)')]
        for k in sorted(views, key=lambda k: rotulos_v[k].lower()):
            if k in usadas or (ocultar and ja_em_folha[k] and pares.get(estado[u'folha']) != k):
                continue
            if t and t not in rotulos_v[k].lower():
                continue
            itens.append(ui.item(Chave=k, Texto=rotulos_v[k]))
        f(u'lista').ItemsSource = ui.lista(itens)

    def abrir_dropdown(sender, args):
        src = args.OriginalSource
        if not isinstance(src, Button) or src.DataContext is None:
            return
        estado[u'folha'] = ui.campo(src.DataContext, u'Chave')
        grade.SelectedItem = src.DataContext
        f(u'busca').Text = u''
        opcoes()
        p = f(u'popup')
        p.PlacementTarget = src
        p.IsOpen = True

    def escolher(chave):
        k = estado[u'folha']
        if k is None:
            return
        for outra in [s for s, v in pares.items() if v == chave and s != k]:
            del pares[outra]
        if chave is None:
            pares.pop(k, None)
        else:
            pares[k] = chave
        f(u'popup').IsOpen = False
        mostrar()
        # proxima folha da lista fica selecionada (escolha "uma a uma")
        itens = list(grade.Items)
        for n, i in enumerate(itens):
            if ui.campo(i, u'Chave') == k and n + 1 < len(itens):
                grade.SelectedItem = itens[n + 1]
                grade.ScrollIntoView(itens[n + 1])
                break

    def ao_escolher_na_lista(sender, args):
        sel = f(u'lista').SelectedItem
        if sel is not None:
            escolher(ui.campo(sel, u'Chave'))

    def ao_tecla_na_busca(sender, args):
        if args.Key == Key.Enter and f(u'lista').Items.Count > 1:
            escolher(ui.campo(f(u'lista').Items[1], u'Chave'))     # [0] e' "(nenhuma)"
        elif args.Key == Key.Down:
            f(u'lista').Focus()

    # ------------------------------------------------ posicionar
    def posicionar(a=None, e=None):
        if not pares:
            status(u'Escolha a vista de ao menos uma folha.')
            return
        lista = [(views[v], sheets[s]) for s, v in pares.items()]
        lista.sort(key=lambda p: p[1].SheetNumber)
        n, avisos = casar.posicionar(doc, lista)
        pares.clear()
        recarregar()
        status(u'%d vista(s) posicionada(s) e centralizada(s).' % n)
        if avisos:
            ui.avisar(u'%d vista(s) posicionada(s).\n\nAtenção:\n%s\n\nCtrl+Z desfaz tudo de uma vez.'
                      % (n, u'\n'.join(avisos)))

    def s(fn):
        return ui.proteger(erro, fn)

    grade.AddHandler(Button.ClickEvent, RoutedEventHandler(s(abrir_dropdown)))
    f(u'busca').TextChanged += s(lambda a, e: opcoes())
    f(u'busca').KeyDown += s(ao_tecla_na_busca)
    f(u'popup').Opened += s(lambda a, e: f(u'busca').Focus())
    f(u'lista').SelectionChanged += s(ao_escolher_na_lista)
    f(u'filtro_f').TextChanged += s(lambda a, e: mostrar())
    f(u'sem_vista').Click += s(lambda a, e: mostrar())
    f(u'limpar').Click += s(lambda a, e: (pares.clear(), mostrar()))
    f(u'posicionar').Click += api(posicionar)
    return recarregar
