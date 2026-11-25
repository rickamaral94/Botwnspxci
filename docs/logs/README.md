# Logs de testes do BOTW no Android

Histórico compartilhado por Amaral, Claude e Codex. Cada registro guarda o cenário, o que foi testado, as evidências, a conclusão e o próximo passo. Os relatórios detalhados ficam em `docs/`.

## Histórico

| Registro | Escopo | Resultado e situação |
| --- | --- | --- |
| [Turnip e frame generation](2026-11-historico-odin2.md#turnip-e-frame-generation) | BOTW 1.8.2, Odin 2 Portal | Turnip Amaral v5.7.13.1 com LRZ ligado foi a configuração escolhida no trecho avaliado. |
| [60 FPS e cache de vértices](2026-11-historico-odin2.md#60-fps-e-cache-de-vértices) | BOTW 1.8.2, Odin 2 Portal | 37,56 FPS reais na cena pesada a 1×. O ganho do cache experimental aguarda teste físico. |
| [Upstream 0.3.4-beta-amaral.1](2026-11-historico-odin2.md#upstream-034-beta-amaral1) | Build e testes no host | APK e testes verificados no host. A validação em hardware segue pendente no relatório. |
| [Revisão do repositório, 12/11](2026-11-12-revisao-repo.md) | Amaral.2, host | Sem perdas do upstream; merge do upstream registrado; testes no repositório (`tools/run_host_tests.sh`). O cache de vértices não age no Odin com o Turnip. |
| [Amaral.3, 12/11](2026-11-12-amaral3.md) | Host | Pré-aquecimento de pipelines (opção experimental, desligada) e medição de programas e pipelines em jogo; contador do caso de alias do G-buffer, ainda sem correção. Testes no Odin pendentes. |
| [Amaral.5, 19/11](2026-11-19-amaral5.md) | Host, APK 43 | Upstream 0.4.7 (fence por submissão, vertex input dinâmico, pré-aquecimento do upstream no lugar do nosso); do GTA V: teste de profundidade antecipado, logs de desempenho, GPU por tipo de passe, release por CI. Testes no Odin pendentes. |
| [Amaral.6, 20/11](2026-11-20-amaral6.md) | Host, APK 44 | Travadas de primeira passagem: pré-aquecimento do upstream em Automático (ligado com o Turnip), teste antecipado desligado (o Turnip já faz EARLY_Z), classificação dos pipelines para decidir o pipeline library. Decidido com o agente do Turnip. |
| [Amaral.7, 24/11](2026-11-24-amaral7.md) | Host, APK 45 | Upstream 0.4.11 (slots de textura: +20% num Adreno 750; a janela de constant buffers sai do Odin). Chaves para isolar a água branca e o cabelo preto; A/B do `invariant`; avaliação dos outros ports. |
| [Amaral.8, 24/11](2026-11-24-amaral8.md) | Host, APK 46 | Leitura direta dos alvos no Automático da 740 (as cópias eram 17 de 38,5 ms por quadro); pré-aquecimento pela lista de volta, com a lista distribuída no APK. |
| [Ports de Switch para Android, 24/11](2026-11-24-ports-android.md) | Avaliação | totk-android (mesmo SoC do Odin), TOTKDroid, Peanuts Native (GPL: só ideias): 12 técnicas por ordem de ganho. |
| [Amaral.9, 24/11](2026-11-24-amaral9.md) | Host, APK 47 | Fases 0 e 1 do plano da gravação em várias threads: GPU por quadro protegido, símbolos no release; checagem e hash de texturas em threads auxiliares, micro-cortes (do TOTKDroid). |
| [Amaral.10, 24/11](2026-11-24-amaral10.md) | Host, APK 48 | A lista de pipelines no APK (1.074) e a leitura dela corrigida; thread de fila (experimental) para a espera de 40% no present; registro cru dos timestamps de GPU. |
| [Amaral.11, 24/11](2026-11-24-amaral11.md) | Odin + host, APK 49 | Pré-aquecimento confirmado no Odin: draws pulados ~10.000 → 83–397 por sessão. O +47% da thread de fila não vale (geração de quadros ligada e o primeiro bloco era uma transição); o A/B agora descarta o aquecimento e diz se a thread rodou. |
| [Amaral.12, 24/11](2026-11-24-amaral12.md) | Odin + host, APK 50 | Thread de fila sem ganho (36,36 contra 36,31 fps, p95 pior). O Odin está limitado pela GPU: 27–29 ms por quadro em jogo, com a meta de 60. O "GPU 0,00" vinha de um fim de envio 37,9 s no futuro; a conta agora se recupera. |
| [Amaral.13, 24/11](2026-11-24-amaral13.md) | Odin + host, APK 51 | A conta da GPU certa desde o início (3 fins descartados). SMAA: 1,06 ms contra 0,4 do FXAA. A máscara do HUD da geração de quadros custava 2,8 ms; agora é feita na metade do tamanho. |
| [Amaral.14, 24/11](2026-11-24-amaral14.md) | host, APK 52 | Medições para o agente do Turnip: quantos binds de set são só de offset dinâmico (custam como um set novo no Turnip), e a geração de quadros separada da máscara do HUD na tabela por passe. |
| [Amaral.14 no Odin, 24/11](2026-11-24-amaral14-odin.md) | Odin, 6 sessões + 2 traces | O lab do driver (bindless mask) não dá ganho mensurável. Os traces mostram as cores do jogo sem UBWC e o G-buffer em ~55 passes por quadro; com a lista de formatos, a GPU caiu para 24,4 ms (uma sessão, A/B/A pendente). |
| [Amaral.15, 24/11](2026-11-24-amaral15.md) | host, APK 53 (candidata, sem release) | A queda sustentada é da GPU (31–33 ms por quadro real com 5 mil draws; CPUs 15–21 ms). Telemetria por quadro real com CSV e bytes por origem; UBWC nos alvos de cor no Turnip 7xx (lista de formatos). A/B/A no Odin pendente. |
| [Amaral.16, 24/11](2026-11-24-amaral16.md) | host + traces, APK 54 (candidata) | O LRZ está desligado em 100% dos passes com depth (trace). Regras do Turnip lidas no código da versão do Odin; previsão por draw (`[lrz]`) para achar quem o invalida. Nenhuma mudança na imagem. |
| [Amaral.17, 24/11](2026-11-24-amaral17.md) | host, APK 55 (candidata) | As linhas `[lrz]` separam as invalidações de FS sem escrita de depth (pedido do agente do Turnip para um lab) e trazem a contagem de vértices dos draws, para achar clears por draw do jogo. |
| [Release Amaral.17, 24/11](2026-11-24-release-amaral17.md) | release (não pre-release), APK 55 | A versão para jogar: as melhorias medidas ligadas, os experimentos sem ganho desligados, as medições só durante "Medir desempenho", e a configuração recomendada no Odin. |
| [Amaral.18, 24/11](2026-11-24-amaral18.md) | Odin (release .17) + host, APK 56 | A .17 no Odin: 29,76 quadros reais/s, GPU 24,1 ms (antes 27,9 e 27,5). As pequenas quedas são buracos de 33 ms na grade da geração de quadros e pipelines novos em área nova. Nova opção "Suavidade da geração de quadros" (folga de um período, ligada). |

## Revisões externas e Turnip

- [12/11 — Passagem para o Claude com os ajustes de PC pendentes](2026-11-12-handoff-claude-ajustes-pc.md)
- [11/11 — Amaral.2, mudanças vindas de outros ports e testes](2026-11-11-amaral2-cross-port.md)
- [11/11 — outros ports e experimentos para o BOTW](2026-11-11-revisao-externa.md)
- [Turnip — evidências para o Amaral Adreno Tools](TURNIP.md)
- [Campainha do agente Turnip — como pedir ajuste ou análise do driver](CAMPAINHA-TURNIP.md)

## Próxima rodada no Odin 2 Portal

1. Comparar a build de referência e a candidata no Grande Platô, com o mesmo save, trajeto, versão do jogo, driver, resolução, cache aquecido, modo de energia e temperatura inicial comparável. Rodar A/B/A com framegen desligado e registrar FPS reais, p95/p99, 1% low e regressões visuais ou de física.
2. **Não** medir o cache de vértices no Odin com o Turnip: lá os vértices são lidos direto da memória do jogo e o cache não roda (`[guest-copy-diag]` mostra `vertex binds direct=` alto e `copied=` perto de zero). Medir onde há cópia: driver da Qualcomm, Mali, ou o Turnip com "Memória do jogo na GPU" desligada ([revisão de 12/11](2026-11-12-revisao-repo.md)).
3. Comparar taxa de quadros 40 sem framegen, framegen 3x (40 → 120) e framegen 2x, como no [plano de 12/11](2026-11-12-revisao-repo.md#conclusão-e-próximo-passo).
4. Se testar framegen, registrar o multiplicador e os FPS reais e apresentados separadamente. Repetir a rota e observar o HUD e a imagem em movimento.

## Como registrar e revisar

- Crie `AAAA-MM-DD-build-cenario.md` a partir do [modelo](MODELO.md) e acrescente uma linha ao índice. Acrescente novas rodadas ao registro do mesmo experimento e date qualquer revisão de conclusão.
- Identifique **medição no aparelho**, **relato do jogador**, **verificação no host** e **hipótese**. Cite o nome do log, a janela ou o marcador relevante e o trecho de `[diag] summary` quando houver. Indique as condições que limitam a comparação.
- Mantenha os logs brutos com Amaral. No Git, use métricas resumidas e referências às capturas, sem dados pessoais, credenciais ou arquivos do jogo.
- Testes no host: `tools/run_host_tests.sh` (os que não pedem aparelho, NDK nem extras do Python).
- Claude e Codex consultam este índice antes de repetir um teste. Registrem o parecer, a evidência conferida e as pendências. Na issue ou no PR relacionado, incluam o caminho do registro e o commit.
