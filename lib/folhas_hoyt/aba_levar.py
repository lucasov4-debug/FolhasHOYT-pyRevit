# -*- coding: utf-8 -*-
"""Aba Levar folhas da janela Folhas HOYT."""
from . import eid, folhas, transferir, ui


def montar(janela, doc, erro, api, app):
    """Liga a aba; devolve recarregar()."""
    def f(n):
        return janela.FindName(u'l_' + n)

    tabela = ui.Tabela(f(u'grade'), f(u'filtro'), f(u'todas'))
    sheets = {}
    destinos = []

    def recarregar():
        sheets.clear()
        itens = []
        idx = folhas.indice(doc)
        for s in folhas.todas(doc):
            sheets[eid(s.Id)] = s
            leg = folhas.nome_legendas(doc, s, idx)
            itens.append(ui.item(Marcado=False, Chave=eid(s.Id), Numero=s.SheetNumber, NomeFolha=s.Name,
                                 Legenda=leg, Busca=(s.SheetNumber + u' ' + s.Name + u' ' + leg).lower()))
        tabela.carregar(itens)
        f(u'info').Text = ui.plural(len(itens), u'folha', u'folhas')
        atualizar_destinos()

    def atualizar_destinos():
        antes = f(u'destino').SelectedItem
        del destinos[:]
        f(u'destino').Items.Clear()
        for d in transferir.documentos_destino(app, doc):
            destinos.append(d)
            f(u'destino').Items.Add(d.Title)
        if destinos:
            f(u'destino').SelectedItem = antes if antes in [d.Title for d in destinos] else destinos[0].Title
        f(u'status').Text = u'' if destinos else u'Abra o documento de destino no Revit e clique em "Atualizar lista".'

    def levar(a=None, e=None):
        alvo = [sheets[ui.campo(i, u'Chave')] for i in tabela.marcados()]
        idx = f(u'destino').SelectedIndex
        if not alvo or idx < 0:
            f(u'status').Text = u'Marque as folhas e escolha o documento de destino.'
            return
        destino = destinos[idx]
        if not ui.confirmar(u'Levar %s para "%s"?' % (ui.plural(len(alvo), u'folha', u'folhas'), destino.Title)):
            return
        criadas, avisos = transferir.levar(doc, destino, alvo)
        f(u'status').Text = u'%d folha(s) criada(s) em %s.' % (len(criadas), destino.Title)
        texto = u'%d folha(s) criada(s) em "%s": %s' % (len(criadas), destino.Title, u', '.join(criadas))
        if avisos:
            texto += u'\n\nAtenção:\n' + u'\n'.join(avisos)
        ui.avisar(texto + u'\n\nCtrl+Z (no documento de destino) desfaz.')

    f(u'levar').Click += api(levar)
    f(u'atualizar').Click += api(lambda a, e: atualizar_destinos())
    return recarregar
