# -*- coding: utf-8 -*-
"""Montar Folha - posicionar vistas numa folha arrastando, com a area util
do carimbo como limite, e trocar o formato da folha.

Historico:
  0.1 (26/09/2026) - so' MEDE: le a folha, detecta quadro/carimbo pelas
                     linhas da familia e compara caixa do viewport com o
                     recorte da vista. Nada escreve no modelo.
  0.2 (26/09/2026) - a medicao nao pergunta folha: cria folhas de teste
                     (uma por formato) + amostra de vistas livres, mede e
                     desfaz. JSON via folhas_disciplina.json_seguro (a 0.1
                     quebrava com acento: "byte 0xe9").
  0.3 (26/09/2026) - v0.2 no Revit: carimbo sem linha nenhuma na folha de
                     teste e caixa != recorte/escala. Mede 5 caminhos para
                     as linhas (inclui folha salva e o documento da
                     familia tipo a tipo) e projeta o recorte na folha.
  0.4 (26/09/2026) - SIMPLES (Lucas: "vc ta viajando"): tamanho de cada
                     formato = Largura/Altura da folha do TIPO
                     (leitura.formatos_do_projeto). Medicao so' lista os
                     tipos (com avisos) e mede vistas numa folha de teste.
  0.5 (26/09/2026) - corrige "'FamilySymbol' object has no attribute
                     'RollBack'": no IronPython 2.7 a variavel da list
                     comprehension vazava e sobrescrevia a transacao.
  0.6 (26/09/2026) - v0.5 mostrou 0 de 22 tipos com Largura/Altura: os
                     parametros so' existem na folha colocada. Le numa folha
                     de teste por tipo (desfeita). Area util = folha -
                     margens - carimbo (padroes.py, medidos nas familias;
                     Lucas: "folha menos as margens e o carimbo"). Plugin
                     mostra so' a familia das folhas do projeto.
  0.7 (26/09/2026) - O EDITOR: fita de folhas planejadas, vistas livres
                     agrupadas por tipo (arrastar ou dois cliques), mover
                     com mouse/setas com encaixe, trocar disciplina/numero/
                     formato/nome, criar tudo numa transacao (reaproveita o
                     criar_folhas do Gerenciador). Medicao virou Shift+clique
                     (config.py). Testado no IronPython 2.7 fora do Revit.
  0.8 (29/09/2026) - ABA "Folhas existentes": previa das folhas que ja
                     estao no projeto (vistas nas posicoes reais), mover
                     com mouse/setas/X-Y, "Centralizar a folha" (conjunto
                     das vistas) e "Aplicar" (SetBoxCenter, 1 transacao).
                     A centralizacao (nas duas abas) agora usa a regiao
                     ao lado do carimbo INTEIRO: a faixa vertical do
                     carimbo e' ignorada mesmo acima dele (Lucas).
  0.9 (29/09/2026) - "Centralizar a folha" NAO mexe nas legendas: elas
                     ficam onde estao e nao entram na conta do centro.
  0.10 (29/09/2026) - Folhas existentes: checkbox em cada folha + "Selecionar
                     todas" (respeita o filtro) + "Centralizar as marcadas"
                     em lote (sem legendas; pula folha sem carimbo, so' com
                     legenda ou com vista fixada e lista o motivo).
"""

VERSAO = u"0.10"
