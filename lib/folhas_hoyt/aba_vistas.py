# -*- coding: utf-8 -*-
"""Aba Vistas da janela Folhas HOYT."""
from . import eid, nome, regras, ui, vistas


def montar(janela, doc, erro, api):
    """Liga a aba; devolve recarregar()."""
    def f(n):
        return janela.FindName(u'v_' + n)

    tabela = ui.Tabela(f(u'grade'), f(u'filtro'), f(u'todas'))
    views = {}

    def recarregar():
        views.clear()
        itens = []
        for v in vistas.listar(doc):
            n, t, folha = nome(v), vistas.titulo_da_pagina(v), vistas.folha_da_vista(v)
            views[eid(v.Id)] = v
            itens.append(ui.item(Marcado=False, Chave=eid(v.Id), Nome=n, NomeOrig=n, Titulo=t, TituloOrig=t,
                                 Tipo=u'%s' % v.ViewType, Escala=vistas.escala(v), Folha=folha,
                                 Busca=(n + u' ' + t + u' ' + folha).lower()))
        tabela.carregar(itens)
        f(u'info').Text = ui.plural(len(itens), u'planta', u'plantas')

    def status(texto):
        f(u'status').Text = texto

    def relatorio(titulo, falhas):
        if falhas:
            ui.avisar(u'%s\n\nAtenção:\n%s\n\nCtrl+Z desfaz.' % (titulo, u'\n'.join(falhas)))

    def duplicar(com_detalhe):   # roda dentro do ExternalEvent
        marcadas = [views[ui.campo(i, u'Chave')] for i in tabela.marcados()]
        if not marcadas:
            status(u'Marque ao menos uma vista.')
            return
        feitas, falhas = vistas.duplicar(doc, marcadas, com_detalhe)
        recarregar()
        status(u'%d duplicada(s).' % len(feitas))
        relatorio(u'%d duplicada(s).' % len(feitas), falhas)

    def previa():
        marcadas = tabela.marcados()
        for i in marcadas:
            ui.definir(i, u'Nome', regras.aplicar(ui.campo(i, u'NomeOrig'), f(u'pre').Text, f(u'suf').Text,
                                                   f(u'bus').Text, f(u'tro').Text))
        tabela.mostrar()
        status(u'Prévia em %d vista(s). Ajuste na tabela (F2) e clique em Aplicar.' % len(marcadas))

    def aplicar(a=None, e=None):
        ui.confirmar_edicao(f(u'grade'))
        mudancas = []
        for i in tabela.itens:
            n, t = (ui.campo(i, u'Nome') or u'').strip(), ui.campo(i, u'Titulo') or u''
            novo_n = n if n and n != ui.campo(i, u'NomeOrig') else None
            novo_t = t if t != ui.campo(i, u'TituloOrig') else None
            if novo_n is not None or novo_t is not None:
                mudancas.append((views[ui.campo(i, u'Chave')], novo_n, novo_t))
        if not mudancas:
            status(u'Nada editado para aplicar.')
            return
        feitas, falhas = vistas.renomear(doc, mudancas)
        recarregar()
        status(u'%d alteração(ões) aplicada(s).' % feitas)
        relatorio(u'%d alteração(ões) aplicada(s).' % feitas, falhas)

    def s(fn):
        return ui.proteger(erro, fn)

    f(u'dup').Click += api(lambda a, e: duplicar(False))
    f(u'dup_det').Click += api(lambda a, e: duplicar(True))
    f(u'previa').Click += s(lambda a, e: previa())
    f(u'aplicar').Click += api(aplicar)
    f(u'desfazer').Click += api(lambda a, e: (recarregar(), status(u'Edições descartadas.')))
    return recarregar
