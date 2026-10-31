# Diagnóstico de desempenho (Fase M)

O diagnóstico responde onde vai o tempo de cada quadro: em que threads do jogo, na GPU, e em que clocks e
temperaturas. É o primeiro passo antes de qualquer otimização de CPU (Fase C). Código: `runtime/diag.c`.

## Como usar

1. Na tela inicial, em **Configurações > Arquivos**, deixe **Salvar um arquivo de log** ligado e toque em **Medir desempenho (60 s)**.
   A aba Arquivos só existe na tela inicial.
2. Inicie o jogo e jogue normalmente. A gravação começa depois de **5 s seguidos de jogo**, fora de menus, pausa,
   eventos e filmes, e dura 60 s. Uma linha no canto da tela mostra a espera e quanto falta.
3. No fim, o relatório vai para o log, em linhas `[diag]`, e para `perf-diag.txt` na pasta de dados do app. Mande o
   `botwrecomp-log.txt`.

Por adb, `LARECOMP_DIAG=<segundos>` mede a partir do início da sessão. `LARECOMP_DIAG_TID=<id>[,<id>]` acrescenta
threads do jogo à amostragem.

Desligado, o diagnóstico custa um teste de flag em cada svc e em cada espera instrumentada. Nada é gravado e nenhum
timer existe.

## O que o relatório traz

### Quadros

O intervalo entre dois `vkQueuePresentKHR` na thread de render:
- média, p50, p95, p99 e máximo, só dos quadros de gameplay;
- a mesma estatística separada entre os blocos com o amostrador ligado e desligado. Ele alterna 5 s ligado e 5 s
  desligado, e a diferença entre os dois blocos mostra o custo dele;
- o tempo de `vkAcquireNextImageKHR` e o de `vkQueuePresentKHR`.

### GPU

- **Tempo ocupado por intervalo entre presents:** timestamps no início e no fim de cada submissão, sem o tempo ocioso
  entre elas (`gpu_busy_total`, em exec.c).
- **Composição final:** dois timestamps em volta de "a imagem do jogo na janela + menus/overlay" (device.c), lidos 16
  quadros depois.

### Aparelho, a cada 2 s

- frequência de cada cluster de CPU (mínima, média e máxima);
- temperatura do SoC;
- status térmico do Android;
- headroom.

O que o aparelho não fornece aparece como "n/a".

### Threads: tempo de parede em categorias exclusivas

Cada intervalo de tempo cai em **uma única** categoria. A categoria interna pausa a externa: uma svc dentro de uma
espera do host volta para a espera quando termina.

| Categoria | O que é |
| --- | --- |
| `run` | trabalho da própria thread: código do jogo e HLE/NVN do runtime. As amostras dizem qual |
| `svc` | dentro de uma svc que não bloqueia |
| `svc-block` | dentro de uma svc que bloqueia, por número: WaitSynchronization, ArbitrateLock, WaitProcessWideKeyAtomic, WaitForAddress… A CPU do próprio handler entra junto |
| `yield` | `SleepThread(0/-1/-2)` |
| `core0-wait` | esperando a vez no núcleo 0 (`core0_acquire`) |
| `host-wait` | esperas longas do runtime numa thread do jogo (`kernel_blocking_begin/_end`, o renderer) |
| `gpu-wait` | `vk_wait_seq` |
| `render-idle` / `render-present` | a thread de render sem trabalho / apresentando |
| `acquire` / `present-call` | as duas chamadas do swapchain |
| *não atribuído* | o tempo antes da primeira transição da thread na janela (por exemplo, uma thread bloqueada desde antes) |

- **CPU própria de cada thread:** lida **por ela mesma** (`CLOCK_THREAD_CPUTIME_ID`), na primeira transição e a
  cada 100 ms. Parede menos CPU menos as esperas é o tempo em que a thread estava pronta mas não rodou (preempção,
  migração).
- **Quem é quem:** o relatório diz se a thread que apresenta é a thread principal (handle 0x101). Pelos logs de
  outubro, não é: a t82 apresenta e espera a t80.
- **Custo dos ganchos:** o relatório estima o custo total pelo número de transições.

### Amostras por endereço

Amostradas: a thread principal, a que apresenta, a de render e as listadas em `LARECOMP_DIAG_TID`.
- **Como é medido:**
  - cada thread cria **o próprio timer** sobre o **próprio relógio de CPU**, com sinal para ela mesma
    (`SIGEV_THREAD_ID`);
  - o handler confere que está na thread certa. Se não estiver, a amostra é descartada e contada;
  - o pedido é uma amostra por 1 ms de CPU, mas o kernel entrega na granularidade do tick (4 ms com HZ 250, o comum no
    Android).
