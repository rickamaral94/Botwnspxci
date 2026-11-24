# Plano: gravação dos comandos Vulkan em várias threads (24/11/2026)

Pedido do Rick, depois da [avaliação dos ports](logs/2026-11-24-ports-android.md): planejar a gravação em várias
threads, a técnica que o totk-android usa para segurar o TOTK em 30 fps no AYN Thor (o mesmo SoC do Odin 2).

## 1. O que a medição diz antes de qualquer código

### O Odin hoje

Amaral.7 em 1x, Turnip v5.9.19.1, 120 s de "Medir desempenho":

| Linha | Log | Quadros reais/s | Thread de render (CPU) | Ociosa esperando trabalho | Thread principal do jogo (CPU) | GPU por quadro (janelas de 2 s) |
| --- | --- | --- | --- | --- | --- | --- |
| Cópias, sem geração de quadros | `de0604a7` | 35,1 | 15,5 ms por quadro (48,7% do tempo) | **37%** | 13,9 ms | 14,5–38,5 ms |
| Leitura direta, geração de quadros 2x | `d818ee27` | 30 (limite do 2x) | 12,2 ms por apresentação (48,8%) | **36%** | 11,1 ms | 29,6–33,1 ms |

- Por módulo, a thread de render é **55% nosso código, 27% Turnip e 15% libc** (memcpy das cópias).
- Ela passa mais de um terço do tempo **ociosa**, esperando o jogo mandar a próxima lista.
- O limite do quadro hoje é a **GPU**: ~30 ms por quadro com a leitura direta, contra 33 ms de orçamento a 30 fps e
  16,7 ms a 60.

Gravar em várias threads tira trabalho da CPU. Com a CPU com folga, **isso não dá fps agora**.

### O que os outros mediram

- **TOTKDroid** (mesma arquitetura que a nossa), POCO F7 Ultra:
  - construiu uma **thread de replay**, que grava os `vkCmd*` em ordem a partir de pacotes (`replay.c`, MIT);
  - foi estável, com a imagem certa, e tirou ~5 ms de CPU por quadro da thread de render;
  - **e deu 0 fps**: 46,5 contra 46,8 forçado a 60, 42,1 contra 42,7 sem limite;
  - o aparelho chegava a 93 °C em um minuto, e a CPU extra virou calor. Ficou desligada.
- **totk-android**, AYN Thor (Snapdragon 8 Gen 2 / Adreno 740):
  - uma thread "walker" decide os recursos de cada desenho, e **dois workers** gravam em command buffers;
  - um terceiro worker foi testado e rejeitado, porque as esperas cresceram;
  - o walker é o caminho crítico, com ~24–25 ms por quadro, e só 6% disso é Turnip;
  - a conclusão deles: **"o número de decisões tem que cair"**. Mais um cache não resolve.

### Consequência para o plano

A gravação em várias threads é **uma etapa da meta de 60 fps**, não um ganho imediato. Ela só vale quando:
1. a GPU couber em ~16 ms por quadro, que hoje está em ~30;
2. a thread de render virar o caminho crítico (hoje ela tem 37% de folga).

O plano vai em fases, com um critério de passagem entre elas. Nenhuma fase troca o padrão sem A/B no Odin.

## 2. As fases

### Fase 0 — medir direito (1–2 dias, sem risco)

1. **Consertar o "GPU por quadro real".** Ele sai 0,00 ou acima do intervalo desde o merge da Amaral.5.
   - Hipótese: com o fence por envio, a fila fica mais funda e 60% dos envios ficam dentro do intervalo de outro (o
     Turnip grava o início com `STAGE_NONE` antes do trabalho).
   - Correção: medir a GPU pelo fim de cada envio contra o fim do anterior (a união dos fins), não pelo início.
   - Teste: `LARECOMP_SEQ_FENCES=0` contra o padrão.
2. **Rodada sem limite de taxa** (`LARECOMP_PRESENT_WAIT=0`, mailbox), sem geração de quadros, mesmo save e trajeto.
   Mostra quem segura o quadro quando nada o segura de fora.
3. **Perfil da thread de render com símbolos** (`tools/diag_symbolize.py` com o build-id do log), na tabela do
   TOTKDroid: `draw_`, `stage_set`, checagem de texturas, cópias, Turnip por chamada.

**Critério:**
- Se, sem limite, a thread de render passar de ~85% ocupada e a GPU tiver folga, a CPU é o limite: seguir para as
  Fases 1 e 2.
- Se a GPU continuar no limite, a prioridade é a GPU (luzes a 2×2, passes caros), e este plano espera.

### Fase 1 — cortes baratos na thread de render (2–4 dias, risco baixo)

Itens que o TOTKDroid mediu e o BOTW não tem (conferido no código: nenhum existe aqui):

