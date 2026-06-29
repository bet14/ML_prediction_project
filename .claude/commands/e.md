Exit the session: save log then close.

Steps:
1. Run /savelog first — save all session activities to SESSION_LOG.md.
2. After saving, confirm to the user: "Session log saved. Closing..."
3. Then run this bash command to close the terminal window:

```bash
taskkill /F /IM cmd.exe /T 2>/dev/null; taskkill /F /IM WindowsTerminal.exe /T 2>/dev/null; exit
```

If taskkill does not work, tell the user to close the window manually. Do not retry or loop.
