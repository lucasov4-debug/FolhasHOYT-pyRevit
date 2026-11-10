# -*- coding: utf-8 -*-
"""Aba Folhas da janela Folhas HOYT.

Janela nao modal: so' o que escreve no Revit passa por `api` (ExternalEvent);
a tela le apenas dados guardados ao carregar (nomes, legendas por folha)."""
from System.Windows import RoutedEventHandler
from System.Windows.Controls import CheckBox

from . import casar, destaque, eid, folhas, nome, regras, ui


def montar(janela, doc, erro, api, ajustes):
    """Liga a aba; devolve recarregar()."""
    def f(n):
        return janela.FindName(u'f_' + n) or ajustes.FindName(u'f_' + n)

    def abrir_ajustes(a=None, e=None):
        if not ajustes.IsVisible:
            if ajustes.Owner is None:
                ajustes.Owner = janela
            ajustes.Show()
        ajustes.Activate()

    def ocultar_ajustes(a=None, e=None):
        ajustes.Hide()

    encerrando = [False]

    def ao_fechar_ajustes(sender, args):
        if not encerrando[0]:
            args.Cancel = True
            ajustes.Hide()

    def ao_fechar_principal(sender, args):
        encerrando[0] = True
        ajustes.Close()

    f(u'abrir_ajustes').Click += ui.proteger(erro, abrir_ajustes)
    ajustes.FindName(u'aj_fechar').Click += ui.proteger(erro, ocultar_ajustes)
    ajustes.Closing += ao_fechar_ajustes
    janela.Closed += ao_fechar_principal

    tabela = ui.Tabela(f(u'grade'), f(u'filtro'), f(u'todas'))
    sheets = {}
    leg_views, leg_nomes = {}, {}     # chave da legenda -> View / nome
    sai = []                          # chaves na mesma ordem do combo "sai"
    entra = []                        # [View] na mesma ordem do combo "entra"
    padroes = []                      # chaves das folhas na ordem do combo "padrao"
    tipos = []                      # [FamilySymbol] na ordem do combo "tipo_novo"

    def recarregar(manter=False):
        """manter=True: reaplica nas linhas que continuam existindo as edicoes
        ainda nao aplicadas (numero, nome, prancha) e as marcas."""
        guardado = {}
        if manter:
            ui.confirmar_edicao(f(u'grade'))
            for i in tabela.itens:
                guardado[ui.campo(i, u'Chave')] = dict(
                    (c, ui.campo(i, c)) for c in (u'Numero', u'NomeFolha', u'Prancha', u'Marcado'))
        sheets.clear()
        leg_views.clear()
        leg_nomes.clear()
        itens = []
        idx = folhas.indice(doc)
        novas = destaque.novas(doc)
        for s in folhas.todas(doc):
            k = eid(s.Id)
            sheets[k] = s
            vps = folhas.legendas_da_folha(doc, s, idx)
            chaves = []
            for vp in vps:
                v = doc.GetElement(vp.ViewId)
                leg_views[eid(v.Id)] = v
                leg_nomes[eid(v.Id)] = nome(v)
                chaves.append(eid(v.Id))
            leg = u'; '.join(leg_nomes[c] for c in chaves)
            pr, tem_pr = folhas.numero_prancha(s)
            n_vistas = len(folhas.viewports_da_folha(doc, s, idx)) - len(vps)
            itens.append(ui.item(Marcado=False, Chave=k, Numero=s.SheetNumber, NumeroOrig=s.SheetNumber,
                                 NomeFolha=s.Name, NomeOrig=s.Name, TipoFolha=folhas.tipo_do_carimbo(doc, s, idx), Prancha=pr, PranchaOrig=pr,
                                 PranchaOk=tem_pr, Legenda=leg, Nova=s.UniqueId in novas, Marca=(u'● NOVA' if s.UniqueId in novas else u''), Chaves=chaves, Vistas=n_vistas,
                                 Busca=(s.SheetNumber + u' ' + s.Name + u' ' + leg + u' ' + pr).lower()))
        for it in itens:
            for c, v in guardado.get(ui.campo(it, u'Chave'), {}).items():
                ui.definir(it, c, v)
        tabela.carregar(itens)
        f(u'info').Text = ui.plural(len(itens), u'folha', u'folhas')
        del entra[:]
        f(u'leg_entra').Items.Clear()
        for v in folhas.legendas_do_projeto(doc):
            entra.append(v)
            f(u'leg_entra').Items.Add(nome(v))
        antes_padrao = padroes[f(u'padrao').SelectedIndex] if 0 <= f(u'padrao').SelectedIndex < len(padroes) else None
        del padroes[:]
        f(u'padrao').Items.Clear()
        for it in itens:
            padroes.append(ui.campo(it, u'Chave'))
            f(u'padrao').Items.Add(u'%s - %s' % (ui.campo(it, u'NumeroOrig'), ui.campo(it, u'NomeOrig')))
        if antes_padrao in padroes:
            f(u'padrao').SelectedIndex = padroes.index(antes_padrao)
        del tipos[:]
        f(u'tipo_novo').Items.Clear()
        for sm in folhas.tipos_de_carimbo(doc):
            tipos.append(sm)
            f(u'tipo_novo').Items.Add(folhas.rotulo_do_tipo(sm))
        atualizar_legendas()

    def alvos():
        """Itens marcados; se nao houver, as linhas selecionadas na tabela."""
        marcados = tabela.marcados()
        if marcados:
            return marcados
        sel = list(f(u'grade').SelectedItems)
        sel.sort(key=lambda i: f(u'grade').Items.IndexOf(i))
        return sel

    def atualizar_legendas():
        """Legendas das folhas-alvo (com a contagem) no combo "sai"."""
        antes = sai[f(u'leg_sai').SelectedIndex] if 0 <= f(u'leg_sai').SelectedIndex < len(sai) else None
        contagem = {}
        for i in alvos():
            for c in set(ui.campo(i, u'Chaves')):
                contagem[c] = contagem.get(c, 0) + 1
        ordem = sorted(contagem, key=lambda c: (-contagem[c], leg_nomes[c].lower()))
        del sai[:]
        f(u'leg_sai').Items.Clear()
        for c in ordem:
            sai.append(c)
            f(u'leg_sai').Items.Add(u'%s  (%s)' % (leg_nomes[c], ui.plural(contagem[c], u'folha', u'folhas')))
        if antes in sai:
            f(u'leg_sai').SelectedIndex = sai.index(antes)
        elif sai:
            f(u'leg_sai').SelectedIndex = 0

    def status(texto):
        f(u'status').Text = texto

    def relatorio(titulo, avisos):
        if avisos:
            ui.avisar(u'%s\n\nAtenção:\n%s\n\nCtrl+Z desfaz.' % (titulo, u'\n'.join(avisos)))

    def duplicar(a=None, e=None):
        alvo = [sheets[ui.campo(i, u'Chave')] for i in alvos()]
        if not alvo:
            status(u'Marque (ou selecione) ao menos uma folha.')
            ui.avisar(u'Marque (ou selecione) as folhas que deseja duplicar.')
            return
        sufixo = f(u'copia').Text or u'-COPIA'
        lista = u', '.join(s_.SheetNumber for s_ in alvo[:10]) + (u'…' if len(alvo) > 10 else u'')
        if not ui.confirmar(u'Duplicar %s?\n\n%s\n\nNovo número = número original + "%s".' %
                            (ui.plural(len(alvo), u'folha', u'folhas'), lista, sufixo)):
            return
        criadas, avisos = folhas.duplicar(doc, alvo, sufixo)
        recarregar(True)
        status(u'%d folha(s) criada(s): %s' % (len(criadas), u', '.join(n.SheetNumber for _o, n in criadas)))
        ui.avisar(u'%d folha(s) criada(s):\n%s\n\nCtrl+Z desfaz.' %
                  (len(criadas), u', '.join(n.SheetNumber for _o, n in criadas[:15])))
        relatorio(u'%d folha(s) criada(s).' % len(criadas), avisos)

    def trocar_legenda(a=None, e=None):
        alvo = [sheets[ui.campo(i, u'Chave')] for i in alvos()]
        i_sai, i_entra = f(u'leg_sai').SelectedIndex, f(u'leg_entra').SelectedIndex
        if not alvo or i_sai < 0 or i_entra < 0:
            status(u'Marque as folhas e escolha a legenda que sai e a que entra.')
            return
        n, avisos = folhas.trocar_legenda(doc, alvo, leg_views[sai[i_sai]], entra[i_entra])
        recarregar(True)
        status(u'Legenda trocada em %d lugar(es).' % n)
        relatorio(u'Legenda trocada em %d lugar(es).' % n, avisos)

    def limpar_destaque(a=None, e=None):
        alvo = [sheets[ui.campo(i, u'Chave')].UniqueId for i in alvos()]
        destaque.limpar(doc, alvo or None)
        recarregar(True)
        status(u'Destaque removido de %s.' % (u'as folhas marcadas' if alvo else u'todas as folhas'))

    def ajustar_tamanho(a=None, e=None):
        i_pad = f(u'padrao').SelectedIndex
        alvo = [sheets[ui.campo(i, u'Chave')] for i in alvos()]
        if i_pad < 0 or not alvo:
            status(u'Escolha a folha padrão e marque as folhas a ajustar.')
            ui.avisar(u'Escolha a folha padrão e marque (ou selecione) as folhas a ajustar.')
            return
        padrao = sheets[padroes[i_pad]]
        alvo = [s_ for s_ in alvo if eid(s_.Id) != eid(padrao.Id)]
        if not alvo:
            ui.avisar(u'Marque folhas diferentes da folha padrão.')
            return
        if not ui.confirmar(u'Ajustar %s ao tamanho da folha %s?\n\nCopia só Altura e Largura do carimbo '
                            u'(tipo e vistas ficam como estão).\nCtrl+Z desfaz.' %
                            (ui.plural(len(alvo), u'folha', u'folhas'), padrao.SheetNumber)):
            return
        n, avisos = folhas.ajustar_tamanho(doc, padrao, alvo)
        recarregar(True)
        status(u'%d folha(s) ajustada(s) pela %s.' % (n, padrao.SheetNumber))
        ui.avisar(u'%d folha(s) ajustada(s) pela %s.' % (n, padrao.SheetNumber))
        relatorio(u'%d folha(s) ajustada(s).' % n, avisos)

    def mover_legendas(a=None, e=None):
        alvo = [sheets[ui.campo(i, u'Chave')] for i in alvos()]
        if not alvo:
            status(u'Marque (ou selecione) as folhas cujas legendas devem mover.')
            ui.avisar(u'Marque (ou selecione) as folhas cujas legendas devem mover.')
            return
        try:
            val = float((f(u'mov_val').Text or u'').strip().replace(u',', u'.'))
        except ValueError:
            ui.avisar(u'Valor inválido: digite um número em cm (ex.: 1,5).')
            return
        d = f(u'mov_dir').SelectedIndex          # 0 direita, 1 esquerda, 2 cima, 3 baixo
        dx = val if d == 0 else -val if d == 1 else 0.0
        dy = val if d == 2 else -val if d == 3 else 0.0
        n, avisos = folhas.mover_legendas(doc, alvo, dx, dy)
        recarregar(True)
        status(u'%d legenda(s) movida(s) %.2f cm para %s.' % (n, val, f(u'mov_dir').Text.lower()))
        relatorio(u'%d legenda(s) movida(s).' % n, avisos)

    def titulos(a=None, e=None):
        sel = alvos()
        alvo = [sheets[ui.campo(i, u'Chave')] for i in sel] if sel else list(sheets.values())
        escopo = u'as folhas marcadas' if sel else u'TODAS as folhas do projeto'
        if not ui.confirmar(u'Subir o título das vistas %.0f cm em %s (%d)?\n\nCtrl+Z desfaz.' %
                            (casar.SUBIR_TITULO_CM, escopo, len(alvo))):
            return
        n, avisos = casar.padronizar_titulos(doc, alvo)
        status(u'Título padronizado em %d vista(s).' % n)
        ui.avisar(u'Título padronizado em %d vista(s).' % n)
        relatorio(u'Título padronizado em %d vista(s).' % n, avisos)

    def apagar(a=None, e=None):
        sel = alvos()
        alvo = [sheets[ui.campo(i, u'Chave')] for i in sel]
        if not alvo:
            status(u'Marque (ou selecione) as folhas a apagar.')
            return
        lista = u', '.join(s_.SheetNumber for s_ in alvo[:12]) + (u'…' if len(alvo) > 12 else u'')
        if not ui.confirmar(u'Apagar %s do projeto?\n\n%s\n\nCtrl+Z desfaz.' %
                            (ui.plural(len(alvo), u'folha', u'folhas'), lista)):
            return
        n, avisos = folhas.apagar(doc, alvo)
        recarregar(True)
        status(u'%d folha(s) apagada(s).' % n)
        relatorio(u'%d folha(s) apagada(s).' % n, avisos)

    def trocar_tipo(a=None, e=None):
        alvo = [sheets[ui.campo(i, u'Chave')] for i in alvos()]
        idx = f(u'tipo_novo').SelectedIndex
        if not alvo or idx < 0:
            status(u'Marque as folhas e escolha o tipo de folha novo.')
            return
        n, avisos = folhas.trocar_tipo(doc, alvo, tipos[idx])
        recarregar(True)
        status(u'Tipo trocado em %d folha(s).' % n)
        relatorio(u'Tipo trocado em %d folha(s).' % n, avisos)

    def lote(prefixo, sufixo, buscar, trocar, usar_seq, base):
        """Devolve [(item, novo_texto)] das marcadas."""
        ini = regras.inteiro(f(u'ini').Text, 1)
        passo = regras.inteiro(f(u'passo').Text, 1)
        dig = regras.inteiro(f(u'dig').Text, 0)
        saida = []
        for k, i in enumerate(tabela.marcados()):
            if usar_seq:
                saida.append((i, regras.sequencia(k, prefixo, ini, passo, dig, sufixo)))
            else:
                saida.append((i, regras.aplicar(base(i), prefixo, sufixo, buscar, trocar)))
        return saida

    def previa_numeros():
        r = lote(f(u'n_pre').Text, f(u'n_suf').Text, f(u'n_bus').Text, f(u'n_tro').Text,
                 bool(f(u'seq').IsChecked), lambda i: ui.campo(i, u'NumeroOrig'))
        for i, novo in r:
            ui.definir(i, u'Numero', novo)
        tabela.mostrar()
        status(u'Prévia de número em %d folha(s). Confira e clique em Aplicar.' % len(r))

    def previa_nomes():
        r = lote(f(u'm_pre').Text, f(u'm_suf').Text, f(u'm_bus').Text, f(u'm_tro').Text,
                 False, lambda i: ui.campo(i, u'NomeOrig'))
        for i, novo in r:
            ui.definir(i, u'NomeFolha', novo)
        tabela.mostrar()
        status(u'Prévia de nome em %d folha(s). Confira e clique em Aplicar.' % len(r))

    def previa_prancha():
        r = lote(f(u'p_pre').Text, f(u'p_suf').Text, f(u'p_bus').Text, f(u'p_tro').Text,
                 bool(f(u'p_seq').IsChecked), lambda i: ui.campo(i, u'PranchaOrig'))
        r = [(i, n) for i, n in r if ui.campo(i, u'PranchaOk')]
        for i, novo in r:
            ui.definir(i, u'Prancha', novo)
        tabela.mostrar()
        status(u'Prévia do Nº da Prancha em %d folha(s). Confira e clique em Aplicar.' % len(r))

    def aplicar(a=None, e=None):
        mudancas = []
        for i in tabela.itens:
            s = sheets[ui.campo(i, u'Chave')]
            n = (ui.campo(i, u'Numero') or u'').strip()
            m = (ui.campo(i, u'NomeFolha') or u'').strip()
            p = ui.campo(i, u'Prancha') or u''
            n = n if n and n != ui.campo(i, u'NumeroOrig') else None
            m = m if m and m != ui.campo(i, u'NomeOrig') else None
            p = p if ui.campo(i, u'PranchaOk') and p != ui.campo(i, u'PranchaOrig') else None
            if n is not None or m is not None or p is not None:
                mudancas.append((s, n, m, p))
        if not mudancas:
            status(u'Nada editado para aplicar.')
            return
        feitas, avisos = folhas.renumerar_renomear(doc, mudancas)
        recarregar()
        status(u'%d alteração(ões) aplicada(s).' % feitas)
        relatorio(u'%d alteração(ões) aplicada(s).' % feitas, avisos)

    def s(fn):
        return ui.proteger(erro, fn)

    g = f(u'grade')
    g.AddHandler(CheckBox.ClickEvent, RoutedEventHandler(s(lambda a, e: atualizar_legendas())))
    g.SelectionChanged += s(lambda a, e: atualizar_legendas())
    f(u'todas').Click += s(lambda a, e: atualizar_legendas())
    f(u'filtro').TextChanged += s(lambda a, e: atualizar_legendas())
    f(u'leg_sai').DropDownOpened += s(lambda a, e: atualizar_legendas())
    f(u'dup').Click += api(duplicar)
    f(u'limpar_novas').Click += api(limpar_destaque)
    f(u'apagar').Click += api(apagar)
    f(u'titulos').Click += api(titulos)
    f(u'mover').Click += api(mover_legendas)
    f(u'ajustar_tam').Click += api(ajustar_tamanho)
    f(u'criar').Click += api(duplicar)

    def so_novas(a=None, e=None):
        marcado = bool(f(u'so_novas').IsChecked)
        tabela.extra = (lambda i: ui.campo(i, u'Nova')) if marcado else None
        tabela.mostrar()
        atualizar_legendas()
    f(u'so_novas').Click += s(so_novas)
    f(u'leg_trocar').Click += api(trocar_legenda)
    f(u'tipo_trocar').Click += api(trocar_tipo)
    f(u'prev_n').Click += s(lambda a, e: previa_numeros())
    f(u'prev_m').Click += s(lambda a, e: previa_nomes())
    f(u'prev_p').Click += s(lambda a, e: previa_prancha())
    f(u'aplicar').Click += api(aplicar)
    f(u'desfazer').Click += api(lambda a, e: (recarregar(), status(u'Edições descartadas.')))
    return recarregar
