---
bootstrapped_at: 2026-08-07T10:51:31Z
starter_id: 10x-astro-starter
starter_name: "10x Astro Starter (Astro + Supabase + Cloudflare)"
project_name: squash-analyzer
language_family: js
package_manager: npm
cwd_strategy: git-clone
bootstrapper_confidence: first-class
phase_3_status: ok
audit_command: "npm audit --json"
---

## Hand-off

```yaml
starter_id: 10x-astro-starter
package_manager: npm
project_name: squash-analyzer
hints:
  language_family: js
  team_size: solo
  deployment_target: cloudflare-pages
  ci_provider: github-actions
  ci_default_flow: auto-deploy-on-merge
  bootstrapper_confidence: first-class
  path_taken: standard
  quality_override: false
  self_check_answers: null
  has_auth: true
  has_payments: false
  has_realtime: false
  has_ai: true
  has_background_jobs: true
```

Why this stack: Solo, po godzinach, 3-tygodniowe MVP aplikacji webowej z logowaniem, uploadem dużych wideo i analizą AI — priorytetem jest starter, który daje auth, bazę i deploy od ręki, zamiast tygodnia konfiguracji. 10x Astro Starter (Astro + React + TypeScript + Tailwind + Supabase + Cloudflare Pages) to rekomendowany default dla (web, js): przechodzi wszystkie cztery bramki agent-friendly, Supabase pokrywa FR-001/002 (logowanie zewnętrznym dostawcą) i storage dla nagrań (FR-003), a Cloudflare Pages z auto-deployem po merge (GitHub Actions) domyka CI/CD bez dodatkowej pracy. Znana rezerwa: edge runtime nie udźwignie długiej analizy wideo (do 1h) — flaga has_background_jobs jest ustawiona, a przetwarzanie analizy trzeba będzie zaprojektować jako zadanie poza edge (kolejka / zewnętrzny worker); decyzja o mechanizmie zapada na etapie planowania, nie w starterze. Flagi has_auth i has_ai ustawione; płatności i realtime poza zakresem zgodnie z non-goals PRD.

## Pre-scaffold verification

| Signal      | Value                                                        | Severity | Notes                                              |
| ----------- | ------------------------------------------------------------ | -------- | -------------------------------------------------- |
| npm package | not run                                                      | —        | cmd_template starts with `git clone`; no create-* CLI |
| GitHub repo | przeprogramowani/10x-astro-starter last pushed 2026-05-17    | fresh    | from card.docs_url                                 |

## Scaffold log

**Resolved invocation**: `git clone https://github.com/przeprogramowani/10x-astro-starter .bootstrap-scaffold && cd .bootstrap-scaffold && npm install`
**Strategy**: git-clone
**Exit code**: 0
**Files moved**: 19 (top-level entries: .env.example, .github, .gitignore, .husky, .nvmrc, .prettierrc.json, .vscode, CLAUDE.md, README.md, astro.config.mjs, components.json, eslint.config.js, node_modules, package-lock.json, package.json, public, src, supabase, tsconfig.json, wrangler.jsonc)
**Conflicts (.scaffold siblings)**: none
**.gitignore handling**: moved silently (absent in cwd)
**.bootstrap-scaffold cleanup**: deleted (`.git/` usunięty przed przeniesieniem — historia startera nie wycieka do projektu)

## Post-scaffold audit

**Tool**: npm audit --json
**Summary**: 1 CRITICAL, 12 HIGH, 7 MODERATE, 2 LOW (22 total)
**Direct vs transitive**: 3 direct (astro HIGH, supabase MODERATE, wrangler MODERATE) of total 22; 19 transitive

#### CRITICAL findings

- **tar** (transitive) — node-tar: seria advisories, m.in. PAX size override / file smuggling, DoS przez nieograniczone wejście, nieskończona pętla przy ujemnym rozmiarze wpisu. Zależność narzędziowa (toolchain), nie runtime aplikacji.

#### HIGH findings

- **astro** (direct) — seria XSS: unescaped slot name, spread props/attribute names, View Transition properties, transition:* directives; oraz Host header SSRF w prerendered error page fetch. Zalecenie: podbić Astro do najnowszej wersji 6.x (`npm audit fix` / aktualizacja zależności).
- **brace-expansion** (transitive) — DoS (wykładnicza ekspansja).
- **devalue** (transitive) — DoS via sparse array deserialization.
- **fast-uri** (transitive) — host confusion (backslash authority, IDN).
- **js-yaml** (transitive) — kwadratowa złożoność CPU (merge keys / !!omap).
- **miniflare** (transitive) — dev tooling Cloudflare.
- **postcss** (transitive) — path traversal przez sourceMappingURL.
- **sharp** (transitive) — odziedziczone CVE libvips.
- **svgo** (transitive) — removeScripts zostawia wykonywalne skrypty.
- **undici** (transitive) — seria: TLS bypass w SOCKS5 ProxyAgent, header injection, cache poisoning, response desync.
- **vite** (transitive) — NTLMv2 hash disclosure (Windows), server.fs.deny bypass (Windows).
- **ws** (transitive) — uninitialized memory disclosure, DoS.

#### MODERATE findings

- **supabase** (direct), **wrangler** (direct) + 5 transitive — szczegóły w `npm audit`.

#### LOW / INFO findings

- 2 low — szczegóły w `npm audit`.

## Hints recorded but not acted on

| Hint                    | Value            |
| ----------------------- | ---------------- |
| bootstrapper_confidence | first-class      |
| quality_override        | false            |
| path_taken              | standard         |
| self_check_answers      | null             |
| team_size               | solo             |
| deployment_target       | cloudflare-pages |
| ci_provider             | github-actions   |
| ci_default_flow         | auto-deploy-on-merge |
| has_auth                | true             |
| has_payments            | false            |
| has_realtime            | false            |
| has_ai                  | true             |
| has_background_jobs     | true             |

## Next steps

Next: a future skill will set up agent context (CLAUDE.md, AGENTS.md). For now, your project is scaffolded and verified — happy hacking.

Useful manual steps in the meantime:
- `git init` (if you have not already) to start your own repo history.
- Review any `.scaffold` siblings the conflict policy created and decide which version of each file to keep.
- Address audit findings per your project's risk tolerance — the full breakdown is in this log.
