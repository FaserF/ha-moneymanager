# Security Best Practices for Home Assistant MoneyManager Integration

When integrating your MoneyManager Android App (PC Manager) with Home Assistant, it is recommended to follow basic security guidelines.

## 1. Network Exposure
The PC Manager feature runs an embedded HTTP server directly on your mobile device (default port: `8888`).
- Keep the server confined to your private local home network (LAN / Wi-Fi).
- Never expose the PC Manager port directly to the public internet without a reverse proxy or VPN.

## 2. Passcode Protection
MoneyManager provides an optional passcode setting within the PC Manager screen on Android.
- If you share your local network with untrusted guests or devices, enable the passcode option in MoneyManager.
- Configure the same passcode in the Home Assistant integration options.

## 3. Data Privacy & Offline Fallback
- The integration only connects to your smartphone locally. No telemetry or financial data leaves your local network.
- When the PC Manager server is turned off, Home Assistant securely keeps the last known state in memory and persistent storage without deleting historical entity values.
