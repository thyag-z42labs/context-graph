# Copyright 2026 Neo4j Labs
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the NAMS backend path: rendered templates, ingest serializer, defaults."""

from __future__ import annotations

import json
from pathlib import Path

from create_context_graph.config import ProjectConfig
from create_context_graph.ingest import _serialize_entity_to_description
from create_context_graph.ontology import load_domain
from create_context_graph.renderer import ProjectRenderer


class TestProjectConfigNamsDefaults:
    """ProjectConfig defaults flip to NAMS and force-coerce profile/preferences."""

    def test_default_backend_is_nams(self):
        cfg = ProjectConfig(project_name="x", domain="healthcare")
        assert cfg.memory_backend == "nams"
        assert cfg.is_nams is True
        assert cfg.is_self_hosted is False

    def test_default_framework_is_strands(self):
        cfg = ProjectConfig(project_name="x", domain="healthcare")
        assert cfg.framework == "strands"

    def test_nams_forces_core_mcp_profile(self):
        cfg = ProjectConfig(
            project_name="x",
            domain="healthcare",
            with_mcp=True,
            mcp_profile="extended",  # user-requested
        )
        assert cfg.effective_mcp_profile == "core"

    def test_bolt_preserves_requested_mcp_profile(self):
        cfg = ProjectConfig(
            project_name="x",
            domain="healthcare",
            memory_backend="bolt",
            with_mcp=True,
            mcp_profile="extended",
        )
        assert cfg.effective_mcp_profile == "extended"

    def test_nams_disables_auto_preferences(self):
        cfg = ProjectConfig(
            project_name="x", domain="healthcare", auto_preferences=True
        )
        assert cfg.effective_auto_preferences is False

    def test_bolt_keeps_auto_preferences(self):
        cfg = ProjectConfig(
            project_name="x",
            domain="healthcare",
            memory_backend="bolt",
            auto_preferences=True,
        )
        assert cfg.effective_auto_preferences is True


class TestEntitySerializer:
    """The B-partial port packs entity attributes into the description field."""

    def test_basic_fields_render(self):
        out = _serialize_entity_to_description(
            {"name": "Alice", "age": 30, "role": "doctor"},
            label="Patient",
            pole_type="PERSON",
        )
        assert "Patient." in out
        assert "**Age**: 30" in out
        assert "**Role**: doctor" in out
        assert "_pole_type: PERSON_" in out

    def test_existing_description_preserved(self):
        out = _serialize_entity_to_description(
            {"name": "Alice", "description": "A patient under treatment.", "status": "active"},
            label="Patient",
            pole_type="PERSON",
        )
        assert "A patient under treatment." in out
        assert "**Status**: active" in out

    def test_reserved_keys_excluded(self):
        out = _serialize_entity_to_description(
            {"name": "Alice", "id": "P-1", "domain": "healthcare", "uuid": "abc"},
            label="Patient",
            pole_type="PERSON",
        )
        # None of the reserved keys should appear as attribute lines.
        assert "**Id**:" not in out
        assert "**Domain**:" not in out
        assert "**Uuid**:" not in out

    def test_empty_values_skipped(self):
        out = _serialize_entity_to_description(
            {"name": "Alice", "role": "", "age": None},
            label="Patient",
            pole_type="PERSON",
        )
        assert "**Role**:" not in out
        assert "**Age**:" not in out


class TestNamsRenderedTemplates:
    """Generated project templates honor the NAMS backend."""

    def _render(self, tmp_path: Path) -> tuple[Path, ProjectConfig]:
        cfg = ProjectConfig(
            project_name="NAMS Test",
            domain="financial-services",
            framework="strands",
            nams_api_key="test-key-123",
        )
        ontology = load_domain(cfg.domain)
        out = tmp_path / "nams-test"
        out.mkdir()
        ProjectRenderer(cfg, ontology).render(out)
        return out, cfg

    def test_env_has_memory_api_key(self, tmp_path):
        out, _ = self._render(tmp_path)
        env = (out / ".env").read_text()
        assert "MEMORY_API_KEY=test-key-123" in env
        assert "MEMORY_BACKEND=nams" in env
        # Bolt-only lines should NOT be present on the NAMS path
        assert "NEO4J_URI=" not in env

    def test_env_example_has_litellm_hints(self, tmp_path):
        out, _ = self._render(tmp_path)
        env_example = (out / ".env.example").read_text()
        assert "MEMORY_LLM=" in env_example
        assert "MEMORY_EMBEDDING=" in env_example
        assert "anthropic/claude-haiku-4-5" in env_example
        assert "ollama/llama3" in env_example
        assert "memory.neo4jlabs.com" in env_example

    def test_pyproject_has_litellm_no_extraction(self, tmp_path):
        out, _ = self._render(tmp_path)
        pkg = (out / "backend" / "pyproject.toml").read_text()
        assert "neo4j-agent-memory[litellm,sentence-transformers]" in pkg
        assert ">=0.4.0" in pkg
        assert "<0.6.0" in pkg
        # NAMS path should NOT pull in spaCy/GLiNER (extraction happens server-side)
        assert "extraction" not in pkg
        assert "fuzzy" not in pkg

    def test_config_py_has_memory_settings(self, tmp_path):
        out, _ = self._render(tmp_path)
        cfg_py = (out / "backend" / "app" / "config.py").read_text()
        assert "memory_backend" in cfg_py
        assert "memory_api_key" in cfg_py
        assert "memory_nams_endpoint" in cfg_py
        assert "memory_llm" in cfg_py
        assert "memory_embedding" in cfg_py

    def test_memory_py_branches_on_backend(self, tmp_path):
        out, _ = self._render(tmp_path)
        mem = (out / "backend" / "app" / "memory.py").read_text()
        assert "backend=\"nams\"" in mem
        assert "NamsConfig" in mem
        assert "_resolve_llm_model" in mem
        assert "_resolve_embedding_model" in mem
        # All three high-level entry points still exported
        assert "async def store_message" in mem
        assert "async def get_context" in mem
        assert "def resolve_session_id" in mem

    def test_memory_adapter_present(self, tmp_path):
        out, _ = self._render(tmp_path)
        adapter = out / "backend" / "app" / "memory_adapter.py"
        assert adapter.exists()
        src = adapter.read_text()
        assert "list_documents_nams" in src
        assert "list_traces_nams" in src
        assert "expand_node_nams" in src
        assert "schema_visualization_nams" in src
        assert "get_entity_detail_nams" in src

    def test_routes_dispatch_on_backend(self, tmp_path):
        out, _ = self._render(tmp_path)
        routes = (out / "backend" / "app" / "routes.py").read_text()
        assert "_is_nams" in routes
        assert "list_documents_nams" in routes
        assert "list_traces_nams" in routes
        assert "expand_node_nams" in routes

    def test_mcp_config_nams_shape_when_enabled(self, tmp_path):
        cfg = ProjectConfig(
            project_name="NAMS MCP",
            domain="financial-services",
            framework="strands",
            nams_api_key="test-key-123",
            with_mcp=True,
        )
        ontology = load_domain(cfg.domain)
        out = tmp_path / "nams-mcp"
        out.mkdir()
        ProjectRenderer(cfg, ontology).render(out)

        config = json.loads((out / "mcp" / "claude_desktop_config.json").read_text())
        server = next(iter(config["mcpServers"].values()))
        assert "--backend" in server["args"]
        assert "nams" in server["args"]
        assert "core" in server["args"]  # NAMS forces core profile
        assert server["env"]["MEMORY_API_KEY"] == "${MEMORY_API_KEY}"


class TestBoltRenderedTemplates:
    """Generated project templates on the self-hosted bolt path still work."""

    def test_pyproject_has_extraction_extras_on_bolt(self, tmp_path):
        cfg = ProjectConfig(
            project_name="Bolt Test",
            domain="financial-services",
            framework="pydanticai",
            memory_backend="bolt",
        )
        ontology = load_domain(cfg.domain)
        out = tmp_path / "bolt-test"
        out.mkdir()
        ProjectRenderer(cfg, ontology).render(out)

        pkg = (out / "backend" / "pyproject.toml").read_text()
        assert "extraction" in pkg
        assert "fuzzy" in pkg
        assert "neo4j-agent-memory[litellm,sentence-transformers,extraction,fuzzy]" in pkg

    def test_env_has_neo4j_lines_on_bolt(self, tmp_path):
        cfg = ProjectConfig(
            project_name="Bolt Test",
            domain="financial-services",
            framework="pydanticai",
            memory_backend="bolt",
            neo4j_uri="neo4j://localhost:7687",
            neo4j_password="testpw",
        )
        ontology = load_domain(cfg.domain)
        out = tmp_path / "bolt-test"
        out.mkdir()
        ProjectRenderer(cfg, ontology).render(out)
        env = (out / ".env").read_text()
        assert "NEO4J_URI=neo4j://localhost:7687" in env
        assert "NEO4J_PASSWORD=testpw" in env
        assert "MEMORY_API_KEY" not in env