- **O que cada amostra guarda:**
  - **pc e lr como dois endereços soltos**, não como pilha. O lr é só "quem chamou por último";
  - a categoria atual da thread.
- **Contadores:** amostras mantidas, perdidas (anel cheio) e descartadas (thread errada), e o tempo gasto no handler.
- **Nomes:**
  - código do jogo vira `f_<endereço do jogo>`, pela tabela do gamelib;
  - o resto vira `módulo:símbolo` quando o módulo exporta o símbolo, senão `módulo+offset` em blocos de 64 bytes,
    com o build id do módulo listado no fim.
  - `tools/diag_symbolize.py log --lib <libmain.so sem strip da mesma build>` resolve esses offsets e soma por
    função. O script avisa se o build id não bate.
- **Desligado no código nativo:** com "Código do jogo: Nativo", o amostrador não liga (handler de sinal entre
  instruções do jogo reescritas não foi testado). As categorias continuam.

## Testes

- **No host:** `cc -DDIAG_TESTING -I runtime runtime/diag.c tools/diag_tests/test_diag.c -lpthread -ldl -lrt`, com
  ASan/UBSan. Cobre:
  - percentis;
  - contabilidade exclusiva com relógio falso: soma igual à janela, recorte nas bordas, pop sem push ignorado;
  - amostrador real com o timer na própria thread, sem amostras perdidas e sem amostras na thread errada;
  - nomes por módulo;
  - o fluxo inteiro do relatório.
- **No aparelho:** o relatório precisa mostrar as categorias somando a janela, as amostras perdidas e o custo do
  amostrador (ligado vs desligado).

## Fase C, item 1: constant buffers lidos no lugar sem o Sync lag (30/10/2026)

### O que a medição mostrou

Odin 2 Portal, Turnip 27, 1.8.2, Sync lag desligado (com ele, o Link afunda):
- **Quadro:** p50 22,1 ms. Com o Sync lag ligado eram 18,9 ms.
- **Thread principal:** espera **7,3 ms por quadro** pela GPU. A GPU fica ocupada só ~6,6 ms; o resto da espera é a
  tradução na thread de render, ~9,7 ms por quadro.
- **Thread de render:** ~16% das amostras estão nas cópias dos constant buffers (`guest_copy` / `ubo_span` chamando o
  memcpy da libc).

### O que mudou

- **Ligado sozinho:** quando o jogo espera a GPU a cada quadro (o Sync lag fora de efeito) e o heap está na memória
  da GPU (Turnip), os constant buffers são lidos no lugar. Isso vale para o `ubo_direct` e para a janela por draw
  (`cbwin_bind`). As duas coisas já existiam e estavam desligadas por padrão.
- **Por que estavam desligadas:** os artefatos (água branca, "cortinas" no terreno, pontas em objetos ao longe) foram
  atribuídos à CPU escrevendo o quadro seguinte enquanto a GPU ainda lia este. Só o Sync lag deixa isso acontecer.
- **Decisão por draw:** ligar o Sync lag em jogo volta às cópias.
- **Tradução dos shaders:** passa a incluir o teste da janela sempre que o heap está na GPU. O cache de SPIR-V é
  indexado pelo fonte, então os shaders são compilados de novo uma vez.
- **Chaves:**
  - `LARECOMP_INPLACE_CBUF=0` desliga e `=1` força, inclusive com o lag;
  - `LARECOMP_AB=<quadros>:inplace` alterna;
  - `LARECOMP_CB_WINDOW=0` tira o teste dos shaders;
  - o log mostra `[vk] constant buffers read in place: on/off`.
- **Ganho esperado**, pelas medições do upstream (1.9.0, POCO): ~0,6 ms (`UBO_DIRECT`) + ~0,3 ms (janela) da thread de
  render, que hoje está no caminho crítico.
- **A conferir no aparelho:**
  - visual: água, terreno de longe, golpes em objetos distantes;
  - a medição de 60 s, comparada com os 22,1 ms.

### Resultado (Medir e comparar, 120 s, SoC no modo padrão, Sync lag desligado)

| | Ligado | Desligado |
| --- | --- | --- |
| Intervalo entre quadros (p50 / média) | 26,12 / 26,40 ms | 26,51 / 26,57 ms |
| CPU da thread de render por quadro | **10,21 ms** | 11,43 ms |
| CPU da thread principal por quadro | 12,92 ms | 13,14 ms |
| GPU ocupada por quadro (média) | 18,08 ms | 18,38 ms |
| Clocks médios (MHz) | 1152 / 2525 / 1843 | 1122 / 2560 / 1887 |

