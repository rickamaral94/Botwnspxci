# 11/11/2026 — BOTW 0.3.4-beta-amaral.2

APK Android ARM64, `com.botwrecomp.android`, versionCode 40. A base é a
Amaral.1. Os experimentos físicos abaixo aguardam coleta no Odin 2 Portal Pro.

## Mudanças no APK

| Mudança | Evidência de origem | Comportamento nesta build |
| --- | --- | --- |
| Cache de programas compute expansível | [SavageWindRecomp 0.5.1 para PC](https://github.com/Revivedx/SavageWindRecomp/commit/0a5f9fd934d5e57d6d497dcc9c8b0d61c60a7838) | A tabela fixa de 256 deixava programas novos fora do cache e permitia recompilar repetidamente o mesmo shader. A tabela agora cresce por demanda. Os endereços dos programas continuam estáveis durante a compilação assíncrona. `[compute-cache]` registra os crescimentos. |
| Faixas aprendidas no modo de cópia | [LASRecompAndroid](https://github.com/mamcjr/LASRecompAndroid/commit/95dcc2ab07) | Passa de 16 para 48 faixas e atualiza a recência quando uma faixa volta a ser solicitada. `LARECOMP_GRES_LEGACY=1` restaura o comportamento anterior para A/B. |
| Espera de shader/pipeline | [SavageWindRecomp para PC](https://github.com/Revivedx/SavageWindRecomp/commit/c60a6c42b81708cc957a639ba24a068a73fe9a0b) | O padrão continua sendo dormir por 200 µs entre verificações. `LARECOMP_PIPELINE_WAIT_SPIN=1` testa até 200 µs de espera ativa antes de dormir. `[pipeline-wait-diag]` registra quantas esperas houve, quantas terminaram durante a espera ativa e o tempo total. |

O SavageWind também usa pré-compilação guiada por uma lista de gameplay e
otimizações na geração de C. A lista depende da versão do jogo e de shaders,
pipelines e recursos presentes na carga. A versão 0.5.1 de desktop requer BOTW
1.9.0. A [variante Wii U para Linux ARM64](https://github.com/ToolchainFern/BotWRecomp-Android/commit/3950b0abcc)
traz uma metodologia de treino e benchmark para PGO. O [port Wii U para Mac/iOS](https://github.com/IshaanKalra2103/BotWRecomp)
usa Metal. Os resultados desses backends e os números de FPS publicados para PC
servem para formular hipóteses. Os cenários e os patches de runtime precisam de
validação no BOTW Switch/NVN para Vulkan. A correção desktop de alias no G-buffer
ficou em revisão, pois o BOTW já agrega os slots que apontam para o mesmo
objeto. Falta reproduzir o caso com views e subrecursos neste backend.

## Testes no Odin 2

As opções de ambiente vão em **Configurações → Compatibilidade do driver →
Variáveis do driver**. Reiniciar o app após cada alteração. Usar o mesmo
save, driver, estado do cache, resolução, rota e estado térmico por comparação.
Começar com framegen desligado.

1. **Compute:** Amaral.1 → Amaral.2 → Amaral.1. Em sessão longa com teletransportes e
   santuários, procurar `[compute-cache]` acima de 256 programas, compilação
   repetida, memória, p95/p99, imagem e travadas. Uma rota curta que nunca
   chegue a 256 programas verifica apenas regressão de uso comum. A volta para
   Amaral.1 é um downgrade de versionCode e pode exigir reinstalação. Exporte o
   save antes e importe o mesmo save nas duas builds.
2. **Modo de cópia:** na Amaral.2, alternar `LARECOMP_GRES_LEGACY=1` e
   `LARECOMP_GRES_LEGACY=0`. Confirmar que o caminho de cópia com arena está ativo
   e registrar `[gmiss] learned_range_limit`. Comparar iluminação, `[gmiss]`,
   memória e frametime em um interior com luzes complexas.
3. **Espera:** na Amaral.2, alternar `LARECOMP_PIPELINE_WAIT_SPIN=0` e
   `LARECOMP_PIPELINE_WAIT_SPIN=1`, primeiro com cache quente. Medir contagem e
   duração das esperas, p99, CPU render, temperatura e integridade do terreno.
   Separar a coleta de cache frio.
4. **Cache de vértices:** a opção experimental da Amaral.1 continua disponível. No Odin com o Turnip ela não roda,
   porque os vértices são lidos direto da memória do jogo. Ver a [revisão de 12/11](2026-11-12-revisao-repo.md).
   Comparar separadamente conforme a [revisão anterior](2026-11-11-revisao-externa.md).

Se a diferença persistir variando apenas o driver, registrar a coleta na
[seção Turnip](TURNIP.md). Estas mudanças atuam no runtime do APK.

## Validação do APK

- Fonte compilada: [`b8dd4533533e`](https://github.com/rickamaral94/Botwnspxci/commit/b8dd4533533ec62f078a1b8ef8be4a4897f6d3f0).
- `assembleRelease` e `lintVitalRelease` passaram com JDK 17, SDK 36, NDK r30 e CMake 3.30.4.
- Testes no host passaram para cache compute com 768 endereços (no repositório desde 12/11: `tools/test_exec_caches.py`, e todos os de host em `tools/run_host_tests.sh`), falha de alocação na expansão, recência e descarte de faixas e ambos os modos de espera. Passaram também os testes de compilação do jogo, RomFS e cache de shaders.
- O teste legado de cache de uploads falha ao extrair código que depende de símbolos ausentes no harness. O trecho extraído é idêntico na Amaral.1 e na Amaral.2.
- APK final `BOTW-0.3.4-beta-amaral.2-arm64.apk`, 90.772.564 bytes, SHA-256 `8cd3ebfae2a1398652c4ae1294ac8a1359f2a3f740a0565aa268ebee4eab4062`. ZIP, alinhamento, pacote, versão e ABI conferidos. Assinatura v3 com o certificado fixo BOTWDroid Amaral.
- Validação de instalação e gameplay no Odin 2 pendente.
