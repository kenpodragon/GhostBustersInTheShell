"""Tests for VoiceProfileService."""
import pytest
from utils.voice_profile_service import VoiceProfileService


@pytest.fixture
def svc():
    from db import init_pool, get_conn
    init_pool()
    with get_conn() as conn:
        yield VoiceProfileService(conn)


class TestProfileCRUD:
    def test_list_profiles(self, svc):
        profiles = svc.list_profiles()
        assert isinstance(profiles, list)
        assert len(profiles) >= 1
        assert profiles[0]["profile_type"] == "baseline"

    def test_create_profile(self, svc):
        profile = svc.create_profile("Test Overlay", "A test overlay", "overlay")
        assert profile["name"] == "Test Overlay"
        assert profile["profile_type"] == "overlay"
        assert profile["parse_count"] == 0
        svc.delete_profile(profile["id"])

    def test_get_profile(self, svc):
        profile = svc.create_profile("Get Test", "desc", "overlay")
        fetched = svc.get_profile(profile["id"])
        assert fetched["name"] == "Get Test"
        assert "elements" in fetched
        assert "prompts" in fetched
        assert len(fetched["elements"]) == 5  # starter elements
        svc.delete_profile(profile["id"])

    def test_update_profile(self, svc):
        profile = svc.create_profile("Update Test", "desc", "overlay")
        svc.update_profile(profile["id"], name="Updated Name")
        fetched = svc.get_profile(profile["id"])
        assert fetched["name"] == "Updated Name"
        svc.delete_profile(profile["id"])

    def test_delete_profile(self, svc):
        profile = svc.create_profile("Delete Test", "desc", "overlay")
        svc.delete_profile(profile["id"])
        assert svc.get_profile(profile["id"]) is None

    def test_get_nonexistent_profile(self, svc):
        assert svc.get_profile(99999) is None


# =============================================================================
# Task 3: Elements & Prompts CRUD
# =============================================================================

class TestElements:
    def test_get_elements(self, svc):
        profile = svc.create_profile("Elem Test", "", "overlay")
        try:
            elements = svc.get_elements(profile["id"])
            assert isinstance(elements, list)
            assert len(elements) == 5  # starter elements
        finally:
            svc.delete_profile(profile["id"])

    def test_update_elements(self, svc):
        profile = svc.create_profile("Update Elem Test", "", "overlay")
        try:
            elements = svc.get_elements(profile["id"])
            # Change weight of first element
            first = elements[0]
            first["weight"] = 0.99
            svc.update_elements(profile["id"], [first])
            updated = svc.get_elements(profile["id"])
            match = next(e for e in updated if e["name"] == first["name"])
            assert abs(match["weight"] - 0.99) < 0.001
        finally:
            svc.delete_profile(profile["id"])

    def test_add_custom_element(self, svc):
        profile = svc.create_profile("Add Elem Test", "", "overlay")
        try:
            elem_id = svc.add_element(profile["id"], {
                "name": "custom_marker",
                "category": "idiosyncratic",
                "element_type": "directional",
                "direction": "more",
                "weight": 0.7,
                "tags": ["custom"],
                "source": "manual",
            })
            assert isinstance(elem_id, int)
            elements = svc.get_elements(profile["id"])
            names = [e["name"] for e in elements]
            assert "custom_marker" in names
            assert len(elements) == 6  # 5 starters + 1 custom
        finally:
            svc.delete_profile(profile["id"])

    def test_delete_element(self, svc):
        profile = svc.create_profile("Del Elem Test", "", "overlay")
        try:
            elements = svc.get_elements(profile["id"])
            first_id = elements[0]["id"]
            svc.delete_element(first_id)
            remaining = svc.get_elements(profile["id"])
            assert len(remaining) == 4
            assert all(e["id"] != first_id for e in remaining)
        finally:
            svc.delete_profile(profile["id"])


