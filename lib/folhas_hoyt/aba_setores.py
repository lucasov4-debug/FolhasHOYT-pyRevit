# -*- coding: utf-8 -*-
"""Aba Setores da janela Folhas HOYT: marca as vistas-setor de referencia
(ex.: os 4 setores do terreo), marca as plantas de destino, define quantos
setores cada uma recebe e replica."""
from System.Windows import RoutedEventHandler
from System.Windows.Controls import CheckBox

from . import eid, nome, regras, setores, ui, vistas


def montar(janela, doc, erro, api):
    """Liga a aba; devolve recarregar()."""
    def f(n):
        return janela.FindName(u's_' + n)

    refs_tab = ui.Tabela(f(u'grade_r'), f(u'filtro_r'))
    dest_tab = ui.Tabela(f(u'grade_d'), f(u'filtro_d'), f(u'todas_d'))
    views = {}

    def recarregar():
        views.clear()
        itens_r, itens_d = [], []
        for v in vistas.listar(doc):
            k, n = eid(v.Id), nome(v)
            views[k] = v
            caixa = setores.caixa_no_modelo(v)
            base = dict(Marcado=False, Chave=k, Nome=n, Escala=vistas.escala(v), Busca=n.lower())
            itens_r.append(ui.item(X=caixa[0] if caixa else None, Setor=u'',
                                   Recorte=u'sim' if caixa and v.CropBoxActive else u'não', **base))
            itens_d.append(ui.item(Qtd=u'', **base))
        refs_tab.carregar(itens_r)
        dest_tab.carregar(itens_d)
        f(u'info').Text = ui.plural(len(itens_d), u'planta', u'plantas')
        atualizar_refs()

    def refs_marcadas():
        """[(chave, x)] das referencias marcadas, da esquerda para a direita."""
        marc = [i for i in refs_tab.itens if ui.campo(i, u'Marcado') and ui.campo(i, u'X') is not None]
        marc.sort(key=lambda i: ui.campo(i, u'X'))
        return marc

    def atualizar_refs():
        ui.confirmar_edicao(f(u'grade_r'))
        marc = refs_marcadas()
        try:
            inicio = int(f(u'inicio').Text)
        except Exception:
            inicio = 5
        for i in refs_tab.itens:
            ui.definir(i, u'Setor', u'')
        for k, i in enumerate(marc):
            ui.definir(i, u'Setor', setores.codigo(inicio, k))
        refs_tab.mostrar()
        f(u'resumo').Text = (u'%d setor(es) de referência, da esquerda para a direita: %s'
                             % (len(marc), u', '.join(ui.campo(i, u'Setor') for i in marc))) if marc else \
            u'Marque à esquerda as vistas-setor de referência (ex.: os 4 setores do térreo).'

    def status(texto):
        f(u'status').Text = texto

    def aplicar_qtd():
        alvo = dest_tab.marcados()
        q = f(u'qtd').Text.strip()
        for i in alvo:
            ui.definir(i, u'Qtd', q)
        dest_tab.mostrar()
        status(u'Nº de setores = %s definido em %d planta(s).' % (q or u'(todos)', len(alvo)))

    def replicar(a=None, e=None):
        ui.confirmar_edicao(f(u'grade_d'))
        marc = refs_marcadas()
        if not marc:
            status(u'Marque ao menos uma vista de referência.')
            return
        chaves_ref = set(ui.campo(i, u'Chave') for i in marc)
        refs = [views[ui.campo(i, u'Chave')] for i in marc]
        alvos, ignoradas = [], []
        for i in dest_tab.marcados():
            k = ui.campo(i, u'Chave')
            if k in chaves_ref:
                ignoradas.append(ui.campo(i, u'Nome'))
                continue
            n = regras.inteiro(ui.campo(i, u'Qtd'), len(refs)) if (ui.campo(i, u'Qtd') or u'').strip() else len(refs)
            n = max(0, min(n, len(refs)))
            if n:
                alvos.append((views[k], n))
        if not alvos:
            status(u'Marque as plantas de destino (e confira o Nº de setores).')
            return
        total = sum(n for _v, n in alvos)
        if not ui.confirmar(u'Criar %d vista(s) de setor em %s?' % (total, ui.plural(len(alvos), u'planta', u'plantas'))):
            return
        try:
            inicio = int(f(u'inicio').Text)
        except Exception:
            inicio = 5
        criadas, avisos = setores.replicar(doc, refs, alvos, inicio, bool(f(u'anot').IsChecked))
        recarregar()
        status(u'%d vista(s) de setor criada(s).' % len(criadas))
        if ignoradas:
            avisos.append(u'Referências ignoradas como destino: %s' % u', '.join(ignoradas))
        if avisos:
            ui.avisar(u'%d vista(s) criada(s).\n\nAtenção:\n%s\n\nCtrl+Z desfaz tudo de uma vez.'
                      % (len(criadas), u'\n'.join(avisos)))

    def s(fn):
        return ui.proteger(erro, fn)

    f(u'grade_r').AddHandler(CheckBox.ClickEvent, RoutedEventHandler(s(lambda a, e: atualizar_refs())))
    f(u'inicio').TextChanged += s(lambda a, e: atualizar_refs())
    f(u'aplicar_qtd').Click += s(lambda a, e: aplicar_qtd())
    f(u'replicar').Click += api(replicar)
    return recarregar
