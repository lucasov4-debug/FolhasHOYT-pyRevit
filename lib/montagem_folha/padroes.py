# -*- coding: utf-8 -*-
"""Margens e carimbo das folhas SYNC - o que tira espaco da area util.

Valores MEDIDOS nas familias reais em 26/09/2026 (linhas da familia,
medicao v0.3 - ver tests/test_montagem_folha_familias_reais.py) e
confirmados pelo Lucas como o limite a usar ("folha menos as margens e o
carimbo"). Todos em mm de papel. Mudou a familia? Muda aqui.
"""

MARGEM_ESQ = 25.0
MARGEM_DIR = 10.0
MARGEM_BAIXO = 10.0
MARGEM_CIMA = 10.0
MARGEM_CIMA_FOLHA_BAIXA = 7.0      # folhas de 420 de altura (A2 e A2 - E*)
ALTURA_FOLHA_BAIXA = 500.0         # abaixo disso vale a margem de cima de 7

# carimbo: coluna no canto inferior direito, encostada nas margens
CARIMBO_LARGURA = 175.0
CARIMBO_ALTURA = {
    u'SYNC_HID_FOLHA_R04': 280.0,
    u'SYNC_FOLHA PARAMÉTRICA_R01': 381.5,
}
CARIMBO_ALTURA_PADRAO = 280.0


def da_familia(familia, altura_folha):
    """{'margens': (esq, baixo, dir, cima), 'carimbo': (largura, altura)}"""
    cima = MARGEM_CIMA_FOLHA_BAIXA if altura_folha < ALTURA_FOLHA_BAIXA else MARGEM_CIMA
    return {u'margens': (MARGEM_ESQ, MARGEM_BAIXO, MARGEM_DIR, cima),
            u'carimbo': (CARIMBO_LARGURA, CARIMBO_ALTURA.get(familia, CARIMBO_ALTURA_PADRAO))}