| Item | Ganho medido no TOTKDroid | Chave de A/B |
| --- | --- | --- |
| Progresso da GPU perguntado **uma vez por envio** em `guest_copy` (`bcopy_pending`), não a cada chamada (~3.000 `ioctl` por quadro) | −0,68 a −0,75 ms por quadro, 7 de 7 pares | `bcpoll` |
| Checagem das texturas estáticas numa thread auxiliar | −0,38 ms, 7 de 7 | `texhelper` |
| Hash de texturas ≥ 2 MB em 4 partes (a fonte de 8 MB era ~8% da thread) | thread de render 27,5% → 24,1% das amostras | `LARECOMP_TEX_HASH_THREADS=0` |
| Tabela de formatos filtráveis e invalidação de snapshot pulada sem snapshot | ~2,4% | — |

Esperado: −1,5 a −2 ms por quadro na thread de render. É o código dele (MIT, mesma base) adaptado, não reescrita.

### Fase 2 — a thread de replay do TOTKDroid (4–6 dias para portar, risco médio)

O que existe lá (`runtime/nvn/vulkan/replay.c` / `replay.h`, 467 linhas, MIT, com a revisão de lifetimes já feita):

- O `draw_` continua decidindo tudo e escreve **pacotes** num anel (pipeline, estado dinâmico, sets com offsets,
  vértices, índices, draw; início e fim de passe, barreira, dispatch, write-back). A thread "vk replay" chama o Turnip
  em ordem.
- **A ordem é garantida por construção:** cada ponteiro `vkCmd*` do volk ganha uma checagem. Qualquer gravação que não
  virou pacote espera o anel esvaziar antes. Uma gravação esquecida custa uma espera, não um erro.
- Pool de comandos próprio para os uploads.

**O que falta, e o TOTKDroid listou:**
- clears dentro do passe como pacotes (~11 por quadro, ~1,3 ms de espera);
- o envio na própria thread de replay (~10 por quadro).

**O que é nosso e precisa entrar na conta:**
- a captura do HUD (`hud_capture`) e as marcas do perfil por passe (`gp_mark`);
- as cópias de feedback e a geração de quadros;
- tudo isso grava direto. O mecanismo de espera os deixa corretos; depois, os mais frequentes viram pacotes.

**Diferença do Odin para o POCO:** o Odin tem ventoinha. Nos logs, o SoC ficou em 43–61 °C, contra 93 °C no POCO, e
o calor foi o que anulou o ganho lá. Por isso o resultado aqui pode ser outro, e só o A/B diz.

**Critério:** A/B `LARECOMP_AB=300:replay` sem limite e no limite de 60, com o aparelho carregado e frio. Só vira
padrão com ganho em fps reais ou em p95/p99.

### Fase 3 — gravação paralela de verdade (12–18 dias, risco alto; só se a Fase 2 mostrar o replay como gargalo)

O modelo do totk-android:
- **command buffers secundários por passe**, gravados em **2 workers**;
- montados no primário ao fechar o passe;
- o Turnip aceita os secundários de "render pass continue" por referência.

O que muda:
- pools de comandos e de descritores por worker;
- cache de sets por worker, que acerta menos;
- clears e timestamps dentro dos secundários;
- o tratamento de `pipe_evict`, `vk_collect_dead` e do despejo de views com pacotes em voo.

Ganho, se a Fase 2 já tiver tirado o Turnip do caminho: dividir os ~4–5 ms de gravação por dois. Pouco perto do
custo, e por isso fica por último.

### Fase 4 — menos decisões por desenho (contínua)

A lição do totk-android: o custo está em decidir o que cada desenho lê (`stage_set` e a checagem de texturas, ~20%
aqui), não em gravar. Caminhos:
- reaproveitar o conjunto de bindings inteiro quando o desenho repete o anterior (o "freeze memo" deles acerta 38%);
- decodificar o estático no bind, não no draw.

Cada item com A/B próprio.

## 3. Ordem e marcos

| # | Fase | Entrega | Critério para seguir |
| --- | --- | --- | --- |
| 0 | Medir | GPU por quadro confiável; rodada sem limite; perfil com símbolos | quem segura o quadro, em número |
| 1 | Cortes baratos | Amaral.9 ou .10, cada item com chave de A/B | ganho medido, imagem igual |
| 2 | Thread de replay | opção desligada, `LARECOMP_VK_REPLAY=1`, A/B | ganho em fps ou p95 no Odin frio |
| 3 | Secundários em 2 workers | só se o replay virar o gargalo | idem |
| 4 | Menos decisões | contínua | idem |

**Riscos gerais:**
- objetos destruídos com pacotes em voo (o TOTKDroid achou dois e corrigiu);
- diagnósticos que leem o estado vivo no `draw_`;
- uma thread a mais girando num aparelho que esquenta.

Toda fase fica atrás de uma chave, com a volta a um toque.
