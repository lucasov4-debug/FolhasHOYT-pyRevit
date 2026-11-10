# -*- coding: utf-8 -*-
"""Aba Tamanhos: padrões reutilizáveis e medidas manuais por folha.
Recentralizar usa o tamanho atual da área útil e continua como ação separada."""
import os

from . import casar, eid, folhas, padroes_tamanho, ui


def _cm(v):
    return u'' if v is None else (u'%.2f' % v).replace(u'.', u',')


def montar(janela, doc, erro, api):
    """Liga a aba; devolve recarregar()."""
    def f(n):
        return janela.FindName(u't_' + n)

    tabela = ui.Tabela(f(u'grade'), f(u'filtro'), f(u'todas'))
    sheets = {}
    padroes = {}

    def opcoes_padrao():
        itens = [ui.item(Chave=u'', Texto=u'Manter tamanho atual')]
        for chave, medidas in sorted(padroes.items(), key=lambda p: p[0].lower()):
            alt, larg = medidas
            itens.append(ui.item(Chave=chave, Texto=u'%s — %s × %s cm' %
                                 (chave, _cm(larg), _cm(alt))))
        return ui.lista(itens)

    def carregar_padroes():
        padroes.clear()
        for chave, alt, larg in padroes_tamanho.PADROES_FIXOS:
            padroes[chave] = (alt, larg)
        try:
            for chave, alt, larg in padroes_tamanho.ler():
                padroes[chave] = (alt, larg)
        except Exception as ex:
            ui.avisar(u'Não foi possível ler os padrões salvos: %s' % ex)

    def recarregar(manter=False):
        guardado = {}
        if manter:
            ui.confirmar_edicao(f(u'grade'))
            for i in tabela.itens:
                guardado[ui.campo(i, u'Chave')] = (
                    ui.campo(i, u'Padrao'), ui.campo(i, u'Marcado'),
                    ui.campo(i, u'AlturaManual'), ui.campo(i, u'LarguraManual'))
        carregar_padroes()
        opcoes = opcoes_padrao()
        sheets.clear()
        idx = folhas.indice(doc)
        itens = []
        for s in folhas.todas(doc):
            k = eid(s.Id)
            sheets[k] = s
            c = folhas.carimbo(doc, s, idx)
            alt, larg = folhas.tamanho_atual(c) if c is not None else (None, None)
            it = ui.item(Marcado=False, Chave=k, Numero=s.SheetNumber, NomeFolha=s.Name,
                         TipoFolha=folhas.tipo_do_carimbo(doc, s, idx),
                         Altura=_cm(alt), Largura=_cm(larg), Padrao=u'',
                         AlturaManual=u'', LarguraManual=u'', Opcoes=opcoes,
                         AlturaCm=alt, LarguraCm=larg,
                         Busca=(s.SheetNumber + u' ' + s.Name).lower())
            if k in guardado:
                ui.definir(it, u'Padrao', guardado[k][0])
                ui.definir(it, u'Marcado', guardado[k][1])
                ui.definir(it, u'AlturaManual', guardado[k][2])
                ui.definir(it, u'LarguraManual', guardado[k][3])
            itens.append(it)
        tabela.carregar(itens)
        f(u'info').Text = ui.plural(len(itens), u'folha', u'folhas')

    def status(texto):
        f(u'status').Text = texto

    def relatorio(titulo, avisos):
        if avisos:
            ui.avisar(u'%s\n\nAtenção:\n%s\n\nCtrl+Z desfaz.' % (titulo, u'\n'.join(avisos)))

    def alvos():
        marcados = tabela.marcados()
        if marcados:
            return marcados
        sel = list(f(u'grade').SelectedItems)
        sel.sort(key=lambda i: f(u'grade').Items.IndexOf(i))
        return sel

    def aplicar(a=None, e=None):
        ui.confirmar_edicao(f(u'grade'))
        mudancas, invalidos = [], []
        for i in tabela.itens:
            chave = ui.campo(i, u'Padrao') or u''
            alt_txt = (ui.campo(i, u'AlturaManual') or u'').strip()
            larg_txt = (ui.campo(i, u'LarguraManual') or u'').strip()
            if not chave and not alt_txt and not larg_txt:
                continue
            try:
                alt, larg = padroes_tamanho.resolver(chave, alt_txt, larg_txt, padroes)
            except ValueError as ex:
                invalidos.append(u'%s: %s' % (ui.campo(i, u'Numero'), ex))
                continue
            atual_alt, atual_larg = ui.campo(i, u'AlturaCm'), ui.campo(i, u'LarguraCm')
            if ((alt is not None and (atual_alt is None or abs(atual_alt - alt) > 0.01)) or
                    (larg is not None and (atual_larg is None or abs(atual_larg - larg) > 0.01))):
                mudancas.append((sheets[ui.campo(i, u'Chave')], alt, larg))
        if invalidos:
            ui.avisar(u'Corrija antes de aplicar:\n%s' % u'\n'.join(invalidos))
            return
        if not mudancas:
            status(u'Nenhuma medida pendente para aplicar.')
            return
        if not ui.confirmar(u'Aplicar as medidas pendentes em %s?\n\nAltura e largura serão gravadas no carimbo. Ctrl+Z desfaz.' %
                            ui.plural(len(mudancas), u'folha', u'folhas')):
            return
        n, avisos = folhas.definir_tamanho(doc, mudancas)
        recarregar()
        status(u'Medidas gravadas em %d folha(s); %d aviso(s).' % (n, len(avisos)))
        ui.avisar(u'Medidas gravadas em %d folha(s).' % n)
        relatorio(u'Medidas gravadas em %d folha(s).' % n, avisos)

    def abrir_padrao(a=None, e=None):
        pasta = os.path.dirname(os.path.abspath(__file__))
        popup = ui.carregar_janela(pasta, u'PadraoTamanho.xaml', u'Cadastrar padrão de tamanho')
        popup.Owner = janela  # a janela principal já foi exibida quando há clique

        def campo(n):
            return popup.FindName(u'p_' + n)

        def salvar(a=None, e=None):
            try:
                chave, alt, larg = padroes_tamanho.salvar(
                    campo(u'nome').Text, campo(u'altura').Text,
                    campo(u'largura').Text)
            except Exception as ex:
                campo(u'status').Text = u'Padrão não salvo: %s' % ex
                return
            padroes[chave] = (alt, larg)
            opcoes = opcoes_padrao()
            for item in tabela.itens:
                ui.definir(item, u'Opcoes', opcoes)
            tabela.mostrar()
            status(u'Padrão "%s" salvo na lista. Nenhuma folha foi alterada.' % chave)
            popup.Close()

        campo(u'salvar').Click += s(salvar)
        campo(u'cancelar').Click += s(lambda a, e: popup.Close())
        popup.ShowDialog()

    def recentralizar(a=None, e=None):
        alvo = [sheets[ui.campo(i, u'Chave')] for i in alvos()]
        if not alvo:
            status(u'Marque (ou selecione) as folhas a recentralizar.')
            ui.avisar(u'Marque (ou selecione) as folhas cujas vistas devem ser recentralizadas.')
            return
        if not ui.confirmar(u'Recentralizar as vistas de %s na área útil?\n\nCtrl+Z desfaz.' %
                            ui.plural(len(alvo), u'folha', u'folhas')):
            return
        n, avisos = casar.recentralizar(doc, alvo)
        recarregar(True)
        status(u'Vistas recentralizadas em %d folha(s).' % n)
        ui.avisar(u'Vistas recentralizadas em %d folha(s).' % n)
        relatorio(u'Vistas recentralizadas em %d folha(s).' % n, avisos)

    def s(fn):
        return ui.proteger(erro, fn)

    f(u'aplicar').Click += api(aplicar)
    f(u'abrir_padrao').Click += s(abrir_padrao)
    f(u'recentralizar').Click += api(recentralizar)
    f(u'desfazer').Click += api(lambda a, e: (recarregar(), status(u'Edições descartadas.')))
    return recarregar
