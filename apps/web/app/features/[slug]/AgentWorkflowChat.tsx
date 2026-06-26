"use client";

import Link from "next/link";
import Image from "next/image";
import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata?: AgentMessageMetadata | null;
};

type AgentSubCallMetadata = {
  agent: string;
  tool: string;
  message: string;
};

type AgentToolCallMetadata = {
  sequence: number;
  id: string;
  agent: string | null;
  target_agent?: string | null;
  tool: string;
  arguments: Record<string, unknown>;
  result: string;
  is_error: boolean;
  sub_calls?: AgentSubCallMetadata[];
};

type AgentInternalCallMetadata = {
  sequence: number;
  call_type: string;
  message: string;
};

type AgentMessageMetadata = {
  tool_calls?: AgentToolCallMetadata[];
  internal_calls?: AgentInternalCallMetadata[];
};

const VISIBLE_AGENT_PROCESS_CALL_TYPES = new Set([
  "agent_final_synthesis",
  "answer_review",
  "answer_revision",
  "answer_revision_final",
]);

type ApiMessage = Message & {
  conversation_id: string;
  sequence_number: number;
  provider: string | null;
  model: string | null;
  metadata: AgentMessageMetadata | null;
  created_at: string;
};

type ConversationApiResponse = {
  id: string;
  title: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
  is_processing: boolean;
  messages: ApiMessage[];
};

type ConversationSummary = {
  id: string;
  title: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
  is_processing: boolean;
};

type MessageExchangeApiResponse = {
  user_message: ApiMessage;
  assistant_message: ApiMessage;
  memory_update_status: string;
};

type ProgressStreamEvent = {
  type: "progress";
  stage: string;
  message: string;
  specialist: string | null;
  tool: string | null;
};

type CompleteStreamEvent = {
  type: "complete";
  exchange: MessageExchangeApiResponse;
};

type ErrorStreamEvent = {
  type: "error";
  message: string;
};

type MessageStreamEvent =
  | ProgressStreamEvent
  | CompleteStreamEvent
  | ErrorStreamEvent;

type AvailableModel = {
  id: string;
  label: string;
  is_default: boolean;
  is_enabled: boolean;
};

const CONVERSATION_STORAGE_KEY = "open-reliability-conversation-id";
const MODEL_STORAGE_KEY = "open-reliability-model-id";
const FALLBACK_MODEL_ID = "deepseek/deepseek-v4-flash";
const TITLE_STOP_WORDS = new Set([
  "a",
  "about",
  "an",
  "and",
  "are",
  "can",
  "could",
  "do",
  "for",
  "from",
  "help",
  "how",
  "i",
  "in",
  "is",
  "me",
  "my",
  "of",
  "on",
  "please",
  "should",
  "the",
  "to",
  "what",
  "with",
  "you",
]);

const starterPrompts = [
  {
    label: "Identify repeat failures",
    prompt: "Help me identify repeat failures from my work order history.",
    icon: "trend",
  },
  {
    label: "Review a maintenance strategy",
    prompt: "Review an existing maintenance strategy and identify coverage gaps.",
    icon: "shield",
  },
  {
    label: "Analyse work order data",
    prompt: "Analyse my work order data for bad actors and recurring failure patterns.",
    icon: "document",
  },
  {
    label: "Search equipment records",
    prompt:
      "Find critical pumps in the equipment register and summarize the matching assets.",
    icon: "target",
  },
] as const;

function ArrowLeftIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m15 18-6-6 6-6" />
      <path d="M9 12h11" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M21 12a8 8 0 0 1-8 8H7l-4 2 1.3-4A9 9 0 1 1 21 12Z" />
      <path d="M8 12h.01M12 12h.01M16 12h.01" />
    </svg>
  );
}

function AttachmentIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.6-9.6a4 4 0 0 1 5.7 5.7l-9.6 9.6a2 2 0 0 1-2.8-2.8l8.9-8.9" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m22 2-7 20-4-9-9-4Z" />
      <path d="M22 2 11 13" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <rect height="10" rx="1.5" width="10" x="7" y="7" />
    </svg>
  );
}

function ChevronDownIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20">
      <path d="m6.5 8 3.5 3.5L13.5 8" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function ShieldCheckIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function PromptIcon({ name }: { name: (typeof starterPrompts)[number]["icon"] }) {
  if (name === "trend") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M3 3v18h18" />
        <path d="m7 15 4-4 3 3 6-7" />
      </svg>
    );
  }

  if (name === "shield") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
        <path d="m9 12 2 2 4-4" />
      </svg>
    );
  }

  if (name === "document") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
        <path d="M14 2v6h6M8 13h8M8 17h8" />
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v4M22 12h-4" />
    </svg>
  );
}

function AgentMark() {
  return (
    <span className="agent-mark" aria-hidden="true">
      <ChatIcon />
    </span>
  );
}

function formatAgentName(agent: string | null) {
  if (!agent) {
    return "Agent";
  }

  const formattedAgent = agent
    .split("_")
    .map(titleCaseWord)
    .join(" ");

  return formattedAgent === "Reliability Agent" ? "Polaris" : formattedAgent;
}

function formatToolName(tool: string) {
  return tool
    .split("_")
    .map(titleCaseWord)
    .join(" ");
}

function formatMetadataValue(value: unknown) {
  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, null, 2);
}

function extractIntentLabel(toolCall: AgentToolCallMetadata): string | null {
  const intent = toolCall.arguments?.intent;
  if (typeof intent !== "string") {
    return null;
  }

  return intent
    .split("_")
    .map(titleCaseWord)
    .join(" ");
}

function ToolCallItem({ toolCall, sequenceNumber }: { toolCall: AgentToolCallMetadata; sequenceNumber: number }) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const intentLabel = extractIntentLabel(toolCall);

  return (
    <li className="agent-tool-call">
      <div className="agent-tool-call-header">
        <span>#{sequenceNumber}</span>
        <strong>{formatAgentName(toolCall.agent)}</strong>
        {toolCall.target_agent ? (
          <b aria-label="Target agent">
            {formatAgentName(toolCall.target_agent)}
          </b>
        ) : null}
        <code>
          {intentLabel ?? formatToolName(toolCall.tool)}
        </code>
        {toolCall.is_error ? <em>error</em> : null}
      </div>
      {toolCall.sub_calls && toolCall.sub_calls.length > 0 ? (
        <ol className="agent-subcall-list">
          {toolCall.sub_calls.map((sub, subIndex) => (
            <li
              className="agent-subcall"
              key={`${toolCall.id}-sub-${subIndex}`}
            >
              <div className="agent-subcall-header">
                <span>#{sequenceNumber}.{subIndex + 1}</span>
                <strong>{formatAgentName(sub.agent)}</strong>
                <code>{formatToolName(sub.tool)}</code>
              </div>
              <div className="agent-subcall-body">
                <span>{sub.message}</span>
              </div>
            </li>
          ))}
        </ol>
      ) : null}
      <button
        aria-expanded={detailsOpen}
        className="agent-tool-call-details-toggle"
        onClick={() => setDetailsOpen((open) => !open)}
        type="button"
      >
        <span>{detailsOpen ? "Hide" : "Show"} details</span>
      </button>
      {detailsOpen ? (
        <div className="agent-tool-call-body">
          <div>
            <span>Arguments</span>
            <pre>{formatMetadataValue(toolCall.arguments)}</pre>
          </div>
          <div>
            <span>Result</span>
            <pre>{formatMetadataValue(toolCall.result)}</pre>
          </div>
        </div>
      ) : null}
    </li>
  );
}

function InternalCallItem({ call, sequenceNumber }: { call: AgentInternalCallMetadata; sequenceNumber: number }) {
  return (
    <li className="agent-tool-call">
      <div className="agent-tool-call-header">
        <span>#{sequenceNumber}</span>
        <strong>Polaris</strong>
        <code>{formatToolName(call.call_type)}</code>
      </div>
      <div className="agent-tool-call-message">
        <span>{call.message}</span>
      </div>
    </li>
  );
}

function interleaveCalls(
  internalCalls: AgentInternalCallMetadata[],
  toolCalls: AgentToolCallMetadata[],
): Array<
  | { kind: "internal"; data: AgentInternalCallMetadata }
  | { kind: "tool"; data: AgentToolCallMetadata }
