---
type: converter
id: CONV-internal-adapter-contract-v1
title: Internal Adapter Contract v1
status: deprecated
created: 2026-02-11
updated: 2026-03-04
owners:
  - platform
tags:
  - integration
  - adapter
  - contract
  - internal
links:
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/internal_adapter_contract_v2.md
  - scripts/sir_convert_a_lot/integrations/adapter_profiles.py
---

## Purpose

Define normative requirements for thin internal consumer adapters (HuleEdu and
Skriptoteket) that submit conversion jobs to Sir Convert-a-Lot without contract
drift or business-logic forks.

This document is retained as historical context only. Active adapter behavior
is now v2-only and implemented in:

- `scripts/sir_convert_a_lot/integrations/adapter_profiles.py`

## Status

This document is deprecated and retained for historical context only.

The normative internal adapter contract is now:

- `docs/converters/internal_adapter_contract_v2.md`

All active adapter behavior is v2-only and implemented in:

- `scripts/sir_convert_a_lot/integrations/adapter_profiles.py`
