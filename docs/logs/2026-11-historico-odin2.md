# Novembro de 2026 — histórico inicial no Odin 2 Portal

Aparelho de referência: AYN Odin 2 Portal Pro, Snapdragon 8 Gen 2 e Adreno 740. Este histórico reúne resultados anteriores dos relatórios do projeto.

## Turnip e frame generation

- **Medição no aparelho, 31/10:** BOTW 1.8.2, margem do lago, coletas de 60 s, LSFG 3.1 em 2× e sync lag desligado. O Turnip Amaral 27.0.0-devel v5.7.13.1 com LRZ ligado e resolução 1× registrou 28,0 FPS reais, p95 de tela de 33,4 ms e 14,9 ms de GPU por quadro real. No Turnip 26.2 R4, com LRZ ligado e 1×, a coleta registrou 15,7 FPS reais e p95 de tela de 75,2 ms.
- **Conclusão:** o relatório escolheu o Turnip Amaral com LRZ ligado para o cenário medido. A rodada com LRZ desligado também mudou a resolução, deixando em aberto o ganho isolado dessa opção. Fonte [avaliação do Turnip no Odin 2](../AVALIACAO-TURNIP-2026-10-31.md).

## 60 FPS e cache de vértices

- **Medição no aparelho, registrada em 04/11:** no BOTW 1.8.2, Turnip Amaral v5.8.17.1, resolução 1× e framegen desligado, a cena pesada registrou 37,56 FPS reais em 60 s e frametime de apresentação p50/p95/p99 de 26,12/32,26/44,34 ms. A rodada a 0,75× registrou 40,08 FPS com diferenças de trajeto, cache e temperatura. A cena leve chegou a cerca de 59,9 FPS.
- **Verificação no host:** o APK experimental com reaproveitamento de cópias de vértices passou pelo build Gradle e pelas verificações de empacotamento. As capturas citadas são anteriores a esse experimento.
- **Conclusão:** 60 FPS nativos sustentados na cena pesada e o ganho do cache de vértices seguem pendentes. A próxima rodada deve alternar a opção dentro do mesmo APK e cruzar `[guest-copy-diag]` com frametime e inspeção da geometria. Fonte [passagem para revisão do Claude](https://github.com/rickamaral94/Botwnspxci/blob/827a0db95821426f53b41b4ab1a5044bd2b95414/docs/HANDOFF-CLAUDE-2026-11-04.md).

## Upstream 0.3.4-beta-amaral.1

- **Verificação no host, registrada em 11/11:** passaram os testes de compilação do jogo, RomFS e ASTC, além de `assembleRelease` e verificações do APK ARM64, incluindo assinatura v3 e alinhamento.
- **Conclusão:** a candidata está documentada e verificada no host. FPS, frametime e compatibilidade no Odin 2 aguardam a comparação física com a build de referência. Fonte [relatório da Amaral.1](https://github.com/rickamaral94/Botwnspxci/blob/827a0db95821426f53b41b4ab1a5044bd2b95414/docs/UPSTREAM-AMARAL1-2026-11-11.md).
