# BOTW 1.8.2 no Odin 2: caminho para 60 FPS nativos

Análise em 2026-11-04 dos logs `botwrecomp-log.txt` e `botwrecomp-log-previous.txt` enviados pelo usuário, do branch `ccr-83419136-h3hlw3` e da fonte TOTK local `.16`. O APK da sessão é BOTW 1.8.2 recompilado (`de0b6ac4...`), Turnip Amaral 27.0.0-devel v5.8.17.1, LRZ ligado, resolução interna 1×, framegen desligado, 60 FPS selecionados e sync lag desligado. O suporte a 60 FPS já existe nas versões 1.8.2 e 1.9.0, inclusive nos hooks de VFR/espera do código recompilado e no caminho nativo. A medição diz por que essa cena ainda não chega lá.

| Evidência | Interpretação e limite |
| --- | --- |
| Duas capturas, janelas quentes de 42–90 s com espera de build até 18 ms/2 s: média das janelas 36,4 e 37,3 FPS (10 e 22 janelas, respectivamente). | São trajetórias similares, não A/B de um patch. Cache de shaders frio causa travadas iniciais, mas não explica o platô de 35–41 FPS. |
| Captura atual: 2.195 quadros de gameplay/60 s, 37,56 FPS; intervalo p50 26,12, p95 32,26, p99 44,34 ms. | Para 60 sustentados é preciso atingir ~16,67 ms também em quadros difíceis. O diagnóstico soma menus/cenas diferentes no intervalo. |
| No trecho anterior à área pesada, o log registra 59,9 FPS entre 29,8 e 31,8 s, com 7.040 draws e 12,6 MB de ring; entre 39,9 e 41,9 s já são mais de 140 mil draws e mais de 1 GB de ring por janela. | A opção de 60 funciona numa cena leve. O alvo real é sustentar 60 nas cenas de mundo aberto; a mudança de carga impede comparar FPS das duas janelas como efeito de um patch. |
| Render thread CPU 9,66 ms/quadro, ocioso 16,40 ms; thread principal CPU 13,05 ms/quadro e espera GPU 9,38 ms. | Render CPU isolado cabe em 16,67 ms. Main espera a GPU, mas as dependências entre threads não estão completamente atribuídas. |
| GPU: média de busy 15,41 ms por intervalo, p50 22,02, p95 25,07; 4.558/9.902 spans de timestamp contidos em spans anteriores, 15.108,7 ms brutos cobertos. | A média agregada está enviesada pela política de união/epochs; não concluir folga de GPU a partir dos 15,41 ms. Precisamos de quadros por passe e teste de resolução 1× contra 0,75× no mesmo save. |
| Janelas quentes: ~143 mil draws e ~1.108 MB de alocação lógica do anel a cada 2 s na captura atual. | Muito trabalho de tradução/upload; o log não atribui bytes a vértices, uniforms, cópias de texturas ou espaço reservado no anel. |
| SoC 46–71 °C; Android thermal status 0. | Temperatura elevada, mas sem evidência de thermal throttling no status. |

## Rodada de sensibilidade a 0,75× (recebida depois da análise inicial)

Log `botwrecomp-log.txt` das 15:06, com o mesmo BOTW 1.8.2, Turnip v5.8.17.1, LRZ, 60 selecionados, framegen e sync lag desligados. O `botwrecomp-log-previous.txt` desta rodada contém apenas a inicialização de 15:05; a referência de 1× abaixo vem da captura anterior descrita acima. **Não é A/B/BA da PR: a build é a mesma e não há `[guest-copy-diag]`, logo a opção experimental não estava disponível/ligada.**

