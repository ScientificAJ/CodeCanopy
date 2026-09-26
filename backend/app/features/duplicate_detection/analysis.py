"""Cached duplicate and potentially-unused analysis for immutable snapshots."""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from difflib import SequenceMatcher
from functools import lru_cache

from app.features.duplicate_detection import (
    AnalysisCoverage,
    DuplicateCandidate,
    DuplicateDetectionResult,
    FunctionEvidence,
    PotentiallyUnusedFunction,
    UnusedDetectionResult,
)
from app.features.duplicate_detection.provider import SemanticSimilarityProvider, configured_provider
from app.models.codebase import Function, Relationship
from app.services.snapshot_service import get_inventory, get_syntax_records, read_source_lines

MAX_CANDIDATES = 80
MAX_PAIR_COMPARISONS = 10000
MAX_SEMANTIC_PAIRS = 8
_STOP_NAME_WORDS = {'are', 'check', 'ensure', 'find', 'get', 'has', 'is', 'make', 'test', 'valid', 'validate', 'verify'}
_semantic_cache: dict[tuple[str, str, tuple[str, ...]], list[float]] = {}


def _stable_id(*parts: str) -> str:
    return hashlib.sha256(':'.join(parts).encode('utf-8')).hexdigest()[:32]


def _name_key(name: str) -> str:
    words = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name).casefold().split('_')
    return '_'.join(word for word in words if word and word not in _STOP_NAME_WORDS)


def _evidence(function: Function, file_id: str) -> FunctionEvidence:
    return FunctionEvidence(
        id=_stable_id(file_id, function.name, str(function.line_start)),
        name=function.name,
        file_id=file_id,
        path=function.file,
        line_start=function.line_start,
        line_end=function.line_end,
    )


@lru_cache(maxsize=24)
def _static_analysis(snapshot_id: str):
    inventory = get_inventory(snapshot_id, limit=10000).files
    syntax = get_syntax_records(snapshot_id)
    records = [
        (file_id, function)
        for file_id, parsed_file in syntax.items()
        for function in parsed_file.functions
    ]

    by_hash: dict[str, list[int]] = defaultdict(list)
    by_name: dict[str, list[int]] = defaultdict(list)
    by_call: dict[str, list[int]] = defaultdict(list)
    for index, (_, function) in enumerate(records):
        if function.structural_hash:
            by_hash[function.structural_hash].append(index)
        if key := _name_key(function.name):
            by_name[key].append(index)
        for call in function.calls:
            by_call[call].append(index)

    pairs: set[tuple[int, int]] = set()
    for groups in (by_hash, by_name):
        for indices in groups.values():
            for offset, left in enumerate(indices):
                for right in indices[offset + 1:]:
                    pairs.add((left, right))
                    if len(pairs) >= MAX_PAIR_COMPARISONS:
                        break
                if len(pairs) >= MAX_PAIR_COMPARISONS:
                    break
            if len(pairs) >= MAX_PAIR_COMPARISONS:
                break
        if len(pairs) >= MAX_PAIR_COMPARISONS:
            break
    for indices in by_call.values():
        if len(indices) <= 40 and len(pairs) < MAX_PAIR_COMPARISONS:
            for offset, left in enumerate(indices):
                for right in indices[offset + 1:]:
                    pairs.add((left, right))
                    if len(pairs) >= MAX_PAIR_COMPARISONS:
                        break
                if len(pairs) >= MAX_PAIR_COMPARISONS:
                    break

    candidates = []
    for left, right in pairs:
        left_file_id, left_function = records[left]
        right_file_id, right_function = records[right]
        left_signature = left_function.structural_signature
        right_signature = right_function.structural_signature
        structural = SequenceMatcher(None, left_signature, right_signature, autojunk=False).ratio()
        if left_function.structural_hash and left_function.structural_hash == right_function.structural_hash:
            structural = 1.0
        if structural < 0.62:
            continue
        pair_id = _stable_id(snapshot_id, left_file_id, left_function.name, str(left_function.line_start),
                             right_file_id, right_function.name, str(right_function.line_start))
        confidence = 'high' if structural >= 0.9 else 'medium' if structural >= 0.75 else 'low'
        candidates.append(DuplicateCandidate(
            id=pair_id,
            functions=[_evidence(left_function, left_file_id), _evidence(right_function, right_file_id)],
            structural_similarity=round(structural, 3),
            confidence=confidence,
            method='normalized_ast_structure_and_call_shape',
        ))
    candidates.sort(key=lambda candidate: (candidate.structural_similarity, candidate.id), reverse=True)
    candidates = candidates[:MAX_CANDIDATES]

    by_name_functions: dict[tuple[str, str], list[tuple[str, Function]]] = defaultdict(list)
    for file_id, function in records:
        language = syntax[file_id].language
        by_name_functions[(language, function.name)].append((file_id, function))
    relationships: list[Relationship] = []
    for file_id, parsed_file in syntax.items():
        for caller in parsed_file.functions:
            for called_name in caller.calls:
                for target_file_id, target in by_name_functions.get((parsed_file.language, called_name), ()):
                    relationships.append(Relationship(
                        source=_evidence(caller, file_id).id,
                        target=_evidence(target, target_file_id).id,
                        type='calls',
                    ))

    referenced_names = {
        (parsed_file.language, name)
        for parsed_file in syntax.values()
        for name in parsed_file.references
    }
    referenced_ids = {relationship.target for relationship in relationships}
    unused = []
    for file_id, function in records:
        function_id = _evidence(function, file_id).id
        language = syntax[file_id].language
        if ((language, function.name) not in referenced_names and function_id not in referenced_ids
                and not (function.name.startswith('__') and function.name.endswith('__'))
                and not function.name.startswith('test_')):
            unused.append(PotentiallyUnusedFunction(
                id=_stable_id(snapshot_id, 'unused', function_id),
                function=_evidence(function, file_id),
            ))
    unused.sort(key=lambda item: (item.function.path, item.function.line_start))

    parsed_languages = sorted({parsed_file.language for parsed_file in syntax.values()})
    limitations = [
        f"Static function analysis covered parsed source files in: {', '.join(parsed_languages)}." if parsed_languages
        else 'No supported source-language files were parsed.',
        'Other languages and excluded or unparsed files are not assessed.',
        'Call resolution is name-based and cannot see reflection, dynamic dispatch, framework registration, or external callers.',
        'Unused results are candidates for review, not proof that a function is unused.',
    ]
    return inventory, syntax, candidates, unused, len(relationships), limitations