- **A thread de render ficou 1,2 ms mais rápida (-11%)**, e não apareceu nenhum artefato. A leitura no lugar fica
  ligada por padrão sem o Sync lag.
- **O quadro só ganhou 0,4 ms.** No modo padrão do SoC, quem segura é a **GPU**: 18 ms ocupada por quadro, contra
  ~6,6 ms quando os clocks estavam no máximo. A thread principal espera a GPU ~10 ms por quadro.
- **A causa provável:** o governador deixa o clock da GPU baixo, porque o quadro é em série (o jogo, depois a
  tradução, depois a GPU) e a GPU fica parada parte do tempo.

### Desligado por padrão de novo (30/10, à tarde)

- Com a leitura no lugar ligada e o Sync lag desligado, as pernas do Link voltaram a afundar no Odin 2 Portal.
- As alturas do terreno que posicionam os pés saem de passes de GPU que leem esses buffers.
- **Agora o padrão volta às cópias.** A opção **Vídeo > Constant buffers lidos no lugar (experimental)** liga a
  leitura no lugar para teste.
- O "Medir e comparar" continua alternando a leitura no lugar, com ou sem a opção ligada.
- **Confirmado no Odin 2 Portal (30/10):** com a opção desligada e a geração de quadros 2x ligada, o Link não afunda.
  - A causa do afundamento era a leitura no lugar, mesmo com o Sync lag desligado.
  - A explicação antiga do projeto (o Sync lag deixa a CPU um quadro à frente) não basta: algum buffer que alimenta
    as alturas do terreno é reescrito pela CPU antes de a GPU usá-lo, também sem o lag.
  - A opção fica experimental e desligada.


## ADPF com as threads do jogo (30/10)

**O que os dados mostraram (Odin 2, framegen 2x, trecho pesado):** a sessão de dicas de desempenho tinha só a thread
que apresenta e a de renderização.

- A thread que apresenta usa ~0,6 ms de CPU por quadro: ela passa o tempo esperando.
- Quem trabalha é a thread principal do jogo e duas threads de trabalho, com 4–7 ms cada. Elas ficavam fora da
  sessão.
- Os núcleos grandes rodavam a ~1,9 de 3,2 GHz.

**Mudança** (`platform/android.c`, com o `kernel_busiest_threads` em `kernel.c`):

- A cada 2 s entram na sessão até 3 threads do jogo que mais usaram CPU, cada uma com mais de 15% do tempo.
- Para o conjunto não oscilar, uma thread que já está na sessão continua enquanto estiver entre as 4 mais ocupadas.
- A meta e o trabalho reportado são os de antes. O SoC continua no modo padrão, e o Android só sobe o clock quando o
  quadro passa da meta.
- `LARECOMP_ADPF_WORKERS=0` desliga.

**"Medir e comparar"** agora alterna isso a cada 10 s. O relatório mostra, para cada lado:

- quadros reais por segundo;
- a cadência na tela;
- o intervalo entre presents;
- a CPU das threads;
- os MHz dos clusters, que dão o custo de bateria.

Os constant buffers no lugar saíram da comparação: estão desligados por padrão e não voltam.

**Saúde dos timestamps de GPU:** no último teste, o "GPU ocupada" somou só ~4 s em 60 s. A dinâmica e o diagnóstico
dependem desse número, por isso o relatório agora conta as submissões:

- lidas;
- contidas no intervalo de outra;
- não prontas;
- invertidas;
- nunca lidas (slot reutilizado antes).

**Resultado do A/B** (Odin 2, framegen 2x, 120 s, trecho pesado):

| | ADPF com as threads do jogo | Só as duas threads de antes |
| --- | --- | --- |
| Quadros reais por segundo | 26,32 | 27,33 |
| p95 da cadência na tela | 33,46 ms | 33,45 ms |
| Clusters (média, MHz) | 1152 / 2605 / 1977 | 1221 / 2330 / 1887 |

Não houve ganho, e o clock ficou mais alto. Por isso fica **desligado por padrão**; `LARECOMP_ADPF_WORKERS=1` liga.

**Timestamps de GPU:**

- 9193 submissões contadas;
- 18187 dentro do intervalo de outra, nenhuma perdida ou não lida.

