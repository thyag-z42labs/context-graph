# Agent Instructions

## Source-grounded ontology work

- For any new source document, spreadsheet, sample data file, schema, or example provided with an ontology request, read and inspect that source before editing or creating ontology YAML.
- Use `ontology-creation/SKILL.md` as the governing workflow for ontology generation, especially its `Source Grounding and Scope Control` section.
- Before designing the ontology, extract a compact source inventory: document topic, relevant nouns/entities, records/tables, fields/columns, repeated identifiers, metrics, places, workflows, and explicit decisions found in the source.
- When creating or editing ontology YAML files, inspect the provided source documents or sample data before designing entities, relationships, tools, templates, or decision traces.
- Do not add domain concepts from general knowledge unless they are present in the user's source material or the user explicitly asks for inferred/general-domain coverage.
- If a requested domain conflicts with the provided source document, stop and report the mismatch before creating the ontology. Example: if the user asks for a clinical-trials ontology but the supplied document is about agent harnesses, do not invent clinical-trial entities.
- If the user provides sample data, derive the ontology primarily from observed sheet names, table names, column headers, representative values, and relationships implied by shared keys.
- Prefer exact source terms for entity names and properties, normalized only as needed for the repo schema. Keep unsupported concepts out of the YAML.
- Before finalizing, verify that every major entity type, relationship, template, decision trace, demo prompt, and agent tool can be traced back to source content, sample data, or explicit user instruction.

## Validation

- Validate ontology YAML with the repo loader after edits.
- Run the focused ontology tests when practical.
- If a validation command modifies unrelated files such as `uv.lock`, revert only those incidental changes and preserve user-created work.
