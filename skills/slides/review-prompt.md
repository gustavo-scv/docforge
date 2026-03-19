# Instruções de Dispatch do Slides Reviewer

Este arquivo documenta como o SKILL.md deve invocar o agent slides-reviewer.

## Spec Review (após Fase 2)

Dispatch com o seguinte prompt:

```
Revise o spec de apresentação em: [caminho do spec]

Modo: Spec Review
Critérios: completude, coerência, viabilidade, referências, assets.

Leia o spec e avalie conforme seus critérios de Spec Review.
Retorne no formato padronizado (Status + Issues + Recomendações).
```

## Output Review (Fase 4)

Dispatch com o seguinte prompt:

```
Revise o output de apresentação.

Modo: Output Review
Spec aprovado: [caminho do spec]
Output gerado: [caminho do output]
Manifests dos PDFs: [caminhos dos manifests, se houver]

Leia o spec e o output. Avalie conforme seus critérios de Output Review.
Retorne no formato padronizado (Status + Issues + Recomendações).
```

## Mecânica do loop

1. Dispatch → agent retorna resultado
2. Se `Issues Found`: corrigir issues, re-dispatch (máximo 3 iterações)
3. Se `Approved`: prosseguir para revisão do usuário
4. Se 3 iterações sem aprovação: informar o usuário e pedir orientação
