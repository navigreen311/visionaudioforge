"""The names the console sends, checked against the server that receives them.

Both sides of the audio augmentation feature were tested and both suites passed
while the feature did not work at all. ``tests/test_audio_augmentation.py`` calls
``apply_pipeline`` with ``{"type": "noise"}``, which is the vocabulary the
service defines; the console sent ``{"type": "white_noise"}`` from one panel and
``{"type": "freq_mask"}`` from another. Nothing exercised the join, so nothing
failed.

The defect is not in either component. It is in the agreement between them, and
an agreement can only be tested from a place that can see both. So this reads the
console's own source for the step names and parameter keys it can emit, and runs
each one through the real augmenter against a real waveform.

That makes the failure mode loud in the right direction: add a control to the
console with a name the server does not accept and this test fails, naming the
control, before anyone ships a panel whose buttons do nothing.
"""

from __future__ import annotations

import pathlib
import re

import numpy as np
import pytest

from app.services.audio.augmentation import AudioAugmenter

CONSOLE = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src"

BUILDER = CONSOLE / "components" / "audio" / "AugmentationBuilder.tsx"
AUDIO_PAGE = CONSOLE / "app" / "(dashboard)" / "audio" / "page.tsx"

pytestmark = pytest.mark.skipif(
    not BUILDER.exists(), reason="console source not present in this checkout"
)


# ---------------------------------------------------------------------------
# Reading the console
# ---------------------------------------------------------------------------


def _builder_steps() -> list[tuple[str, list[str], str]]:  # noqa: D401
    """(type, param keys, source label) for each control in AugmentationBuilder.

    The panel declares its controls as a literal array of
    ``{ type, label, params: [{ key, ... }] }``, so the names and the parameter
    keys are both recoverable without executing anything.
    """
    text = BUILDER.read_text(encoding="utf-8")
    block = text[text.index("const AUGMENTATION_TYPES"):]
    block = block[: block.index("] as const;")]

    steps = []
    for chunk in re.split(r"\n  \{", block)[1:]:
        type_match = re.search(r'type:\s*"([^"]+)"', chunk)
        if not type_match:
            continue
        keys = re.findall(r'key:\s*"([^"]+)"', chunk)
        steps.append((type_match.group(1), keys, "AugmentationBuilder"))
    return steps


def _studio_steps() -> list[tuple[str, list[str], str]]:
    """(type, param keys, source label) for each push in handleStudioAugment.

    ``AugmentationStudio`` hands its config to the page, which turns it into
    steps with literal ``steps.push({ type: "...", params: { key: ... } })``
    calls - so the emitted shape is likewise readable from source.
    """
    text = AUDIO_PAGE.read_text(encoding="utf-8")

    steps = []
    for match in re.finditer(
        r'steps\.push\(\{\s*type:\s*"([^"]+)",\s*params:\s*\{([^}]*)\}', text
    ):
        keys = re.findall(r"(\w+):", match.group(2))
        steps.append((match.group(1), keys, "AugmentationStudio"))
    return steps


def _console_steps() -> list[tuple[str, list[str], str]]:
    """Every step either panel can emit, or [] when the console is not checked out.

    This runs at import time to build the parametrize list, which is *before*
    the module-level skipif is consulted. Raising here would abort collection
    for the whole suite rather than skipping one module - the same failure that
    once stopped 1398 tests from running at all. So a missing console is an
    empty list, and `test_the_console_source_was_actually_read` below turns an
    unexpected empty list back into a failure when the files are present.
    """
    if not (BUILDER.exists() and AUDIO_PAGE.exists()):
        return []
    return _builder_steps() + _studio_steps()


def _tone(seconds: float = 0.5, sr: int = 16_000) -> tuple[np.ndarray, int]:
    """Half a second of A440. Long enough for an STFT, short enough to be fast."""
    t = np.linspace(0.0, seconds, int(sr * seconds), endpoint=False, dtype=np.float32)
    return (0.5 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32), sr


def _defaults_for(keys: list[str]) -> dict[str, object]:
    """A plausible value per parameter key the console can send.

    Values matter less than types here - the point is that the keyword is
    accepted and the call returns audio, not that a particular SNR was chosen.
    """
    table: dict[str, object] = {
        "noise_type": "white",
        "snr_db": 20.0,
        "snr": 20.0,
        "amplitude": 0.2,
        "rate": 1.1,
        "semitones": 2.0,
        "n_steps": 2.0,
        "steps": 2.0,
        "shift_ms": 100.0,
        "shift_pct": 10.0,
        "shift_s": 0.1,
        "num_masks": 1,
        "mask_size": 8,
        "mask_size_pct": 10.0,
        "mask_width": 8,
        "axis": "frequency",
    }
    missing = [k for k in keys if k not in table]
    assert not missing, (
        f"the console emits parameter(s) {missing} that this test has no value for - "
        "add them here and to AudioAugmenter._normalise_params"
    )
    return {k: table[k] for k in keys}


CONSOLE_STEPS = _console_steps()
STEP_IDS = [f"{source}:{name}" for name, _, source in CONSOLE_STEPS]


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------


def test_the_console_source_was_actually_read():
    """Zero parametrized cases is a passing suite that checked nothing.

    If the panels are on disk they must yield steps; a parser that silently
    stops matching would otherwise turn this whole module green and blind.
    """
    assert CONSOLE_STEPS, (
        "the console source is present but no augmentation steps were parsed "
        "from it - AugmentationBuilder or handleStudioAugment has been "
        "restructured and the parsers here need updating"
    )
    sources = {source for _, _, source in CONSOLE_STEPS}
    assert sources == {"AugmentationBuilder", "AugmentationStudio"}, (
        f"only parsed steps from {sources}"
    )


