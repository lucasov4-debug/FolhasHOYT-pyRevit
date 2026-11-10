# Folhas HOYT — instalação e vídeo

## Instalação

1. Extraia `FolhasHOYT_0.3.1.zip`, mantendo a pasta `FolhasHOYT.extension` inteira.
2. Copie essa pasta para `%APPDATA%\pyRevit\Extensions` ou adicione a pasta que a contém aos caminhos de extensões do pyRevit.
3. No Revit, execute **pyRevit > Reload**. A aba **Folhas HOYT** terá o painel **Gerenciamento** e o botão **Folhas HOYT**.

## Roteiro para o vídeo

1. Abra **Folhas HOYT** e mostre as abas Vistas, Folhas, Casar, Setores, Levar e Tamanhos.
2. Na aba **Legenda**, escolha uma legenda do projeto e filtre as folhas de destino.
3. Marque as folhas e clique em **Inserir ou corrigir legenda**.
4. Confira a confirmação antes de aplicar. A operação usa **Viewport: No Title** e a correção de posição medida pelo usuário (+2,53 cm à direita; +0,41 cm acima).
5. Se a mesma legenda já existir na folha, a viewport é corrigida sem duplicação.
6. Use **Atualizar esta aba** para reler as folhas depois de alterações no projeto.

A extensão usa as famílias de carimbo e legendas já carregadas no projeto. Teste ações que gravam no modelo em uma cópia apropriada antes de gravar o vídeo.

## Altura e largura das folhas

Na aba **Tamanhos**, digite **Altura** e/ou **Largura** em cm na linha da folha. Um campo vazio mantém a medida atual quando não há padrão escolhido. Se houver padrão e medida digitada na mesma linha, a medida digitada prevalece naquele campo. A última coluna, **Padrão pronto**, contém os formatos disponíveis. Clique **Aplicar tamanhos pendentes** e confirme para gravar no carimbo.

Para criar um padrão reutilizável, clique **+ Cadastrar padrão de tamanho**. No popup, preencha nome, altura e largura e clique **Salvar padrão**. Isso salva o padrão em `%APPDATA%\FolhasHOYT\padroes_tamanho.json` e não altera o modelo. O padrão fica disponível na última coluna de cada folha, inclusive após reabrir o Revit. **Cancelar** fecha o popup sem salvar e preserva as edições pendentes da tabela.