As contidas são submissões leves. O Turnip grava os timestamps delas assim que o processador de comandos chega a
elas, sem esperar o trabalho anterior. A união dos intervalos continua valendo como tempo ocupado. No trecho pesado a
dinâmica mede 23–27 ms de GPU por quadro, contra quadros de 36–40 ms. A GPU fica perto do limite no clock que o modo
padrão dá, e baixar a resolução faz o governador baixar o clock junto.

## Comparar drivers Turnip

O relatório (`perf-diag.txt`) começa com duas linhas:

- **`run:`** mostra a configuração da medição: o pacote do driver e o nome e a versão que ele declara, o LRZ, a
  resolução interna (na Dinâmica, a escala do momento), o framegen, a taxa de quadros e o Sync lag.
- **`summary:`** é a linha para comparar execuções. Ela traz quadros reais por segundo, a cadência na tela
  (p50/p95/p99), a GPU por quadro real, os MHz médios dos clusters e a faixa de temperatura.

Cada relatório também é copiado como `perf-diag-AAAAMMDD-HHMMSS.txt`, para várias medições irem juntas.

**Protocolo:**

1. Todos os drivers com as mesmas configurações:
   - **resolução interna fixa**: não Dinâmica, para a GPU fazer o mesmo trabalho em todos;
   - framegen 2x e 30 fps;
   - SoC no modo padrão.
2. O mesmo trecho, partindo de um save perto dele e fazendo o mesmo caminho.
3. Esperar o aparelho esfriar entre as medições (a faixa de temperatura aparece no resumo).
4. "Medir desempenho (60 s)" em cada driver.
5. **No mesmo driver, LRZ ligado e desligado** (Iniciar > Turnip low-resolution Z). No Adreno 740 o automático o
   deixa desligado, porque o LRZ pode perder desenhos em alguns Adreno. Ele economiza GPU em cenas com muita
   sobreposição, mas é preciso conferir a imagem: objetos sumindo ou piscando.
6. **Critério:** mais quadros reais por segundo e menor p95 na tela, com a GPU por quadro real como explicação, sem
   defeito visual e com MHz e temperatura parecidos.

**Primeiras medições** (30/10, Odin 2, framegen 2x, resolução Dinâmica, 120 s):

| Driver | Quadros reais/s | Tela p50 / p95 / p99 | GPU por quadro real | Observação |
| --- | --- | --- | --- | --- |
| turnip_amaral 27.0.0-devel v5.7.13.1 (Mesa git-4b0f64ceac) | 28,79 | 16,71 / 33,43 / 41,78 ms | 16,5 ms | escala em 0,55 |
| Qualcomm do sistema (build 69e13475cb, 27/12/2023) | 14,83 | 25,06 / 75,16 / 75,22 ms | 17,7 ms | inutilizável |

O driver do sistema tem muitos artefatos e falhas visuais. Ele roda no modo de cópia, sem o heap da GPU, e a thread de
render chega a ~52 ms por quadro (ver `ANALISE-DRIVER-PADRAO-2026-10-21.md`). Por isso fica fora da comparação, que
segue só entre builds do Turnip, e com o LRZ ligado e desligado.

**Segunda rodada** (30/10, Odin 2, framegen 2x, resolução 1x fixa, 60 s):

| Driver | LRZ | Quadros reais/s | Tela p50 / p95 / p99 | GPU por quadro real | SoC |
| --- | --- | --- | --- | --- | --- |
| turnip_amaral 27.0.0-devel v5.7.13.1 | ligado | **28,00** | 16,71 / 33,42 / 41,77 ms | **14,9 ms** | 47–66 °C |
| Turnio v26.2.0 R4 (Mesa 26.2) | ligado | 15,65 | 41,78 / 75,20 / 75,23 ms | 17,2 ms | 42–51 °C |

- **v26.2 R4:** a thread de render fica 77% do tempo "rodando" (24,9 ms por quadro), mas só 7,2 ms disso é CPU. O
  resto é espera dentro do driver, no envio, que aparece como `ioctl`. Ele faz o mesmo trabalho que o amaral (~2000
  desenhos por quadro) e fica com metade da taxa. Descartado.
- **LRZ no amaral:** em 1x com o LRZ ligado, a GPU gasta 14,9 ms por quadro real. Com o LRZ desligado e a escala em
  0,55 eram 16,5 ms. Ou seja, o LRZ economiza mais GPU do que baixar a resolução quase pela metade. Falta confirmar que
  não há defeito visual (desenhos sumindo ou piscando) para o automático ligar o LRZ no Adreno 740 com esse driver.
