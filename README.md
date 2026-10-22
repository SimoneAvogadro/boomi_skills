# boomi-skills

Claude Code skills that add **house conventions and unit testing** to Boomi development.

> **An addition, not a replacement.** These skills sit on top of the official
> [Boomi Companion](https://github.com/OfficialBoomi/boomi-companion), which stays the reference for building,
> pushing, deploying and testing Boomi components. Install it first; use these alongside it.

## What you get

| Plugin | In one line |
|---|---|
| `boomi-conventions` | Naming rules: `PP_` / `D_` for dynamic properties, `[S]` for subprocesses, `[UT]` for unit tests, a `Unit test` folder next to the code. Where it differs from Companion's examples (`DPP_` / `DDP_`), these win. |
| `boomi-unit-testing` | Unit tests that run inside Boomi: a `[UT]` process calls the `[S]` under test unchanged, and the run fails if a check fails. Skill `boomi-unit-testing` is the strategy (test structure, test environment, cleanup); one skill per mocked connector: `boomi-unit-testing-database-operations` mocks the Database Legacy and V2 connectors at the JDBC level with [mockjdbc](https://github.com/SimoneAvogadro/mockjdbc). |

Priority, from the lowest to the highest: the Boomi Companion (the same for everyone), these skills (specialised for
unit testing with agents, independent of the project), and project or customer skills, which win over everything.

The conventions and their reasons are written for people in [docs/CODING_CONVENTIONS.md](docs/CODING_CONVENTIONS.md).

## Install

```text
/plugin marketplace add SimoneAvogadro/boomi_skills
/plugin install boomi-conventions@boomi-skills
/plugin install boomi-unit-testing@boomi-skills
```

## License

[CC BY-SA 4.0](LICENSE): share and adapt, with credit to Simone Avogadro and under the same license.
