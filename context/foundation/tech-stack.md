---
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
---

## Why this stack

Solo, po godzinach, 3-tygodniowe MVP aplikacji webowej z logowaniem, uploadem dużych wideo i analizą AI — priorytetem jest starter, który daje auth, bazę i deploy od ręki, zamiast tygodnia konfiguracji. 10x Astro Starter (Astro + React + TypeScript + Tailwind + Supabase + Cloudflare Pages) to rekomendowany default dla (web, js): przechodzi wszystkie cztery bramki agent-friendly, Supabase pokrywa FR-001/002 (logowanie zewnętrznym dostawcą) i storage dla nagrań (FR-003), a Cloudflare Pages z auto-deployem po merge (GitHub Actions) domyka CI/CD bez dodatkowej pracy. Znana rezerwa: edge runtime nie udźwignie długiej analizy wideo (do 1h) — flaga has_background_jobs jest ustawiona, a przetwarzanie analizy trzeba będzie zaprojektować jako zadanie poza edge (kolejka / zewnętrzny worker); decyzja o mechanizmie zapada na etapie planowania, nie w starterze. Flagi has_auth i has_ai ustawione; płatności i realtime poza zakresem zgodnie z non-goals PRD.
