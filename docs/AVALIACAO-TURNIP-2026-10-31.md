# Avaliação do Turnip no Odin 2 Portal (31/10/2026)

Aparelho: AYN Odin 2 Portal, Snapdragon 8 Gen 2 com Adreno 740 (`Adreno740v2`), tela de 120 Hz, Android 13
(API < 35). SoC no modo padrão de energia. Jogo: BOTW 1.8.2, framegen 2x (LSFG 3.1, escala do fluxo 0,5), sync lag
desligado.

Medições com "Medir desempenho (60 s)" (`runtime/diag.c`), no mesmo trecho pesado (a margem do lago, de dia).

## Drivers

| Driver | LRZ | Resolução | Quadros reais/s | Tela p50 / p95 / p99 | GPU por quadro real | Situação |
| --- | --- | --- | --- | --- | --- | --- |
| turnip_amaral 27.0.0-devel v5.7.13.1 (Mesa git-4b0f64ceac) | ligado | 1x | **28,0** | 16,7 / 33,4 / 41,8 ms | **14,9 ms** | **escolhido** |
| turnip_amaral 27.0.0-devel v5.7.13.1 | desligado | Dinâmica (0,55) | 28,8 | 16,7 / 33,4 / 41,8 ms | 16,5 ms | |
| Turnio v26.2.0 R4 (Mesa 26.2, sem `driverInfo`) | ligado | 1x | 15,7 | 41,8 / 75,2 / 75,2 ms | 17,2 ms | descartado |
| Qualcomm do sistema (build 69e13475cb, 27/12/2023) | desligado | Dinâmica (0,50) | 14,8 | 25,1 / 75,2 / 75,2 ms | 17,7 ms | inutilizável |

- **amaral 27 + LRZ:** é o melhor. O LRZ ligado em 1x gasta menos GPU que o LRZ desligado em 0,55 de escala, e não
  aparece nenhum defeito visual. O automático agora liga o LRZ na Adreno 740 (`vk_lrz_auto`).
- **Turnio 26.2 R4:**
  - faz o mesmo trabalho por quadro, ~2.000 desenhos, e entrega metade dos quadros;
  - a thread de render fica 24,9 ms por quadro "rodando", mas só 7,2 ms disso é CPU;
  - o resto é espera dentro do driver, no caminho de envio, que aparece como `ioctl` nas amostras.
- **Qualcomm:** o driver não tem `VK_EXT_map_memory_placed` nem `VK_EXT_external_memory_host`. Sem isso, o heap do
  jogo não vira memória da GPU e o app cai no modo de cópia:
  - render ~52 ms por quadro;
  - artefatos e quadros pretos (`ANALISE-DRIVER-PADRAO-2026-10-21.md`).

## A carga do jogo, por quadro real

Valores do amaral 27 no trecho pesado. As linhas `[vk] t=...` do log contam a cada 2 s, em ~25 quadros por segundo.

| Item | Por quadro | Observação |
| --- | --- | --- |
| Desenhos | ~2.100 | G-buffer com 6 cores mais profundidade, ~55 passes e ~2.460 desenhos (perfil no Adreno 830) |
| Passes (rendering) | ~175 | muitos passes pequenos: o autotune do Turnip escolhe sysmem; `TU_DEBUG=gmem` vai a ~30 ms |
| Dispatches de compute | ~20–60 | mais os do LSFG |
| Uploads | ~15 MB | constant buffers: o jogo reescreve 16 bytes de um bloco de 64 KB antes de cada desenho |
| Submissões | ~9 | envio em pedaços, enquanto a thread de render traduz |
| Leituras no lugar de alvos de desenho | ~600 amostradas | feedback loop: o desenho lê o próprio alvo, sem cópia (só no Turnip) |
| Quebras de passe por leitura no lugar | ~1–40 | |

## O tempo de GPU

- **Por quadro real:** 14,9 ms no amaral 27 com LRZ em 1x, mais ~4–5 ms do framegen (LSFG, quase só compute). Nos
  trechos mais pesados, 23–27 ms.