def get_unused_findings(snapshot_id: str) -> UnusedDetectionResult:
    inventory, syntax, _, unused, relationship_count, limitations = _static_analysis(snapshot_id)
    parsed_count = len(syntax)
    coverage = AnalysisCoverage(
        inventoried_files=len(inventory), parsed_files=parsed_count,
        analyzed_functions=sum(len(file.functions) for file in syntax.values()),
        unresolved_references=max(0, sum(len(file.references) for file in syntax.values()) - relationship_count),
        limitations=limitations,
    )
    return UnusedDetectionResult(snapshot_id=snapshot_id, findings=unused, coverage=coverage)


def _candidate_source(snapshot_id: str, evidence: FunctionEvidence) -> str:
    selected_end = min(evidence.line_end, evidence.line_start + 79)
    source = read_source_lines(snapshot_id, evidence.file_id, evidence.line_start, selected_end, max_lines=80)
    return source.content[:4000]


async def get_duplicate_findings(snapshot_id: str) -> DuplicateDetectionResult:
    inventory, syntax, candidates, _, relationship_count, limitations = _static_analysis(snapshot_id)
    candidates = [candidate.model_copy(deep=True) for candidate in candidates]
    provider: SemanticSimilarityProvider | None = configured_provider()
    if provider is None:
        limitations = [*limitations, 'Semantic comparison is not configured; scores use static AST and call structure only.']
    elif candidates:
        selected = candidates[:MAX_SEMANTIC_PAIRS]
        key = (snapshot_id, provider.cache_key, tuple(candidate.id for candidate in selected))
        scores = _semantic_cache.get(key)
        if scores is None:
            pairs = [
                {
                    'name_a': candidate.functions[0].name,
                    'code_a': _candidate_source(snapshot_id, candidate.functions[0]),
                    'name_b': candidate.functions[1].name,
                    'code_b': _candidate_source(snapshot_id, candidate.functions[1]),
                }
                for candidate in selected
            ]
            try:
                scores = await provider.score_pairs(pairs)
                if len(_semantic_cache) >= 64:
                    _semantic_cache.pop(next(iter(_semantic_cache)))
                _semantic_cache[key] = scores
            except Exception:
                scores = []
                limitations = [*limitations, 'The semantic provider was unavailable; structural results are still shown.']
        for candidate, semantic in zip(selected, scores):
            candidate.semantic_similarity = round(semantic, 3)
            candidate.method = 'normalized_ast_structure_and_ai_semantic_comparison'
            combined = candidate.structural_similarity * 0.65 + semantic * 0.35
            candidate.confidence = 'high' if combined >= 0.9 else 'medium' if combined >= 0.75 else 'low'
    coverage = AnalysisCoverage(
        inventoried_files=len(inventory), parsed_files=len(syntax),
        analyzed_functions=sum(len(file.functions) for file in syntax.values()),
        unresolved_references=max(0, sum(len(file.references) for file in syntax.values()) - relationship_count),
        limitations=limitations,
    )
    return DuplicateDetectionResult(snapshot_id=snapshot_id, candidates=candidates, coverage=coverage)