| Métrica | Referência 1× | Nova rodada 0,75× | Limite da comparação |
| --- | ---: | ---: | --- |
| FPS reais, diagnóstico 60 s | 37,56 | 40,08 | +2,52 FPS (+6,7%) observados entre sessões; percurso/cache/calor não idênticos. |
| Present p50 / p95 / p99 | 26,12 / 32,26 / 44,34 ms | 24,81 / 28,00 / 32,31 ms | Melhora observada na distribuição; não atribuída exclusivamente à resolução. |
| GPU busy p50 / p95 por intervalo | 22,02 / 25,07 ms | 20,43 / 21,87 ms | Há spans sobrepostos (4.384 de 11.218 na nova captura); a média agregada de 15,01 ms não comprova folga por quadro. |
| CPU principal / render, clock próprio | 13,05 / 9,66 ms/quadro | 12,50 / 10,14 ms/quadro | Trabalho e percurso variam. |
| Temperatura do SoC | 46–71 °C | 42–52 °C | Fator de confusão importante; Android thermal status 0 nas duas capturas. |

Nas janelas quentes da nova rodada (t=43–89 s), 23 amostras de dois segundos tiveram média de 40,15 FPS; na referência 1×, 22 janelas similares tiveram 37,27 FPS. A queda de resolução reduziu a carga observada, mas ainda ficou longe dos 60 FPS e não tornou plausível resolver o platô somente mudando pixels. Próxima prioridade: medir custo GPU por passe e separar CPU, submissões, descriptors e cópias em cena equivalente. Manter 1× como alvo de qualidade.

## Experimentos anteriores que orientam o próximo ciclo

Os registros existentes em `docs/ANALISE-DRIVER-PADRAO-2026-10-21.md`, `docs/DESEMPENHO-60FPS-2026-10-23.md` e `docs/BOTW-PORT.md` já examinaram o mesmo tipo de carga: dividir os sets de texturas dos UBOs reduziu binds, mas não o tempo de GPU; SGSR reduziu o tempo GPU numa sessão BOTW 1.9.0 sem melhorar o período do quadro; e um perfil por passe mostrou o G-buffer como parte importante do custo, com o perfilador aumentando significativamente o próprio tempo medido. Não repetir essas mudanças como solução presumida para 1.8.2. Também há evidência histórica de uma cadeia serial entre lógica do jogo, tradução da lista e apresentação, variando com a versão e a cena.

Na captura nova de 1.8.2, a render thread consumiu 10,14 ms de CPU por quadro; 29,2% de suas amostras ficaram em `libvulkan_freedreno.so`. A thread principal consumiu 12,50 ms de CPU e 8,80 ms em espera GPU por quadro. São tempos de threads diferentes, com sobreposição, não parcelas que se somam para obter o frametime. Há ~140 mil draws e ~1,2 GB de reservas lógicas do ring por dois segundos nas janelas quentes. O perfil por passe (`LARECOMP_GPUPROF_AT`) e o detalhamento de CPU (`LARECOMP_VK_PROF`) já existem; ativá-los de forma curta e isolada no trecho 1× e comparar com a execução sem perfil para estimar sua perturbação. O relatório `[guest-copy-diag]` só virá de uma build da PR, e não desta captura. A hipótese do cache de vértices permanece **sem validação**.

## Transferências entre os projetos

| Direção | Estado | Decisão |
| --- | --- | --- |
| TOTK → BOTW: reaproveitar prefixo de cópias de vértices em uma submissão | TOTK `.16` evita recopiar bytes iniciais quando o draw seguinte pede mais índices; BOTW ainda cacheava exatamente `(endereço, tamanho)`. | Implementado como `LARECOMP_GCOPY_RANGE=1` **experimental**, desativado por padrão. O mesmo binário permite A/B; métricas `[guest-copy-diag]` medem bytes efetivamente copiados/reusados e crescimento. A hipótese só se mantém se houver menos bytes e queda repetível de CPU/frametime no BOTW. |
| TOTK → BOTW: prioridade a shaders bloqueantes / dois workers | Na captura fria BOTW anterior, 1.746 ms de espera com 345 compilações numa janela e travada de 1.032 ms; a atual mostra 294 ms e travada de 278 ms em outra passagem. | Investigar separadamente; cenas/cache diferem. Quatro workers já coincidiram com pressão Scudo no TOTK. Não escalar trabalhadores sem RSS, crash e A/B/BA. |
| TOTK → BOTW: timestamps por passe e verificação de epochs | Há `LARECOMP_GPUPROF_AT` e `LARECOMP_VK_PROF` no BOTW, mas a captura não contém esses perfis. | Usar o diagnóstico existente para caracterizar os passes GPU; não atribuir custo de 22–25 ms a um shader ou ao driver antes da medição. |
| BOTW → TOTK: VFR com pagamento gradual de tempo, evento/menu a 30, tempo de controle | O BOTW possui lógica própria em `runtime/hle/framepace.c`; TOTK usa controlador e relógios diferentes, com `totk_step_update` e patches da 1.4.2/1.4.3. | Comparar tolerância a hitch e pacing, portar princípios após teste físico/eventos; **não** copiar endereços/patches de jogo ou VFR literalmente. |
| BOTW → TOTK: Native game code | O BOTW mede pouco ganho de FPS da execução nativa sobre recompilada em cenário próprio, mas evita compilação no aparelho. | Pode inspirar distribuição, não é patch comprovado para 60 FPS do TOTK e exigiria trampolins específicos por versão. |

