# Prompt: o que o Turnip pode melhorar para a carga do BOTWRecompAndroid

> Cole o texto abaixo numa sessão com o código do Mesa (`src/freedreno/vulkan`, `src/freedreno/ir3`,
> `src/freedreno/common` e `src/freedreno/drm`). A base é a avaliação de 31/10/2026 (`AVALIACAO-TURNIP-2026-10-31.md`)
> e os logs do zip.

---

Você vai analisar o driver Vulkan **Turnip** (Mesa, `src/freedreno/vulkan`) e o compilador **ir3**, procurando
melhorias concretas para uma carga real: um port nativo de Zelda: Breath of the Wild (Switch, NVN traduzido para
Vulkan 1.3) rodando num **Adreno 740** (Snapdragon 8 Gen 2, AYN Odin 2 Portal, Android 13). O objetivo é reduzir o
tempo de GPU e o tempo de CPU do driver por quadro.

## Driver de referência

- O melhor resultado é do Turnip **27.0.0-devel**, commit `4b0f64ceac`, pacote "turnip_amaral v5.7.13.1", com
  **LRZ ligado**.
- Um build **26.2** ("Turnio v26.2.0 R4") faz o mesmo trabalho e entrega metade dos quadros. A thread que grava e
  envia os comandos passa ~25 ms por quadro dentro do driver, com só ~7 ms de CPU. O resto é espera no caminho de
  envio, que aparece como `ioctl`.

## A carga (por quadro, no trecho pesado)

- ~2.100 desenhos e ~175 passes de dynamic rendering, a maioria pequenos (decalques, pós-processamento,
  composição).
- No G-buffer: 6 alvos de cor mais profundidade, ~55 passes e ~2.400 desenhos.
- ~20–60 dispatches de compute do jogo, mais o frame generation (LSFG 3.1, só compute, ~4–5 ms de GPU por quadro
  real numa escala de fluxo de 0,5).
- ~15 MB de uploads de constant buffers, porque o jogo reescreve 16 bytes de um bloco de 64 KB antes de cada desenho.
  ~9 submissões por quadro.
- ~650 desenhos leem o próprio alvo de cor dentro do passe (feedback loop em layout `GENERAL`, **sem**
  `VK_EXT_attachment_feedback_loop_layout`) e ~1–40 quebras de passe.
- Memória: o heap de 3 GB do jogo fica na GPU via `VK_EXT_map_memory_placed`. Os shaders o acessam por storage
  buffers em janelas de 128 MB, porque `maxStorageBufferRange` é de 128 MB.
- Formatos: alvos da cena e da imagem final em `A2B10G10R10_UNORM_PACK32`, saída da janela em `R8G8B8A8_UNORM`.
- Frame pacing: FIFO, `VK_GOOGLE_display_timing` e 60 Hz pedidos numa tela de 120 Hz.

## Medições

- GPU por quadro real: **14,9 ms** (LRZ ligado, 1x) contra 16,5 ms (LRZ desligado, escala 0,55). Nos trechos mais
  pesados, 23–27 ms.
- **O custo é por desenho e por passe, não por pixel.**
  - 50% de resolução, ou 720p no lugar de 900p, dá o mesmo tempo de GPU.
  - Estimativa: ~2 µs por desenho e ~20–40 µs por passe (Adreno 830).
- O autotune escolhe **sysmem** para esses passes. `TU_DEBUG=gmem` é muito pior (~30 ms contra ~17 ms).
- Não mudaram nada: `TU_DEBUG=noubwc` (+1 ms), `TU_DEBUG=sysmem`, `IR3_SHADER_DEBUG=nouboopt` e a emulação de int64
  contra 32 bits.
- CPU: `libvulkan_freedreno.so` é ~28% das amostras da thread que grava os comandos (~1,7 ms de ~6 ms por quadro).
  - Endereços mais quentes no build `56becd8cf1d7c217e30cb37c4f5dd4814677e68b`: `+0xc7b480`, `+0x8e81c0`,
    `+0x929780`, `+0x8c1580`, `+0x918280`, `+0x917d80`, `+0x8e8100`, `+0x93c840`, `+0x909900`, `+0x916300`.
  - Chamadores: `+0x8c1700`, `+0x8e8240`, `+0x916140`, `+0x903d00`.
  - Do lado do app, `vkUpdateDescriptorSets`, alocação de sets e binds somam ~12%.
- No modo padrão de energia, a GPU fica ~70% ocupada nos trechos pesados. Quando a resolução cai, o governador baixa
  o clock.

## Comportamentos que observamos e queremos entender

