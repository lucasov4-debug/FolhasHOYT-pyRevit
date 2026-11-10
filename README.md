# Folhas HOYT para Revit

## ⬇️ Baixe a extensão aqui

### [👉 CLIQUE AQUI PARA BAIXAR O FOLHAS HOYT (ZIP)](https://github.com/lucasov4-debug/FolhasHOYT-pyRevit/releases/download/v0.3.1/FolhasHOYT_0.3.1.zip)

**Você não precisa criar conta no GitHub.** O link acima baixa o arquivo `FolhasHOYT_0.3.1.zip` diretamente. Use esse link, em vez do botão verde **Code** do GitHub.

## Como instalar — passo a passo

**Antes de começar:** tenha o Autodesk Revit instalado. O Folhas HOYT usa o pyRevit para aparecer como uma aba dentro do Revit.

1. **Instale o pyRevit, se ainda não tiver.** [Clique aqui para baixar o instalador do pyRevit 6.5.3](https://github.com/pyrevitlabs/pyRevit/releases/download/v6.5.3.26176%2B2017/pyRevit_6.5.3.26176_signed.exe). Abra o arquivo `.exe` baixado e siga as telas de instalação. Se a aba **pyRevit** já aparece no seu Revit, pule este passo.
2. **Baixe o Folhas HOYT** pelo link grande no início desta página.
3. **Extraia o ZIP:** na pasta **Downloads**, clique com o botão direito em `FolhasHOYT_0.3.1.zip` e escolha **Extrair Tudo**. Abra a pasta extraída; dentro dela estará `FolhasHOYT.extension`.
4. **Abra a pasta de extensões:** pressione **Win + R**, cole `%APPDATA%\pyRevit\Extensions` e pressione **Enter**. Se a pasta `Extensions` não existir, crie-a dentro de `%APPDATA%\pyRevit`.
5. **Copie a pasta inteira** `FolhasHOYT.extension` para dentro de `Extensions`. O resultado deve ser `Extensions\FolhasHOYT.extension\extension.json` — sem outra pasta entre `Extensions` e `FolhasHOYT.extension`.
6. **Abra o Revit.** Se ele já estiver aberto, clique em **pyRevit → Reload**. Procure a aba **Folhas HOYT** na faixa superior e clique no botão **Folhas HOYT**.

> **Para atualizar depois:** baixe o ZIP da versão nova, substitua a pasta `FolhasHOYT.extension` antiga pela nova e use **pyRevit → Reload**. Os padrões de tamanho pessoais ficam fora da extensão, em `%APPDATA%\FolhasHOYT\padroes_tamanho.json`.

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