## Próxima comparação controlada

Mesmo save/driver/câmera, framegen desligado, sync lag fixo, energia e calor equivalentes: A (cópia padrão), B (`LARECOMP_GCOPY_RANGE=1`), A de novo; cache quente e depois frio. Repetir resolução 1×/0,75× separadamente. Registrar FPS real, p95/p99, GPU por passe, CPU render/main, bytes `[guest-copy-diag]`, RSS/Scudo e correção de geometria. O perfilador detalhado (`LARECOMP_VK_PROF`) pode alterar custo; medir seu overhead. Sem aparelho conectado e sem SDK/NDK neste workspace, não há build ARM64 nem validação de ganho deste candidato.

Critério para habilitar por padrão: menos cópia e melhora de frametime reproduzível sem vertices desatualizados, crashes ou aumento relevante de memória; caso não ocorra, reverter. A comparação de resolução já indica efeito limitado; o passo seguinte é localizar os passes e o trabalho de render que consomem os ~8 ms por quadro restantes antes de atribuir o custo ao driver ou ao jogo.

## Build experimental e assinatura

O menu Android > Video > Rendering oferece **Vertex copy reuse (experimental)**, desligado por padrão. A troca vale imediatamente e invalida entradas do cache feitas pelo modo anterior; `gcopy_range = 0/1` persiste no arquivo de ajustes. `LARECOMP_GCOPY_RANGE=0/1` prevalece se definido no lançamento; remova essa variável para usar o menu. `versionCode` 25, pacote `com.botwrecomp.android`. Medir A/B/A no mesmo APK, save e trecho em 1×, com framegen desligado, registrando `[guest-copy-diag]`, FPS real, P95/P99 e correção visual.

Em 2026-11-04 a compilação `assembleRelease` ARM64 foi concluída com SDK 36, NDK r30, CMake 3.30.4 e JDK 17, incluindo SDL3, shaderc, FFmpeg, Python/Zig/Unicorn e frame generation. O submódulo `PancakeTAS/dxbc` estava indisponível na origem; recuperamos **o mesmo commit** `78ab59a8aaeb43cd1b0a5e91ba86722433a10b78` de `manuelgzz/dxbc` apenas no checkout de build. `apksigner verify`, `zipalign -c`, `unzip -t`, manifesto e ELF64/AArch64 passaram; não houve execução no Odin.

`app/build.gradle.kts` usa `~/.botwrecompandroid/keystore.properties` para assinatura de release e cai na chave Android Debug quando ela não existe. Esse arquivo e a chave privada não foram encontrados no Git, no home ou nos arquivos BOTW acessíveis nesta sessão. O APK experimental compilado foi assinado pela chave de debug local (certificado SHA-256 `4ea20dde2ee1bbde1d7b594512fa8c31af481de98d580713e78d3a0bb41748f7`). **Não foi comprovado que atualize a instalação atual.** Para gerar o APK de atualização é necessário usar a chave original e comparar o certificado do APK anterior; não publicar a chave no repositório.
