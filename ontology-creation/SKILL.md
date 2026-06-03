---
name: ontology-creation
description: Create complete domain ontology YAML files for the create-context-graph repo. Use this skill whenever the user asks for a new domain YAML, custom ontology, ontology schema, domain model, graph ontology, POLE+O ontology, domain-specific context graph, agent tools for a domain, or a file similar to src/create_context_graph/domains/*.yaml.
---

# Ontology Creation

Use this skill to create a domain ontology YAML compatible with this repo's `create_context_graph.ontology.DomainOntology` schema and similar to the files in `src/create_context_graph/domains/`.

The output should be a complete YAML ontology for one domain, not a prose explanation. If the user asks you to save the ontology in the repo, put it in `src/create_context_graph/domains/<domain-id>.yaml` unless they specify another path.

## Source Grounding and Scope Control

When the user provides source documents, spreadsheets, sample data, schemas, or examples, the ontology must be grounded in those sources first.

- Inspect the provided sources before choosing entities, relationships, properties, tools, templates, or decision traces.
- Do not add domain concepts from general knowledge unless they appear in the sources or the user explicitly asks for general-domain inference.
- If the requested domain conflicts with the supplied source, stop and report the mismatch before writing YAML. For example, if the user asks for a clinical-trials ontology but the document is about agent harnesses, do not invent clinical-trial concepts.
- For spreadsheets and sample data, derive the ontology from observed sheet names, table names, column headers, representative values, repeated identifiers, and shared keys.
- Keep source terms whenever possible. Normalize names only to satisfy YAML, Cypher, and repo schema conventions.
- Exclude concepts that are plausible for the domain but absent from the source. For clinical-trials data, for example, do not add participants, endpoints, arms, visits, adverse events, or investigators unless those concepts are present in the source.
- The "complete ontology" requirement means complete relative to the available source scope, not exhaustive for the whole industry domain.

## Core Shape

Every domain ontology uses this top-level order:

```yaml
inherits: _base

domain:
  id: <kebab-case-id>
  name: <Human Name>
  description: <one-line scope>
  tagline: "<short product-style tagline>"
  emoji: "<single emoji or escaped unicode>"

entity_types:
  - label: <PascalCase>
    pole_type: <PERSON|ORGANIZATION|LOCATION|EVENT|OBJECT>
    subtype: <UPPER_SNAKE_CASE>
    color: "#16a34a"
    icon: <lucide-icon-name>
    properties:
      - name: <snake_case>
        type: <string|integer|float|boolean|date|datetime|point>
        required: true
        unique: true

relationships:
  - type: <UPPER_SNAKE_CASE>
    source: <EntityLabel>
    target: <EntityLabel>

document_templates:
  - id: <snake_case_or_kebab_case>
    name: <Template Name>
    description: <what this document represents>
    count: <integer>
    prompt_template: |
      <prompt using {{entity.property}} placeholders>
    required_entities: [<EntityLabel>, ...]

decision_traces:
  - id: <snake_case>
    task: "<decision task with {{placeholders}}>"
    steps:
      - thought: "<reasoning step>"
        action: "<graph query or analysis action>"
    outcome_template: "<result template with {{placeholders}}>"

demo_scenarios:
  - name: <Scenario Name>
    prompts:
      - "<realistic user prompt>"

agent_tools:
  - name: <snake_case_tool_name>
    description: <what the tool retrieves or analyzes>
    cypher: |
      MATCH ...
      RETURN ...
      LIMIT 20
    parameters:
      - name: <param_name>
        type: string
        description: <parameter description>

system_prompt: |
  <domain assistant role and capabilities>

visualization:
  node_colors:
    <EntityLabel>: "#16a34a"
  node_sizes:
    <EntityLabel>: 25
  default_cypher: "MATCH (n)-[r]-(m) RETURN n, r, m LIMIT 100"
```

## Base Ontology

All generated domain files should begin with `inherits: _base`. Do not redefine the inherited base entity types unless the user explicitly asks.

The base POLE+O categories are:

- `PERSON`: people, users, professionals, stakeholders, customers, providers, students.
- `ORGANIZATION`: companies, agencies, teams, institutions, departments.
- `LOCATION`: physical or geographic places, facilities, regions, venues.
- `EVENT`: time-bound activities, transactions, incidents, encounters, workflows, reviews, sessions.
- `OBJECT`: durable things, records, assets, products, policies, datasets, documents, instruments, metrics.

Prefer domain-specific labels over generic base labels. For example, use `Patient`, `Repository`, `Trade`, or `Destination`, while retaining the correct `pole_type`.

## Generation Workflow

1. Read the user's domain description and any source documents or sample data. Extract only the nouns, actors, records, workflows, metrics, places, and decisions that are actually present or explicitly requested.
2. Choose the number of domain-specific entity types warranted by the source. Repo-quality examples often use 6 or more, but source-grounded ontologies may use fewer or more depending on observed tables, documents, records, and shared keys.
3. Assign each entity to the best POLE+O category. When uncertain, decide by graph behavior: actors are `PERSON`, institutions are `ORGANIZATION`, places are `LOCATION`, time-bound occurrences are `EVENT`, and everything else is usually `OBJECT`.
4. For each entity, create useful properties from observed columns, source fields, or explicit user requirements. Include one stable identifier property such as `<entity>_id`, `code`, `ticker`, `slug`, or a source key with `required: true` and `unique: true`; also include a human-readable `name` or `title` when natural.
5. Add relationships supported by repeated identifiers, shared keys, containment, ownership, location, workflow order, or explicit source language. Do not add relationships solely because they are common in the broader domain.
6. Add document templates that fit the source scope and observed document/data types. Their prompts should mention source-backed entity properties and use `{{entity.property}}`, `{{entity_list}}`, or task-specific placeholders.
7. Add decision traces only for workflows supported by the source data, such as lookup, comparison, prioritization, risk checks, operational review, or metric review.
8. Add demo scenarios with prompts that sound like real end-user requests for the observed source data.
9. Add agent tools that answer source-backed graph questions. Include search/list/get-by-id tools for the primary entity when appropriate, plus analytical tools grounded in observed metrics or relationships. Cypher node labels and relationship types must exactly match the ontology.
10. Add a concise `system_prompt` that describes the domain assistant's role, capabilities, grounding behavior, and domain-specific cautions.
11. Add `visualization.node_colors`, `visualization.node_sizes`, and `visualization.default_cypher`.

## Naming Rules

- `domain.id`: kebab-case and should match the filename stem.
- Entity `label`: PascalCase singular, no spaces.
- Entity `subtype`: UPPER_SNAKE_CASE.
- Property `name`: snake_case.
- Relationship `type`: UPPER_SNAKE_CASE.
- Tool `name`: snake_case.
- Template and trace `id`: prefer snake_case to match the current domain files.
- Enum values: lowercase snake_case strings. Quote values that YAML might parse as booleans or special scalars.

## Property Rules

Valid property types are:

- `string`
- `integer`
- `float`
- `boolean`
- `date`
- `datetime`
- `point`

Use enums for bounded status, category, severity, type, priority, level, role, and stage properties. Keep enums realistic and compact. Use strings for long text, notes, descriptions, addresses, identifiers, URLs, and codes.

Avoid unsupported list-like properties unless existing application code has been updated for them. If the domain needs many-to-many values, model them as entity types and relationships instead of storing a list property.

## Entity Design Heuristics

Good entity sets cover the full domain workflow:

- Actors: a user, professional, specialist, reviewer, operator, customer, student, investigator, or manager.
- Core objects: the main thing being tracked, bought, analyzed, treated, built, or managed.
- Events: transactions, encounters, sessions, incidents, deployments, inspections, reviews, bookings, decisions.
- Context objects: categories, plans, policies, metrics, instruments, assets, documents, datasets, locations, facilities.
- Outcomes: assessment, result, report, issue, alert, risk, recommendation, claim, task, milestone.

Prefer entities that will appear repeatedly in documents and queries. Avoid tiny entities that only hold one property and have no meaningful relationships.

For source-grounded ontology generation, these heuristics are secondary to the source. They suggest what to look for; they do not authorize adding absent concepts.

## Relationship Design Heuristics

Relationships should make common questions easy:

- Ownership and membership: `OWNS`, `BELONGS_TO`, `PART_OF`, `AFFILIATED_WITH`.
- Participation: `ATTENDED`, `PARTICIPATED_IN`, `ASSIGNED_TO`, `AUTHORED`, `REVIEWED`.
- Causality and workflow: `TRIGGERED_BY`, `RESULTED_IN`, `CAUSED`, `PRECEDED_BY`, `FIXES`.
- Geography and placement: `LOCATED_AT`, `OCCURRED_AT`, `NEAR`, `AVAILABLE_IN`.
- Usage and dependency: `USES`, `DEPENDS_ON`, `CONTAINS`, `INCLUDES`.
- Evaluation: `MEASURED_BY`, `ASSESSED_BY`, `RECOMMENDED_FOR`, `CONTRAINDICATED_WITH`.

Every relationship `source` and `target` must be either an inherited base label or one of the domain entity labels.

For spreadsheet-backed ontologies, relationships should usually come from shared keys such as `study_id`, `country_name`, `site_number`, account IDs, customer IDs, product IDs, or other repeated identifiers. If the source does not support the edge, leave it out.

## Agent Tool Rules

Agent tools should be immediately useful to a graph-backed assistant:

- Include one broad search tool for the primary entity.
- Include one list tool for the primary entity with a `limit` parameter.
- Include one get-by-id tool that returns connections around a specific entity.
- Include domain analysis tools that answer real decisions, comparisons, risk checks, history lookup, or network exploration.
- Use `$parameter` placeholders in Cypher and define each parameter under `parameters`.
- Include `LIMIT` on read queries.
- Use `OPTIONAL MATCH` for related data that might not exist.
- Return meaningful aliases when returning scalar values.

Example tool pattern:

```yaml
agent_tools:
  - name: get_primary_by_id
    description: "Get a specific PrimaryEntity by ID with all connections"
    cypher: |
      MATCH (n:PrimaryEntity {primary_id: $id})
      OPTIONAL MATCH (n)-[r]-(related)
      RETURN n, type(r) AS relationship, labels(related) AS related_labels, related.name AS related_name
      LIMIT 50
    parameters:
      - name: id
        type: string
        description: "The primary_id to look up"
```

## Document Template Rules

Document templates drive synthetic document generation, so write prompts that produce rich, domain-specific text. Each template should:

- Use at least 2 required entity types.
- Reference specific properties from those entities.
- Produce a realistic document type for the domain, such as a report, note, plan, memo, review, summary, brief, record, confirmation, or analysis.
- Set `count` between 5 and 12 for normal domains.
- Use multiline block scalars with `prompt_template: |`.

For source-grounded ontologies, keep templates aligned to the observed source scope. Do not introduce document types that require absent entities or unsupported workflows.

## Decision Trace Rules

Decision traces should demonstrate how an agent reasons over the graph. Strong traces include:

- A concrete task with placeholders.
- 3 to 4 steps.
- Each step has a `thought` and `action`.
- Actions mention graph operations, comparisons, filters, historical lookups, relationship traversal, or risk checks.
- `outcome_template` summarizes the decision and rationale.

For source-grounded ontologies, every trace should be answerable from the ontology and source-backed properties. Avoid traces that depend on external domain assumptions.

## System Prompt Rules

The `system_prompt` should make the generated assistant domain-specific. Include:

- Role: "You are an AI <domain> assistant..."
- Capabilities tied to the ontology and tools.
- Grounding requirement: use graph data, cite connected entities, avoid unsupported claims.
- Domain caution when relevant, such as safety, compliance, risk, privacy, financial uncertainty, or operational impact.

Keep it concise: 2 to 5 short paragraphs or a short capability list.

## Visualization Rules

Add every domain entity label to `node_colors`. Include inherited base labels only when agent tools or default Cypher commonly return them.

Use distinct hex colors. Typical node sizes:

- Primary entities: 25 to 30
- Important actors or organizations: 25 to 30
- Events: 15 to 25
- Supporting objects and metrics: 15 to 20

The `default_cypher` should return a useful subgraph centered on the primary domain entity and include `LIMIT 100`.

## Completeness Checklist

Before finalizing, verify:

- YAML parses and has no markdown fences.
- Top-level order follows the repo examples.
- `inherits: _base` is present.
- `domain.id` matches the intended filename.
- Entity types are justified by source documents, sample data, or explicit user instructions. Use at least 6 entity types for a broad production-quality domain only when the source supports that scope.
- Every entity has a stable required unique identifier property.
- Every entity has a `color`, `icon`, `pole_type`, `subtype`, and useful properties.
- Every relationship references valid entity labels or inherited base labels.
- Every relationship is supported by source language, shared keys, or explicit user instruction.
- Every property type is one of the supported types.
- Enum values are strings, not YAML booleans.
- Document templates, decision traces, demo scenarios, and agent tools are source-backed and proportional to the ontology scope.
- Agent tool Cypher labels and relationship names match the ontology exactly.
- `system_prompt` and `visualization` are non-empty.

## Final Output

When the user asks you to generate an ontology, output only the YAML unless they also ask for explanation. When saving a file, write the YAML file and then briefly report the path and any validation performed.
