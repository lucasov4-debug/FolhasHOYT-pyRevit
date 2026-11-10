# Folhas HOYT para Revit

## ⬇️ Baixe a extensão aqui

### [👉 CLIQUE AQUI PARA BAIXAR O FOLHAS HOYT (ZIP)](https://github.com/lucasov4-debug/FolhasHOYT-pyRevit/releases/download/v0.3.1/FolhasHOYT_0.3.1.zip)

**Você não precisa criar conta no GitHub.** O link acima baixa o arquivo `FolhasHOYT_0.3.1.zip` diretamente. Use esse link, em vez do botão verde **Code** do GitHub.

## Antes de instalar o Folhas HOYT

**Antes de começar:** tenha o Autodesk Revit instalado. O Folhas HOYT usa o pyRevit para aparecer como uma aba dentro do Revit.

1. **Instale o pyRevit, se ainda não tiver.** [Clique aqui para baixar o instalador do pyRevit 6.5.3](https://github.com/pyrevitlabs/pyRevit/releases/download/v6.5.3.26176%2B2017/pyRevit_6.5.3.26176_signed.exe). Abra o arquivo `.exe` baixado e siga as telas de instalação. Se a aba **pyRevit** já aparece no seu Revit, pule este passo.
2. **Baixe o Folhas HOYT** pelo link grande no início desta página.
3. **Extraia o ZIP:** na pasta **Downloads**, clique com o botão direito em `FolhasHOYT_0.3.1.zip` e escolha **Extrair Tudo**. Ao abrir a pasta extraída, você verá a pasta `FolhasHOYT.extension` dentro dela.

Agora escolha **uma** das duas opções abaixo. A **Opção 1** é a mais simples: você seleciona a pasta extraída nas configurações do pyRevit.

## Opção 1 — selecionar a pasta extraída no pyRevit

1. **Abra o Revit** e clique na aba **pyRevit**, na faixa superior.
2. Clique em **Settings** (Configurações).
3. Na janela de configurações, procure **Custom Extension Directories** (Diretórios de extensões personalizadas) e clique em **Add folder** (Adicionar pasta).
4. Na janela de escolha de pasta, vá até **Downloads** e **selecione a pasta que foi criada ao extrair o ZIP**. Normalmente ela se chama `FolhasHOYT_0.3.1`. **Não selecione `FolhasHOYT.extension`**: o pyRevit precisa receber a pasta que está *um nível acima* dela.
5. Clique em **Save Settings and Reload** (Salvar configurações e recarregar). Quando terminar, procure a nova aba **Folhas HOYT** no Revit.

Confira a estrutura antes de selecionar:

```text
Downloads
└── FolhasHOYT_0.3.1           ← selecione ESTA pasta em Add folder
    └── FolhasHOYT.extension    ← não selecione esta pasta
        ├── extension.json
        ├── Folhas HOYT.tab
        └── lib
```

Se o programa que extraiu o ZIP criou uma pasta com outro nome, não tem problema: selecione aquela que **contém `FolhasHOYT.extension` diretamente**. Deixe a pasta extraída nesse lugar depois de configurar; mover ou apagar a pasta fará a aba desaparecer no próximo Reload.

## Opção 2 — copiar para a pasta padrão do pyRevit

1. Pressione **Win + R**, cole `%APPDATA%\pyRevit\Extensions` e pressione **Enter**. Se a pasta `Extensions` não existir, crie-a dentro de `%APPDATA%\pyRevit`.
2. Copie a pasta inteira **`FolhasHOYT.extension`**, que está dentro da pasta extraída, para `Extensions`. O resultado deve ser `Extensions\FolhasHOYT.extension\extension.json` — sem outra pasta entre `Extensions` e `FolhasHOYT.extension`.
3. Abra o Revit. Se ele já estiver aberto, clique em **pyRevit → Reload**. Procure a aba **Folhas HOYT** e clique no botão **Folhas HOYT**.

> **Para atualizar depois:** baixe o ZIP da versão nova e substitua a pasta `FolhasHOYT.extension` antiga pela nova no local escolhido. Depois use **pyRevit → Reload**. Os padrões de tamanho pessoais ficam fora da extensão, em `%APPDATA%\FolhasHOYT\padroes_tamanho.json`.

## O que há na extensão

Ela gerencia vistas, folhas, legendas e tamanhos de folhas. As famílias de carimbo e as legendas precisam estar carregadas no seu projeto Revit. Veja o [roteiro de uso](LEIA-ME.md).

A interface e as listas foram abertas no Revit 2023 com pyRevit 6.5.3. Antes de usar ações que alteram o projeto, faça um ensaio em uma cópia do RVT. As posições de legenda e os padrões de folha foram calibrados para folhas HOYT; confira o resultado ao usar outras famílias de carimbo.

<details>
<summary>Instalação por comando Git (para usuários avançados)</summary>

Com o pyRevit instalado, execute:

```powershell
pyrevit extend ui FolhasHOYT https://github.com/lucasov4-debug/FolhasHOYT-pyRevit
```

Depois clique **pyRevit → Reload** no Revit.

</details>
