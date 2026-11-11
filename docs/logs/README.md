# Logs de testes do BOTW no Android

Histórico compartilhado por Amaral, Claude e Codex. Cada registro guarda o cenário, o que foi testado, as evidências, a conclusão e o próximo passo. Os relatórios detalhados ficam em `docs/`.

## Histórico

| Registro | Escopo | Resultado e situação |
| --- | --- | --- |
| [Turnip e frame generation](2026-11-historico-odin2.md#turnip-e-frame-generation) | BOTW 1.8.2, Odin 2 Portal | Turnip Amaral v5.7.13.1 com LRZ ligado foi a configuração escolhida no trecho avaliado. |
| [60 FPS e cache de vértices](2026-11-historico-odin2.md#60-fps-e-cache-de-vértices) | BOTW 1.8.2, Odin 2 Portal | 37,56 FPS reais na cena pesada a 1×. O ganho do cache experimental aguarda teste físico. |
| [Upstream 0.3.4-beta-amaral.1](2026-11-historico-odin2.md#upstream-034-beta-amaral1) | Build e testes no host | APK e testes verificados no host. A validação em hardware segue pendente no relatório. |

## Revisões externas e Turnip

- [11/11 — outros ports e experimentos para o BOTW](2026-11-11-revisao-externa.md)
- [Turnip — evidências para o Amaral Adreno Tools](TURNIP.md)

## Próxima rodada no Odin 2 Portal

1. Comparar a build de referência e a candidata no Grande Platô, com o mesmo save, trajeto, versão do jogo, driver, resolução, cache aquecido, modo de energia e temperatura inicial comparável. Rodar A/B/A com framegen desligado e registrar FPS reais, p95/p99, 1% low e regressões visuais ou de física.
2. Medir o cache de vértices em A/B/A dentro do mesmo APK, mudando apenas a opção experimental. Cruzar `[guest-copy-diag]` com frametime e correção da geometria.
3. Se testar framegen, registrar o multiplicador e os FPS reais e apresentados separadamente. Repetir a rota e observar o HUD e a imagem em movimento.

## Como registrar e revisar

- Crie `AAAA-MM-DD-build-cenario.md` a partir do [modelo](MODELO.md) e acrescente uma linha ao índice. Acrescente novas rodadas ao registro do mesmo experimento e date qualquer revisão de conclusão.
- Identifique **medição no aparelho**, **relato do jogador**, **verificação no host** e **hipótese**. Cite o nome do log, a janela ou o marcador relevante e o trecho de `[diag] summary` quando houver. Indique as condições que limitam a comparação.
- Mantenha os logs brutos com Amaral. No Git, use métricas resumidas e referências às capturas, sem dados pessoais, credenciais ou arquivos do jogo.
- Claude e Codex consultam este índice antes de repetir um teste. Registrem o parecer, a evidência conferida e as pendências. Na issue ou no PR relacionado, incluam o caminho do registro e o commit.
