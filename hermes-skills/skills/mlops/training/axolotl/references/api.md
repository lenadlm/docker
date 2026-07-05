# Axolotl - Api

**Pages:** 150

---

## cli.cloud.modal_

**URL:** https://docs.axolotl.ai/docs/api/cli.cloud.modal_.html

**Contents:**
- cli.cloud.modal_
- Classes
  - ModalCloud
- Functions
  - run_cmd

Modal Cloud support from CLI

Modal Cloud implementation.

Run a command inside a folder, with Modal Volume reloading before and commit on success.

**Examples:**

Example 1 (python):
```python
cli.cloud.modal_.ModalCloud(config, app=None)
```

Example 2 (python):
```python
cli.cloud.modal_.run_cmd(cmd, run_folder, volumes=None)
```

---

## core.trainers.base

**URL:** https://docs.axolotl.ai/docs/api/core.trainers.base.html

**Contents:**
- core.trainers.base
- Classes
  - AxolotlTrainer
    - Methods
      - log
        - Parameters
      - push_to_hub
      - store_metrics
        - Parameters

Module for customized trainers

Extend the base Trainer for axolotl helpers

Log logs on the various objects watching training, including stored metrics.

Overwrite the push_to_hub method in order to force-add the tags when pushing the model on the Hub. Please refer to ~transformers.Trainer.push_to_hub for more details.

Store metrics with specified reduction type.

**Examples:**

Example 1 (python):
```python
core.trainers.base.AxolotlTrainer(
    *_args,
    bench_data_collator=None,
    eval_data_collator=None,
    dataset_tags=None,
    **kwargs,
)
```

Example 2 (python):
```python
core.trainers.base.AxolotlTrainer.log(logs, start_time=None)
```

Example 3 (python):
```python
core.trainers.base.AxolotlTrainer.push_to_hub(*args, **kwargs)
```

Example 4 (python):
```python
core.trainers.base.AxolotlTrainer.store_metrics(
    metrics,
    train_eval='train',
    reduction='mean',
)
```

---

## prompt_strategies.input_output

**URL:** https://docs.axolotl.ai/docs/api/prompt_strategies.input_output.html

**Contents:**
- prompt_strategies.input_output
- Classes
  - RawInputOutputPrompter
  - RawInputOutputStrategy

prompt_strategies.input_output

Module for plain input/output prompt pairs

prompter for raw i/o data

Prompt Strategy class for input/output pairs

**Examples:**

Example 1 (python):
```python
prompt_strategies.input_output.RawInputOutputPrompter()
```

Example 2 (python):
```python
prompt_strategies.input_output.RawInputOutputStrategy(
    *args,
    eos_token=None,
    **kwargs,
)
```

---

## prompt_strategies.completion

**URL:** https://docs.axolotl.ai/docs/api/prompt_strategies.completion.html

**Contents:**
- prompt_strategies.completion
- Classes
  - CompletionPromptTokenizingStrategy
  - CompletionPrompter

prompt_strategies.completion

Basic completion text

Tokenizing strategy for Completion prompts.

Prompter for completion

**Examples:**

Example 1 (python):
```python
prompt_strategies.completion.CompletionPromptTokenizingStrategy(
    *args,
    max_length=None,
    **kwargs,
)
```

Example 2 (python):
```python
prompt_strategies.completion.CompletionPrompter()
```

---

## utils.collators.core

**URL:** https://docs.axolotl.ai/docs/api/utils.collators.core.html

**Contents:**
- utils.collators.core

basic shared collator constants

---

## monkeypatch.data.batch_dataset_fetcher

**URL:** https://docs.axolotl.ai/docs/api/monkeypatch.data.batch_dataset_fetcher.html

**Contents:**
- monkeypatch.data.batch_dataset_fetcher
- Functions
  - apply_multipack_dataloader_patch
  - patch_fetchers
  - patched_worker_loop
  - remove_multipack_dataloader_patch

monkeypatch.data.batch_dataset_fetcher

Monkey patches for the dataset fetcher to handle batches of packed indexes.

This patch allows DataLoader to correctly process batches that contain multiple bins of packed sequences.

Apply patches to PyTorch’s DataLoader components.

Worker loop that ensures patches are applied in worker processes.

Remove the monkeypatch and restore original PyTorch DataLoader behavior.

**Examples:**

Example 1 (python):
```python
monkeypatch.data.batch_dataset_fetcher.apply_multipack_dataloader_patch()
```

Example 2 (python):
```python
monkeypatch.data.batch_dataset_fetcher.patch_fetchers()
```

Example 3 (python):
```python
monkeypatch.data.batch_dataset_fetcher.patched_worker_loop(*args, **kwargs)
```

Example 4 (python):
```python
monkeypatch.data.batch_dataset_fetcher.remove_multipack_dataloader_patch()
```

---

## core.datasets.chat

**URL:** https://docs.axolotl.ai/docs/api/core.datasets.chat.html

