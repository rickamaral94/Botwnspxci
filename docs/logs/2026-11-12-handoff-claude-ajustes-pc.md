# Passagem para o Claude — próximo APK BOTW Android

Base de trabalho: `codex/botw-cross-port-amaral2`, com a Amaral.2 compilada em
[`b8dd4533533e`](https://github.com/rickamaral94/Botwnspxci/commit/b8dd4533533ec62f078a1b8ef8be4a4897f6d3f0).
O [registro da Amaral.2](2026-11-11-amaral2-cross-port.md) tem o APK de referência,
a verificação de host e os testes físicos pendentes. Preserve o cache compute
expansível, as 48 faixas no modo de cópia e a espera ativa opcional de 200 µs.

## Ordem proposta para os APKs

| Ordem | Ajuste | Entrega |
| --- | --- | --- |
| 1 | Pré-aquecimento de pipelines a partir de uma rota | Primeira candidata Android, com opção experimental desligada por padrão e comparação no mesmo APK. |
| 2 | Alias de G-buffer | Teste de regressão primeiro. Se houver falha no BOTW, incluir a correção em commit isolado com imagem comparável. |
| 3 | Registradores e flags em variáveis locais no C gerado | Candidata separada após testes de semântica e rebuild do código do jogo. |
| 4 | PGO | Experimento separado, condicionado a perfil de CPU e à confirmação de suporte no toolchain Android. |

### 1. Pré-aquecimento de pipelines

O SavageWind pré-compila pipelines a partir de uma lista coletada em gameplay.
O [changelog de referência](https://github.com/Revivedx/SavageWindRecomp/blob/d8c5e70bc642cc26cda2737498fbefa6bbc14c25/CHANGELOG.md)
descreve a técnica. O BOTW Android já carrega e salva `cache/vk_pipelines.bin`
em `runtime/nvn/vulkan/device.c`. Em `runtime/nvn/vulkan/exec.c`, o fluxo
`draw_` → `PipeKey` → `run_job(build_pipeline, pp)` cria pipelines sob demanda.

1. Instrumente esse ponto para coletar, em uma rota local, quais pipelines
   realmente bloqueiam draws ou causam stutter. Registre identidade de shaders
   e estado de pipeline estáveis. `PipeKey` contém um `Prog *`, então uma
   cópia binária da estrutura ou a lista de endereços do PC não serve para
   replay. Registre o necessário para reconstruir a criação válida de cada
   pipeline, incluindo formatos, amostras, layouts e estado relevante.
2. Comece pelo BOTW 1.8.2 no Odin 2, com a primeira entrada no Grande Platô
   e a abertura do menu de pausa. Faça uma opção experimental que consuma
   uma lista gerada localmente e reutilize o caminho atual de criação.
   Valide o formato e identifique o jogo, a revisão do tradutor/runtime e as
   features efetivas de Vulkan. Para o cache binário do driver, mantenha a
   validação de dispositivo, driver e `pipelineCacheUUID` já existente.
3. Limite a fila e o tempo de aquecimento, preserve as regras atuais de
   sincronização e retenção de pipelines e faça fallback para a criação sob
   demanda quando a entrada faltar ou não for compatível. Guarde a lista e
   os caches no armazenamento local do app. O APK pode carregar a ferramenta
   de coleta, sem precisar embutir shaders, binários ou dados do jogo.
4. Registre tempo até jogar, tempo de aquecimento, entradas aproveitadas ou
   rejeitadas, falhas, compilações em jogo, draws pulados, esperas, p95/p99 e
   pico de memória. Compare cache frio e quente em séries distintas.
   Só considere o experimento bem-sucedido se reduzir travadas na primeira
   passagem e mantiver imagem, memória e tempo até jogar aceitáveis.

### 2. Alias de G-buffer

Leia a [correção do SavageWind](https://github.com/Revivedx/SavageWindRecomp/commit/62677b2e57fb4c48c2684af9ae092a096d36ed1f)
e o [teste de origem](https://github.com/Revivedx/SavageWindRecomp/commit/c7765cb9115aa76b8e1e6b2a41e1a42c38daf7b5).
O port de PC já teve artefatos no RADV. No BOTW, `is_attachment_entry`,
`view_overlaps_rt`, `draw_writes`, `resolve_feedback` e a seleção de slots
duplicados em `begin_pass` precisam ser conferidos juntos. O código atual
já combina por máscara os slots que apontam para o mesmo objeto.

- Cubra alvo gravável e slot mascarado na mesma imagem, views sobrepostas,
  mips/camadas disjuntos e escrita de draw anterior no mesmo passe. Use como
  referência o caminho de cópia existente e compare decalques, terreno, água e
  efeitos. Confira barreiras/layouts com a validação Vulkan quando disponível.
- Se o baseline falhar, corrija o teste de sobreposição e a escolha do caminho
  no menor ponto possível. Preserve o fallback de cópia e os gates do caminho
  in-place. Se todos os casos passarem, registre a cobertura no log e mantenha
  a candidata sem esse patch. Se o defeito persistir variando apenas o driver
  com uma sequência Vulkan válida, registre em [Turnip](TURNIP.md).

### 3. Otimizações no C gerado

O SavageWind reduziu acessos ao estado do guest ao manter registradores e flags
em locais de C. Comece em `tools/gen.py` (`emit_function`), confira a
emissão em `tools/lifter.py` e `tools/simd_c.py` e as convenções em
`runtime/cpu.h`. O APK já tem listas hot/cold em
`tools/hot_functions_<versão>.txt` e um pipeline de compilação em
`runtime/gamebuild.c`. Use essas listas para selecionar poucos blocos quentes.

- Defina quais locais precisam ser escritos de volta antes de chamadas
  HLE, helpers, saídas do bloco, branches indiretos, tail calls e exceções.
  Comece pelo caso em que o fluxo de controle e o contrato de leitura/escrita
  são conhecidos. Compare registradores, flags, PC e efeitos de memória
  contra a emissão atual em testes diferenciais.
- Confirme que `android/gamelib_id.cmake` e o empacotamento em
  `android/botwrecompandroid/app/build.gradle.kts` cobrem todos os arquivos
  modificados do gerador e preservam a invalidação do código e dos objetos
  gerados. Teste tanto o setup inicial quanto a atualização a partir da
  Amaral.2, com a mesma versão do jogo. Meça CPU da thread principal, tempo
  de build no aparelho, pico de RAM e tamanho do código gerado.

### 4. PGO

Use o [port Wii U para Linux ARM64](https://github.com/ToolchainFern/BotWRecomp-Android/commit/3950b0abcc9338e66527a8b9776d613a5252bafe)
como referência para treino e validação. Primeiro confirme que o compilador
e a etapa de link usados pelo nosso Android suportam instrumentar, exportar,
mesclar e consumir o perfil. Declare se o alvo é o runtime ARM64 do APK ou
a biblioteca do jogo gerada no aparelho. Use perfil obtido da mesma revisão,
ABI, versão do jogo e modo de execução. Treine em uma rota e meça em outra
com as mesmas condições térmicas. Use uma build de avaliação sem
instrumentação. Se o fluxo móvel bloquear o experimento, registre em qual
etapa e compile a candidata com os ajustes já validados.

## Compilação e verificação

Use Linux, JDK 17, SDK Android 36, Build Tools 36.0.0, NDK `30.0.16248370`,
CMake/Ninja `3.30.4` e o Gradle Wrapper `8.14.3`. Parta da branch informada,
confirme a revisão e incremente `versionCode` a partir da maior versão
distribuída. A Amaral.2 usa 40. Mantenha `com.botwrecomp.android` e
`arm64-v8a`. Para assinar, siga [a documentação de assinatura fixa](../SIGNING-AMARAL.md).

```bash
# Com ANDROID_HOME e JAVA_HOME apontando para as instalações acima
git submodule update --init --recursive
export ANDROID_NDK_LINUX="$ANDROID_HOME/ndk/30.0.16248370"
export PATH="$ANDROID_HOME/cmake/3.30.4/bin:$PATH"
bash android/deps/build_deps.sh
bash android/deps/build_ffmpeg.sh
bash android/deps/build_gen_deps.sh
git diff --check
python3 tools/test_gamebuild_hot.py
python3 tools/test_romfs_build.py
(cd android/botwrecompandroid && bash gradlew assembleRelease)
apk=android/botwrecompandroid/app/build/outputs/apk/release/app-release.apk
bt="$ANDROID_HOME/build-tools/36.0.0"
"$bt/apksigner" verify --verbose --print-certs "$apk"
"$bt/zipalign" -c -P 16 4 "$apk"
"$bt/aapt2" dump badging "$apk"
unzip -tq "$apk"
sha256sum "$apk"
```

Se a origem do submódulo DXBC estiver indisponível, o build da Amaral.2 recuperou
o mesmo commit `78ab59a8aaeb43cd1b0a5e91ba86722433a10b78` pelo espelho
`Username404-59/dxbc`. Confira o SHA do gitlink antes de compilar.
```bash
git -C third_party/lsfg-vk-android \
  -c submodule.thirdparty/dxbc.url=https://github.com/Username404-59/dxbc.git \
  submodule update --init thirdparty/dxbc
git -C third_party/lsfg-vk-android/thirdparty/dxbc rev-parse HEAD
```

Rode os testes novos e confirme assinatura v3 e certificado fixo. Se o
Gradle gerar apenas assinatura v2, assine o APK final em um arquivo de
saída separado com a mesma chave. O `apksigner` solicita a senha de forma
interativa quando ela não é fornecida.

```bash
"$bt/apksigner" sign --ks "$BOTW_RELEASE_KEYSTORE" --ks-key-alias botwdroid-amaral \
  --v2-signing-enabled true --v3-signing-enabled true \
  --out BOTW-candidata-arm64.apk "$apk"
"$bt/apksigner" verify --verbose --print-certs BOTW-candidata-arm64.apk
"$bt/zipalign" -c -P 16 4 BOTW-candidata-arm64.apk
sha256sum BOTW-candidata-arm64.apk
```

Registre commit, versão, SHA-256 do APK final, resultados dos testes e se o
setup e gameplay foram exercitados no aparelho.

## Validação no Odin 2

Use a Amaral.2 como baseline, BOTW Switch 1.8.2 recompilado, framegen desligado,
mesmo save, rota, driver, resolução e estado térmico. Para opções reversíveis,
altere um item por vez na mesma build. Para builds diferentes, preserve o save
e considere o bloqueio de downgrade de `versionCode`. Capture FPS reais,
1% low, p95/p99, stutter, CPU main/render, tempo de compilação, memória e
imagem. No registro de testes, identifique as janelas e deixe os resultados
físicos pendentes até medir no aparelho.
