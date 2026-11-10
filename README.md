# Folhas HOYT para pyRevit

Gerenciador de vistas, folhas, legendas e tamanhos de folhas no Revit. Esta extensão adiciona a aba **Folhas HOYT** ao pyRevit.

## Requisitos

- Autodesk Revit com pyRevit instalado. A interface foi aberta no Revit 2023 com pyRevit 6.5.3.
- As famílias de carimbo e as legendas usadas pelo projeto devem estar carregadas no próprio RVT.

Quem ainda não tem pyRevit deve instalar primeiro o [pyRevit oficial](https://github.com/pyrevitlabs/pyRevit/releases). Baixe o instalador **pyRevit**, não apenas o **pyRevit CLI**.

## Instalação pelo Git

No terminal do computador que já tem pyRevit:

```powershell
pyrevit extend ui FolhasHOYT https://github.com/lucasov4-debug/FolhasHOYT-pyRevit
```

No Revit, clique **pyRevit > Reload**. A aba **Folhas HOYT** aparecerá no ribbon.

## Instalação sem terminal

Baixe o arquivo `FolhasHOYT_0.3.1.zip` na seção [Releases](https://github.com/lucasov4-debug/FolhasHOYT-pyRevit/releases). Extraia a pasta `FolhasHOYT.extension` inteira para `%APPDATA%\pyRevit\Extensions` e clique **pyRevit > Reload** no Revit. Não use o botão **Code > Download ZIP** para esse método: o ZIP automático do GitHub não tem a pasta `.extension` no nível exigido pelo pyRevit.

## Atualização

Na instalação pelo Git, use o gerenciador de extensões do pyRevit ou `pyrevit extensions update FolhasHOYT` e depois **Reload**. Na instalação por ZIP, substitua a pasta `FolhasHOYT.extension` pelo ZIP da nova versão e dê **Reload**.

Os padrões de tamanho criados pelo usuário ficam em `%APPDATA%\FolhasHOYT\padroes_tamanho.json`, fora da pasta da extensão.

## Uso e validação

Consulte [LEIA-ME.md](LEIA-ME.md) para um roteiro curto das abas. As janelas e listas foram verificadas no Revit 2023; ações que gravam no RVT devem ser ensaiadas em uma cópia adequada do projeto antes de uso em produção. Os padrões e as compensações de posição de legendas foram calibrados para folhas HOYT e podem exigir conferência em outras famílias de carimbo.
