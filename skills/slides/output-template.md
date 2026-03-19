# Formato de Output — Slides para Claude no PowerPoint

Este template define o formato exato do structured output que o skill gera.
O Claude no PowerPoint consome este output bloco a bloco.

## Estrutura do documento

```
# Apresentação: [Título]
Gerado por docforge | Data: YYYY-MM-DD
Spec: [caminho do spec]

---

## Configuração Global
- **Aspecto:** 16:9
- **Tamanho mínimo de fonte:** 12pt (nenhum texto abaixo deste valor)
- **Paleta:** primária #XXXXXX, secundária #XXXXXX, acento #XXXXXX, fundo #XXXXXX
- **Tipografia títulos:** [Fonte] Bold, [tamanho]pt
- **Tipografia corpo:** [Fonte] Regular, [tamanho]pt (mínimo 12pt)
- **Tipografia destaques:** [Fonte] SemiBold, [tamanho]pt
- **Tipografia legendas/labels:** [Fonte] Regular, [tamanho]pt (mínimo 12pt)
- **Estilo gráfico:** [descrição do estilo visual]

---
```

## Bloco por slide

Cada slide segue este formato exato. Blocos são autocontidos e coláveis isoladamente.

```
## Slide N — [Título do Slide]
**Layout:** [descrição semântica: ex. "Título superior, conteúdo em duas colunas"]

**Conteúdo:**
- [Texto, listas, dados — tudo que aparece visualmente no slide]

**Visual:**
- [Cores específicas em hex para elementos deste slide]
- [Posicionamento: "metade esquerda", "centro", "60% da largura"]
- [Dimensões em pt ou %]
- [Decoração: bordas, sombras, cantos, gradientes]

**Asset externo:** (se houver)
- Arquivo: [nome exato do arquivo]
- Posição: [descrição semântica]
- Tamanho: [% da área útil]
- Formatação: [borda, cantos, legenda com fonte/cor]

**Referência:** [block IDs das fontes — ex: ref1:p7:s2.3:t1]
**Notas do apresentador:** [texto para modo apresentação — complementa, não repete]
```

## Regras

1. **Configuração Global** é colada uma vez no início da sessão do PowerPoint
2. Cada slide é um **bloco independente** — colável sozinho sem depender de contexto anterior
3. **Layout semântico** — descrever posição em linguagem natural, não coordenadas
4. **Cores sempre em hex**, tamanhos em **pt** (mínimo 12pt em qualquer texto), proporções em **%**
5. **Fluxogramas/diagramas** descritos nó a nó com conectores explícitos
6. **Tabelas** com cabeçalhos e dados exatos, formatação de cada elemento
7. **Assets** referenciados pelo nome exato do arquivo
8. **Notas do apresentador** são conteúdo para o modo apresentação, separado do visível

## Fallback para blocos grandes

Se um slide tem conteúdo muito extenso, dividir em dois pastes:

**Paste 1 — Conteúdo + Layout:**
```
## Slide N — [Título] (Parte 1: Conteúdo)
**Layout:** [...]
**Conteúdo:** [...]
**Asset externo:** [...]
```

**Paste 2 — Visual + Formatação:**
```
## Slide N — [Título] (Parte 2: Visual)
**Visual:** [...]
**Referência:** [...]
**Notas do apresentador:** [...]
```
