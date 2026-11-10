# -*- coding: utf-8 -*-
"""Aba de inserção de uma legenda nas folhas marcadas."""
from . import eid, folhas, legendas, nome, ui


def montar(janela, doc, erro, api):
    def f(n):
        return janela.FindName(u'lg_' + n)

    tabela = ui.Tabela(f(u'grade'), f(u'filtro'), f(u'todas'))
    vistas = {}
    folhas_por_id = {}

    def recarregar():
        vistas.clear()
        folhas_por_id.clear()
        combo = f(u'legenda')
        anterior = combo.SelectedValue
        opcoes = []
        for vista in folhas.legendas_do_projeto(doc):
            chave = eid(vista.Id)
            vistas[chave] = vista
            opcoes.append(ui.item(Chave=chave, Texto=nome(vista)))
        combo.ItemsSource = ui.lista(opcoes)
        combo.DisplayMemberPath = u'Texto'
        combo.SelectedValuePath = u'Chave'
        if anterior in vistas:
            combo.SelectedValue = anterior
        elif opcoes:
            combo.SelectedIndex = 0
        idx = folhas.indice(doc)
        itens = []
        for folha in folhas.todas(doc):
            chave = eid(folha.Id)
            folhas_por_id[chave] = folha
            atual = folhas.nome_legendas(doc, folha, idx)
            itens.append(ui.item(Marcado=False, Chave=chave, Numero=folha.SheetNumber,
                                 NomeFolha=folha.Name, Legendas=atual or u'—',
                                 Busca=(folha.SheetNumber + u' ' + folha.Name + u' ' + atual).lower()))
        tabela.carregar(itens)
        f(u'info').Text = ui.plural(len(itens), u'folha', u'folhas')
        f(u'status').Text = u'Selecione a legenda e marque as folhas de destino.'

    def aplicar(a=None, e=None):
        chave = f(u'legenda').SelectedValue
        marcadas = tabela.marcados()
        if chave not in vistas or not marcadas:
            f(u'status').Text = u'Escolha uma legenda e marque pelo menos uma folha.'
            return
        vista = vistas[chave]
        alvo = [folhas_por_id[ui.campo(i, u'Chave')] for i in marcadas]
        existentes = sum(1 for folha in alvo if any(
            eid(vp.ViewId) == chave for vp in folhas.legendas_da_folha(doc, folha)))
        texto = (u'Inserir ou corrigir "%s" no canto superior direito interno de %d folha(s)?\n\n'
                 u'%d já contém esta legenda e terá posição e tipo de viewport corrigidos.\n'
                 u'Tipo aplicado: Viewport: No Title.\n'
                 u'A operação pode ser desfeita com Ctrl+Z.'
                 % (nome(vista), len(alvo), existentes))
        if not ui.confirmar(texto):
            return
        n, corrigidas, avisos = legendas.inserir(doc, alvo, vista)
        recarregar()
        f(u'status').Text = u'%d inserida(s), %d corrigida(s), %d falha(s).' % (n, corrigidas, len(avisos))
        ui.avisar(f(u'status').Text + (u'\n\n' + u'\n'.join(avisos) if avisos else u''))

    f(u'aplicar').Click += api(aplicar)
    return recarregar
