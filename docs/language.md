# Documentation languages

The documentation of the A2A-T SDK Python is bilingual, and each layer is produced the way that keeps it from drifting:

**Narrative guides — hand-written in both languages.**

- [User Guide](en/user_guide.md) / [用户指南](zh/用户指南.md)
- [Developer Guide](en/developer_guide.md) / [开发指南](zh/开发指南.md)

Every narrative page exists in both `docs/en/` and `docs/zh/` with equivalent content, and both language versions are updated in the same change — the bilingual-pairing rule the project inherited from the Java SDK.

**API Reference — generated from English docstrings.**

The pages under [API Reference](api/client.md) are built by mkdocstrings directly from the English docstrings of the public modules in `src/a2a_t/`. The docstrings are the single source of the API surface, so the reference cannot go stale the way a hand-mirrored API document does. The narrative guides carry the Chinese explanation of the same API surface; see the developer guide of your language for the bilingual API overview.

**Bilingual error messages.**

Runtime error messages are rendered from the bilingual templates in `prompt_resources/errors/{en-US,zh-CN}/errors.json` according to the configured language; see the `A2AT_LANGUAGE` key in the configuration quick reference of the user guides.

**Bilingual prompt resources.**

The bundled templates, slot schemas, scenarios, and negotiation vocabulary are published for both `zh-CN` and `en-US`.
