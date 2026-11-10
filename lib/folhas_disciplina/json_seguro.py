# -*- coding: utf-8 -*-
"""JSON que sobrevive a acento DENTRO do Revit.

No IronPython 2.7.12 do pyRevit (o motor dos botoes sem `#! python3`),
json.dumps E json.loads quebram no primeiro acento: "'unknown' codec
can't decode byte 0xe9" - o encoder faz s.decode('utf-8') numa string que
ja' e' unicode. Reproduz fora do Revit com
`py -3 tests/rodar_no_ironpython.py` (motor 2712). Ja' aconteceu no
Salvar Padroes do Gerenciador de Folhas, no Montar Folha, no Exportar
Pranchas, no bimview e nos kits.

Solucao (a mesma que roda em producao no Exportar Pranchas):
  - escrever: serializador proprio, saida SEMPRE ASCII (acento vira
    \\uXXXX caractere a caractere, sem regex e sem .encode());
  - ler: trocar todo caractere nao-ASCII por \\uXXXX ANTES do json.loads.
"""

import json

try:
    _TEXTO = (unicode, str)          # noqa: F821  (IronPython 2)
    _INTEIROS = (int, long)          # noqa: F821
except NameError:
    _TEXTO = (str,)
    _INTEIROS = (int,)


def _escapar(texto):
    partes = [u'"']
    for c in texto:
        n = ord(c)
        if c == u'"':
            partes.append(u'\\"')
        elif c == u'\\':
            partes.append(u'\\\\')
        elif 32 <= n < 127:
            partes.append(c)
        elif n > 0xFFFF:               # CPython: fora do BMP vira par substituto
            n -= 0x10000
            partes.append(u'\\u%04x\\u%04x' % (0xD800 | (n >> 10), 0xDC00 | (n & 0x3FF)))
        else:
            partes.append(u'\\u%04x' % n)
    partes.append(u'"')
    return u''.join(partes)


def _valor(obj, recuo, nivel):
    if obj is None:
        return u'null'
    if obj is True:
        return u'true'
    if obj is False:
        return u'false'
    if isinstance(obj, _TEXTO):
        return _escapar(obj)
    if isinstance(obj, float):
        if obj != obj or obj in (float('inf'), float('-inf')):
            return u'null'
        return u'%r' % obj
    if isinstance(obj, _INTEIROS):
        return u'%d' % obj
    if recuo:
        quebra = u'\n' + u' ' * (recuo * (nivel + 1))
        fecha = u'\n' + u' ' * (recuo * nivel)
        sep = u','
    else:
        quebra = fecha = u''
        sep = u', '
    if isinstance(obj, dict):
        if not obj:
            return u'{}'
        itens = [u'%s%s: %s' % (quebra, _escapar(u'%s' % k), _valor(v, recuo, nivel + 1))
                 for k, v in obj.items()]
        return u'{' + sep.join(itens) + fecha + u'}'
    if isinstance(obj, (list, tuple)):
        if not obj:
            return u'[]'
        itens = [quebra + _valor(v, recuo, nivel + 1) for v in obj]
        return u'[' + sep.join(itens) + fecha + u']'
    # tipo .NET ou qualquer outro: vira texto
    return _escapar(u'%s' % obj)


def dumps(obj, indent=None):
    """Texto JSON 100% ASCII."""
    return _valor(obj, indent or 0, 0)


def loads(texto):
    if not texto:
        return None
    partes = []
    for c in texto:
        if ord(c) < 128:
            partes.append(c)
        else:
            partes.append(_escapar(c)[1:-1])
    return json.loads(u''.join(partes))


def gravar_texto(caminho, texto):
    """Grava em UTF-8 pelo .NET (o open() do IronPython usa a code page do
    Windows e tambem quebra com acento). Fora do Revit (py -3), io.open."""
    try:
        from System.IO import File
        from System.Text import UTF8Encoding
        File.WriteAllText(caminho, texto, UTF8Encoding(False))
    except ImportError:
        import io
        with io.open(caminho, 'w', encoding='utf-8') as arq:
            arq.write(texto)
