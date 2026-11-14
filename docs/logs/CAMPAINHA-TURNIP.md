# Campainha do agente Turnip (Amaral Adreno Tools)

Pedido do Rick em 14/11/2026. O agente que trabalha no Botwnspxci (Claude ou Codex) pode acionar o agente do driver
**Amaral Adreno Tools** (Turnip/Mesa para Adreno, `rickamaral94/Amaral-Adreno-Tools`) quando precisar de ajuste ou de
análise do lado do driver.

Isto complementa a [seção Turnip](TURNIP.md). Aquela seção guarda as evidências; esta diz como pedir ajuda.

## Quando acionar

Acione quando a evidência apontar para o **driver**, não para o port:

- **Falha só no Turnip.** Crash, `VK_ERROR_DEVICE_LOST`, GPU travada ou defeito de imagem que aparece com Turnip e não
  com o driver da Qualcomm (ou com outro Turnip), no mesmo APK, save e rota.
- **Desempenho pior só no Turnip.** Um passe, cópia, submit ou espera de fence fica mais lento entre dois drivers ou
  versões, com A/B/A ou AB/BA, como descrito na [seção Turnip](TURNIP.md).
- **Dúvida de driver.** Se uma variável (`TU_DEBUG=...`, `IR3_SHADER_DEBUG=...`, driconf) ajuda; se um recurso Vulkan
  é confiável no Turnip (heap colocado, leitura do próprio alvo, LRZ, feedback loop, UBWC).
- **Pedido de build.** Um Turnip de laboratório com uma mudança isolada para A/B.

Não acione para bugs que também aparecem no driver da Qualcomm. Esses ficam no port. Vale a regra do
`CLAUDE.md`: antes de propor mudança no Amaral Adreno Tools, registre a identidade do ELF carregado e o teste que
separa app, GPU e driver.

## Como acionar

Guia completo do que mandar, por tipo de problema (crash, imagem, desempenho, recurso), com as variáveis do Turnip que existem na versão publicada: [O que os ports devem mandar](https://github.com/rickamaral94/Amaral-Adreno-Tools/blob/ccr-05e1d523-htngw2/docs/PORTS-EVIDENCIA.md), mantido no Amaral Adreno Tools.

Comente no **PR de campainha** deste repositório (`turnip: campainha do agente Turnip (NÃO MESCLAR)`). O agente
Turnip está inscrito nele e é acordado por cada comentário novo.

Comece o comentário com `[botw]` e traga:

1. **Sintoma**, em uma frase, com o rótulo do [índice](README.md): medição no aparelho, relato do jogador,
   verificação no host ou hipótese.
2. **APK e jogo:**
   - versão do APK (ex.: `0.3.4-beta-amaral.3`) e commit;
   - versão do BOTW e modo (Recompilado ou Nativo);
   - opções efetivas de Compatibilidade do driver: `gpu_heap`, `inplace_reads`, `turnip_lrz` e as variáveis do
     driver.
3. **Driver:** pacote, SHA-256 do ZIP e do ELF, se possível o build-id, e `driverName` e `driverInfo` do log.
4. **Comparação:**
   - A/B contra o driver da Qualcomm ou entre dois Turnip;
   - mesma rota e cache aquecido por driver;
   - FPS reais separados de FPS apresentados;
   - p95 e p99, GPU por passe e espera de fence, quando houver.
5. **Onde está o registro:** caminho e commit em `docs/logs/`. Os logs brutos ficam com o Rick.
6. **O que você espera:** diagnóstico, variável para testar, driver de laboratório ou correção.

## O que o agente Turnip devolve

- Resposta no próprio PR de campainha, com a análise no código do Turnip/Mesa citando arquivo e commit.
- Quando der sem build, uma variável ou driconf para testar. `TU_DEBUG=flushall`, `syncdraw` e `nolrz` servem para
  diagnóstico, não para deixar ligados.
- Quando precisar de driver novo, um **ZIP de laboratório** no formato adrenotools, com SHA-256 e com o que muda em
  relação à versão publicada. Ele não substitui a release até ser testado no Odin.
- A correção definitiva vai para o Amaral Adreno Tools e, quando couber, para o Mesa upstream. O registro de volta
  é anotado na [seção Turnip](TURNIP.md).

O agente Turnip não altera código do Botwnspxci sem pedido. Merge, release e Latest continuam sendo decisão do Rick.

## Contexto que o agente Turnip já levantou

Levantado em 06/11/2026; detalhes em
[`docs/research/2026-11-survey.md`](https://github.com/rickamaral94/Amaral-Adreno-Tools/blob/ccr-05e1d523-htngw2/docs/research/2026-11-survey.md)
§2 do Amaral Adreno Tools.

- **Driver publicado:** Amaral `mesa-27.0.0-devel-v5.8.17.1` (Latest), Mesa `fd8ef2b`, ELF Standard
  `e64f5306c5c8f52f013f01f3d2627a81704f07ba71ab9518c27be2b209863a96`. Já inclui o `0009` (bind de pipeline).
- **Driver compatibility no Automatic.** Conferido no código deste fork em 14/11:
  - LRZ automático liga em Adreno 8xx **e no 740** (`vk_lrz_auto`, `runtime/nvn/vulkan/device.c`);
  - `gpu_heap` liga em qualquer Turnip que consiga colocar o heap (`vk_turnip_heap_on`);
  - `inplace_reads` continua só em 8xx (`vk_turnip_path_on` usa `vk_adreno_8xx`). No A740, a leitura do próprio alvo
    vira cópia a cada barreira (os decalques do terreno no Grande Platô).

  O fork do TOTK passou a ligar também o in-place no 740 desde a amaral.20 (`vk_turnip_path_on` com `vk_lrz_auto`).
  Na `.19` do TOTK, com as três opções ligadas juntas, os FPS reais foram de 29,2 para 41,4.
- **Leitura do próprio alvo sem a extensão.** O port não usa `VK_EXT_attachment_feedback_loop_layout`. O Turnip a
  expõe e, com ela, tira o passe de GMEM. Hipótese do agente Turnip: as listras do A750 (issue #129 do upstream) vêm
  de passes em GMEM, e a extensão tornaria `inplace_reads` correto em todo A7xx, sem as cópias.
- **Testes baratos, sem build novo, no Odin com a 5.8.17.1, A/B contra o Automatic (o LRZ já fica ligado no
  740):**
  - A2: `inplace_reads=on`;
  - A3: A2 com `TU_DEBUG=sysmem`.

  Previsão:
  - A2 sem listras: as cópias por quadro caem;
  - A2 com listras e A3 limpo: a causa é GMEM, o que reforça o uso da extensão no port.
