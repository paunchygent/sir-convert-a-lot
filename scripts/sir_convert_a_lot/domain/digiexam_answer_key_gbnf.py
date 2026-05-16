"""DigiExam answer-key GBNF grammars.

Purpose:
    Provide llama.cpp GBNF grammars that constrain answer-key completion output
    to JSON objects compatible with the DigiExam advisory decoder.

Relationships:
    - Consumed by `digiexam_answer_key_completion_candidates` for llama.cpp
      GBNF candidate plans.
    - Mirrors the validated Skriptoteket convention of sending a `grammar`
      request field to llama.cpp chat completions.
    - Complements JSON Schema output specs, which remain the post-decode
      validation contract for the same advisory payloads.
"""

from __future__ import annotations


def choice_answer_key_decision_gbnf() -> str:
    """Return GBNF for choice answer-key decision JSON."""

    return "\n".join(
        [
            "root ::= choice_decision",
            "",
            'choice_decision ::= "{" ws "\\"decision_state\\"" ws ":" ws decision_state "," ws '
            '"\\"correct_alternative_ids\\"" ws ":" ws integer_array "," ws '
            '"\\"manual_follow_up_code\\"" ws ":" ws nullable_string "}" ws',
            "",
            'decision_state ::= "\\"answered\\"" | "\\"manual_follow_up_required\\""',
            'integer_array ::= "[" ws (integer ("," ws integer)*)? "]" ws',
            "integer ::= [0-9]+",
            'nullable_string ::= "null" | string',
            *_JSON_STRING_GBNF_LINES,
        ]
    ).strip()


def gap_fill_answer_key_decision_gbnf() -> str:
    """Return GBNF for gap-fill answer-key decision JSON."""

    return "\n".join(
        [
            "root ::= gap_fill_decision",
            "",
            'gap_fill_decision ::= "{" ws "\\"decision_state\\"" ws ":" ws decision_state "," ws '
            '"\\"gap_answers\\"" ws ":" ws gap_answer_array "," ws '
            '"\\"manual_follow_up_code\\"" ws ":" ws nullable_string "}" ws',
            "",
            'decision_state ::= "\\"answered\\"" | "\\"manual_follow_up_required\\""',
            'gap_answer_array ::= "[" ws (gap_answer ("," ws gap_answer)*)? "]" ws',
            'gap_answer ::= "{" ws "\\"gap_id\\"" ws ":" ws string "," ws '
            '"\\"accepted_values\\"" ws ":" ws string_array "}" ws',
            'string_array ::= "[" ws (string ("," ws string)*)? "]" ws',
            'nullable_string ::= "null" | string',
            *_JSON_STRING_GBNF_LINES,
        ]
    ).strip()


def numbered_gap_fill_answer_key_gbnf(gap_count: int) -> str:
    """Return GBNF for a numbered gap-fill facit JSON object."""

    if gap_count <= 0:
        raise ValueError("Numbered gap-fill grammar requires at least one gap.")
    answer_fields = [
        f'"\\"{index}\\"" ws ":" ws string "," ws' for index in range(1, gap_count + 1)
    ]
    return "\n".join(
        [
            "root ::= gap_fill_numbered",
            "",
            'gap_fill_numbered ::= "{" ws "\\"decision_state\\"" ws ":" ws decision_state "," ws '
            + " ".join(answer_fields)
            + ' "\\"manual_follow_up_code\\"" ws ":" ws nullable_string "}" ws',
            "",
            'decision_state ::= "\\"answered\\"" | "\\"manual_follow_up_required\\""',
            'nullable_string ::= "null" | string',
            *_JSON_STRING_GBNF_LINES,
        ]
    ).strip()


_JSON_STRING_GBNF_LINES = [
    'string ::= "\\"" (',
    '  [^"\\\\\\x7F\\x00-\\x1F] |',
    '  "\\\\" (["\\\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])',
    ')* "\\"" ws',
    "",
    "ws ::= ([ \\t\\n] ws)?",
]
