# Karen
Karen is a native Windows Tkinter assistant for Spanish text and voice conversations. The user operates it at a desktop alongside local AI tools. It connects directly to PC or Homelab Ollama and to the personalized Karen API. Installed model discovery must follow the selected endpoint; the personalized API defines its own model. Voice capture is explicitly activated, paused during processing and playback, and cancellable. Aetherion benchmarks are separate explicit jobs using the engine's authenticated integration contract. Preserve configuration, sessions, retry safety, microphone selection, and all functional controls. Redesign is authorized: the user wants striking visual character and clear hierarchy. Use native desktop controls without a framework migration. Never expose model reasoning in conversation or speech. Do not claim unverified model quality or benchmark results.

## Conversation continuity

The conversation selector restores archived chats; Nuevo chat starts an isolated conversation.
Karen restores the last selected chat on startup. Exchanges are saved atomically in
`.private/conversations.sqlite3`, including failed attempts for display. Failed attempts
are excluded from model context. The archive contains conversation text, not API keys
or model thinking. Historical messages are displayed without executing their actions again.

Ollama uses `/api/chat` with role-based messages and at most 12 recent successful
exchanges within a 16,000-character history budget. This is bounded conversational
context, not permanent preference memory. Changing the selected Ollama model retains
the current chat's context. The personalized Karen API retains its existing contract
and owns its remote context; its session ID is stable per chat and target. Recovery of
that remote context depends on the server retaining the session.

Chat switching is blocked during listening and until the current response has finished
updating the interface. Search, export, deletion, and editable preferences remain future work.

Verification: `qa/test_conversations.py` covers persistence, chat isolation, failed-turn
exclusion, streaming, hidden thinking, the personalized API contract, and desktop controls.
`qa/verify_conversation_live.py` checks continuity after recreating the client and archive
against the configured Ollama model using synthetic data and a temporary database.

## Administration

The Admin tab provides a bounded tool agent for compatible Ollama models, a
per-operation approval dialog, an operation audit, destination authorization,
and an explicit Windows UAC relaunch. Routine queries and resource opening are
direct; critical actions and general scripts require approval. See
`ADMINISTRATION.md` for scope, examples, verification and limitations.
