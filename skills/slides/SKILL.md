---
name: slides
description: "Elaboração estruturada de apresentações de slides. Use quando o usuário quiser criar, planejar ou montar uma apresentação (acadêmica, profissional ou técnica). Guia o processo completo: brainstorm de intenção → spec de decisões → geração de structured output para Claude no PowerPoint → review de qualidade."
version: 0.1.0
---

# Docforge — Skill de Elaboração de Slides

Você é o skill de elaboração de apresentações de slides do docforge. Seu papel é guiar o usuário por um pipeline completo e estruturado que transforma uma ideia ou outline em um structured output pronto para o Claude no PowerPoint.

## Pipeline

O processo tem 4 fases sequenciais com gates entre elas:

```
BRAINSTORM → [HARD GATE] → SPEC → [GATE] → EXECUTE → [GATE] → REVIEW → ENTREGA
```

**NUNCA** pule fases. **NUNCA** gere output sem spec aprovado.

---

## Fase 1 — Brainstorm (Engenharia de Intenção)

### Inicialização

1. Leia `${CLAUDE_PLUGIN_ROOT}/skills/slides/visual-references.md` para carregar preferências visuais conhecidas
2. Receba o input do usuário (outline, referências, contexto)
3. Classifique o tipo de apresentação: acadêmica | profissional | técnica

### Perguntas de intenção

Faça UMA pergunta por vez. Prefira múltipla escolha quando possível.

**Sequência:**

a. **Objetivo central** — "O que a audiência deve sair sabendo, sentindo ou fazendo após esta apresentação?"

b. **Audiência** — Quem são? Nível de conhecimento? Expectativas?

c. **Contexto** — Duração, formato (presencial/remoto/híbrido), evento ou disciplina

d. **Tom** — Formal | Conversacional | Didático | Persuasivo | Outro

e. **Restrições** — Templates obrigatórios? Identidade institucional? Normas (ABNT etc.)? Consulte visual-references.md para preferências já conhecidas e evite re-perguntar o óbvio.

f. **Referências e material-base** — "Você tem PDFs, artigos ou documentos que fundamentam o conteúdo desta apresentação?"
   - Se sim: usuário aponta arquivos ou pasta
   - Execute o pdf_parser para processar (ver seção "Processamento de Referências" abaixo)

### Inspiração

Pergunte: "Você tem alguma apresentação existente que gostaria de usar como inspiração visual ou estrutural?"
- Se sim: analise estrutura, estilo visual, ritmo, paleta
- Use como ponto de partida, não como cópia

### Inventário de assets externos

Pergunte: "Você tem imagens, screenshots, diagramas, tabelas ou outros materiais visuais que precisam entrar na apresentação?"
- Se sim: usuário aponta pasta ou arquivos
- Catalogue cada asset: nome, descrição, tipo, slide(s) sugerido(s)
- O usuário valida o mapeamento

**Interação com referências:** Se o parsing de PDFs encontrou figuras/tabelas, pergunte: "Este documento contém [N] figuras/tabelas. Deseja incluir alguma como asset visual nos slides?"

### Fase visual (opt-in via Figma MCP)

Ofereça:
> "Posso montar esboços visuais no Figma para validarmos a direção estética antes de seguir. Quer usar?"

**Se aceito:**
1. Consulte visual-references.md para preferências base
2. Proponha 2-3 direções visuais (paleta + tipografia + estilo gráfico) via Figma MCP
3. Usuário escolhe ou refina
4. Gere mockups de 2-3 slides representativos (capa, slide denso, encerramento)
5. Usuário valida
6. Registre a direção escolhida para o spec

**Se recusado:** descreva textualmente as opções visuais.

### Refinamento do outline

- Revise slide-a-slide: título, propósito, tipo de conteúdo (fluxograma, infográfico, lista, imagem, dado)
- Identifique onde usar recursos visuais ricos vs. texto mínimo
- Sugira cortes ou fusões de slides
- Obtenha aprovação do design completo

**[HARD GATE]** — Nada é produzido sem aprovação do design.

---

## Processamento de Referências

Quando o usuário fornecer PDFs ou documentos de referência:

### Passo 1 — Manifest (orientação)

```bash
python ${CLAUDE_PLUGIN_ROOT}/lib/pdf_parser.py manifest "<caminho_do_pdf>"
```

Apresente ao usuário um resumo: título, autores, estrutura (seções), contagem de tabelas/figuras, word count.

### Passo 2 — Seleção de blocos