> {
  const beforeTools: AgentInternalCallMetadata[] = [];
  const afterTools: AgentInternalCallMetadata[] = [];

  for (const ic of internalCalls) {
    if (ic.call_type === "agent_tool_selection") {
      continue; // redundant — the specialist call that follows represents this
    }
    if (ic.call_type.startsWith("memory_")) {
      beforeTools.push(ic);
    } else if (VISIBLE_AGENT_PROCESS_CALL_TYPES.has(ic.call_type)) {
      afterTools.push(ic);
    }
  }

  return [
    ...beforeTools.map((ic) => ({ kind: "internal" as const, data: ic })),
    ...toolCalls.map((tc) => ({ kind: "tool" as const, data: tc })),
    ...afterTools.map((ic) => ({ kind: "internal" as const, data: ic })),
  ];
}

function ToolCallMetadata({ metadata }: { metadata?: AgentMessageMetadata | null }) {
  const [isOpen, setIsOpen] = useState(false);
  const toolCalls = metadata?.tool_calls ?? [];
  const internalCalls = metadata?.internal_calls ?? [];

  const allItems = interleaveCalls(internalCalls, toolCalls);

  if (allItems.length === 0) {
    return null;
  }

  return (
    <div className="agent-tool-metadata">
      <button
        aria-expanded={isOpen}
        className="agent-tool-metadata-toggle"
        onClick={() => setIsOpen((open) => !open)}
        type="button"
      >
        <span>{isOpen ? "Hide" : "Show"} agent process</span>
        <span aria-hidden="true">{allItems.length}</span>
      </button>
      {isOpen ? (
        <ol className="agent-tool-call-list">
          {allItems.map((item, index) => {
            const seq = index + 1;
            if (item.kind === "internal") {
              return (
                <InternalCallItem
                  key={`internal-${item.data.sequence}`}
                  call={item.data}
                  sequenceNumber={seq}
                />
              );
            }
            return (
              <ToolCallItem
                key={`${item.data.id}-${item.data.sequence}`}
                toolCall={item.data}
                sequenceNumber={seq}
              />
            );
          })}
        </ol>
      ) : null}
    </div>
  );
}

function AssistantMessage({
  content,
  metadata,
}: {
  content: string;
  metadata?: AgentMessageMetadata | null;
}) {
  return (
    <>
      <div className="agent-message-markdown">
        <ReactMarkdown
          components={{
            a: ({ children, ...props }) => (
              <a {...props} rel="noreferrer" target="_blank">
                {children}
              </a>
            ),
            table: ({ children, node, ...props }) => {
              void node;
              return (
                <div className="agent-message-table-scroll">
                  <table {...props}>{children}</table>
                </div>
              );
            },
          }}
          remarkPlugins={[remarkGfm]}
        >
          {content}
        </ReactMarkdown>
      </div>
      <ToolCallMetadata metadata={metadata} />
    </>
  );
}

function conversationTitle(conversation: ConversationSummary) {
  return conversation.title ?? "Untitled reliability chat";
}

function conversationTimestamp(conversation: ConversationSummary) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(conversation.updated_at));
}

function titleCaseWord(word: string) {
  if (word === word.toUpperCase() || /\d/.test(word)) {
    return word;
  }

  return `${word.charAt(0).toUpperCase()}${word.slice(1).toLowerCase()}`;
}