1. **Timestamps:**
   - `vkCmdWriteTimestamp2(VK_PIPELINE_STAGE_2_NONE)` no início de uma submissão é gravado antes do fim do trabalho
     anterior.
   - `ALL_COMMANDS` no fim de uma submissão leve sai antes do fim da submissão anterior: 5.128 de 7.715 submissões
     ficaram com o intervalo dentro de outra.
   - É o comportamento esperado? Existe um jeito barato de medir o tempo ocupado por submissão?
2. **UBWC em A2B10G10R10:**
   - `texelFetch` numa imagem A2B10G10R10 comprimida, escrita por um passe de cor, devolvia blocos 16x4 de zeros no
     Adreno 830 (Turnip 26.3-devel). Sem compressão (`MUTABLE_FORMAT`), dava certo.
   - `textureGather` e o sampler no alvo A2B10G10R10 davam imagem borrada e com pontos, e `texelFetch` dava certo.
   - É um bug conhecido? Onde ficaria no código?
3. **LRZ:** era desligado fora das Adreno 8xx por relatos de desenhos sumindo. Na 740, com o Turnip 27, não há defeito.
   - Quais commits recentes mudaram o LRZ?
   - Ainda existem casos que desligam o LRZ por passe (blend, `discard`, escrita de profundidade no fragment shader,
     feedback loop) e que custam caro aqui?
4. **Feedback loop em `GENERAL`, sem a extensão:**
   - O que o Turnip faz hoje: resolve para sysmem, quebra o passe, faz flush de cache?
   - Usar `VK_EXT_attachment_feedback_loop_layout` (se o Turnip expõe) daria um caminho mais barato?

## O que pedimos

Para cada item abaixo, aponte arquivos e funções do Turnip/ir3, estime o ganho e diga se dá para resolver no driver
ou com uma mudança de uso do lado do app:

1. **Custo fixo por desenho no command stream:**
   - emissão de estado (`tu_cmd_buffer.cc`, `tu_pipeline.cc`, dirty bits, `tu6_emit_*`, draw states / `CP_SET_DRAW_STATE`);
   - re-emissão de descriptor sets e push constants;
   - custo de `vkCmdBindDescriptorSets` com sets novos a cada desenho, frente a push descriptors ou descriptor buffer;
   - o que um app com ~2.000 desenhos e ~2.000 binds por quadro deveria preferir para minimizar o trabalho do CP
     e do driver.
2. **Custo fixo por passe em sysmem:**
   - flushes e invalidações de cache e esperas (`tu_emit_cache_flush`, `CP_WAIT_FOR_IDLE`, `WFI`) no início e no
     fim de cada `vkCmdBeginRendering`;
   - barreiras completas (`vkCmdPipelineBarrier2` com `ALL_COMMANDS` → `ALL_COMMANDS`, que o app emite entre
     passes): o quanto custam e o que trocar por elas;
   - o autotune GMEM/sysmem para passes pequenos: heurística e limiares.
3. **Constant buffers:**
   - o caminho mais barato para 16 bytes mudando a cada desenho: push constants, inline uniform blocks (se houver),
     UBO com offset dinâmico;
   - como o ir3 promove UBO para const registers (`ir3_nir_analyze_ubo_ranges`), e se isso falha com UBOs de
     64 KB acessados por janela.
4. **Storage buffers grandes:** o que limita `maxStorageBufferRange` a 128 MB na Adreno 7xx, e se um acesso por
   ponteiro (`VK_KHR_buffer_device_address`) ao heap de 3 GB seria mais barato que as janelas.
5. **Envio:**
   - por que o 26.2 bloqueia no `ioctl` de submit e o 27 não (throttling, syncobj, `tu_queue_submit`, BO lists);
   - quais mudanças entre 26.2 e 27.0 explicam a diferença.
6. **Compute (LSFG):** ocupação, tamanho de workgroup, `shaderStorageImageWriteWithoutFormat` e
   `VulkanMemoryModel` no ir3. Existe algo conhecido que penalize esse tipo de shader na Adreno 740?
7. **LRZ e UBWC:** os pontos das perguntas 2 e 3 acima, com os commits relevantes.
8. **Medição:** como ler o clock e os contadores da GPU pelo Turnip (`VK_KHR_performance_query`, perfetto, fdperf),
   para separar trabalho de frequência num aparelho sem root.

## Formato da resposta

Uma tabela por prioridade com as colunas: item, onde no código, ganho estimado na GPU ou na CPU, se é mudança no
driver ou no app, e risco. Depois, para os 3 melhores itens, os detalhes de implementação.

Não copie código GPL para o app. O app é MIT, e o Mesa é MIT, então trechos do Mesa podem servir de referência com
atribuição.
