"""Model-agnostic contracts for the ML layer.

These are intentionally minimal. They exist to establish stable interfaces
that the original SysDaG codebase (arriving separately) can be adapted to,
without dictating any implementation detail: dataset format, preprocessing,
model architecture, training loop, or metrics are all undecided.

Do NOT add framework-specific logic here until the original codebase has
been audited (see ml/TODO.md, Phase A).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator


class DatasetInterface(ABC):
    """Produces model-ready samples.

    Concrete implementations will wrap whatever dataset/loading code the
    original codebase provides (e.g. a PTB-XL/WFDB pipeline). This
    interface makes no assumption about file formats, preprocessing, label
    encoding, or how splits are stored.
    """

    @abstractmethod
    def __len__(self) -> int:
        ...

    @abstractmethod
    def __getitem__(self, index: int) -> Any:
        """Return a single model-ready sample."""

    @abstractmethod
    def split(self, name: str) -> "DatasetInterface":
        """Return the subset for a named split (e.g. 'train'/'val'/'test').

        Split semantics (patient-level vs. record-level) are defined by the
        original codebase and must be preserved, not reinvented here.
        """


class ModelInterface(ABC):
    """Accepts standardized input and produces output.

    No architecture is assumed. Concrete models are a decision for after
    the original codebase audit.
    """

    @abstractmethod
    def forward(self, inputs: Any) -> Any:
        ...

    @abstractmethod
    def parameters(self) -> Iterator[Any]:
        """Expose trainable parameters, whatever the underlying framework."""


class TrainerInterface(ABC):
    """Trains a model using a dataset.

    No optimizer, loss function, or training loop is assumed.
    """

    @abstractmethod
    def fit(
        self, model: ModelInterface, dataset: DatasetInterface, **kwargs: Any
    ) -> Any:
        """Train `model` on `dataset`.

        Return value is implementation-defined (e.g. a history object, final
        checkpoint path, etc.) until the original training code is audited.
        """


class EvaluatorInterface(ABC):
    """Evaluates predictions/results.

    No metric set is assumed. The original codebase's ECG evaluation
    infrastructure must be audited before choosing concrete metrics here.
    """

    @abstractmethod
    def evaluate(
        self, model: ModelInterface, dataset: DatasetInterface, **kwargs: Any
    ) -> dict:
        """Return a dict of metric name -> value."""