@pytest.mark.parametrize("name,keys,source", CONSOLE_STEPS, ids=STEP_IDS)
def test_the_server_accepts_every_step_the_console_can_send(name, keys, source):
    """Each control in each panel, run end to end through the real augmenter.

    Six of these raised ValueError and three more raised TypeError before the
    alias table existed - which is to say most of two panels did nothing.
    """
    audio, sr = _tone()
    augmenter = AudioAugmenter()

    step = {"type": name, "params": _defaults_for(keys)}
    result, applied = augmenter.apply_pipeline(audio, sr, [step])

    assert applied, f"{source} step {name!r} was accepted but did not run"
    assert applied[0]["requested"] == name
    assert isinstance(result, np.ndarray) and result.size > 0
    assert np.isfinite(result).all(), f"{name!r} produced NaN or inf"


def test_a_step_the_server_does_not_know_is_a_400_not_a_500():
    """The unknown-name path names what it knows, so the next drift is legible."""
    audio, sr = _tone()

    with pytest.raises(ValueError) as excinfo:
        AudioAugmenter().apply_pipeline(audio, sr, [{"type": "reticulate", "params": {}}])

    message = str(excinfo.value)
    assert "reticulate" in message
    assert "white_noise" in message, "the error should list the names that do work"


def test_an_unknown_name_fails_even_when_the_probability_gate_would_skip_it():
    """Resolution happens before the dice roll.

    A pipeline that rejects a typo only some of the time is worse than one that
    always does: the bug reproduces on a customer's machine and not on yours.
    """
    audio, sr = _tone()
    step = {"type": "reticulate", "probability": 0.0, "params": {}}

    for _ in range(10):
        with pytest.raises(ValueError):
            AudioAugmenter().apply_pipeline(audio, sr, [step])


def test_every_alias_resolves_to_a_method_that_exists():
    """The table cannot name a dispatch target the class does not have."""
    augmenter = AudioAugmenter()
    for alias, (op, _) in AudioAugmenter._ALIASES.items():
        target = {"noise": "add_noise", "stretch": "time_stretch", "pitch": "pitch_shift",
                  "shift": "time_shift", "spec_mask": "spec_mask"}.get(op)
        assert target, f"alias {alias!r} resolves to unknown operation {op!r}"
        assert callable(getattr(augmenter, target)), f"{target} is not callable"


# ---------------------------------------------------------------------------
# Behaviour of the parameter translations
# ---------------------------------------------------------------------------


def test_amplitude_becomes_a_quieter_signal_as_it_rises():
    """The studio's pink-noise slider has to move something in the right direction.

    Accepting the keyword is not enough - a control that is accepted and ignored
    is the same defect wearing a 200.
    """
    audio, sr = _tone()
    augmenter = AudioAugmenter()

    def noise_energy(amplitude: float) -> float:
        out, _ = augmenter.apply_pipeline(
            audio, sr, [{"type": "pink_noise", "params": {"amplitude": amplitude}}]
        )
        return float(np.mean((out - audio) ** 2))

    assert noise_energy(0.5) > noise_energy(0.05) * 10, (
        "raising the amplitude did not add meaningfully more noise"
    )


def test_a_shift_given_as_a_percentage_scales_with_the_clip():
    """`shift_pct` only means milliseconds once the clip length is known."""
    augmenter = AudioAugmenter()
    short, sr = _tone(seconds=0.5)
    long, _ = _tone(seconds=1.0)

    _, short_applied = augmenter.apply_pipeline(
        short, sr, [{"type": "time_shift", "params": {"shift_pct": 10.0}}]
    )
    _, long_applied = augmenter.apply_pipeline(
        long, sr, [{"type": "time_shift", "params": {"shift_pct": 10.0}}]
    )

    assert short_applied[0]["params"]["shift_ms"] == pytest.approx(50.0, abs=1.0)
    assert long_applied[0]["params"]["shift_ms"] == pytest.approx(100.0, abs=1.0)


def test_semitones_and_n_steps_are_the_same_request():
    """The console said semitones, the method said n_steps, and nothing bridged."""
    audio, sr = _tone()
    augmenter = AudioAugmenter()

    by_alias, _ = augmenter.apply_pipeline(
        audio, sr, [{"type": "pitch_shift", "params": {"semitones": 3}}]
    )
    by_keyword, _ = augmenter.apply_pipeline(
        audio, sr, [{"type": "pitch", "params": {"n_steps": 3}}]
    )

    assert np.allclose(by_alias, by_keyword), (
        "the alias and the keyword produced different audio"
    )


def test_spectral_masking_returns_audio_not_a_spectrogram():
    """`freq_mask` was rejected because the only masker spoke spectrograms.

    The endpoint's contract is audio in, audio out, so the bridge has to survive
    the round trip and come back the same length.
    """
    audio, sr = _tone()
    augmenter = AudioAugmenter()

    for name in ("freq_mask", "frequency_mask", "time_mask"):
        out, _ = augmenter.apply_pipeline(
            audio, sr, [{"type": name, "params": {"num_masks": 2, "mask_size_pct": 20}}]
        )
        assert out.ndim == 1, f"{name} returned a {out.ndim}-D array"
        assert len(out) == len(audio), f"{name} changed the clip length"
        assert not np.allclose(out, audio), f"{name} was a no-op"


def test_a_bad_keyword_says_which_step_and_which_keyword():
    """A TypeError from deep in librosa is not an answer anyone can act on."""
    audio, sr = _tone()

    with pytest.raises(ValueError) as excinfo:
        AudioAugmenter().apply_pipeline(
            audio, sr, [{"type": "time_stretch", "params": {"tempo": 1.5}}]
        )

    message = str(excinfo.value)
    assert "time_stretch" in message
    assert "tempo" in message