- **Custo por desenho e por passe, não por pixel:**
  - 50% de resolução, ou 1280x720 no lugar de 1600x900, dá o mesmo tempo de GPU;
  - ~2 µs por desenho e ~20–40 µs por passe (Adreno 830, 23/10);
  - no Adreno 830, o G-buffer leva ~10 ms dos ~17 ms do quadro.
- **Clock:** no modo padrão do SoC, a GPU fica ~70% ocupada nos trechos pesados. Quando a resolução baixa, o
  governador baixa o clock junto.
- **O que não mudou nada:** `TU_DEBUG=noubwc` (+1 ms), `sysmem` (igual ao autotune), `IR3_SHADER_DEBUG=nouboopt`
  (igual), matemática de shader em 32 bits (igual ao int64), sem barreira no início de cada passe (igual).

## O tempo de CPU dentro do driver (thread de render)

- No amaral 27, `libvulkan_freedreno.so` aparece em ~28% das amostras da thread de render, ~1,7 ms dos ~6 ms de CPU
  por quadro: gravação dos `vkCmd*`, descriptor sets e envio.
- Endereços mais amostrados (build id `56becd8cf1d7c217e30cb37c4f5dd4814677e68b`): `+0xc7b480`, `+0x8e81c0`,
  `+0x929780`, `+0x8c1580`, `+0x918280`, `+0x917d80`, `+0x8e8100`, `+0x93c840`, `+0x909900`, `+0x916300`.
- Chamadores dentro do driver: `+0x8c1700`, `+0x8e8240`, `+0x916140`, `+0x903d00`.
- Do lado do app: os descriptor sets são ~12% da thread de render, e o `memcpy` dos constant buffers ~10–12%.

## Comportamentos do Turnip observados

1. **Timestamps:** `vkCmdWriteTimestamp2` com `VK_PIPELINE_STAGE_2_NONE` (início) é gravado quando o processador de
   comandos chega nele, sem esperar o trabalho anterior. Com `ALL_COMMANDS` (fim), numa submissão leve, sai antes do
   fim da submissão anterior. Num teste de 60 s:
   - 7.715 submissões contadas;
   - 5.128 com o intervalo inteiro dentro de outra.

   O tempo ocupado só sai certo pela união dos intervalos.
2. **UBWC em A2B10G10R10:** no Adreno 830 (Turnip 26.3-devel), um `texelFetch` numa imagem intermediária
   A2B10G10R10 comprimida devolvia blocos 16x4 de zeros (traços pretos). O app passou a criar essas imagens sem
   compressão, com `MUTABLE_FORMAT`.
3. **`textureGather` e sampler em A2B10G10R10:** no alvo da cena (A2B10G10R10) davam imagem borrada e com pontos. A
   leitura direta (`texelFetch`) dava certo.
4. **LRZ:** era desligado fora das Adreno 8xx, por relatos de desenhos sumindo em algumas Adreno. Na 740, com o
   amaral 27, não há defeito e ele economiza GPU.
5. **Feedback loop sem `VK_EXT_attachment_feedback_loop_layout`:** o app lê o alvo dentro do próprio passe, em
   layout `GENERAL`. No Turnip funciona e foi conferido quadro a quadro, mas o Vulkan não define esse caso.
6. **`maxStorageBufferRange` de 128 MB:** o heap de 3 GB do jogo fica na GPU via `VK_EXT_map_memory_placed`, mas
   os shaders só alcançam a memória global por janelas de 128 MB.
7. **Sem `uniformAndStorageBuffer8BitAccess`** (`uniform-storage8 0`).
8. **Turnip 26.2 R4:** o envio bloqueia a thread de render, o que não acontece no 27.

## Conclusão

O amaral 27 com LRZ é a melhor combinação no Odin 2. Para dar o próximo salto, a GPU precisaria de menos custo fixo
por desenho e por passe, porque a carga do BOTW é de muitos desenhos e passes pequenos, não de pixels. O prompt em
`PROMPT-TURNIP-GPU.md` leva esses gargalos para uma análise do código do Turnip.
