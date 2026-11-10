# -*- coding: utf-8 -*-
"""Padroes por disciplina (prefixo, proximo numero, ultimo formato usado) -
guardados no PROPRIO arquivo Revit via Extensible Storage no
ProjectInformation, para toda a equipe compartilhar o mesmo contador
(decisao Q11 do grilling: numeracao de folha e dado de projeto
compartilhado, nao preferencia pessoal de quem roda o plugin).

Guardado como um unico campo de texto (JSON) em vez de um Schema com um
campo por disciplina: mais simples de estender - a lista de disciplinas
NAO e mais fixa (ver disciplinas.py: a familia real tem AF, AF/AQ, CLI,
EST alem dos 5 codigos originais, e pode ganhar mais no futuro), entao os
Padroes tem que aceitar qualquer codigo, sem um schema fixo por
disciplina. A logica de mesclagem com o default (entrada_de) e pura
Python, testada isolada com "py -3" antes de mexer em Revit.

Precisa de transacao aberta por quem chama para salvar() - mesma convencao
de lib/ambientes/folhas.py.
"""
from . import json_seguro

from Autodesk.Revit.DB.ExtensibleStorage import Schema, SchemaBuilder, Entity, AccessLevel
from System import Guid

# GUID fixo do schema - gerado uma unica vez para este plugin. NUNCA mudar:
# trocar o GUID faz o plugin "esquecer" os padroes ja salvos em projetos
# existentes (Schema.Lookup para de achar a entidade antiga).
_SCHEMA_GUID = Guid(u"f1c1f7c1-6b1d-4e2b-9a0a-2f6e6c9a5d31")
_CAMPO = u"padroes_json"
_NOME_SCHEMA = u"SYNC_GerenciadorDeFolhas_Padroes"

NUMERO_INICIAL_PADRAO = 101

# chave reservada dentro do mesmo JSON, para a última seleção de
# disciplinas/quantidades da aba Criar Folhas (botão "Salvar seleção",
# pedido em 19/09/2026 - "para eu poder usar depois"). Por convenção,
# qualquer chave começando com "_" é reservada e NUNCA é um código de
# disciplina de verdade (esses sempre vêm de Tag_Disciplina_<algo>, sem
# "_" na frente).
CHAVE_ULTIMO_PEDIDO = u"_ultimo_pedido"


def _eh_reservada(chave):
    return (chave or u"").startswith(u"_")


def _padrao_para(codigo):
    return {u"prefixo": codigo, u"proximo_numero": NUMERO_INICIAL_PADRAO,
            u"ultimo_formato": None, u"legenda_id": None, u"tipo_projeto": u""}


def entrada_de(dados, codigo):
    """Entrada de 1 disciplina dentro dos Padroes - default (código como
    prefixo, número inicial, sem formato/legenda/tipo de projeto ainda) se
    essa disciplina ainda não tiver sido salva (disciplina nova,
    descoberta agora na família). "Tipo de Projeto" é POR DISCIPLINA
    (Lucas, 19/09/2026: não é um valor global)."""
    entrada = dict(_padrao_para(codigo))
    entrada.update((dados or {}).get(codigo) or {})
    return entrada


def codigos_salvos(dados):
    """Códigos de disciplina realmente salvos em 'dados' - exclui as
    chaves reservadas (ver _eh_reservada)."""
    return [c for c in (dados or {}).keys() if not _eh_reservada(c)]


def carregar_ultimo_pedido(doc):
    """{'ESG': {'selecionada': True, 'quantidade': '3'}, ...} - a última
    seleção de disciplinas/quantidades salva manualmente na aba Criar
    Folhas (botão "Salvar seleção"). {} se nunca foi salvo."""
    dados = carregar(doc)
    return dict((dados.get(CHAVE_ULTIMO_PEDIDO) or {}))


def salvar_ultimo_pedido(doc, pedido):
    """Atualiza só a última seleção de disciplinas/quantidades,
    preservando os Padroes de disciplina já salvos. Chamar dentro de
    transação aberta."""
    dados = carregar(doc)
    dados[CHAVE_ULTIMO_PEDIDO] = dict(pedido or {})
    salvar(doc, dados)


def _schema_existente():
    return Schema.Lookup(_SCHEMA_GUID)


def _obter_ou_criar_schema():
    schema = _schema_existente()
    if schema is not None:
        return schema
    construtor = SchemaBuilder(_SCHEMA_GUID)
    construtor.SetSchemaName(_NOME_SCHEMA)
    construtor.SetReadAccessLevel(AccessLevel.Public)
    construtor.SetWriteAccessLevel(AccessLevel.Public)
    construtor.AddSimpleField(_CAMPO, str)
    return construtor.Finish()


def carregar(doc):
    """{'ESG': {'prefixo': 'ESG', 'proximo_numero': 101,
    'ultimo_formato': 'A1'}, ...} tal como está salvo - {} se o projeto
    ainda não tiver nada. Use entrada_de(dados, codigo) para ler 1
    disciplina específica com o default já aplicado."""
    schema = _schema_existente()
    if schema is None:
        return {}
    try:
        info = doc.ProjectInformation
        entidade = info.GetEntity(schema)
        if not entidade.IsValid():
            return {}
        texto = entidade.Get[str](_CAMPO)
    except Exception:
        return {}
    if not texto:
        return {}
    try:
        return json_seguro.loads(texto) or {}
    except Exception:
        return {}


def salvar(doc, dados):
    """Sobrescreve os Padroes no ProjectInformation com 'dados' tal como
    dado (sem forçar disciplina nenhuma) - chamar dentro de uma transação
    já aberta, esta função não abre nem fecha nenhuma."""
    schema = _obter_ou_criar_schema()
    info = doc.ProjectInformation
    entidade = Entity(schema)
    # json_seguro, nunca json.dumps: dentro do Revit o dumps quebra no
    # primeiro acento ("'unknown' codec can't decode byte 0xc1" - era o
    # erro do "Salvar Padrões", ultimo_erro.txt de 19/09/2026).
    entidade.Set[str](_CAMPO, json_seguro.dumps(dados))
    info.SetEntity(entidade)


def registrar_uso(doc, codigo_disciplina, proximo_numero_livre, formato_usado):
    """Atualiza, para 1 disciplina, o próximo número livre e o último
    formato usado - chamado pelo motor de criação logo após criar as
    folhas daquela disciplina. Chamar dentro da MESMA transação da
    criação das folhas (Q11: o contador só avança se a criação vingar)."""
    dados = carregar(doc)
    entrada = entrada_de(dados, codigo_disciplina)
    entrada[u"proximo_numero"] = proximo_numero_livre
    if formato_usado:
        entrada[u"ultimo_formato"] = formato_usado
    dados[codigo_disciplina] = entrada
    salvar(doc, dados)
