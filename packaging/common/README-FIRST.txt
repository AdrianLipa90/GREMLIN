GREMLIN EARLY ACCESS — START HERE
=================================

1. Install GREMLIN for your operating system.
2. Open GREMLIN Control Center.
3. In Setup, paste your customer key beginning with GRM1- and choose Activate GREMLIN.
4. If your signed license requires a customer-specific GREMLIN profile, Control Center will ask for it. Drop the supplied JSON file onto the window and choose Import & verify customer profile. If the profile is optional, you can add it later without reconnecting your AI client.
5. GREMLIN detects supported AI clients installed on your computer.
6. Choose your client and press Connect & Test.
7. When Control Center shows READY, setup is complete.
8. Choose Launch Workspace for GREMLIN's local visual research surface, or continue inside your connected MCP client.

You do not need Python, pip, a virtual environment, or manual MCP JSON editing for supported clients.
GREMLIN Workspace binds to loopback only and remains subject to the same signed license/profile capability gates as the product MCP.

Supported on Windows:
- OpenAI Codex
- OpenCode
- Anthropic Claude Code
- Anthropic Claude Desktop
- Google Gemini CLI
- Cursor
- Visual Studio Code / GitHub Copilot
- Windsurf

Supported on Linux:
- OpenAI Codex
- OpenCode
- Anthropic Claude Code
- Google Gemini CLI
- Cursor
- Visual Studio Code / GitHub Copilot
- Windsurf

ChatGPT clean-account setup
---------------------------

ChatGPT is not treated as another local desktop MCP client. A fresh ChatGPT account must pass the dedicated clean-account gate.

Run:

gremlin-chatgpt-clean --json

The bootstrap is fail-closed. It requires all of the following before READY:
- supported ChatGPT web surface explicitly confirmed;
- developer mode explicitly confirmed for the target account/workspace;
- either a deployed public HTTPS /mcp endpoint or an admitted Secure MCP Tunnel route;
- GREMLIN app/plugin registration explicitly confirmed;
- ChatGPT tool scan explicitly PASS;
- the actual account capability recorded as read or full.

The clean-account path must not depend on prior chat history, ChatGPT Memory, NOEMA Library state, or an existing GREMLIN account/session.

Full instructions:
packaging/common/CHATGPT-CLEAN-INSTALL.md

If setup does not reach READY, open Diagnostics in Control Center. It will show the action still required.
For support, Diagnostics can export a sanitized committed report without license keys, config contents or provider command output.

For Early Access onboarding support, contact the seller through Contra.

GREMLIN
Stop shouting at your AI. Give it architecture.