class TestPrompts:
    def test_get_prompts_empty(self, svc):
        profile = svc.create_profile("Prompt Empty Test", "", "overlay")
        try:
            prompts = svc.get_prompts(profile["id"])
            assert isinstance(prompts, list)
            assert len(prompts) == 0
        finally:
            svc.delete_profile(profile["id"])

    def test_update_prompts(self, svc):
        profile = svc.create_profile("Prompt Update Test", "", "overlay")
        try:
            svc.update_prompts(profile["id"], [
                {"prompt_text": "Write like a scientist.", "sort_order": 0},
                {"prompt_text": "Avoid jargon.", "sort_order": 1},
            ])
            prompts = svc.get_prompts(profile["id"])
            assert len(prompts) == 2
            texts = [p["prompt_text"] for p in prompts]
            assert "Write like a scientist." in texts
            assert "Avoid jargon." in texts
        finally:
            svc.delete_profile(profile["id"])

    def test_replace_prompts(self, svc):
        profile = svc.create_profile("Prompt Replace Test", "", "overlay")
        try:
            svc.update_prompts(profile["id"], [
                {"prompt_text": "First prompt.", "sort_order": 0},
            ])
            assert len(svc.get_prompts(profile["id"])) == 1
            # Replace with 2 new prompts
            svc.update_prompts(profile["id"], [
                {"prompt_text": "New prompt A.", "sort_order": 0},
                {"prompt_text": "New prompt B.", "sort_order": 1},
            ])
            prompts = svc.get_prompts(profile["id"])
            assert len(prompts) == 2
            texts = [p["prompt_text"] for p in prompts]
            assert "First prompt." not in texts
            assert "New prompt A." in texts
            assert "New prompt B." in texts
        finally:
            svc.delete_profile(profile["id"])


# =============================================================================
# Task 4: Stack Resolution & Active Config
# =============================================================================

class TestStackResolution:
    def test_get_active_stack(self, svc):
        stack = svc.get_active_stack()
        assert isinstance(stack, dict)
        assert "baseline" in stack
        assert "overlays" in stack
        assert "resolved_elements" in stack
        assert "prompts" in stack

    def test_set_active_stack(self, svc):
        # Find the baseline profile
        profiles = svc.list_profiles()
        baseline = next(p for p in profiles if p["profile_type"] == "baseline")
        svc.set_active_stack(baseline["id"], [])
        stack = svc.get_active_stack()
        assert stack["baseline"] is not None
        assert stack["baseline"]["id"] == baseline["id"]

    def test_overlay_overrides_baseline(self, svc):
        profiles = svc.list_profiles()
        baseline = next(p for p in profiles if p["profile_type"] == "baseline")
        overlay = svc.create_profile("Override Overlay", "", "overlay")
        try:
            # Add contraction_rate with direction="less", weight=0.2 to overlay
            svc.add_element(overlay["id"], {
                "name": "contraction_rate",
                "category": "lexical",
                "element_type": "directional",
                "direction": "less",
                "weight": 0.2,
                "source": "manual",
            })
            svc.set_active_stack(baseline["id"], [overlay["id"]])
            stack = svc.get_active_stack()
            resolved = {e["name"]: e for e in stack["resolved_elements"]}
            assert "contraction_rate" in resolved
            # Overlay value wins
            assert resolved["contraction_rate"]["direction"] == "less"
            assert abs(resolved["contraction_rate"]["weight"] - 0.2) < 0.001
        finally:
            svc.delete_profile(overlay["id"])
            svc.set_active_stack(baseline["id"], [])

    def test_baseline_fallthrough(self, svc):
        profiles = svc.list_profiles()
        baseline = next(p for p in profiles if p["profile_type"] == "baseline")
        overlay = svc.create_profile("Fallthrough Overlay", "", "overlay")
        try:
            # Add a unique element to overlay only
            svc.add_element(overlay["id"], {
                "name": "unique_overlay_element",
                "category": "lexical",
                "element_type": "directional",
                "direction": "more",
                "weight": 0.3,
                "source": "manual",
            })
            svc.set_active_stack(baseline["id"], [overlay["id"]])
            stack = svc.get_active_stack()
            resolved_names = [e["name"] for e in stack["resolved_elements"]]
            # Baseline elements still present
            baseline_elements = svc.get_elements(baseline["id"])
            for be in baseline_elements:
                assert be["name"] in resolved_names
            # Overlay unique element also present
            assert "unique_overlay_element" in resolved_names
        finally:
            svc.delete_profile(overlay["id"])
            svc.set_active_stack(baseline["id"], [])


