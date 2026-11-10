# -*- coding: utf-8 -*-
# ============================================================
# Folhas HOYT - gerenciador de vistas e folhas (Revit 2023).
# Janela de gerenciamento de vistas, folhas e legendas.
# Codigo das abas: lib/folhas_hoyt/aba_*.py
# ============================================================
import os
import sys
import traceback

for _m in [_n for _n in list(sys.modules)
           if _n.split('.')[0] in ('folhas_hoyt', 'montagem_folha', 'folhas_disciplina')]:
    try:
        del sys.modules[_m]
    except Exception:
        pass

PASTA = os.path.dirname(os.path.abspath(__file__))


def principal():
    from pyrevit import revit
    from System.Windows.Controls import TabControl
    from folhas_hoyt import aba_casar, aba_folhas, aba_legendas, aba_levar, aba_setores, aba_tamanhos, aba_vistas, ui, VERSAO

    doc = revit.doc
    erro = ui.erro_de(PASTA, u'Folhas HOYT')
    janela = ui.carregar_janela(PASTA, u'FolhasHOYT.xaml', u'Folhas HOYT  v%s' % VERSAO)
    ajustes = ui.carregar_janela(PASTA, u'FolhasHOYTAjustes.xaml', u'Folhas HOYT — edição em lote')
    # janela NAO modal: o que escreve no Revit passa pelo ExternalEvent (executor.api)
    executor = ui.Executor(erro)
    api = executor.api
    recarregadores = [
        aba_vistas.montar(janela, doc, erro, api),
        aba_folhas.montar(janela, doc, erro, api, ajustes),
        aba_casar.montar(janela, doc, erro, api),
        aba_setores.montar(janela, doc, erro, api),
        aba_levar.montar(janela, doc, erro, api, __revit__.Application),   # noqa: F821
        aba_tamanhos.montar(janela, doc, erro, api),
        aba_legendas.montar(janela, doc, erro, api),
    ]
    abas = janela.FindName(u'abas')
    carregadas = set([0])
    recarregadores[0]()      # so' a primeira aba carrega agora; as outras na primeira vez que abrem

    def ao_trocar_de_aba(sender, args):
        # SelectionChanged das tabelas sobe ate' aqui: so' a troca de aba interessa
        if args.OriginalSource is not abas:
            return
        i = abas.SelectedIndex
        if 0 <= i < len(recarregadores):
            if i not in carregadas:          # cada aba le o Revit so' uma vez (depois, use Atualizar)
                carregadas.add(i)
                executor.executar(recarregadores[i])

    abas.SelectionChanged += ui.proteger(erro, ao_trocar_de_aba)
    janela.FindName(u'btn_atualizar').Click += ui.proteger(
        erro, lambda a, e: executor.executar(recarregadores[abas.SelectedIndex]))
    janela.FindName(u'btn_fechar').Click += ui.proteger(erro, lambda a, e: janela.Close())
    janela.Tag = (executor, recarregadores, ajustes)     # mantem vivos enquanto a janela existir
    janela.Show()


try:
    principal()
except Exception:
    from folhas_hoyt import ui as _ui
    _ui.erro_de(PASTA, u'Folhas HOYT')(traceback.format_exc())
