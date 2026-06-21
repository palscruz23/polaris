# Conversation Memory Architecture

## Purpose

Open Reliability conversations must support follow-up questions within a session,
such as:

```text
User: How do I troubleshoot pump P-101?
Assistant: Start by checking suction conditions, alignment, and bearings.
User: What about the bearings?
```

The Reliability Agent must understand that "the bearings" refers to pump P-101
and the preceding troubleshooting discussion.

The architecture is model-agnostic. Conversation storage and context selection
belong to Open Reliability, not to DeepSeek or any other model provider.

## Source of Truth

PostgreSQL is the authoritative store for:

- Conversation metadata
- Complete message history
- The current Markdown memory
- Memory revisions

The session memory is represented as Markdown and treated as `memory.md` by the
application. In production, the Markdown content is stored in PostgreSQL rather
than relying on a local file. It may be exported as a physical `memory.md` file
for inspection, debugging, or backup.

Original messages are never replaced by the memory. The complete history remains
available for auditing, exact-value retrieval, memory regeneration, and future
context-retrieval features.

## PostgreSQL Data Model

### `conversations`

| Column | Type | Purpose |
| --- | --- | --- |
| `id` | UUID, primary key | Stable session identifier |
| `title` | text, nullable | User-facing conversation title |
| `memory_markdown` | text | Current contents of `memory.md` |
| `message_count` | integer | Number of persisted user and assistant messages |
| `created_at` | timestamptz | Conversation creation time |
| `updated_at` | timestamptz | Last conversation activity |
| `memory_updated_at` | timestamptz, nullable | Last successful memory update |

`message_count` is maintained transactionally whenever a message is inserted.
It is a context-selection optimization; the `messages` table remains the source
of truth if the count ever needs to be rebuilt.

### `messages`

| Column | Type | Purpose |
| --- | --- | --- |
| `id` | UUID, primary key | Stable message identifier |
| `conversation_id` | UUID, foreign key | Owning conversation |
| `role` | text | `user` or `assistant` |
| `content` | text | Original message content |
| `sequence_number` | integer | Deterministic ordering within the conversation |
| `created_at` | timestamptz | Message creation time |
| `provider` | text, nullable | Provider used for an assistant response |
| `model` | text, nullable | Model used for an assistant response |

Required constraints and indexes:

- Foreign key from `messages.conversation_id` to `conversations.id`
- Unique constraint on `(conversation_id, sequence_number)`
- Index on `(conversation_id, sequence_number)`
- Check constraint limiting `role` to supported application roles

### `conversation_memory_revisions`

| Column | Type | Purpose |
| --- | --- | --- |
| `id` | UUID, primary key | Revision identifier |
| `conversation_id` | UUID, foreign key | Owning conversation |
| `memory_markdown` | text | Memory contents at this revision |
| `through_sequence_number` | integer | Latest message represented by the memory |
| `created_at` | timestamptz | Revision creation time |

Memory revisions allow recovery when a summary drops or distorts an important
engineering fact.

## `memory.md` Structure

Each conversation uses the same headings:

```markdown
# Conversation Memory

## Objective

## Equipment

## Known Facts

## Assumptions

## Decisions

## Recommended Actions

## Open Questions
```

Memory updates must:

- Preserve exact equipment identifiers, measurements, dates, and work-order IDs
- Keep facts separate from assumptions
- Record decisions and unresolved questions
- Avoid unsupported information
- Remove or replace information only when explicitly corrected or resolved

## Context Selection Policy

The current user message is persisted before context is assembled. Message
counts include both user and assistant messages.

### Up to 10 messages

Send:

```text
System prompt
+ memory.md
+ complete ordered message history
```

The complete history includes the current user message.

### More than 10 messages

Send:

```text
System prompt
+ memory.md
+ latest 10 ordered messages
```

The latest 10 messages include the current user message. Selection is based on
`sequence_number`, not timestamps, so ordering remains deterministic.

### Exact historical questions

The initial implementation still follows the 10-message rule. A later retrieval
feature may add relevant original messages when the user asks for exact older
details, such as a previous measurement, date, work-order number, or decision.

## Request Lifecycle

```text
Frontend sends conversation_id + new user message
                    |
                    v
FastAPI validates that the conversation exists
                    |
                    v
PostgreSQL stores the user message and sequence number
                    |
                    v
Context builder loads memory_markdown and message_count
                    |
          +---------+----------+
          |                    |
    count <= 10          count > 10
          |                    |
  load all messages      load latest 10
          +---------+----------+
                    |
                    v
Model-agnostic message list is sent to the configured provider
                    |
                    v
PostgreSQL stores the assistant response
                    |
                    v
Memory service updates memory_markdown and creates a revision
                    |
                    v
FastAPI returns the assistant response to the frontend
```

Do not keep a database transaction open while waiting for a model provider. Use
short transactions:

1. Persist the user message and commit.
2. Call the configured model provider.
3. Persist the assistant response and commit.
4. Update memory and create its revision in one transaction.

If the provider fails, the user message remains part of the complete history and
the request returns a provider error. If memory updating fails, the assistant
response remains stored, the previous memory remains active, and the failed
memory update must be visible and retryable. A memory failure must never erase
or replace the complete message history.

## Model-Agnostic Boundaries

Open Reliability uses its own internal message type:

```python
ChatMessage(
    role="user",
    content="What about the bearings?",
)
```

The context builder returns an ordered list of these generic messages. A provider
adapter converts them into the format required by DeepSeek, OpenAI, Anthropic,
or a local model.

```text
PostgreSQL
    |
    v
Conversation repository
    |
    v
Context builder
    |
    v
Generic ChatMessage list
    |
    v
Configured provider adapter
```

Provider-specific response objects must not become the primary conversation
history. Provider and model names may be stored as metadata for observability.

## API Shape

```text
POST /conversations
GET  /conversations/{conversation_id}
POST /conversations/{conversation_id}/messages
```

Example follow-up request:

```http
POST /conversations/abc123/messages
Content-Type: application/json
```

```json
{
  "content": "What about the bearings?"
}
```

The frontend sends only the new message and conversation identifier. The backend
owns history loading, memory selection, and provider context construction.

## Initial Implementation Boundary

The first implementation will include:

- PostgreSQL conversation and message persistence
- One Markdown memory per conversation stored in `memory_markdown`
- The fixed 10-message context policy
- Memory revision history
- A model-agnostic context builder and provider interface

Semantic retrieval, token-budget selection, and automatic long-term fact
extraction are future enhancements.
