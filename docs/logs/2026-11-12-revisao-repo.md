# 12/11/2026 — revisão do repositório (Amaral.2) e próximos testes

## O que foi avaliado

- Responsável: Claude, a pedido de Amaral. É uma **verificação no host**: código, build e testes. Nenhuma medição no
  aparelho.
- Base: `codex/botw-cross-port-amaral2` (`541cf31`, 0.3.4-beta-amaral.2, versionCode 40), comparada com o upstream
  `mamcjr/BOTWRecompAndroid` `82534ac` (0.3.4-beta) e com o trabalho de outubro (framegen, máscara do HUD,
  diagnóstico, LRZ).

## Resultados e evidências

- **Integração da 0.3.4:** dos 77 arquivos que o upstream mudou desde `4acbf40`:
  - 56 estão idênticos;
  - 21 só acrescentam as funções da Amaral;
  - nenhum foi perdido.
  - As linhas removidas são trocas: a cópia de vértices com faixas, a tabela de compute expansível, as 48 faixas e o
    `present` em duas etapas do framegen.
- **Funções de outubro presentes:**
  - framegen, máscara do HUD, LRZ automático na 740, `vk_diag_context` e saúde dos timestamps;
  - resolução dinâmica com desconto do framegen;
  - ADPF das threads do jogo desligado por padrão.
- **Assinatura:**
  - nenhuma chave, keystore ou senha no repositório;
  - o build `release` falha sem `~/.botwrecompandroid/keystore.properties`.
- **Build:** `assembleDebug` do Amaral.2 compilou.
- **Testes no host:** `tools/run_host_tests.sh`, novo, reúne os seis grupos:
  - diagnóstico, com ASan e UBSan;
  - extração do LSFG (52 shaders);
  - cópia de buffers;
  - `tools/test_exec_caches.py`, novo;
  - build do jogo;
  - RomFS.

  Os seis passam.
- **`test_exec_caches.py`** testa o código do próprio `exec.c`:
  - **cache de compute:** 768 endereços, todos achados de novo com o mesmo programa;
  - **faixas aprendidas:** 48 com recência, e 16 sem recência com `LARECOMP_GRES_LEGACY=1`; a faixa descartada vira
    janela livre;
  - **espera de shader:** dormindo por padrão, e com espera ativa com `LARECOMP_PIPELINE_WAIT_SPIN=1`.

  Eram testes citados no registro do Amaral.2 que não estavam no repositório.
- **Histórico do git:**
  - a 0.3.4 tinha entrado como um commit comum (`9c9701f`), e o git ainda listava os 130 commits do upstream como
    pendentes;
  - um merge `-s ours` de `82534ac` registra a ligação, sem mudar nenhum arquivo;
  - a próxima versão do upstream entra só com os commits novos.

## Conclusão e próximo passo

1. **O cache de vértices (A/B/A) não age no Odin com o Turnip.**
   - O cache só atua em vértices copiados (`guest_copy`).
   - Com o heap colocado do Turnip (`guest heap ... is GPU memory (placed ...)`), os vértices são lidos direto da
     memória do jogo (`guest_direct`) e nunca passam por ele.
   - O A/B/A no Odin mediria ruído. O teste vai para o driver da Qualcomm, Mali ou o Turnip com "Memória do jogo na
     GPU" desligada.
   - O `[guest-copy-diag]` passou a contar `vertex binds direct=` e `copied=`, que mostram se o caminho rodou.
2. **60 fps nativos contra framegen.**
   - Registro de 04/11 (driver v5.8.17.1, 1x, framegen desligado, 60 selecionados): 37,6 quadros reais na cena
     pesada.
   - Com o framegen, os quadros reais ficam presos a 30.
   - Na tela de 120 Hz do Odin, comparar três configurações, todas no mesmo APK, save, rota de 60 s e driver, com
     cache quente e temperatura inicial parecida:

     | Execução | Configuração | O que olhar |
     | --- | --- | --- |
     | A | Taxa de quadros **40** (da 0.3.0 do upstream), framegen desligado | quadros reais, p95/p99 na tela, a cadência a 40 em 120 Hz |
     | B | Framegen **3x** (40 → 120) | reais e mostrados, `[fg] 2 s` (GPU do framegen), HUD |
     | C | Framegen **2x** (30 → 60), a configuração atual | idem |
     | A' | A de novo | deriva térmica |

   - **Critério:**
     - a cadência na tela mais estável;
     - os reais acima da base sem queda na cena pesada;
     - no 3x, os 120 mostrados sem descartes;
     - consumo de energia na linha "Power" do overlay.
3. **LRZ isolado:** alternar só o LRZ, em 1x fixo e com o mesmo driver (v5.8.17.1). A rodada de 31/10 mudou também a
   resolução.
4. **Amaral.2 no aparelho:** os testes de `2026-11-11-amaral2-cross-port.md` (cache de compute, faixas e espera)
   continuam pendentes.

## Revisão

12/11/2026, Claude. Evidência conferida: diffs contra o upstream, build, os testes acima e o código de `guest_copy` /
`guest_direct` (`runtime/nvn/vulkan/exec.c`). Parecer: Amaral.2 coerente e sem perdas do upstream. O plano de teste do
cache de vértices foi corrigido (item 1).
