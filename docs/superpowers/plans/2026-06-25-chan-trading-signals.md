# Chan Trading Signals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Chan-theory trading signal module with CLI and local Web UI that returns buy/sell/hold actions with reasons, invalidation levels, and data degradation status.

**Architecture:** Add focused Python modules under `src/astockdata`: K-line models and data providers, Chan structure rules, signal generation, CLI rendering, and a standard-library local HTTP server. The Web UI calls the same core signal engine as CLI so business logic stays single-source.

**Tech Stack:** Python 3.9 standard library, `requests`, existing `unittest` test suite, simple HTML/CSS/JavaScript served by `http.server`.

---

## File Structure

- Create `src/astockdata/kline.py`: unified `KLine` model, HTTP daily provider, optional mootdx provider wrapper.
- Create `src/astockdata/chan.py`: K-line inclusion merge, fractals, strokes, trend and divergence approximation.
- Create `src/astockdata/signals.py`: position model, signal model, signal generation and action mapping.
- Create `src/astockdata/chan_cli.py`: command-line interface for single stock and CSV portfolio.
- Create `src/astockdata/web.py`: local HTTP server and JSON API.
- Create `src/astockdata/web_static.py`: embedded local Web UI HTML.
- Create tests: `tests/test_kline.py`, `tests/test_chan.py`, `tests/test_signals.py`, `tests/test_chan_cli.py`, `tests/test_web.py`.
- Modify `docs/local-analysis.md`: document Chan CLI and local Web UI startup.

## Task 1: K-Line Model And HTTP Daily Provider

**Files:**
- Create: `src/astockdata/kline.py`
- Test: `tests/test_kline.py`

- [ ] **Step 1: Write failing tests**

```python
import unittest

from astockdata.kline import KLine, parse_baidu_kline_response


class KLineTests(unittest.TestCase):
    def test_parse_baidu_kline_response_maps_rows_to_klines(self):
        payload = {
            "Result": {
                "newMarketData": {
                    "keys": ["time", "open", "close", "high", "low", "volume", "amount"],
                    "marketData": "20260620,10,11,12,9,100,1000;20260621,11,12,13,10,120,1500",
                }
            }
        }
        rows = parse_baidu_kline_response("600519", "1d", payload)
        assert rows == [
            KLine("600519", "1d", "20260620", 10.0, 12.0, 9.0, 11.0, 100.0, 1000.0),
            KLine("600519", "1d", "20260621", 11.0, 13.0, 10.0, 12.0, 120.0, 1500.0),
        ]

    def test_parse_baidu_kline_response_ignores_short_rows(self):
        payload = {
            "Result": {
                "newMarketData": {
                    "keys": ["time", "open", "close", "high", "low", "volume", "amount"],
                    "marketData": "bad,row;20260621,11,12,13,10,120,1500",
                }
            }
        }
        assert [row.timestamp for row in parse_baidu_kline_response("600519", "1d", payload)] == ["20260621"]
```

- [ ] **Step 2: Verify tests fail**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_kline -v`

Expected: FAIL because `astockdata.kline` does not exist.

- [ ] **Step 3: Implement minimal code**

Create `KLine`, `parse_baidu_kline_response`, and `BaiduDailyKLineProvider.daily_klines(code)`.

- [ ] **Step 4: Verify tests pass**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_kline -v`

Expected: PASS.

## Task 2: Chan Structure Rules

**Files:**
- Create: `src/astockdata/chan.py`
- Test: `tests/test_chan.py`

- [ ] **Step 1: Write failing tests**

Tests cover inclusion merge, top/bottom fractals, stroke approximation, trend classification, and divergence approximation using deterministic K-lines.

- [ ] **Step 2: Verify tests fail**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_chan -v`

Expected: FAIL because `astockdata.chan` does not exist.

- [ ] **Step 3: Implement minimal code**

Create `MergedKLine`, `Fractal`, `Stroke`, `ChanStructure`, `merge_inclusions`, `detect_fractals`, `build_strokes`, `classify_trend`, and `analyze_structure`.

- [ ] **Step 4: Verify tests pass**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_chan -v`

Expected: PASS.

## Task 3: Signal Engine

**Files:**
- Create: `src/astockdata/signals.py`
- Test: `tests/test_signals.py`

- [ ] **Step 1: Write failing tests**

Tests cover action mapping, no-30m degradation, position-aware sell/hold behavior, and JSON-safe output.

- [ ] **Step 2: Verify tests fail**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_signals -v`

Expected: FAIL because `astockdata.signals` does not exist.

- [ ] **Step 3: Implement minimal code**

Create `Position`, `ChanSignal`, `ChanSignalEngine`, and `map_signal_to_action`.

- [ ] **Step 4: Verify tests pass**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_signals -v`

Expected: PASS.

## Task 4: Chan CLI

**Files:**
- Create: `src/astockdata/chan_cli.py`
- Test: `tests/test_chan_cli.py`

- [ ] **Step 1: Write failing tests**

Tests cover table rendering, JSON rendering, portfolio CSV parsing, and invalid portfolio rows.

- [ ] **Step 2: Verify tests fail**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_chan_cli -v`

Expected: FAIL because `astockdata.chan_cli` does not exist.

- [ ] **Step 3: Implement minimal code**

Create parser, renderers, CSV loader, and CLI `main`.

- [ ] **Step 4: Verify tests pass**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_chan_cli -v`

Expected: PASS.

## Task 5: Local Web API And UI

**Files:**
- Create: `src/astockdata/web.py`
- Create: `src/astockdata/web_static.py`
- Test: `tests/test_web.py`

- [ ] **Step 1: Write failing tests**

Tests cover `/api/health`, `/api/analyze`, `/api/analyze-portfolio`, missing code validation, and serving `/`.

- [ ] **Step 2: Verify tests fail**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v`

Expected: FAIL because `astockdata.web` does not exist.

- [ ] **Step 3: Implement minimal code**

Create a standard-library `HTTPServer` app with injectable analyzer for tests and embedded HTML UI.

- [ ] **Step 4: Verify tests pass**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v`

Expected: PASS.

## Task 6: Documentation And Smoke Tests

**Files:**
- Modify: `docs/local-analysis.md`

- [ ] **Step 1: Update docs**

Add commands:

```bash
PYTHONPATH=src python -m astockdata.chan_cli 688017 --cost 120.5 --position 0.3
PYTHONPATH=src python -m astockdata.chan_cli --portfolio portfolio.csv
PYTHONPATH=src python -m astockdata.web --port 8010
```

- [ ] **Step 2: Run full unit tests**

Run: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`

Expected: PASS.

- [ ] **Step 3: Run CLI smoke test**

Run: `PYTHONPATH=src .venv/bin/python -m astockdata.chan_cli 600519 --json`

Expected: JSON signal output. If external K-line source is unavailable, command should return a clear error instead of a traceback.

- [ ] **Step 4: Run Web health smoke test**

Run the local server and call `/api/health`.

Expected: JSON status response.

