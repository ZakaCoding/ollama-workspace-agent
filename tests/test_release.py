import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_check', ROOT / 'scripts/check-release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def test_release_tag_must_match_package_and_dated_changelog(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[project]\nversion = "1.2.3"\n')
    (tmp_path / 'CHANGELOG.md').write_text('## [1.2.3] - 2026-09-21\n')
    assert release.check_release(tmp_path, 'v1.2.3') == '1.2.3'
    with pytest.raises(ValueError, match='does not match'):
        release.check_release(tmp_path, 'v1.2.4')
    (tmp_path / 'CHANGELOG.md').write_text('## [Unreleased]\n')
    with pytest.raises(ValueError, match='no dated entry'):
        release.check_release(tmp_path, 'v1.2.3')


def test_evaluation_summary_keeps_metrics_denominators_separate():
    spec = importlib.util.spec_from_file_location('eval_agent', ROOT / 'scripts/eval-agent.py')
    evaluation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluation)
    summary = evaluation.summarize([
        {'case': 'retrieval', 'passed': True, 'seconds': 2, 'groundedness_passed': True},
        {'case': 'edit', 'passed': False, 'seconds': 4, 'patch_correct': False,
         'tools': [{}, {}], 'successful_tools': 1},
        {'case': 'retrieval', 'passed': False, 'failure_kind': 'infrastructure'},
    ])
    assert summary['groundedness'] == {'passed': 1, 'evaluated': 1}
    assert summary['patch_correctness'] == {'passed': 0, 'evaluated': 1}
    assert summary['infrastructure_failures'] == 1
    assert summary['successful_tools'] == 1
    assert summary['tool_calls'] == 2
    assert summary['median_seconds'] == 3
    assert summary['max_seconds'] == 4
