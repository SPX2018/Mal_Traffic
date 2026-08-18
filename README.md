# Mal_Traffic Multi-Agent Workflow

This document records the entry scripts for the LangGraph multi-agent traffic analysis workflow in this repository.

## Workflow Overview

The project has two main multi-agent workflows:

```text
Training workflow:
  train.py
    -> Trainer.py
    -> EngineerAgent + AuditorAgent + ObserverAgent

Detection workflow:
  batch_runner_pro.py
    -> watch_one_dir.py
    -> detect.py
    -> Mal_Traffic_Detection.py
    -> EngineerAgent + AuditorAgent + AnalystAgent + ObserverAgent
```

## Training Entry

Use:

```bash
python train.py
```

Main files:

- `train.py`: batch training driver.
- `Trainer.py`: defines the training LangGraph workflow.
- `agent/EngineerAgent.py`: engineer agent.
- `agent/AuditorAgent.py`: auditor agent.
- `agent/ObserverAgent.py`: observer agent.

The training data path is currently hard-coded in `train.py`:

```python
folder_path = './dataset/cic-ids-2017/train_mask_payload'
```

The progress files are:

```text
memory/success_cic-ids-2017-mask-payload.txt
memory/fail_cic-ids-2017-mask-payload.txt
```

If you change the training dataset, update `folder_path` and the corresponding success/fail file paths in `train.py`.

## Single-File Detection Test

Use:

```bash
python test.py
```

Main files:

- `test.py`: quick single-file test script.
- `Mal_Traffic_Detection.py`: defines the detection LangGraph workflow.

The tested PCAP file is currently hard-coded in `test.py`:

```python
fileName = './dataset/USTC-TFC2016-test_dataset/Cridex/group_003.pcap'
```

Change `fileName` when you want to test another PCAP.

## Single-Directory Detection

Use:

```bash
python watch_one_dir.py <INPUT_DIR> <OUTPUT_DIR>
```

Example:

```bash
python watch_one_dir.py \
  ./dataset/ids2019/test_dataset/benign1 \
  ./report/ids2019/test_dataset/benign1
```

Main files:

- `watch_one_dir.py`: monitors one input directory and reruns detection until the number of JSON reports matches the number of PCAP files.
- `detect.py`: contains `detect(input_dir, output_dir)`, which invokes the multi-agent detector for each PCAP.
- `Mal_Traffic_Detection.py`: builds the detection graph.

`watch_one_dir.py` defaults:

```python
DETECT_SCRIPT = "detect.py"
DETECT_FUNC = "detect"
IN_PATTERN = "*.pcap"
OUT_PATTERN = "*.json"
```

Useful environment variables:

```bash
MAX_RETRIES=3 python watch_one_dir.py <INPUT_DIR> <OUTPUT_DIR>
STAGNANT_LIMIT=10 python watch_one_dir.py <INPUT_DIR> <OUTPUT_DIR>
RECURSIVE=1 python watch_one_dir.py <INPUT_DIR> <OUTPUT_DIR>
```

## Main Test Entry

Your current full test workflow starts from:

```bash
python batch_runner_pro.py
```

Current configuration in `batch_runner_pro.py`:

```python
WORKER_SCRIPT = "watch_one_dir.py"
INPUT_ROOT = "./dataset/USTC-TFC2016/test_simple_mask_payload"
OUTPUT_ROOT = "./report/USTC-TFC2016/test_simple_mask_payload"
MAX_WORKERS = 10
```

`batch_runner_pro.py` scans each first-level category directory under `INPUT_ROOT`, creates the matching category directory under `OUTPUT_ROOT`, and launches:

```text
python watch_one_dir.py <category_input_dir> <category_output_dir>
```

Each category writes its own log:

```text
<category_output_dir>/process_run.log
```

To test another dataset, edit these three values in `batch_runner_pro.py`:

```python
INPUT_ROOT = "<your_dataset_root>"
OUTPUT_ROOT = "<your_report_root>"
MAX_WORKERS = 10
```

For example, to run IDS2019 through the same test entry, set:

```python
WORKER_SCRIPT = "watch_one_dir.py"
INPUT_ROOT = "./dataset/ids2019/test_dataset"
OUTPUT_ROOT = "./report/ids2019/test_dataset"
MAX_WORKERS = 10
```

`batch_run_detect.py` is an older alternate batch launcher for IDS2019. Prefer `batch_runner_pro.py` for the current test flow.

## Result Files

Detection reports are written as JSON files under the selected report directory.

For example:

```text
report/USTC-TFC2016/test_simple_mask_payload/<category>/<pcap_name>.json
report/USTC-TFC2016/test_simple_mask_payload/<category>/fail.txt
report/USTC-TFC2016/test_simple_mask_payload/<category>/process_run.log
```

`fail.txt` records PCAP files for which no report was generated.

## Evaluation Helper

`evaluate.py` is a simple report parser for checking classification results in a report directory. Its input path is currently hard-coded:

```python
dir_path = "./report/benign"
```

Update `dir_path` before using it on another report folder.

Run:

```bash
python evaluate.py
```

## Important Notes

- Several scripts contain hard-coded API keys and dataset paths. Before sharing the repository, move API keys into environment variables and remove secrets from source files.
- `train.py` is the training entry.
- `batch_runner_pro.py` is the current full test entry.
- `test.py` is only for quick single-PCAP debugging.
- `watch_one_dir.py` and `detect.py` are called by the batch test flow.
- `Trainer.py` and `Mal_Traffic_Detection.py` define the actual LangGraph workflows.
- `main.py` is only a small JSON parsing/debug example and is not the main training or detection entry.
- `run_multi.py` is a generic concurrent command runner. It is not specific to the multi-agent traffic detector.

## Quick Reference

```text
Train:
  python train.py

Debug one PCAP:
  python test.py

Detect one directory:
  python watch_one_dir.py <INPUT_DIR> <OUTPUT_DIR>

Run the current full test flow:
  python batch_runner_pro.py

Evaluate reports:
  python evaluate.py
```