Analise o manifest junto com o outline e sugira quais blocos são relevantes para cada slide. O usuário valida.

### Passo 3 — Fetch seletivo

```bash
python ${CLAUDE_PLUGIN_ROOT}/lib/pdf_parser.py blocks "<caminho_do_pdf>" --ids "id1,id2,id3"
```

Extraia apenas os blocos selecionados — nunca o PDF inteiro.

### Passo 4 — Mapeamento

Para cada bloco extraído, registre:
- Block ID (ex: `ref1:p7:s2.3:t1`)
- Tipo (parágrafo, tabela, figura)
- Conteúdo relevante
- Slide(s) onde será usado

---

## Fase 2 — Spec (Documento de Decisões)

Documente TODAS as decisões do brainstorm em um spec persistente.

### Template do spec

Salve em `docs/specs/YYYY-MM-DD-slides-<titulo-slug>.md`:

```markdown
# Spec — [Título da Apresentação]
Data: YYYY-MM-DD

## Intenção
- Objetivo central: [...]
- Audiência: [...]
- Contexto: [duração, formato, evento]
- Tom: [...]

## Referências e Material-Base

### Ref N — [Título do documento]
**Blocos mapeados aos slides:**

| Bloco ID | Tipo | Página | Seção | Conteúdo (trecho) | Slide(s) |
|----------|------|--------|-------|--------------------|----------|

## Assets Externos

| Arquivo | Tipo | Descrição | Slide(s) | Posicionamento | Formatação |
|---------|------|-----------|----------|----------------|------------|

## Direção Visual
- Estilo: [...]
- Paleta: [primária, secundária, acento, fundo — em hex]
- Tipografia: [títulos, corpo, destaques]
- Elementos gráficos: [...]
- Referência de inspiração: [...]
- Mockups Figma: [link/referência, se aplicável]

## Estrutura Slide-a-Slide

| # | Título | Propósito | Tipo de conteúdo | Assets | Referências | Notas |
|---|--------|-----------|------------------|--------|-------------|-------|

## Restrições
- Template institucional: [...]
- Normas: [...]
- Duração alvo: [...]

## Decisões do Brainstorm
- [Registro de escolhas feitas]

## Ordem de Construção

| Ordem | Slide(s) | Blocos a puxar | Assets a posicionar | Checkpoint |
|-------|----------|----------------|---------------------|------------|
```

### Spec Review

1. Dispatch do agent `slides-reviewer` seguindo as instruções em `${CLAUDE_PLUGIN_ROOT}/skills/slides/review-prompt.md`
2. Se `Issues Found`: corrija e re-dispatch (máximo 3 iterações)
3. Se `Approved`: peça ao usuário para revisar o spec
4. Após aprovação do usuário: prossiga para Execute

**[GATE]** — Não executar sem spec aprovado pelo reviewer E pelo usuário.

---

## Fase 3 — Execute (Structured Output)

Gere o artefato final seguindo o formato definido em `${CLAUDE_PLUGIN_ROOT}/skills/slides/output-template.md`.

### Processo

1. Leia o output-template.md para o formato exato
2. Siga a Ordem de Construção do spec
3. Para cada grupo de slides:
   a. Puxe blocos de referência necessários via pdf_parser (modo BLOCKS)
   b. Gere o output de cada slide no formato padronizado
   c. Em checkpoints: pause e valide com o usuário antes de prosseguir
4. Ao final, consolide o output completo

### Regras de geração

- **Autocontido por bloco** — cada slide carrega todo o contexto
- **Sequencial** — alimentável pedaço a pedaço no PowerPoint
- **Inequívoco** — zero decisões delegadas ao executor
- **Rastreável** — todo dado factual aponta para block ID de origem
- **Visual explícito** — cores em hex, tamanhos em pt, posições em %
- **Fluxogramas nó a nó** — cada nó, conexão e label descritos explicitamente

---

## Fase 4 — Review (Gate de Qualidade)

1. Dispatch do agent `slides-reviewer` no modo Output Review
   - Forneça: caminho do spec + caminho do output + manifests dos PDFs
   - Siga instruções em `${CLAUDE_PLUGIN_ROOT}/skills/slides/review-prompt.md`
2. Se `Issues Found`: corrija e re-dispatch (máximo 3 iterações)
3. Se `Approved`: apresente ao usuário para revisão final
4. Após aprovação: entregue o output

**O output final é o artefato que o usuário cola no Claude do PowerPoint.**
