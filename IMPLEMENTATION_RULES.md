# Implementation Rules

## Mandatory Rules

- One implementation chat = one bounded subsystem only
- Never implement multiple architecture domains together
- Never bypass governance documents
- Never implement future phases early
- Never introduce temporary shortcuts
- Never use untyped systems
- Never create giant files/components/services
- Preserve replayability
- Preserve observability
- Preserve event consistency

## Required Workflow

1. Retrieve architecture context
2. Distill relevant context
3. Define bounded scope
4. Implement only requested subsystem
5. Run lint/typecheck/tests
6. Run governance review
7. Commit immediately

## Required Before Every Implementation

- architecture retrieval
- governance retrieval
- dependency validation
- phase validation

## Forbidden

- "build the whole backend"
- "implement entire frontend"
- "create full orchestration system"
- hidden coupling
- bypassing state machine
- direct cross-layer imports
- event schema drift