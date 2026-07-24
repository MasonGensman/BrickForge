"""
BrickForge Generation Pipeline Orchestrator

Package_043: generate_model() is the one canonical application entry
point, coordinating the complete deterministic backend built by
Packages 034-042 -- Generation Input, Generation, Optimization,
Validation, Scene Repair, and Scene Analysis -- behind a single call.
Future application layers (UI, project management, automation, and the
Package_050 Windows executable) should call this function rather than
manually sequencing individual pipeline stages.

The orchestrator introduces no new generation, optimization,
validation, repair, or analysis logic of its own. It never performs
any stage's work -- it only decides which existing function to call
next, and (for the repair loop) when to stop calling it. Every stage
remains fully responsible for its own domain, fully independent, and
fully usable on its own -- this package adds nothing to, and removes
nothing from, any of them.

GenerationInput.from_source() already performs image analysis
internally (Package_035's own design: analyze_image() runs inside it).
Obtaining a GenerationInput is therefore this pipeline's first stage in
its entirety -- there is no separate "image analysis" step to
orchestrate on top of it.

The repair loop is orchestration logic, not repair logic: it decides
WHETHER another repair_scene() call is needed and WHEN the pipeline
terminates; repair_scene() itself continues to decide HOW any given
repair is performed. Termination is based on whether the Scene itself
stopped changing, not on ValidationReport contents -- a Scene can
legitimately still carry deferred issues (e.g. overlapping_bricks, or
an orientation too far from unit length to safely normalize --
repair/scene_repair.py's own documented limits) that no further
deterministic repair will ever resolve. Those are reported honestly in
the final GenerationResult, not hidden or retried forever. A defensive
iteration cap exists purely as a safety net for a scenario current
repair rules cannot actually produce (every one is provably monotonic
-- see repair/scene_repair.py) and is never expected to be reached.

Exceptions from any stage propagate completely unchanged -- no
PipelineError, no wrapping. FileNotFoundError/ValueError from
GenerationInput.from_source() and ValueError from generate_scene() (no
usable candidates) already identify exactly what went wrong; wrapping
them would remove information, not add it.

Depends on every existing pipeline stage's already-public API
(preparation/generation_input.py, generation/generation_engine.py,
optimization/pipeline.py, validation/build_validation.py,
repair/scene_repair.py, scene_analysis/scene_analysis.py) plus
services/part_catalog.py and palette/palette_engine.py -- introduces no
new dependency on engine/render/ui internals beyond what those stages
already expose.
"""

from dataclasses import dataclass
from pathlib import Path

from brickforge.engine.scene import Scene
from brickforge.generation.candidates import GenerationConstraints
from brickforge.generation.generation_engine import generate_scene
from brickforge.optimization.pipeline import optimize_scene
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.preparation.generation_input import GenerationInput
from brickforge.preparation.image_preparation import ImagePreparationSettings
from brickforge.repair.scene_repair import repair_scene
from brickforge.scene_analysis.scene_analysis import (
    SceneAnalysisResult,
    analyze_scene,
)
from brickforge.services.part_catalog import PartCatalog
from brickforge.validation.build_validation import ValidationReport, validate_scene

