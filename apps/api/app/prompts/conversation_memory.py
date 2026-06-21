CONVERSATION_MEMORY_UPDATE_PROMPT = """
Update the conversation memory using the previous memory and latest exchange.

Return only Markdown using exactly these headings:

# Conversation Memory
## Objective
## Equipment
## Known Facts
## Assumptions
## Decisions
## Recommended Actions
## Open Questions

Rules:
- Preserve exact equipment identifiers, work-order identifiers, measurements,
  dates, decisions, and unresolved questions.
- Keep confirmed facts separate from assumptions.
- Do not add unsupported facts.
- Remove or replace information only when explicitly corrected or resolved.
- Keep the memory concise and durable rather than repeating the conversation.
""".strip()


CONVERSATION_MEMORY_COMPACTION_PROMPT = """
Compact the conversation memory so it retains only durable, decision-relevant
context.

Return only Markdown using exactly these headings:

# Conversation Memory
## Objective
## Equipment
## Known Facts
## Assumptions
## Decisions
## Recommended Actions
## Open Questions

Preserve exact identifiers, measurements, dates, decisions, completed actions,
and unresolved questions. Remove repetition and obsolete narrative. Do not add
unsupported facts.
""".strip()
