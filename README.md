# boomi-skills

Claude Code skills that add **house conventions and unit testing** to Boomi development.

> **An addition, not a replacement.** These skills sit on top of the official
> [Boomi Companion](https://github.com/OfficialBoomi/boomi-companion), which stays the reference for building,
> pushing, deploying and testing Boomi components. Install it first; use these alongside it.

## What you get

| Plugin | Version | Skill | In one line |
|---|---|---|---|
| `boomi-conventions` | 0.2.0 | `boomi-coding-conventions` | Naming rules: `PP_` / `D_` for dynamic properties, `[S]` for subprocesses, `[UT]` for unit tests, a `Unit test` folder next to the code. Where it differs from Companion's examples (`DPP_` / `DDP_`), these win. |
| `boomi-unit-testing` | 1.2.0 | `boomi-unit-testing` | The strategy for unit tests that run inside Boomi: a `[UT]` process calls the `[S]` under test unchanged, and the run fails if a check fails. Build the tests, run them to full coverage, then fix the defects they find with non-regression tests; plus test environment and cleanup. |
| | | `boomi-unit-testing-database-operations` | Mocks the Database Legacy and V2 connectors at the JDBC level with [mockjdbc](https://github.com/SimoneAvogadro/mockjdbc): only the driver changes, through connection extensions; queries are answered with CSV data from Dynamic Process Properties, and the parameters of every INSERT, UPDATE, DELETE and stored procedure call are recorded for the `[UT]` to check; a statement can be made to fail with the `SQLException` you choose (a lost connection too). |
| `boomi-companion-known-bugs` | 0.1.0 | `boomi-companion-known-bugs-and-limitations` | Known bugs and limitations of the Boomi Companion, each with the Companion versions where it was seen, the correction and a check: when a newer Companion fixes one, the agent notices and the entry is removed. |

The `boomi-unit-testing` plugin has one skill per mocked connector next to the strategy; the database is the first.

Priority, from the lowest to the highest: the Boomi Companion (the same for everyone), these skills (specialised for
unit testing with agents, independent of the project), and project or customer skills, which win over everything.

The conventions and their reasons are written for people in [docs/CODING_CONVENTIONS.md](docs/CODING_CONVENTIONS.md).
What changed in each version of each plugin: [CHANGELOG.md](CHANGELOG.md).

## Install

```text
/plugin marketplace add SimoneAvogadro/boomi_skills
/plugin install boomi-conventions@boomi-skills
/plugin install boomi-unit-testing@boomi-skills
/plugin install boomi-companion-known-bugs@boomi-skills
```

## License

[CC BY-SA 4.0](LICENSE): share and adapt, with credit to Simone Avogadro and under the same license.