# =============================================================================
# Task 5: Snapshots, Export/Import, Reset
# =============================================================================

class TestSnapshots:
    def test_save_and_list_snapshots(self, svc):
        profile = svc.create_profile("Snap Test", "", "overlay")
        try:
            snap_id = svc.save_snapshot(profile["id"], "v1")
            assert isinstance(snap_id, int)
            snaps = svc.list_snapshots(profile["id"])
            assert len(snaps) >= 1
            assert any(s["id"] == snap_id for s in snaps)
        finally:
            svc.delete_profile(profile["id"])

    def test_load_snapshot(self, svc):
        profile = svc.create_profile("Load Snap Test", "", "overlay")
        try:
            elements = svc.get_elements(profile["id"])
            first = elements[0]
            original_weight = first["weight"]
            # Save snapshot with original weight
            snap_id = svc.save_snapshot(profile["id"], "before_change")
            # Change weight
            first["weight"] = 0.99
            svc.update_elements(profile["id"], [first])
            changed = svc.get_elements(profile["id"])
            match = next(e for e in changed if e["name"] == first["name"])
            assert abs(match["weight"] - 0.99) < 0.001
            # Load snapshot — weight should be restored
            svc.load_snapshot(profile["id"], snap_id)
            restored = svc.get_elements(profile["id"])
            match2 = next(e for e in restored if e["name"] == first["name"])
            assert abs(match2["weight"] - original_weight) < 0.001
        finally:
            svc.delete_profile(profile["id"])

    def test_delete_snapshot(self, svc):
        profile = svc.create_profile("Del Snap Test", "", "overlay")
        try:
            snap_id = svc.save_snapshot(profile["id"], "to_delete")
            svc.delete_snapshot(snap_id)
            snaps = svc.list_snapshots(profile["id"])
            assert all(s["id"] != snap_id for s in snaps)
        finally:
            svc.delete_profile(profile["id"])


class TestExportImport:
    def test_export_profile(self, svc):
        profile = svc.create_profile("Export Test", "export desc", "overlay")
        try:
            exported = svc.export_profile(profile["id"])
            assert exported["name"] == "Export Test"
            assert exported["description"] == "export desc"
            assert "elements" in exported
            assert "prompts" in exported
            assert isinstance(exported["elements"], list)
        finally:
            svc.delete_profile(profile["id"])

    def test_import_profile(self, svc):
        profile = svc.create_profile("Import Source", "to import", "overlay")
        svc.update_prompts(profile["id"], [{"prompt_text": "Be concise.", "sort_order": 0}])
        try:
            exported = svc.export_profile(profile["id"])
            svc.delete_profile(profile["id"])
            profile = None  # deleted

            imported = svc.import_profile(exported)
            try:
                assert imported["name"] == "Import Source"
                full = svc.get_profile(imported["id"])
                assert len(full["elements"]) == len(exported["elements"])
                prompt_texts = [p["prompt_text"] for p in full["prompts"]]
                assert "Be concise." in prompt_texts
            finally:
                svc.delete_profile(imported["id"])
        finally:
            if profile is not None:
                svc.delete_profile(profile["id"])


