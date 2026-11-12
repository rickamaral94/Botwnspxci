# Passagem para revisão do Claude — BOTW Android 60 FPS

Estado consolidado em 04/11/2026. Fonte de verdade: branch `codex/botw-60fps-copy-cache`, PR [#1](https://github.com/rickamaral94/Botwnspxci/pull/1). O checkout transitório da sessão pode voltar a um commit anterior; **ler a branch remota da PR**, especialmente `docs/BOTW-TOTK-60FPS-TRANSFER.md`, antes de editar. Não confundir este trabalho com o projeto TOTK.

## Objetivo e evidência disponível

BOTW 1.8.2 já oferece seleção de 60 FPS e hooks de temporização; uma cena leve registrou ~59,9 FPS. Na cena pesada do Odin 2 Portal Pro (Snapdragon 8 Gen 2, Adreno 740, Turnip Amaral 27.0.0-devel v5.8.17.1, 1×, framegen desligado), os logs anteriores indicaram ~37,56 FPS reais em 60 s, present p50/p95/p99 de 26,12/32,26/44,34 ms. Outra captura a 0,75× indicou 40,08 FPS, porém com trajeto, cache e temperatura diferentes; **não é A/B controlado**. A GPU tem spans sobrepostos e o tempo agregado de busy não mede simplesmente o orçamento de um quadro. Há ~140 mil draws e ~1,1–1,2 GB de reservas lógicas de ring em janelas quentes de dois segundos. Consulte as tabelas e limites metodológicos em `docs/BOTW-TOTK-60FPS-TRANSFER.md`.

Os logs históricos usados foram `botwrecomp-log.txt`, `botwrecomp-log-previous.txt` e a rodada posterior de 0,75× (arquivos compartilhados pelo usuário). Nenhum deles mede o novo cache experimental.

## Alteração isolada implementada

O BOTW copiava exatamente `(endereço, tamanho)` para spans transitórios. A branch adiciona, **opt-in e desligado por padrão**, reaproveitamento do prefixo de cópias de vértices na mesma submissão, inspirado no TOTK. Em `runtime/nvn/vulkan/exec.c`, o modo experimental usa o endereço como chave, permite reutilizar um prefixo e acrescentar só a cauda quando há capacidade; escrita na origem invalida a cópia. A alternância invalida entradas em uso do modo anterior. Diagnóstico `[guest-copy-diag]` inclui bytes copiados, reutilizados e crescimento. Conferir correção de geometria e escopo das invalidações no review.

`runtime/settings.h` e `runtime/settings.c`: `gcopy_range` padrão `false`, persistido no INI. `runtime/ui/menu.mm`: opção **Vertex copy reuse (experimental)** em Video > Rendering. `LARECOMP_GCOPY_RANGE=0/1` sobrepõe o menu se definida no lançamento; removê-la para testar a opção na interface. `android/botwrecompandroid/app/build.gradle.kts`: `versionCode=25`, `versionName=0.2.5-beta-amaral-test`, `applicationId=com.botwrecomp.android`. A branch mantém fallback do modo normal e não afirma ganho de FPS.

## Build entregue e verificações

`assembleRelease` completou em SDK 36, NDK r30, CMake 3.30.4, JDK 17. Dependências nativas compiladas, inclusive SDL3, shaderc, FFmpeg, Python, Zig, Unicorn e frame generation. O submódulo dxbc da origem estava indisponível; o checkout de build usou **o mesmo commit fixado** `78ab59a8aaeb43cd1b0a5e91ba86722433a10b78` no fork `manuelgzz/dxbc`, sem alterar a revisão do gitlink. O submódulo `liblinkernsbypass` também foi inicializado.

APK experimental: [app-release.apk](https://chatgpt.com/library?file_id=libfile_0da3bb8ed5f08191a5d004a90ebe255b&account_id=personal), ~87 MB, SHA-256 `36509d85634bfc0aa11ab507826bb83bed097da82e5f6d82b89ff5d8052ae523`. Passou `apksigner verify` (esquema v2), `zipalign -c -v 4`, `unzip -t`, leitura do manifesto, ABI somente `arm64-v8a`, e build Gradle. **Não houve execução no Odin**, nem verificação de FPS, imagem, saves, crashes/ANRs no dispositivo.

Assinatura: o Gradle busca `~/.botwrecompandroid/keystore.properties` (`storeFile`, `storePassword`, `keyAlias`, `keyPassword`) fora do repositório; quando ausente, usa Android Debug. A chave de release original não foi localizada no Git/histórico, home ou arquivos acessíveis nesta sessão. Este APK usa certificado **Android Debug SHA-256 `930841f5756d9d8716ae5e0de03cd55a871debf5959a30865f935b16a2488223`**, específico desta compilação. **Não alegar que instala por cima da versão existente**. Uma atualização exige a chave original e comparação com o certificado do APK instalado. Não adicionar segredos ao Git.

## Próximo ciclo recomendado

1. Revisar a PR, especialmente cache de intervalos, invalidação após escrita, capacidade/alinhamento e transição da opção em tempo real. Evitar alterar sincronização Vulkan ou subir workers sem evidência.
2. No Odin, usar o mesmo APK, save, trajeto, driver, resolução 1×, framegen desligado e estado térmico similar: A (opção off), B (on), A de novo; separar cache quente e frio. Medir FPS nativo, p95/p99, 1% low, `[guest-copy-diag]`, CPU main/render, RSS/Scudo e geometria. Se não reduzir cópias e frametime repetidamente, reverter ou manter desligado.
3. Fazer perfil GPU por passe (`LARECOMP_GPUPROF_AT`) e medir overhead do perfilador (`LARECOMP_VK_PROF`) na cena pesada. Só atribuir custo ao Turnip após separar renderização do port, CPU, submissão e GPU por quadro. Os efeitos de reduzir a resolução foram modestos em sessões não equivalentes.
4. Com a chave legítima, assinar um novo build e comparar o certificado com o APK existente antes de prometer atualização. O APK experimental publicado acima é para instalação de teste compatível com sua assinatura, sujeito a conflito com uma instalação prévia.
5. Registrar métricas A/B/BA e regressões visuais na documentação; manter 60 FPS nativos e frame generation como métricas distintas.

**Estado:** código e build prontos para revisão e teste físico. Ganho de performance, 60 FPS sustentados e atualização sobre a instalação existente seguem **não comprovados**.

## Revisão do Claude (12/11/2026)

- **Cache de faixas:**
  - a invalidação por escrita, a capacidade em potência de 2 até 1 MB e a troca da opção em jogo (que limpa o cache)
    estão corretas;
  - o prefixo é copiado num momento e a cauda em outro, dentro da mesma submissão, e por isso pode misturar dados se
    o jogo escrever no meio; a cópia exata que já existia tem o mesmo risco.
- **Onde age:**
  - só nos vértices copiados (`guest_copy`);
  - no Odin com o Turnip, o heap fica na GPU (`guest_direct`) e o cache não roda, então o A/B/A do item 2 não mede
    nada lá;
  - o teste vai para o driver da Qualcomm, Mali ou o Turnip com "Memória do jogo na GPU" desligada.
  - O `[guest-copy-diag]` agora mostra `vertex binds direct=` e `copied=`.
- Detalhes em [`logs/2026-11-12-revisao-repo.md`](logs/2026-11-12-revisao-repo.md).
