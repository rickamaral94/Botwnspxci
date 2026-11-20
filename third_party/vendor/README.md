# Cópias de dependências cujo repositório sumiu

- `dxbc-78ab59a/`: o tradutor de shaders do DXVK, de `PancakeTAS/dxbc`, commit
  `78ab59a8aaeb43cd1b0a5e91ba86722433a10b78` (tree `f19b5a7a5c0e509f62c5d3518490e2f4a9367fdd`). É o submódulo
  `third_party/lsfg-vk-android/thirdparty/dxbc`.
  - A origem e o fork `manuelgzz/dxbc` deixaram de ser públicos em 20/11/2026, e o clone falha no CI.
  - Licença zlib (`LICENSE.md`, de Philip Rebohle e outros), mantida junto.
  - Arquivos sem nenhuma alteração. `.github/workflows/release.yml` copia esta pasta para o caminho do submódulo e
    confere que o tree git dela é `f19b5a7…` antes de compilar.
