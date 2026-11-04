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

Critério para habilitar por padrão: menos cópia e melhora de frametime reproduzível sem vertices desatualizados, crashes ou aumento relevante de memória; caso não ocorra, reverter. Para chegar a 60 FPS nativos em 1×, o teste de resolução precisa primeiro indicar quanto do orçamento é trabalho GPU escalável.
