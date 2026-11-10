# -*- coding: utf-8 -*-
"""Numero da folha: template unico "{PREFIXO}-{NUMERO}" para todas as
disciplinas (decisao Q12 do grilling) - so o prefixo e o proximo numero
mudam por disciplina, guardados nos Padroes (ver armazenamento.py).

Sem Revit nenhum aqui de proposito: testado isolado com "py -3" antes de
entrar no motor (mesma regra da memoria "medir antes de escrever geometria
Revit", valendo tambem para logica de numeracao).
"""
import re


def montar_numero(prefixo, numero):
    prefixo = (prefixo or u"").strip()
    if not prefixo:
        return u"%d" % numero
    return u"%s-%d" % (prefixo, numero)


def numero_unico(prefixo, numero_sugerido, ocupados):
    """(codigo, numero) a partir do numero_sugerido, avancando enquanto o
    codigo montado colidir com uma folha que ja existe no projeto
    (ocupados) - mesma logica de nomes.unico() em lib/ambientes, adaptada
    para numero de folha em vez de nome de vista. Rede de seguranca: o
    numero guardado em Padroes e so um palpite, quem manda e o projeto."""
    numero = numero_sugerido
    codigo = montar_numero(prefixo, numero)
    while codigo in ocupados:
        numero += 1
        codigo = montar_numero(prefixo, numero)
    return codigo, numero


def maior_numero_do_prefixo(numeros, prefixo):
    """Maior N encontrado em códigos "PREFIXO-N" dentro de 'numeros' (lista
    ou set de strings) - 0 se nenhum bater. Usado para recalcular o
    próximo número livre depois de um lote: a prévia é editável (Q5 do
    grilling), então o usuário pode ter digitado números fora da
    sequência esperada - o próximo palpite tem que olhar o que ficou de
    verdade no projeto, não só somar a quantidade criada."""
    prefixo = (prefixo or u"").strip()
    marcador = u"%s-" % prefixo if prefixo else u""
    maior = 0
    for numero in numeros:
        texto = numero or u""
        if marcador:
            if not texto.startswith(marcador):
                continue
            resto = texto[len(marcador):]
        else:
            resto = texto
        try:
            valor = int(resto)
        except ValueError:
            continue
        if valor > maior:
            maior = valor
    return maior


def incrementar_numero(codigo, delta):
    """'HID-101' + delta(+1) -> 'HID-102' - usado pelas setinhas ▲▼ da
    prévia (pedido em 19/09/2026). Preserva zeros à esquerda ('HID-001' ->
    'HID-002'). Sem dígito no final, devolve o código sem mudar - não dá
    para "incrementar" algo que não é número."""
    m = re.search(u"([0-9]+)$", codigo or u"")
    if not m:
        return codigo
    novo_valor = max(1, int(m.group(1)) + delta)
    return codigo[:m.start()] + str(novo_valor).zfill(len(m.group(1)))
