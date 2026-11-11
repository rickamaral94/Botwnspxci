# Turnip — evidências para o Amaral Adreno Tools

Use este tópico para relacionar cada atualização do Turnip aos resultados no BOTW. Referencie o registro completo da rodada. A qualificação do driver segue o [registro em hardware](https://github.com/rickamaral94/Amaral-Adreno-Tools/blob/main/docs/tests/README.md) e a [política de evidência](https://github.com/rickamaral94/Amaral-Adreno-Tools/blob/main/docs/EVIDENCE-POLICY.md) do Amaral Adreno Tools.

## Evidência disponível

| Observação | O que ainda precisa ser isolado |
| --- | --- |
| **31/10, Odin 2, BOTW 1.8.2:** com LRZ ligado e 1×, o Amaral v5.7.13.1 registrou 28,0 FPS reais e o Turnip 26.2 R4 registrou 15,7. No R4, apareceram amostras em `ioctl`. | Mesa e patchset diferem. As amostras indicam onde investigar. Medir CPU e tempo de parede de gravação, submit e espera de fence, com GPU por passe na mesma janela. [Relatório BOTW](../AVALIACAO-TURNIP-2026-10-31.md) · [Auditoria Turnip](https://github.com/rickamaral94/Amaral-Adreno-Tools/blob/f080c4f9670bd258a8d755a23157c523fa465b50/docs/audits/2026-10-31-botwrecomp-turnip.md) |
| **LRZ:** na v5.7.13.1, ligado a 1× registrou 14,9 ms de GPU por quadro real. Desligado, em resolução dinâmica de ~0,55×, registrou 16,5 ms. | Alternar LRZ com resolução fixa e o mesmo ELF. Conferir profundidade, stencil, grama e decalques. |
| **04/11, v5.8.17.1:** 37,56 FPS reais a 1×, p95 de 32,26 ms e espera média de GPU da thread principal de 9,38 ms. A captura a 0,75× registrou 40,08 FPS com trajeto, cache e calor diferentes. Os intervalos de timestamps se sobrepõem. | Separar custo por passe da GPU, tradução no app, sincronização e submissão. Registrar draws, binds, uploads e passes na mesma janela. Usar a união de intervalos e tempos por passe quando disponíveis. [Análise dos logs](https://github.com/rickamaral94/Botwnspxci/blob/827a0db95821426f53b41b4ab1a5044bd2b95414/docs/BOTW-TOTK-60FPS-TRANSFER.md) |
| **Bind de pipeline:** a auditoria simbolizada encontrou um `memcpy` de 10.096 bytes em `tu_CmdBindPipeline`. O patch `0009-tu-program-state-pointer.patch` já integra a série Standard da 5.8.17.1. | A estimativa de ~0,4 ms por quadro segue preliminar. Para atribuir ganho ao patch, comparar duas builds do mesmo Mesa com apenas o `0009` alternado. Medir CPU por bind, binds por quadro real, p95/p99 e correção visual. [PR #39](https://github.com/rickamaral94/Amaral-Adreno-Tools/pull/39) · [Relato de hardware da 5.8.17.1](https://github.com/rickamaral94/Amaral-Adreno-Tools/blob/main/docs/tests/2026-10-31-v5.8.17.1-owner-smoke.md) |

## Comparação para a próxima atualização

1. **A** = Standard v5.8.17.1, Mesa `fd8ef2befafd01190e33f12dbfd109b924c8ebc3`. **B** = próxima candidata Standard. Confirmar o driver efetivamente carregado e anotar SHA-256 do ZIP e ELF, build-id, Mesa SHA e hash do patchset de ambos.
2. Fixar APK, BOTW 1.8.2 em modo Recompilado, save, rota de 60 s no Grande Platô, resolução 1×, framegen off, opções efetivas de heap, LRZ e in-place, modo de energia e cache aquecido separadamente para cada driver. Marcar início e fim da rota. Conferir imagem nos mesmos pontos.
3. Fazer cinco ou mais rodadas por variante em ordem balanceada AB/BA, com limite térmico definido previamente. Registrar FPS reais, 1% low, p95/p99, stutter, CPU main/render, espera de submit e fence, GPU por passe, memória, clocks e temperatura. Marcar métricas ausentes como `indisponível`. Registrar defeitos visuais, crashes e `device lost`.
4. Se houver diferença repetível, isolar uma variável em build de laboratório. Normalizar CPU por binds na mesma janela. Separar tempo de CPU e de parede no submit. Para defeitos de imagem, conferir também o caminho de cópia do app e buscar reprodução Vulkan válida.
5. Referenciar o commit do BOTW no ensaio do Amaral Adreno Tools e anotar aqui o link de volta quando houver um patch candidato. Manter capturas brutas com Amaral.

| Rodada | APK / aparelho / cena | Drivers e hashes | Métricas e estabilidade | Conclusão e link no Amaral Adreno Tools |
| --- | --- | --- | --- | --- |
| Próxima candidata | Odin 2 Portal Pro / Adreno 740 / Grande Platô | Referência v5.8.17.1; candidata a identificar | Pendente de coleta | Pendente de comparação |