#
# A defensive safety net only -- every repair rule in
# repair/scene_repair.py is provably monotonic (duplicate-id repair
# strictly reduces colliding groups; part-reference repair strictly
# removes bricks; orientation repair changes a rotation at most once,
# and a freshly-normalized quaternion always passes validation
# afterward), so normal operation never approaches this limit -- verified
# directly during planning: a Scene with two simultaneous problems
# (duplicate ids and an invalid part reference) resolved in exactly 2
# cycles. If this cap is ever reached, the loop simply stops and
# returns the current state, exactly like the ordinary "Scene stopped
# changing" termination -- a safety net must not itself become a new
# failure mode by raising.
#
_MAX_REPAIR_ITERATIONS = 10


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """
    The result of one generate_model() call. Immutable. Includes only
    what the orchestrator itself uniquely produces or owns -- not
    caller-supplied inputs the caller already has (constraints,
    catalog, palette, settings are never echoed back).

    generation_input is included specifically because the orchestrator
    builds it internally from a raw image path -- the caller has no
    other way to obtain it, and Project.generation_input/
    Project.generation_constraints (Packages 034/036) already exist to
    hold exactly this kind of data for a future project-management
    integration.

    validation_report is the FINAL report, after the repair loop
    settles -- it may still name deferred issues; that is an expected,
    honestly-reported outcome, not a failure.
    """

    scene: Scene
    generation_input: GenerationInput
    validation_report: ValidationReport
    scene_analysis: SceneAnalysisResult
    repair_iterations: int


def _scene_signature(scene: Scene):
    """
    A comparable snapshot of a Scene's content, used only to detect
    whether repair_scene() made any change -- repair_scene() always
    returns a newly constructed Scene object even when nothing
    actually changed, so object identity/equality can't be used
    directly.
    """

    return [
        (
            brick.id,
            brick.part_name,
            (brick.position.x, brick.position.y, brick.position.z),
            (
                brick.rotation.x, brick.rotation.y,
                brick.rotation.z, brick.rotation.w,
            ),
            brick.color_code,
        )
        for brick in scene
    ]


def generate_model(
    image_path: str | Path | GenerationInput,
    catalog: PartCatalog,
    palette: PaletteEngine,
    constraints: GenerationConstraints | None = None,
    settings: ImagePreparationSettings | None = None,
) -> GenerationResult:
    """
    Convert one source image into a GenerationResult, running the
    complete deterministic backend pipeline:

        GenerationInput (includes image analysis)
        -> generate_scene
        -> optimize_scene
        -> validate_scene
        -> repair_scene, repeated until the Scene stops changing
        -> analyze_scene

    image_path accepts a raw path (str/Path) OR an already-built
    GenerationInput. Package_043 deliberately accepted only a path --
    zero application callers existed then, so there was no evidence a
    pre-built GenerationInput needed to be supported, and adding it
    speculatively would have been exactly the premature flexibility
    this project avoids. Package_044's inspection found the concrete,
    evidenced need: ImagePreviewWidget already builds a complete
    GenerationInput (prepared_image and analysis both already computed)
    at import time, before generation is ever requested -- passing only
    a path would force a second, redundant load+prepare+analyze pass
    over data the caller already holds in memory. When image_path is
    already a GenerationInput, `settings` is ignored (the input has
    already been prepared with whatever settings were used to build
    it) and no reload occurs at all.

    Deterministic: given identical (image_path, catalog, palette,
    constraints, settings), always returns an identical GenerationResult
    -- every stage this function calls is independently deterministic,
    and this function's own added logic (the repair-loop termination
    check) introduces no randomness or unordered iteration.

    Raises FileNotFoundError/ValueError unchanged from
    GenerationInput.from_source() (bad image path/format), and
    ValueError unchanged from generate_scene() (no usable candidates)
    -- never wrapped.
    """

    generation_input = (
        image_path
        if isinstance(image_path, GenerationInput)
        else GenerationInput.from_source(image_path, settings)
    )

    scene = generate_scene(generation_input, catalog, palette, constraints)
    scene = optimize_scene(scene, catalog, constraints)

    report = validate_scene(scene, catalog)

    iterations = 0

    while iterations < _MAX_REPAIR_ITERATIONS:

        repaired = repair_scene(scene, report)

        if _scene_signature(repaired) == _scene_signature(scene):
            break

        scene = repaired
        iterations += 1
        report = validate_scene(scene, catalog)

    scene_analysis = analyze_scene(scene, catalog)

    return GenerationResult(
        scene=scene,
        generation_input=generation_input,
        validation_report=report,
        scene_analysis=scene_analysis,
        repair_iterations=iterations,
    )