class TestReset:
    def test_reset_corpus(self, svc):
        profile = svc.create_profile("Reset Test", "", "overlay")
        try:
            # Add a parsed element
            svc.add_element(profile["id"], {
                "name": "parsed_element",
                "category": "lexical",
                "element_type": "directional",
                "direction": "more",
                "weight": 0.8,
                "source": "parsed",
            })
            elements_before = svc.get_elements(profile["id"])
            assert any(e["source"] == "parsed" for e in elements_before)

            svc.reset_corpus(profile["id"])

            elements_after = svc.get_elements(profile["id"])
            assert all(e["source"] != "parsed" for e in elements_after)
            summary = svc.get_profile_summary(profile["id"])
            assert summary["parse_count"] == 0
        finally:
            svc.delete_profile(profile["id"])


# =============================================================================
# Task 6: Corpus Averaging
# =============================================================================

class TestCorpusAveraging:
    def _make_parse(self, name, weight, direction="more", element_type="directional", target_value=None):
        return {
            name: {
                "category": "lexical",
                "element_type": element_type,
                "direction": direction,
                "weight": weight,
                "target_value": target_value,
                "tags": [],
            }
        }

    def test_average_single_parse(self, svc):
        profile = svc.create_profile("Avg Single", "", "overlay")
        try:
            svc.apply_parse_results(profile["id"], self._make_parse("test_elem", 0.8))
            elements = {e["name"]: e for e in svc.get_elements(profile["id"])}
            assert "test_elem" in elements
            assert abs(elements["test_elem"]["weight"] - 0.8) < 0.001
            summary = svc.get_profile_summary(profile["id"])
            assert summary["parse_count"] == 1
        finally:
            svc.delete_profile(profile["id"])

    def test_average_second_parse(self, svc):
        profile = svc.create_profile("Avg Second", "", "overlay")
        try:
            # First parse: weight = 0.8
            svc.apply_parse_results(profile["id"], self._make_parse("test_elem", 0.8))
            # Second parse: weight = 0.4 → avg = (0.8*1 + 0.4) / 2 = 0.6
            svc.apply_parse_results(profile["id"], self._make_parse("test_elem", 0.4))
            elements = {e["name"]: e for e in svc.get_elements(profile["id"])}
            assert abs(elements["test_elem"]["weight"] - 0.6) < 0.001
            summary = svc.get_profile_summary(profile["id"])
            assert summary["parse_count"] == 2
        finally:
            svc.delete_profile(profile["id"])

    def test_average_stability_at_high_count(self, svc):
        profile = svc.create_profile("Avg Stability", "", "overlay")
        try:
            # Simulate 99 parses at 0.5 by setting parse_count directly via add_element + update
            # First parse to establish element
            svc.apply_parse_results(profile["id"], self._make_parse("stable_elem", 0.5))
            # Manually set parse_count to 99 and weight to 0.5
            with svc.conn.cursor() as cur:
                cur.execute(
                    "UPDATE voice_profiles SET parse_count = 99 WHERE id = %s",
                    (profile["id"],)
                )
                cur.execute(
                    "UPDATE profile_elements SET weight = 0.5 WHERE voice_profile_id = %s AND name = %s",
                    (profile["id"], "stable_elem")
                )
            svc.conn.commit()

            # 100th parse at 1.0 → (0.5*99 + 1.0) / 100 = 50.5/100 = 0.505
            svc.apply_parse_results(profile["id"], self._make_parse("stable_elem", 1.0))
            elements = {e["name"]: e for e in svc.get_elements(profile["id"])}
            assert abs(elements["stable_elem"]["weight"] - 0.505) < 0.001
        finally:
            svc.delete_profile(profile["id"])

    def test_parse_determinism(self, svc):
        profile = svc.create_profile("Avg Determinism", "", "overlay")
        try:
            # Same value twice → (0.7*1 + 0.7) / 2 = 0.7 (no drift)
            svc.apply_parse_results(profile["id"], self._make_parse("stable_elem", 0.7))
            svc.apply_parse_results(profile["id"], self._make_parse("stable_elem", 0.7))
            elements = {e["name"]: e for e in svc.get_elements(profile["id"])}
            assert abs(elements["stable_elem"]["weight"] - 0.7) < 0.001
        finally:
            svc.delete_profile(profile["id"])