function titleFromMessage(content: string) {
  const words = content
    .split(/\s+/)
    .map((word) => word.replace(/^[.,!?;:()[\]{}"']+|[.,!?;:()[\]{}"']+$/g, ""))
    .filter(Boolean);
  const summaryWords = words.filter(
    (word) => !TITLE_STOP_WORDS.has(word.toLowerCase()),
  );
  const titleWords =
    summaryWords.length < 3 ? words.slice(0, 6) : summaryWords.slice(0, 7);
  const title = titleWords.map(titleCaseWord).join(" ");

  if (!title) {
    return "New Reliability Chat";
  }

  if (title.length <= 60) {
    return title;
  }

  return `${title.slice(0, 57).trimEnd()}...`;
}

export default function AgentWorkflowChat() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [attachment, setAttachment] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [progressMessage, setProgressMessage] = useState(
    "Reliability Agent is reviewing your request.",
  );
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [historyIsOpen, setHistoryIsOpen] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);
  const [selectedModelId, setSelectedModelId] = useState(FALLBACK_MODEL_ID);
  const [modelError, setModelError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const composerInputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const requestControllerRef = useRef<AbortController>(null);
  const latestMessageId = messages[messages.length - 1]?.id;

  useEffect(() => {
    const requestController = new AbortController();
    const savedConversationId = window.localStorage.getItem(
      CONVERSATION_STORAGE_KEY,
    );

    refreshConversations(requestController.signal);
    loadAvailableModels(requestController.signal);

    if (savedConversationId) {
      loadConversation(savedConversationId, requestController.signal);
    }

    return () => requestController.abort();
  }, []);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    messagesEndRef.current?.scrollIntoView({
      behavior: prefersReducedMotion ? "auto" : "smooth",
      block: "end",
    });
  }, [latestMessageId, isLoading]);

  useEffect(() => {
    if (!isLoading && messages.length > 0) {
      composerInputRef.current?.focus();
    }
  }, [isLoading, messages.length]);

  async function submitMessage(message: string) {
    const trimmedMessage = message.trim();

    if (!trimmedMessage || isLoading) {
      return;
    }

    const temporaryMessageId = `temporary-${messages.length + 1}`;

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: temporaryMessageId,
        role: "user",
        content: trimmedMessage,
      },
    ]);

    setDraft("");
    setAttachment("");
    setIsLoading(true);
    setProgressMessage("Reliability Agent is reviewing your request.");
    composerInputRef.current?.focus();

    const requestController = new AbortController();
    requestControllerRef.current = requestController;

    try {
      const activeConversationId =
        conversationId ??
        (await createConversation(requestController.signal, trimmedMessage));
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/conversations/${activeConversationId}/messages/stream`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            content: trimmedMessage,
            model: selectedModelId,
          }),
          signal: requestController.signal,
        },
      );

      if (!response.ok) {
        throw new Error("The Reliability Agent request failed.");
      }

      if (!response.body) {
        throw new Error("The Reliability Agent stream was unavailable.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let completedExchange: MessageExchangeApiResponse | null = null;

      while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.trim()) {
            continue;
          }

          const event = JSON.parse(line) as MessageStreamEvent;

          if (event.type === "progress") {
            setProgressMessage(event.message);
          } else if (event.type === "complete") {
            completedExchange = event.exchange;
          } else {
            throw new Error(event.message);
          }
        }

        if (done) {
          break;
        }
      }

      if (!completedExchange) {
        throw new Error("The Reliability Agent stream ended unexpectedly.");
      }

      const data = completedExchange;
      setMessages((currentMessages) => [
        ...currentMessages.map((message) =>
          message.id === temporaryMessageId
            ? {
                id: data.user_message.id,
                role: data.user_message.role,
                content: data.user_message.content,
                metadata: data.user_message.metadata,
              }
            : message,
        ),
        {
          id: data.assistant_message.id,
          role: data.assistant_message.role,
          content: data.assistant_message.content,
          metadata: data.assistant_message.metadata,
        },
      ]);
      refreshConversations();
    } catch {
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: `${temporaryMessageId}-error`,
          role: "assistant",
          content: requestController.signal.aborted
            ? "Response stopped."
            : "I could not contact the Reliability Agent. Check that the backend is running.",
        },
      ]);
    } finally {
      requestControllerRef.current = null;
      setIsLoading(false);
      setProgressMessage("Reliability Agent is reviewing your request.");
    }
  }

  async function createConversation(
    signal: AbortSignal,
    firstMessage: string,
  ): Promise<string> {
    const title = titleFromMessage(firstMessage);
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/conversations`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ title }),
        signal,
      },
    );

    if (!response.ok) {
      throw new Error("The conversation could not be created.");
    }

    const conversation: ConversationApiResponse = await response.json();
    setConversationId(conversation.id);
    window.localStorage.setItem(
      CONVERSATION_STORAGE_KEY,
      conversation.id,
    );
    setConversations((currentConversations) => [
      {
        id: conversation.id,
        title: conversation.title,
        message_count: conversation.message_count,
        created_at: conversation.created_at,
        updated_at: conversation.updated_at,
        is_processing: conversation.is_processing,
      },
      ...currentConversations.filter((item) => item.id !== conversation.id),
    ]);

    return conversation.id;
  }

  async function refreshConversations(signal?: AbortSignal) {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/conversations`,
        { signal },
      );

      if (!response.ok) {
        throw new Error("Conversation history could not be loaded.");
      }

      const conversationHistory: ConversationSummary[] = await response.json();
      setConversations(conversationHistory);
      setHistoryError("");
    } catch {
      if (!signal?.aborted) {
        setHistoryError("History unavailable while the API is offline.");
      }
    }
  }

  async function loadAvailableModels(signal?: AbortSignal) {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/models`,
        { signal },
      );

      if (!response.ok) {
        throw new Error("Models could not be loaded.");
      }

      const models: AvailableModel[] = await response.json();
      const savedModelId = window.localStorage.getItem(MODEL_STORAGE_KEY);
      const defaultModel =
        models.find(
          (model) => model.id === savedModelId && model.is_enabled,
        ) ??
        models.find((model) => model.is_default && model.is_enabled) ??
        models.find((model) => model.is_enabled);

      setAvailableModels(models);
      if (defaultModel) {
        setSelectedModelId(defaultModel.id);
      }
      setModelError("");
    } catch {
      if (!signal?.aborted) {
        setModelError("Model list unavailable.");
      }
    }
  }

  function selectModel(modelId: string) {
    setSelectedModelId(modelId);
    window.localStorage.setItem(MODEL_STORAGE_KEY, modelId);
  }

  async function loadConversation(id: string, signal?: AbortSignal) {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/conversations/${id}`,
        { signal },
      );

      if (!response.ok) {
        window.localStorage.removeItem(CONVERSATION_STORAGE_KEY);
        return;
      }

      const conversation: ConversationApiResponse = await response.json();
      setConversationId(conversation.id);
      setMessages(
        conversation.messages.map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          metadata: message.metadata,
        })),
      );
      window.localStorage.setItem(CONVERSATION_STORAGE_KEY, conversation.id);
    } catch {
      if (!signal?.aborted) {
        window.localStorage.removeItem(CONVERSATION_STORAGE_KEY);
      }
    }
  }

  function startNewConversation() {
    requestControllerRef.current?.abort();
    setConversationId(null);
    setMessages([]);
    setDraft("");
    setAttachment("");
    setIsLoading(false);
    window.localStorage.removeItem(CONVERSATION_STORAGE_KEY);
    composerInputRef.current?.focus();
  }

  function stopResponse() {
    requestControllerRef.current?.abort();
    composerInputRef.current?.focus();
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitMessage(draft);
  }

  return (
    <main
      className={`agent-chat-shell ${historyIsOpen ? "history-is-open" : ""}`}
    >
      <header className="agent-chat-header">
        <Link className="agent-chat-back" href="/">
          <ArrowLeftIcon />
          <span>Back to home</span>
        </Link>
        <h1 className="sr-only">Polaris</h1>
        <Image
          alt="Polaris"
          className="agent-chat-title-image"
          height={149}
          priority
          src="/brand/polaris-word.png"
          width={1285}
        />
      </header>

      <button
        aria-controls="agent-conversation-history"
        aria-expanded={historyIsOpen}
        className="agent-history-tab"
        onClick={() => setHistoryIsOpen((isOpen) => !isOpen)}
        type="button"
      >
        <ChatIcon />
        <span>History</span>
      </button>

      <aside
        aria-label="Conversation history"
        className="agent-history-panel"
        id="agent-conversation-history"
      >
        <div className="agent-history-panel-header">
          <div>
            <p>Conversation history</p>
            <h2>Recent chats</h2>
          </div>
          <button
            className="agent-history-new-chat"
            onClick={startNewConversation}
            type="button"
          >
            <PlusIcon />
            New chat
          </button>
        </div>
        {historyError ? (
          <p className="agent-history-error">{historyError}</p>
        ) : null}
        <div className="agent-history-list">
          {conversations.length === 0 ? (
            <p className="agent-history-empty">
              Your reliability conversations will appear here once you start
              chatting.
            </p>
          ) : (
            conversations.map((conversation) => (
              <button
                aria-current={
                  conversation.id === conversationId ? "page" : undefined
                }
                className="agent-history-item"
                key={conversation.id}
                onClick={() => loadConversation(conversation.id)}
                type="button"
              >
                <span className="agent-history-title">
                  {conversationTitle(conversation)}
                </span>
                <span className="agent-history-meta">
                  {conversationTimestamp(conversation)}
                  {conversation.message_count > 0
                    ? ` · ${conversation.message_count} messages`
                    : ""}
                  {conversation.is_processing ? " · responding" : ""}
                </span>
              </button>
            ))
          )}
        </div>
      </aside>

      <section
        className={`agent-chat-content ${messages.length ? "has-messages" : ""}`}
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <div className="agent-chat-empty">
            <AgentMark />
            <h2>How can I help with reliability today?</h2>
            <p>
              Ask questions, analyse data, and get expert recommendations from
              the Reliability Agent.
            </p>
            <div className="agent-starter-grid">
              {starterPrompts.map((starter) => (
                <button
                  className="agent-starter-prompt"
                  key={starter.label}
                  onClick={() => setDraft(starter.prompt)}
                  type="button"
                >
                  <PromptIcon name={starter.icon} />
                  <span>{starter.label}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="agent-message-list">
            {messages.map((message) => (
              <article
                className={`agent-message agent-message-${message.role}`}
                key={message.id}
              >
                {message.role === "assistant" ? <AgentMark /> : null}
                <div>
                  <span className="agent-message-role">
                    {message.role === "assistant" ? "Polaris" : "You"}
                  </span>
                  {message.role === "assistant" ? (
                    <AssistantMessage
                      content={message.content}
                      metadata={message.metadata}
                    />
                  ) : (
                    <p>{message.content}</p>
                  )}
                </div>
              </article>
            ))}
            {isLoading ? (
              <article
                className="agent-message agent-message-assistant agent-message-thinking"
                role="status"
              >
                <AgentMark />
                <div>
                  <span className="agent-message-role">Polaris</span>
                  <p>{progressMessage}</p>
                </div>
              </article>
            ) : null}
            <div
              aria-hidden="true"
              className="agent-message-end"
              ref={messagesEndRef}
            />
          </div>
        )}
      </section>

      <footer className="agent-composer-dock">
        <form
          aria-busy={isLoading}
          className="agent-composer"
          onSubmit={handleSubmit}
        >
          <input
            className="sr-only"
            disabled={isLoading}
            ref={fileInputRef}
            type="file"
            onChange={(event) =>
              setAttachment(event.target.files?.[0]?.name ?? "")
            }
          />
          <button
            aria-label="Attach a file"
            className="agent-composer-action"
            disabled={isLoading}
            onClick={() => fileInputRef.current?.click()}
            type="button"
          >
            <AttachmentIcon />
          </button>
          <div className="agent-composer-input-wrap">
            {attachment ? (
              <span className="agent-attachment-name">{attachment}</span>
            ) : null}
            <textarea
              aria-label="Message the Reliability Agent"
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submitMessage(draft);
                }
              }}
              placeholder="Ask about equipment, failures, maintenance strategies, or reliability data…"
              ref={composerInputRef}
              rows={1}
              value={draft}
            />
          </div>
          <div className="agent-model-control">
            <label className="sr-only" htmlFor="agent-model-select">
              Model
            </label>
            <select
              aria-label="Select AI model"
              disabled={isLoading || availableModels.length === 0}
              id="agent-model-select"
              onChange={(event) => selectModel(event.target.value)}
              value={selectedModelId}
            >
              {availableModels.length === 0 ? (
                <option value={FALLBACK_MODEL_ID}>DeepSeek V4 Flash</option>
              ) : (
                availableModels.map((model) => (
                  <option
                    disabled={!model.is_enabled}
                    key={model.id}
                    value={model.id}
                  >
                    {model.label}
                  </option>
                ))
              )}
            </select>
            <ChevronDownIcon />
          </div>
          <button
            aria-label={isLoading ? "Stop response" : "Send message"}
            className={`agent-send-button ${
              isLoading ? "agent-send-button-stop" : ""
            }`}
            disabled={!isLoading && !draft.trim()}
            onClick={isLoading ? stopResponse : undefined}
            type={isLoading ? "button" : "submit"}
          >
            {isLoading ? <StopIcon /> : <SendIcon />}
          </button>
        </form>
        {modelError ? (
          <p className="agent-model-error">{modelError}</p>
        ) : null}
        <p className="agent-composer-note">
          <ShieldCheckIcon />
          Recommendations should be validated against site standards and
          engineering judgement.
        </p>
      </footer>
    </main>
  );
}
