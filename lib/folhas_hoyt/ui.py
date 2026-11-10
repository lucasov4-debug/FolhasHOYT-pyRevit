# -*- coding: utf-8 -*-
"""Pecas de WPF compartilhadas pelas janelas da aba Folhas HOYT."""
import io
import os
import traceback

import clr
clr.AddReference('PresentationCore')
clr.AddReference('PresentationFramework')
clr.AddReference('WindowsBase')

from System import Object, String
from System.Collections.Generic import IDictionary, List
from System.Dynamic import ExpandoObject
from System.Windows import MessageBox, MessageBoxButton, MessageBoxImage, MessageBoxResult
from System.Windows.Controls import DataGridEditingUnit
from System.Windows.Interop import WindowInteropHelper
from System.Windows.Markup import XamlReader

TITULO = u'Folhas HOYT'


def item(**campos):
    """ExpandoObject (o binding do WPF enxerga os campos)."""
    e = ExpandoObject()
    try:
        d = IDictionary[String, Object](e)
        for k, v in campos.items():
            d[k] = v
    except TypeError:
        for k, v in campos.items():
            setattr(e, k, v)
    return e


def campo(it, nome):
    try:
        return IDictionary[String, Object](it)[nome]
    except TypeError:
        return getattr(it, nome)


def definir(it, nome, valor):
    try:
        IDictionary[String, Object](it)[nome] = valor
    except TypeError:
        setattr(it, nome, valor)


def lista(itens):
    saida = List[Object]()
    for i in itens:
        saida.Add(i)
    return saida


def avisar(texto, titulo=TITULO):
    MessageBox.Show(texto, titulo, MessageBoxButton.OK, MessageBoxImage.Information)


def confirmar(texto, titulo=TITULO):
    r = MessageBox.Show(texto, titulo, MessageBoxButton.YesNo, MessageBoxImage.Question)
    return r == MessageBoxResult.Yes


def gravar_erro(pasta, texto):
    try:
        with io.open(os.path.join(pasta, u'ultimo_erro.txt'), 'w', encoding='utf-8') as f:
            f.write(u'%s' % texto)
    except Exception:
        pass


def erro_de(pasta, titulo=TITULO):
    def erro(texto):
        gravar_erro(pasta, texto)
        MessageBox.Show(texto, u'%s - ERRO' % titulo, MessageBoxButton.OK, MessageBoxImage.Error)
    return erro


def proteger(erro, fn):
    """Handler que nao deixa excecao sumir calada (vai para erro(texto))."""
    def handler(sender, args):
        try:
            fn(sender, args)
        except Exception:
            erro(traceback.format_exc())
    return handler


def carregar_janela(pasta, arquivo, titulo):
    with io.open(os.path.join(pasta, arquivo), encoding='utf-8') as f:
        janela = XamlReader.Parse(f.read())
    janela.Title = titulo
    try:
        WindowInteropHelper(janela).Owner = __revit__.MainWindowHandle   # noqa: F821
    except Exception:
        pass
    return janela


def confirmar_edicao(grade):
    try:
        grade.CommitEdit(DataGridEditingUnit.Row, True)
    except Exception:
        pass


class Tabela(object):
    """DataGrid de ExpandoObject com filtro de texto e marcar todos.
    Cada item precisa dos campos Marcado (bool) e Busca (texto minusculo)."""

    def __init__(self, grade, filtro=None, todos=None):
        self.grade = grade
        self.filtro = filtro
        self.todos = todos
        self.itens = []
        self.extra = None        # predicado opcional extra (ex.: so' as novas)
        if filtro is not None:
            filtro.TextChanged += lambda a, e: self.mostrar()
        if todos is not None:
            todos.Click += lambda a, e: self.marcar_todos(bool(todos.IsChecked))

    def carregar(self, itens):
        self.itens = list(itens)
        self.mostrar()

    def visiveis(self):
        t = (self.filtro.Text if self.filtro is not None else u'').strip().lower()
        return [i for i in self.itens
                if (not t or t in campo(i, u'Busca')) and (self.extra is None or self.extra(i))]

    def mostrar(self):
        confirmar_edicao(self.grade)
        self.grade.ItemsSource = lista(self.visiveis())

    def marcados(self):
        confirmar_edicao(self.grade)
        return [i for i in self.visiveis() if campo(i, u'Marcado')]

    def marcar_todos(self, valor):
        for i in self.visiveis():
            definir(i, u'Marcado', valor)
        self.mostrar()


def plural(n, um, varios):
    return u'%d %s' % (n, um if n == 1 else varios)


class Executor(object):
    """Roda codigo da API do Revit a partir de uma janela NAO modal: guarda
    a acao numa fila e dispara um ExternalEvent (a API so' aceita escrita
    dentro dele). Criar no contexto do comando (script.py)."""

    def __init__(self, erro):
        from Autodesk.Revit.UI import ExternalEvent, IExternalEventHandler
        outer = self

        class _Handler(IExternalEventHandler):
            def Execute(self, uiapp):
                while outer.fila:
                    fn = outer.fila.pop(0)
                    try:
                        fn()
                    except Exception:
                        outer.erro(traceback.format_exc())

            def GetName(self):
                return u'Folhas HOYT'

        self.fila = []
        self.erro = erro
        self._handler = _Handler()
        self._evento = ExternalEvent.Create(self._handler)

    def executar(self, fn):
        self.fila.append(fn)
        self._evento.Raise()

    def api(self, fn):
        """Handler de evento WPF que roda fn(sender, args) como acao da API."""
        def handler(sender, args):
            self.executar(lambda: fn(sender, args))
        return handler
