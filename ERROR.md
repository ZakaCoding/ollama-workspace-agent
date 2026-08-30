Run pytest tests/ -v
  pytest tests/ -v
  shell: /usr/bin/bash -e {0}
  env:
    pythonLocation: /opt/hostedtoolcache/Python/3.11.16/x64
    PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.11.16/x64/lib/pkgconfig
    Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.16/x64
    Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.16/x64
    Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.16/x64
    LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.11.16/x64/lib
    LLM_BASE_URL: http://localhost:11434/v1
    LLM_MODEL: test-model
    EMBEDDING_BASE_URL: http://localhost:11434
    EMBEDDING_MODEL: nomic-embed-text
============================= test session starts ==============================
platform linux -- Python 3.11.16, pytest-9.1.1, pluggy-1.6.0 -- /opt/hostedtoolcache/Python/3.11.16/x64/bin/python
cachedir: .pytest_cache
rootdir: /home/runner/work/ollama-workspace-agent/ollama-workspace-agent
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 0 items / 7 errors

==================================== ERRORS ====================================
_______________ ERROR collecting tests/test_agent_guardrails.py ________________
ImportError while importing test module '/home/runner/work/ollama-workspace-agent/ollama-workspace-agent/tests/test_agent_guardrails.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_agent_guardrails.py:5: in <module>
    from app.agent.core import (
E   ModuleNotFoundError: No module named 'app'
______________________ ERROR collecting tests/test_api.py ______________________
ImportError while importing test module '/home/runner/work/ollama-workspace-agent/ollama-workspace-agent/tests/test_api.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_api.py:3: in <module>
    from app.api import create_app
E   ModuleNotFoundError: No module named 'app'
__________________ ERROR collecting tests/test_api_client.py ___________________
ImportError while importing test module '/home/runner/work/ollama-workspace-agent/ollama-workspace-agent/tests/test_api_client.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_api_client.py:1: in <module>
    from app.api_client import ApiClient
E   ModuleNotFoundError: No module named 'app'
__________________ ERROR collecting tests/test_calculator.py ___________________
ImportError while importing test module '/home/runner/work/ollama-workspace-agent/ollama-workspace-agent/tests/test_calculator.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_calculator.py:3: in <module>
    from app.calculator import add, subtract, multiply, divide, power
E   ModuleNotFoundError: No module named 'app'
__________________ ERROR collecting tests/test_code_review.py __________________
ImportError while importing test module '/home/runner/work/ollama-workspace-agent/ollama-workspace-agent/tests/test_code_review.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_code_review.py:3: in <module>
    from app.agent.core import Agent
E   ModuleNotFoundError: No module named 'app'
__________________ ERROR collecting tests/test_llm_stream.py ___________________
ImportError while importing test module '/home/runner/work/ollama-workspace-agent/ollama-workspace-agent/tests/test_llm_stream.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_llm_stream.py:1: in <module>
    from app.llm.client import LLMClient
E   ModuleNotFoundError: No module named 'app'
____________________ ERROR collecting tests/test_service.py ____________________
ImportError while importing test module '/home/runner/work/ollama-workspace-agent/ollama-workspace-agent/tests/test_service.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_service.py:3: in <module>
    from app.service import AgentService
E   ModuleNotFoundError: No module named 'app'
=============================== warnings summary ===============================
../../../../../opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/site-packages/fastapi/testclient.py:1
  /opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
ERROR tests/test_agent_guardrails.py
ERROR tests/test_api.py
ERROR tests/test_api_client.py
ERROR tests/test_calculator.py
ERROR tests/test_code_review.py
ERROR tests/test_llm_stream.py
ERROR tests/test_service.py
!!!!!!!!!!!!!!!!!!! Interrupted: 7 errors during collection !!!!!!!!!!!!!!!!!!!!
========================= 1 warning, 7 errors in 0.55s =========================
Error: Process completed with exit code 2.