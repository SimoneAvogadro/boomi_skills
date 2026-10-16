# boomi-skills

Claude Code skills that add **house conventions and unit testing** to Boomi development.

> **An addition, not a replacement.** These skills sit on top of the official
> [Boomi Companion](https://github.com/OfficialBoomi/boomi-companion), which stays the reference for building,
> pushing, deploying and testing Boomi components. Install it first; use these alongside it.

## What you get

| Plugin | In one line |
|---|---|
| `boomi-conventions` | Naming rules: `PP_` / `D_` for dynamic properties, `[S]` for subprocesses, `[UT]` for unit tests, a `Unit test` folder next to the code. Where it differs from Companion's examples (`DPP_` / `DDP_`), these win. |
| `boomi-unit-testing` | Unit tests that run inside Boomi: a `[UT]` process calls the `[S]` under test, the database is mocked with [mockjdbc](https://github.com/SimoneAvogadro/mockjdbc), and the run fails if the expected DB writes are wrong. |

The conventions and their reasons are written for people in [docs/CODING_CONVENTIONS.md](docs/CODING_CONVENTIONS.md).

## Install

```text
/plugin marketplace add SimoneAvogadro/boomi_skills
/plugin install boomi-conventions@boomi-skills
/plugin install boomi-unit-testing@boomi-skills
```

## License

[CC BY-SA 4.0](LICENSE): share and adapt, with credit to Simone Avogadro and under the same license.
