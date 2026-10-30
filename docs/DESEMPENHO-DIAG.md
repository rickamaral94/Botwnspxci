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