**Contents:**
- core.datasets.chat
- Classes
  - TokenizedChatDataset

Tokenized chat dataset

**Examples:**

Example 1 (python):
```python
core.datasets.chat.TokenizedChatDataset(
    data,
    model_transform,
    *args,
    message_transform=None,
    formatter=None,
    process_count=None,
    keep_in_memory=False,
    **kwargs,
)
```

---

## utils.freeze

**URL:** https://docs.axolotl.ai/docs/api/utils.freeze.html

**Contents:**
- utils.freeze
- Classes
  - LayerNamePattern
    - Methods
      - match
- Functions
  - freeze_layers_except

module to freeze/unfreeze parameters by name

Represents a regex pattern for layer names, potentially including a parameter index range.

Checks if the given layer name matches the regex pattern.

Parameters: - name (str): The layer name to check.

Returns: - bool: True if the layer name matches the pattern, False otherwise.

Freezes all layers of the given model except for the layers that match given regex patterns. Periods in the patterns are treated as literal periods, not as wildcard characters.

Parameters: - model (nn.Module): The PyTorch model to be modified. - regex_patterns (list of str): List of regex patterns to match layer names to keep unfrozen. Note that you cannot use a dot as a wildcard character in the patterns since it is reserved for separating layer names. Also, to match the entire layer name, the pattern should start with “^” and end with “\(", otherwise it will match any part of the layer name. The range pattern part is optional and it is not compiled as a regex pattern which means you must put "\)” before the range pattern if you want to match the entire layer name. E.g., [“^model.embed_tokens.weight\([:32000]", "layers.2[0-9]+.block_sparse_moe.gate.[a-z]+\)”]

Returns: None; the model is modified in place.

**Examples:**

Example 1 (python):
```python
utils.freeze.LayerNamePattern(pattern)
```

Example 2 (python):
```python
utils.freeze.LayerNamePattern.match(name)
```

Example 3 (python):
```python
utils.freeze.freeze_layers_except(model, regex_patterns)
```

---

## monkeypatch.unsloth_

**URL:** https://docs.axolotl.ai/docs/api/monkeypatch.unsloth_.html

**Contents:**
- monkeypatch.unsloth_

module for patching with unsloth optimizations

---

## utils.schemas.datasets

**URL:** https://docs.axolotl.ai/docs/api/utils.schemas.datasets.html

**Contents:**
- utils.schemas.datasets
- Classes
  - DPODataset
  - KTODataset
  - PretrainingDataset
  - SFTDataset
    - Methods
      - handle_legacy_message_fields
  - StepwiseSupervisedDataset
  - UserDefinedDPOType

utils.schemas.datasets

Pydantic models for datasets-related configuration

DPO configuration subset

KTO configuration subset

Pretraining dataset configuration subset

SFT configuration subset

Handle backwards compatibility between legacy message field mapping and new property mapping system.

Stepwise supervised dataset configuration subset

User defined typing for DPO

User defined typing for KTO

Structure for user defined prompt types

**Examples:**

Example 1 (python):
```python
utils.schemas.datasets.DPODataset()
```

Example 2 (python):
```python
utils.schemas.datasets.KTODataset()
```

Example 3 (python):
```python
utils.schemas.datasets.PretrainingDataset()
```

Example 4 (python):
```python
utils.schemas.datasets.SFTDataset()
```

---

## core.chat.format.llama3x

**URL:** https://docs.axolotl.ai/docs/api/core.chat.format.llama3x.html

**Contents:**
- core.chat.format.llama3x

core.chat.format.llama3x

Llama 3.x chat formatting functions for MessageContents

---

## datasets

**URL:** https://docs.axolotl.ai/docs/api/datasets.html

**Contents:**
- datasets
- Classes
  - TokenizedPromptDataset
    - Parameters

Module containing dataset functionality.

We want this to be a wrapper for an existing dataset that we have loaded. Lets use the concept of middlewares to wrap each dataset. We’ll use the collators later on to pad the datasets.

Dataset that returns tokenized prompts from a stream of text files.

**Examples:**

Example 1 (python):
```python
datasets.TokenizedPromptDataset(
    prompt_tokenizer,
    dataset,
    process_count=None,
    keep_in_memory=False,
    **kwargs,
)
```

---

## prompt_strategies.bradley_terry.llama3

**URL:** https://docs.axolotl.ai/docs/api/prompt_strategies.bradley_terry.llama3.html

**Contents:**
- prompt_strategies.bradley_terry.llama3
- Functions
  - icr

prompt_strategies.bradley_terry.llama3

chatml transforms for datasets with system, input, chosen, rejected to match llama3 chat template

chatml transforms for datasets with system, input, chosen, rejected ex. https://huggingface.co/datasets/argilla/distilabel-intel-orca-dpo-pairs

**Examples:**

Example 1 (python):
```python
prompt_strategies.bradley_terry.llama3.icr(cfg, **kwargs)
```

---

## common.datasets