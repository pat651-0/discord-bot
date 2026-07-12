from __future__ import annotations

import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

try:
    import jwt
except ImportError:
    jwt = None

INDEX_HTML = '<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n  <meta name="theme-color" content="#070b16">\n  <meta name="color-scheme" content="dark">\n  <title>XSI Control</title>\n  <link rel="manifest" href="/manifest.webmanifest">\n  <style>\n    :root {\n      --bg: #070b16;\n      --surface: #0e1628;\n      --surface-2: #121d33;\n      --surface-3: #17233a;\n      --border: rgba(148, 163, 184, 0.16);\n      --text: #f8fafc;\n      --muted: #94a3b8;\n      --muted-2: #64748b;\n      --purple: #8b5cf6;\n      --blue: #2563eb;\n      --cyan: #22d3ee;\n      --green: #22c55e;\n      --amber: #f59e0b;\n      --red: #ef4444;\n      --shadow: 0 24px 64px rgba(0, 0, 0, 0.34);\n      --radius-xl: 26px;\n      --radius-lg: 20px;\n      --radius-md: 15px;\n    }\n\n    * { box-sizing: border-box; }\n    html { background: var(--bg); }\n    body {\n      margin: 0;\n      min-height: 100vh;\n      color: var(--text);\n      background:\n        radial-gradient(circle at 10% -10%, rgba(124, 58, 237, 0.25), transparent 34%),\n        radial-gradient(circle at 100% 10%, rgba(37, 99, 235, 0.14), transparent 30%),\n        var(--bg);\n      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,\n        "Segoe UI", Roboto, Helvetica, Arial, sans-serif;\n      -webkit-font-smoothing: antialiased;\n      padding-bottom: calc(84px + env(safe-area-inset-bottom));\n    }\n\n    button, input, textarea { font: inherit; }\n    button { -webkit-tap-highlight-color: transparent; }\n    svg { display: block; }\n\n    .app-header {\n      position: sticky;\n      top: 0;\n      z-index: 30;\n      padding:\n        max(14px, env(safe-area-inset-top))\n        18px\n        12px;\n      background: linear-gradient(\n        to bottom,\n        rgba(7, 11, 22, 0.98),\n        rgba(7, 11, 22, 0.90),\n        rgba(7, 11, 22, 0)\n      );\n      backdrop-filter: blur(18px);\n    }\n\n    .header-inner {\n      max-width: 860px;\n      margin: 0 auto;\n      display: flex;\n      align-items: center;\n      justify-content: space-between;\n      gap: 14px;\n    }\n\n    .brand {\n      min-width: 0;\n      display: flex;\n      align-items: center;\n      gap: 12px;\n    }\n\n    .brand-mark {\n      width: 48px;\n      height: 48px;\n      flex: 0 0 auto;\n      border-radius: 16px;\n      display: grid;\n      place-items: center;\n      font-weight: 900;\n      letter-spacing: -0.04em;\n      color: #fff;\n      background: linear-gradient(135deg, var(--purple), var(--blue));\n      box-shadow: 0 14px 34px rgba(99, 102, 241, 0.35);\n    }\n\n    .brand-copy { min-width: 0; }\n    .brand-copy h1 {\n      margin: 0;\n      font-size: 20px;\n      line-height: 1.1;\n      letter-spacing: -0.02em;\n    }\n    .brand-copy p {\n      margin: 4px 0 0;\n      color: var(--muted);\n      font-size: 12px;\n      white-space: nowrap;\n      overflow: hidden;\n      text-overflow: ellipsis;\n    }\n\n    .connection-badge {\n      display: inline-flex;\n      align-items: center;\n      gap: 7px;\n      border-radius: 999px;\n      padding: 8px 11px;\n      font-size: 11px;\n      font-weight: 800;\n      letter-spacing: 0.05em;\n      color: #86efac;\n      background: rgba(34, 197, 94, 0.10);\n      border: 1px solid rgba(34, 197, 94, 0.28);\n    }\n\n    .connection-badge.offline {\n      color: #fde68a;\n      background: rgba(245, 158, 11, 0.10);\n      border-color: rgba(245, 158, 11, 0.26);\n    }\n\n    .status-dot {\n      width: 7px;\n      height: 7px;\n      border-radius: 50%;\n      background: currentColor;\n      box-shadow: 0 0 12px currentColor;\n    }\n\n    main {\n      width: min(100%, 860px);\n      margin: 0 auto;\n      padding: 4px 16px 24px;\n    }\n\n    .page { display: none; animation: pageIn 0.22s ease; }\n    .page.active { display: block; }\n    @keyframes pageIn {\n      from { opacity: 0; transform: translateY(5px); }\n      to { opacity: 1; transform: translateY(0); }\n    }\n\n    .hero {\n      position: relative;\n      overflow: hidden;\n      border: 1px solid rgba(139, 92, 246, 0.30);\n      border-radius: var(--radius-xl);\n      padding: 22px;\n      background:\n        linear-gradient(135deg, rgba(91, 33, 182, 0.54), rgba(17, 34, 66, 0.82));\n      box-shadow: var(--shadow);\n    }\n\n    .hero::after {\n      content: "";\n      position: absolute;\n      width: 170px;\n      height: 170px;\n      right: -70px;\n      top: -75px;\n      border-radius: 50%;\n      background: radial-gradient(circle, rgba(34, 211, 238, 0.28), transparent 66%);\n    }\n\n    .hero-top {\n      position: relative;\n      z-index: 1;\n      display: flex;\n      justify-content: space-between;\n      gap: 18px;\n      align-items: flex-start;\n    }\n\n    .hero h2 {\n      margin: 0;\n      font-size: clamp(25px, 7vw, 34px);\n      line-height: 1.08;\n      letter-spacing: -0.045em;\n    }\n\n    .hero p {\n      max-width: 520px;\n      margin: 10px 0 0;\n      color: #dbeafe;\n      font-size: 13px;\n      line-height: 1.55;\n    }\n\n    .hero-orb {\n      width: 58px;\n      height: 58px;\n      flex: 0 0 auto;\n      border: 0;\n      border-radius: 20px;\n      display: grid;\n      place-items: center;\n      color: white;\n      cursor: pointer;\n      background: linear-gradient(145deg, #a78bfa, #4f46e5);\n      box-shadow: 0 14px 36px rgba(124, 58, 237, 0.40);\n      transition: transform 0.14s ease, box-shadow 0.14s ease, filter 0.14s ease;\n    }\n\n    .hero-orb:hover {\n      filter: brightness(1.07);\n      box-shadow: 0 17px 40px rgba(124, 58, 237, 0.48);\n    }\n\n    .hero-orb:active {\n      transform: scale(0.94);\n    }\n\n    .hero-orb:focus-visible {\n      outline: 3px solid rgba(34, 211, 238, 0.55);\n      outline-offset: 3px;\n    }\n\n    .hero-meta {\n      position: relative;\n      z-index: 1;\n      display: flex;\n      flex-wrap: wrap;\n      gap: 9px;\n      margin-top: 18px;\n    }\n\n    .meta-pill {\n      border-radius: 999px;\n      padding: 7px 10px;\n      font-size: 11px;\n      font-weight: 700;\n      color: #e2e8f0;\n      background: rgba(15, 23, 42, 0.48);\n      border: 1px solid rgba(226, 232, 240, 0.12);\n    }\n\n    .stats-grid {\n      display: grid;\n      grid-template-columns: repeat(2, minmax(0, 1fr));\n      gap: 12px;\n      margin-top: 14px;\n    }\n\n    .card {\n      border: 1px solid var(--border);\n      border-radius: var(--radius-lg);\n      background: linear-gradient(155deg, rgba(18, 29, 51, 0.96), rgba(12, 20, 36, 0.96));\n      box-shadow: 0 14px 38px rgba(0, 0, 0, 0.20);\n    }\n\n    .stat-card {\n      min-height: 128px;\n      padding: 16px;\n    }\n\n    .eyebrow {\n      color: var(--muted);\n      font-size: 11px;\n      font-weight: 750;\n      letter-spacing: 0.08em;\n      text-transform: uppercase;\n    }\n\n    .stat-value {\n      display: flex;\n      align-items: center;\n      gap: 8px;\n      margin-top: 9px;\n      font-size: clamp(22px, 6vw, 29px);\n      line-height: 1.05;\n      font-weight: 850;\n      letter-spacing: -0.045em;\n    }\n\n    .stat-help {\n      margin-top: 8px;\n      color: var(--muted);\n      font-size: 11px;\n      line-height: 1.35;\n    }\n\n    .section-head {\n      display: flex;\n      align-items: center;\n      justify-content: space-between;\n      gap: 14px;\n      margin: 23px 2px 11px;\n    }\n\n    .section-head h3 {\n      margin: 0;\n      font-size: 18px;\n      letter-spacing: -0.025em;\n    }\n\n    .section-head span {\n      color: var(--muted);\n      font-size: 11px;\n    }\n\n    .action-grid {\n      display: grid;\n      grid-template-columns: repeat(2, minmax(0, 1fr));\n      gap: 11px;\n    }\n\n    .action-card {\n      min-height: 112px;\n      padding: 15px;\n      border: 1px solid var(--border);\n      border-radius: 19px;\n      color: var(--text);\n      text-align: left;\n      background: linear-gradient(150deg, var(--surface-2), var(--surface));\n      transition: transform 0.13s ease, border-color 0.13s ease, background 0.13s ease;\n    }\n\n    .action-card:active {\n      transform: scale(0.975);\n      border-color: rgba(139, 92, 246, 0.52);\n      background: linear-gradient(150deg, #1c2a46, #111a2e);\n    }\n\n    .action-icon,\n    .list-icon {\n      display: grid;\n      place-items: center;\n      color: #c4b5fd;\n      background: rgba(124, 58, 237, 0.16);\n    }\n\n    .action-icon {\n      width: 36px;\n      height: 36px;\n      border-radius: 12px;\n    }\n\n    .action-card strong {\n      display: block;\n      margin-top: 13px;\n      font-size: 14px;\n    }\n\n    .action-card small {\n      display: block;\n      margin-top: 4px;\n      color: var(--muted);\n      font-size: 11px;\n      line-height: 1.35;\n    }\n\n    .panel {\n      padding: 18px;\n    }\n\n    .panel h3 {\n      margin: 0;\n      font-size: 18px;\n      letter-spacing: -0.025em;\n    }\n\n    .panel-copy {\n      margin: 7px 0 0;\n      color: var(--muted);\n      font-size: 12px;\n      line-height: 1.5;\n    }\n\n    .field { margin-top: 15px; }\n    .field label {\n      display: block;\n      margin-bottom: 7px;\n      color: #cbd5e1;\n      font-size: 12px;\n      font-weight: 700;\n    }\n\n    input, textarea {\n      width: 100%;\n      color: var(--text);\n      background: rgba(5, 8, 22, 0.88);\n      border: 1px solid rgba(100, 116, 139, 0.48);\n      border-radius: var(--radius-md);\n      padding: 13px 14px;\n      outline: none;\n      transition: border-color 0.15s ease, box-shadow 0.15s ease;\n    }\n\n    input:focus, textarea:focus {\n      border-color: var(--purple);\n      box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.13);\n    }\n\n    textarea {\n      min-height: 132px;\n      resize: vertical;\n      line-height: 1.5;\n    }\n\n    .primary-btn,\n    .secondary-btn,\n    .danger-btn,\n    .tiny-btn {\n      border: 0;\n      border-radius: 14px;\n      font-weight: 800;\n      color: white;\n    }\n\n    .primary-btn,\n    .secondary-btn,\n    .danger-btn {\n      width: 100%;\n      min-height: 48px;\n      margin-top: 11px;\n      padding: 12px 15px;\n    }\n\n    .primary-btn {\n      background: linear-gradient(135deg, var(--purple), var(--blue));\n      box-shadow: 0 12px 30px rgba(37, 99, 235, 0.22);\n    }\n\n    .secondary-btn {\n      background: var(--surface-3);\n      border: 1px solid var(--border);\n    }\n\n    .danger-btn { background: #7f1d1d; }\n    .primary-btn:active,\n    .secondary-btn:active,\n    .danger-btn:active,\n    .tiny-btn:active { transform: scale(0.985); }\n\n    .notice {\n      margin-bottom: 13px;\n      border-radius: 16px;\n      padding: 12px 14px;\n      color: #fde68a;\n      background: rgba(245, 158, 11, 0.09);\n      border: 1px solid rgba(245, 158, 11, 0.25);\n      font-size: 11px;\n      line-height: 1.5;\n    }\n\n    .list {\n      display: flex;\n      flex-direction: column;\n      gap: 9px;\n    }\n\n    .list-item {\n      display: flex;\n      align-items: center;\n      gap: 12px;\n      min-height: 70px;\n      padding: 12px;\n      border: 1px solid var(--border);\n      border-radius: 17px;\n      background: linear-gradient(145deg, var(--surface-2), var(--surface));\n    }\n\n    .list-icon {\n      width: 42px;\n      height: 42px;\n      flex: 0 0 auto;\n      border-radius: 14px;\n    }\n\n    .list-copy {\n      min-width: 0;\n      flex: 1;\n    }\n\n    .list-copy strong {\n      display: block;\n      font-size: 13px;\n      white-space: nowrap;\n      overflow: hidden;\n      text-overflow: ellipsis;\n    }\n\n    .list-copy p {\n      margin: 5px 0 0;\n      color: var(--muted);\n      font-size: 10px;\n      line-height: 1.35;\n    }\n\n    .tiny-btn {\n      flex: 0 0 auto;\n      padding: 8px 10px;\n      color: #ddd6fe;\n      background: rgba(124, 58, 237, 0.14);\n      border: 1px solid rgba(139, 92, 246, 0.28);\n      font-size: 10px;\n    }\n\n    .code-box {\n      margin-top: 14px;\n      padding: 14px;\n      min-height: 210px;\n      border-radius: 16px;\n      overflow: auto;\n      color: #bae6fd;\n      background: rgba(3, 7, 18, 0.88);\n      border: 1px solid rgba(51, 65, 85, 0.55);\n      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;\n      font-size: 10px;\n      line-height: 1.65;\n      white-space: pre-wrap;\n      overflow-wrap: anywhere;\n    }\n\n    .connection-summary {\n      display: grid;\n      grid-template-columns: 1fr auto;\n      align-items: center;\n      gap: 14px;\n      margin-top: 14px;\n      padding: 14px;\n      border-radius: 16px;\n      background: rgba(5, 8, 22, 0.58);\n      border: 1px solid var(--border);\n    }\n\n    .connection-summary strong {\n      display: block;\n      font-size: 13px;\n    }\n\n    .connection-summary span {\n      display: block;\n      margin-top: 4px;\n      color: var(--muted);\n      font-size: 10px;\n    }\n\n    .bottom-nav {\n      position: fixed;\n      left: 0;\n      right: 0;\n      bottom: 0;\n      z-index: 40;\n      padding: 8px 9px calc(8px + env(safe-area-inset-bottom));\n      background: rgba(7, 11, 22, 0.95);\n      border-top: 1px solid var(--border);\n      backdrop-filter: blur(20px);\n    }\n\n    .nav-inner {\n      max-width: 860px;\n      margin: 0 auto;\n      display: grid;\n      grid-template-columns: repeat(5, minmax(0, 1fr));\n      gap: 2px;\n    }\n\n    .nav-btn {\n      min-width: 0;\n      padding: 6px 2px 5px;\n      border: 0;\n      color: var(--muted);\n      background: transparent;\n      font-size: 9px;\n      font-weight: 700;\n    }\n\n    .nav-icon {\n      width: 21px;\n      height: 21px;\n      margin: 0 auto 4px;\n    }\n\n    .nav-btn.active { color: #c4b5fd; }\n\n    .modal {\n      position: fixed;\n      inset: 0;\n      z-index: 80;\n      display: none;\n      align-items: flex-end;\n      justify-content: center;\n      background: rgba(2, 6, 23, 0.76);\n      backdrop-filter: blur(8px);\n    }\n\n    .modal.show { display: flex; }\n\n    .sheet {\n      width: min(100%, 860px);\n      max-height: 88vh;\n      overflow: auto;\n      padding: 20px 18px calc(18px + env(safe-area-inset-bottom));\n      border-radius: 26px 26px 0 0;\n      background: #0d1629;\n      border: 1px solid var(--border);\n      box-shadow: 0 -30px 80px rgba(0, 0, 0, 0.45);\n    }\n\n    .sheet-handle {\n      width: 42px;\n      height: 4px;\n      margin: -5px auto 17px;\n      border-radius: 99px;\n      background: #334155;\n    }\n\n    .sheet h3 { margin: 0; font-size: 20px; }\n    .sheet p {\n      margin: 8px 0 0;\n      color: var(--muted);\n      font-size: 12px;\n      line-height: 1.55;\n    }\n\n    .toast {\n      position: fixed;\n      z-index: 100;\n      left: 50%;\n      bottom: calc(90px + env(safe-area-inset-bottom));\n      max-width: calc(100vw - 32px);\n      transform: translate(-50%, 24px);\n      opacity: 0;\n      pointer-events: none;\n      padding: 10px 14px;\n      border-radius: 999px;\n      color: white;\n      background: #1e293b;\n      border: 1px solid var(--border);\n      box-shadow: var(--shadow);\n      font-size: 11px;\n      text-align: center;\n      transition: 0.22s ease;\n    }\n\n    .toast.show {\n      opacity: 1;\n      transform: translate(-50%, 0);\n    }\n\n    .spinner {\n      display: inline-block;\n      width: 15px;\n      height: 15px;\n      margin-right: 7px;\n      vertical-align: -2px;\n      border: 2px solid rgba(255,255,255,0.32);\n      border-top-color: white;\n      border-radius: 50%;\n      animation: spin 0.75s linear infinite;\n    }\n    @keyframes spin { to { transform: rotate(360deg); } }\n\n    @media (min-width: 680px) {\n      .stats-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }\n      .action-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }\n      .action-card { min-height: 128px; }\n      main { padding-left: 22px; padding-right: 22px; }\n    }\n  </style>\n</head>\n<body>\n  <header class="app-header">\n    <div class="header-inner">\n      <div class="brand">\n        <div class="brand-mark">XSI</div>\n        <div class="brand-copy">\n          <h1>XSI Control</h1>\n          <p>Private bot command centre</p>\n        </div>\n      </div>\n      <div id="connectionBadge" class="connection-badge offline">\n        <span class="status-dot"></span>\n        <span id="connectionBadgeText">DEMO</span>\n      </div>\n    </div>\n  </header>\n\n  <main>\n    <section id="home" class="page active">\n      <div class="hero">\n        <div class="hero-top">\n          <div>\n            <h2>Welcome back</h2>\n            <p>\n              Monitor your bot, review AI-generated updates, manage GitHub pull\n              requests and control deployments from one clean mobile dashboard.\n            </p>\n          </div>\n          <button\n            type="button"\n            class="hero-orb"\n            aria-label="Create an AI update request"\n            title="Create an AI update request"\n            onclick="openUpdateComposer()"\n          >\n            <svg width="25" height="25" viewBox="0 0 24 24" fill="none" aria-hidden="true">\n              <path d="M12 3v18M3 12h18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>\n            </svg>\n          </button>\n        </div>\n        <div class="hero-meta">\n          <span class="meta-pill">V23 self-update core</span>\n          <span class="meta-pill">Owner protected</span>\n          <span class="meta-pill">GitHub ready</span>\n        </div>\n      </div>\n\n      <div class="stats-grid">\n        <article class="card stat-card">\n          <div class="eyebrow">Bot status</div>\n          <div class="stat-value">\n            <span class="status-dot" style="color:#22c55e"></span>\n            <span id="botStatusValue">Online</span>\n          </div>\n          <div id="botStatusHelp" class="stat-help">Demo connection</div>\n        </article>\n\n        <article class="card stat-card">\n          <div class="eyebrow">Version</div>\n          <div id="versionValue" class="stat-value">V23</div>\n          <div class="stat-help">Self-update core</div>\n        </article>\n\n        <article class="card stat-card">\n          <div class="eyebrow">Open updates</div>\n          <div id="openUpdatesValue" class="stat-value">2</div>\n          <div class="stat-help">Awaiting review</div>\n        </article>\n\n        <article class="card stat-card">\n          <div class="eyebrow">Security</div>\n          <div class="stat-value">Protected</div>\n          <div class="stat-help">Approval required</div>\n        </article>\n      </div>\n\n      <div class="section-head">\n        <h3>Quick controls</h3>\n        <span>Owner only</span>\n      </div>\n\n      <div class="action-grid">\n        <button class="action-card" onclick="requestAction(\'restart\')">\n          <span class="action-icon">\n            <svg width="19" height="19" viewBox="0 0 24 24" fill="none">\n              <path d="M20 11a8 8 0 10-2.34 5.66M20 4v7h-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>\n            </svg>\n          </span>\n          <strong>Restart bot</strong>\n          <small>Restart the current service</small>\n        </button>\n\n        <button class="action-card" onclick="requestAction(\'redeploy\')">\n          <span class="action-icon">\n            <svg width="19" height="19" viewBox="0 0 24 24" fill="none">\n              <path d="M12 3l8 8-8 8-8-8 8-8z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>\n              <path d="M12 7v8M9 12l3 3 3-3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>\n            </svg>\n          </span>\n          <strong>Redeploy</strong>\n          <small>Deploy the latest main branch</small>\n        </button>\n\n        <button class="action-card" onclick="openPage(\'updates\')">\n          <span class="action-icon">\n            <svg width="19" height="19" viewBox="0 0 24 24" fill="none">\n              <path d="M12 3l1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7L12 3zM19 16l.9 2.1L22 19l-2.1.9L19 22l-.9-2.1L16 19l2.1-.9L19 16z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>\n            </svg>\n          </span>\n          <strong>AI update</strong>\n          <small>Request a new feature</small>\n        </button>\n\n        <button class="action-card" onclick="openPage(\'logs\')">\n          <span class="action-icon">\n            <svg width="19" height="19" viewBox="0 0 24 24" fill="none">\n              <path d="M7 4h10M7 9h10M7 14h7M5 2h14a2 2 0 012 2v16a2 2 0 01-2 2H5a2 2 0 01-2-2V4a2 2 0 012-2z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>\n            </svg>\n          </span>\n          <strong>View logs</strong>\n          <small>Inspect recent activity</small>\n        </button>\n      </div>\n\n      <div class="section-head">\n        <h3>Recent activity</h3>\n        <span>Latest events</span>\n      </div>\n\n      <div id="activityList" class="list">\n        <article class="list-item">\n          <div class="list-icon">\n            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">\n              <path d="M5 12l4 4L19 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>\n            </svg>\n          </div>\n          <div class="list-copy">\n            <strong>Bot deployment healthy</strong>\n            <p>Railway service is responding normally</p>\n          </div>\n        </article>\n\n        <article class="list-item">\n          <div class="list-icon">\n            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">\n              <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="2"/>\n              <path d="M8 13c2-4 6-4 8 0" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>\n            </svg>\n          </div>\n          <div class="list-copy">\n            <strong>Colour database active</strong>\n            <p>31,930 searchable colour names loaded</p>\n          </div>\n        </article>\n\n        <article class="list-item">\n          <div class="list-icon">\n            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">\n              <path d="M12 3l7 3v5c0 4.7-2.8 8-7 10-4.2-2-7-5.3-7-10V6l7-3z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>\n            </svg>\n          </div>\n          <div class="list-copy">\n            <strong>Sentinel monitoring</strong>\n            <p>No critical security alerts</p>\n          </div>\n        </article>\n      </div>\n    </section>\n\n    <section id="updates" class="page">\n      <div id="updateNotice" class="notice">\n        You are currently in demo mode. Connect the hosted XSI Control API in\n        Settings to create real GitHub update requests and manage pull requests.\n      </div>\n\n      <article class="card panel">\n        <h3>AI Update Centre</h3>\n        <p class="panel-copy">\n          Describe the feature, fix or behaviour you want. Connected mode submits\n          it to your protected V23 update workflow.\n        </p>\n        <div class="field">\n          <label for="updateRequest">Update request</label>\n          <textarea id="updateRequest" placeholder="Example: Add a trusted trader reputation system with reviews, badges and admin controls"></textarea>\n        </div>\n        <button id="createUpdateButton" class="primary-btn" onclick="createUpdateRequest()">\n          Create update request\n        </button>\n      </article>\n\n      <div class="section-head">\n        <h3>Pull requests</h3>\n        <span id="pullCountLabel">2 pending</span>\n      </div>\n\n      <div id="pullList" class="list">\n        <button class="list-item" style="width:100%;color:inherit;text-align:left" onclick="showDemoPull(41)">\n          <div class="list-icon">41</div>\n          <div class="list-copy">\n            <strong>Advanced server analytics</strong>\n            <p>Tests passed · Medium change · Tap to review</p>\n          </div>\n          <span class="tiny-btn">Review</span>\n        </button>\n        <button class="list-item" style="width:100%;color:inherit;text-align:left" onclick="showDemoPull(42)">\n          <div class="list-icon">42</div>\n          <div class="list-copy">\n            <strong>Ticket satisfaction surveys</strong>\n            <p>Tests passed · Low risk · Tap to review</p>\n          </div>\n          <span class="tiny-btn">Review</span>\n        </button>\n      </div>\n    </section>\n\n    <section id="apps" class="page">\n      <div class="notice">\n        App installations create reviewed server-side updates. They do not\n        download executable Android code.\n      </div>\n\n      <div class="section-head">\n        <h3>XSI App Store</h3>\n        <span>Private catalogue</span>\n      </div>\n\n      <div class="list">\n        <article class="list-item">\n          <div class="list-icon">\n            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">\n              <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="2"/>\n              <path d="M9 12h6M12 9v6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>\n            </svg>\n          </div>\n          <div class="list-copy">\n            <strong>Economy & Shop</strong>\n            <p>Coins, rewards, inventory and purchases</p>\n          </div>\n          <button class="tiny-btn" onclick="installDemoApp(\'Economy & Shop\')">Install</button>\n        </article>\n\n        <article class="list-item">\n          <div class="list-icon">\n            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">\n              <path d="M7 19V9M12 19V5M17 19v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>\n            </svg>\n          </div>\n          <div class="list-copy">\n            <strong>Levels & Rank Cards</strong>\n            <p>XP, leaderboards and custom rank images</p>\n          </div>\n          <button class="tiny-btn" onclick="installDemoApp(\'Levels & Rank Cards\')">Install</button>\n        </article>\n\n        <article class="list-item">\n          <div class="list-icon">\n            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">\n              <path d="M12 3l2.2 4.5 5 .7-3.6 3.5.9 5-4.5-2.4-4.5 2.4.9-5L4.8 8.2l5-.7L12 3z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>\n            </svg>\n          </div>\n          <div class="list-copy">\n            <strong>Trusted Trader</strong>\n            <p>Reviews, ratings and verification badges</p>\n          </div>\n          <button class="tiny-btn" onclick="installDemoApp(\'Trusted Trader\')">Install</button>\n        </article>\n\n        <article class="list-item">\n          <div class="list-icon">\n            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">\n              <path d="M5 19V8M10 19V4M15 19v-7M20 19V6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>\n            </svg>\n          </div>\n          <div class="list-copy">\n            <strong>Advanced Analytics</strong>\n            <p>Growth, activity, ticket and command insights</p>\n          </div>\n          <button class="tiny-btn" onclick="installDemoApp(\'Advanced Analytics\')">Install</button>\n        </article>\n      </div>\n    </section>\n\n    <section id="logs" class="page">\n      <article class="card panel">\n        <h3>Runtime logs</h3>\n        <p class="panel-copy">\n          Connected mode can display logs supplied by your private control API.\n        </p>\n        <div id="logBox" class="code-box">13:05:02  INFO  XSI logged in successfully\n13:05:03  INFO  Colour database ready\n13:05:03  INFO  Sentinel database ready\n13:05:04  INFO  99 slash commands registered\n13:05:05  INFO  Bot ready</div>\n        <button class="secondary-btn" onclick="refreshLogs()">Refresh logs</button>\n      </article>\n    </section>\n\n    <section id="settings" class="page">\n      <article class="card panel">\n        <h3>Secure connection</h3>\n        <p class="panel-copy">\n          Enter only your hosted Control API address and private owner key.\n          GitHub App credentials remain protected as Railway environment variables.\n        </p>\n\n        <div class="field">\n          <label for="apiUrl">Control API URL</label>\n          <input id="apiUrl" inputmode="url" autocomplete="url"\n                 placeholder="https://xsi-control-production.up.railway.app">\n        </div>\n\n        <div class="field">\n          <label for="ownerKey">Owner access key</label>\n          <input id="ownerKey" type="password" autocomplete="current-password"\n                 placeholder="Your private XSI control key">\n        </div>\n\n        <button id="connectButton" class="primary-btn" onclick="connectControlApi()">\n          Connect securely\n        </button>\n        <button class="secondary-btn" onclick="disconnectControlApi()">\n          Disconnect and use demo mode\n        </button>\n\n        <div class="connection-summary">\n          <div>\n            <strong id="connectionTitle">Demo mode</strong>\n            <span id="connectionDetail">No live backend is connected</span>\n          </div>\n          <span id="connectionDot" class="status-dot" style="color:#f59e0b"></span>\n        </div>\n      </article>\n\n      <div class="section-head">\n        <h3>GitHub connection</h3>\n        <span>Backend protected</span>\n      </div>\n\n      <article class="card panel">\n        <p class="panel-copy" style="margin-top:0">\n          The app never stores your GitHub private key. Your hosted backend uses\n          the GitHub App credentials already configured in Railway.\n        </p>\n        <div class="connection-summary">\n          <div>\n            <strong id="repoName">Not connected</strong>\n            <span id="repoDetail">Connect the Control API to verify your repository</span>\n          </div>\n          <span id="githubDot" class="status-dot" style="color:#64748b"></span>\n        </div>\n        <button class="secondary-btn" onclick="refreshStatus()">\n          Test GitHub connection\n        </button>\n      </article>\n\n      <div class="section-head">\n        <h3>Install on Android</h3>\n      </div>\n\n      <article class="card panel">\n        <p class="panel-copy" style="margin-top:0">\n          Once hosted, open the site in Chrome or Samsung Internet, open the\n          browser menu and choose <strong>Add to Home screen</strong>.\n        </p>\n      </article>\n    </section>\n  </main>\n\n  <nav class="bottom-nav">\n    <div class="nav-inner">\n      <button class="nav-btn active" data-page="home" onclick="openPage(\'home\', this)">\n        <svg class="nav-icon" viewBox="0 0 24 24" fill="none">\n          <path d="M4 11l8-7 8 7v9H4v-9z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>\n          <path d="M9 20v-6h6v6" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>\n        </svg>\n        Home\n      </button>\n\n      <button class="nav-btn" data-page="updates" onclick="openPage(\'updates\', this)">\n        <svg class="nav-icon" viewBox="0 0 24 24" fill="none">\n          <path d="M12 3l1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7L12 3z" stroke="currentColor" stroke-width="1.8"/>\n        </svg>\n        Updates\n      </button>\n\n      <button class="nav-btn" data-page="apps" onclick="openPage(\'apps\', this)">\n        <svg class="nav-icon" viewBox="0 0 24 24" fill="none">\n          <rect x="4" y="4" width="6" height="6" rx="1" stroke="currentColor" stroke-width="2"/>\n          <rect x="14" y="4" width="6" height="6" rx="1" stroke="currentColor" stroke-width="2"/>\n          <rect x="4" y="14" width="6" height="6" rx="1" stroke="currentColor" stroke-width="2"/>\n          <rect x="14" y="14" width="6" height="6" rx="1" stroke="currentColor" stroke-width="2"/>\n        </svg>\n        Apps\n      </button>\n\n      <button class="nav-btn" data-page="logs" onclick="openPage(\'logs\', this)">\n        <svg class="nav-icon" viewBox="0 0 24 24" fill="none">\n          <path d="M5 6h14M5 12h14M5 18h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>\n        </svg>\n        Logs\n      </button>\n\n      <button class="nav-btn" data-page="settings" onclick="openPage(\'settings\', this)">\n        <svg class="nav-icon" viewBox="0 0 24 24" fill="none">\n          <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/>\n          <path d="M19 12a7 7 0 00-.1-1l2-1.5-2-3.4-2.4 1A8 8 0 0015 6l-.4-2.6h-4L10 6a8 8 0 00-1.5 1.1l-2.4-1-2 3.4 2 1.5A7 7 0 006 12c0 .3 0 .7.1 1l-2 1.5 2 3.4 2.4-1A8 8 0 0010 18l.4 2.6h4L15 18a8 8 0 001.5-1.1l2.4 1 2-3.4-2-1.5c.1-.3.1-.7.1-1z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>\n        </svg>\n        Settings\n      </button>\n    </div>\n  </nav>\n\n  <div id="modal" class="modal" onclick="if(event.target===this) closeModal()">\n    <div class="sheet">\n      <div class="sheet-handle"></div>\n      <h3 id="modalTitle">Review update</h3>\n      <p id="modalText"></p>\n      <div id="modalCode" class="code-box" style="min-height:0"></div>\n      <button id="approveButton" class="primary-btn" onclick="approveCurrentPull()">Approve and merge</button>\n      <button class="danger-btn" onclick="rejectCurrentPull()">Reject update</button>\n      <button class="secondary-btn" onclick="closeModal()">Close</button>\n    </div>\n  </div>\n\n  <div id="toast" class="toast"></div>\n\n  <script>\n    const state = {\n      apiUrl: localStorage.getItem("xsi_control_api_url") || "",\n      ownerKey: localStorage.getItem("xsi_control_owner_key") || "",\n      token: sessionStorage.getItem("xsi_control_session") || "",\n      connected: false,\n      currentPull: null\n    };\n\n    function $(selector) { return document.querySelector(selector); }\n\n    function openUpdateComposer() {\n      openPage("updates");\n      window.setTimeout(() => {\n        const field = document.getElementById("updateRequest");\n        if (field) {\n          field.focus();\n          field.scrollIntoView({ behavior: "smooth", block: "center" });\n        }\n      }, 220);\n      showToast("Describe the feature you want to add.");\n    }\n\n    function openPage(pageId, button) {\n      document.querySelectorAll(".page").forEach(page => page.classList.remove("active"));\n      document.getElementById(pageId).classList.add("active");\n      document.querySelectorAll(".nav-btn").forEach(item => {\n        item.classList.toggle("active", item.dataset.page === pageId);\n      });\n      window.scrollTo({ top: 0, behavior: "smooth" });\n\n      if (pageId === "updates" && state.connected) loadPullRequests();\n      if (pageId === "logs" && state.connected) refreshLogs();\n      if (pageId === "settings") hydrateSettings();\n    }\n\n    function showToast(message) {\n      const toast = $("#toast");\n      toast.textContent = message;\n      toast.classList.add("show");\n      clearTimeout(showToast.timer);\n      showToast.timer = setTimeout(() => toast.classList.remove("show"), 2600);\n    }\n\n    function setButtonLoading(button, loading, text) {\n      if (!button) return;\n      if (loading) {\n        button.disabled = true;\n        button.dataset.original = button.textContent;\n        button.innerHTML = \'<span class="spinner"></span>\' + text;\n      } else {\n        button.disabled = false;\n        button.textContent = button.dataset.original || text;\n      }\n    }\n\n    function normaliseApiUrl(value) {\n      return value.trim().replace(/\\/+$/, "");\n    }\n\n    async function apiFetch(path, options = {}) {\n      if (!state.apiUrl) throw new Error("Control API URL is missing.");\n      const headers = new Headers(options.headers || {});\n      headers.set("Content-Type", "application/json");\n      if (state.token) headers.set("Authorization", "Bearer " + state.token);\n\n      const response = await fetch(state.apiUrl + path, {\n        ...options,\n        headers\n      });\n\n      let payload = null;\n      const contentType = response.headers.get("content-type") || "";\n      if (contentType.includes("application/json")) {\n        payload = await response.json();\n      } else {\n        payload = { detail: await response.text() };\n      }\n\n      if (!response.ok) {\n        throw new Error(payload.detail || payload.message || "Request failed.");\n      }\n      return payload;\n    }\n\n    function hydrateSettings() {\n      $("#apiUrl").value = state.apiUrl;\n      $("#ownerKey").value = state.ownerKey;\n    }\n\n    function setConnectionUi(connected, detail = "") {\n      state.connected = connected;\n      const badge = $("#connectionBadge");\n      const badgeText = $("#connectionBadgeText");\n\n      badge.classList.toggle("offline", !connected);\n      badgeText.textContent = connected ? "LIVE" : "DEMO";\n\n      $("#connectionTitle").textContent = connected ? "Connected securely" : "Demo mode";\n      $("#connectionDetail").textContent = connected\n        ? (detail || "Live XSI Control API connected")\n        : "No live backend is connected";\n      $("#connectionDot").style.color = connected ? "#22c55e" : "#f59e0b";\n\n      $("#updateNotice").style.display = connected ? "none" : "block";\n      $("#botStatusHelp").textContent = connected ? "Live control API" : "Demo connection";\n    }\n\n    async function connectControlApi() {\n      const button = $("#connectButton");\n      const apiUrl = normaliseApiUrl($("#apiUrl").value);\n      const ownerKey = $("#ownerKey").value;\n\n      if (!apiUrl || !ownerKey) {\n        showToast("Enter the Control API URL and owner key.");\n        return;\n      }\n\n      state.apiUrl = apiUrl;\n      state.ownerKey = ownerKey;\n      setButtonLoading(button, true, "Connecting");\n\n      try {\n        const loginResponse = await fetch(apiUrl + "/api/login", {\n          method: "POST",\n          headers: { "Content-Type": "application/json" },\n          body: JSON.stringify({ key: ownerKey })\n        });\n\n        const loginData = await loginResponse.json();\n        if (!loginResponse.ok) throw new Error(loginData.detail || "Login failed.");\n\n        state.token = loginData.token;\n        sessionStorage.setItem("xsi_control_session", state.token);\n        localStorage.setItem("xsi_control_api_url", state.apiUrl);\n        localStorage.setItem("xsi_control_owner_key", state.ownerKey);\n\n        setConnectionUi(true, "Owner session authenticated");\n        await refreshStatus();\n        showToast("XSI Control connected.");\n      } catch (error) {\n        setConnectionUi(false);\n        showToast(error.message || "Connection failed.");\n      } finally {\n        setButtonLoading(button, false, "Connect securely");\n      }\n    }\n\n    function disconnectControlApi() {\n      state.apiUrl = "";\n      state.ownerKey = "";\n      state.token = "";\n      sessionStorage.removeItem("xsi_control_session");\n      localStorage.removeItem("xsi_control_api_url");\n      localStorage.removeItem("xsi_control_owner_key");\n      hydrateSettings();\n      setConnectionUi(false);\n\n      $("#repoName").textContent = "Not connected";\n      $("#repoDetail").textContent = "Connect the Control API to verify your repository";\n      $("#githubDot").style.color = "#64748b";\n      $("#openUpdatesValue").textContent = "2";\n      $("#pullCountLabel").textContent = "2 pending";\n      showToast("Demo mode enabled.");\n    }\n\n    async function refreshStatus() {\n      if (!state.token) {\n        showToast("Connect the Control API first.");\n        return;\n      }\n\n      try {\n        const status = await apiFetch("/api/status");\n        setConnectionUi(true, "Repository and backend verified");\n        $("#repoName").textContent = status.repo || "GitHub connected";\n        $("#repoDetail").textContent =\n          (status.private ? "Private repository" : "Public repository") +\n          " · " + (status.default_branch || "main") +\n          " · latest " + ((status.latest_commit || {}).sha || "unknown");\n        $("#githubDot").style.color = "#22c55e";\n        $("#openUpdatesValue").textContent = String(status.open_pull_requests || 0);\n        $("#pullCountLabel").textContent =\n          String(status.open_pull_requests || 0) + " pending";\n      } catch (error) {\n        $("#repoName").textContent = "Connection problem";\n        $("#repoDetail").textContent = error.message;\n        $("#githubDot").style.color = "#ef4444";\n        showToast(error.message);\n      }\n    }\n\n    async function createUpdateRequest() {\n      const request = $("#updateRequest").value.trim();\n      const button = $("#createUpdateButton");\n\n      if (!request) {\n        showToast("Describe the feature or change first.");\n        return;\n      }\n\n      if (!state.connected) {\n        const title = request.split("\\n")[0].slice(0, 70);\n        addDemoPull(43, title);\n        $("#updateRequest").value = "";\n        showToast("Demo update request created.");\n        return;\n      }\n\n      setButtonLoading(button, true, "Submitting");\n      try {\n        const result = await apiFetch("/api/update-request", {\n          method: "POST",\n          body: JSON.stringify({ request })\n        });\n        $("#updateRequest").value = "";\n        showToast("Update request #" + result.number + " created.");\n        await loadPullRequests();\n      } catch (error) {\n        showToast(error.message);\n      } finally {\n        setButtonLoading(button, false, "Create update request");\n      }\n    }\n\n    function addDemoPull(number, title) {\n      const list = $("#pullList");\n      const item = document.createElement("button");\n      item.className = "list-item";\n      item.style.cssText = "width:100%;color:inherit;text-align:left";\n      item.onclick = () => showDemoPull(number);\n      item.innerHTML =\n        \'<div class="list-icon">\' + number + \'</div>\' +\n        \'<div class="list-copy"><strong></strong><p>AI analysis queued · Demo proposal</p></div>\' +\n        \'<span class="tiny-btn">Review</span>\';\n      item.querySelector("strong").textContent = title;\n      list.prepend(item);\n      $("#openUpdatesValue").textContent = "3";\n      $("#pullCountLabel").textContent = "3 pending";\n    }\n\n    async function loadPullRequests() {\n      if (!state.connected) return;\n      try {\n        const pulls = await apiFetch("/api/pulls");\n        const list = $("#pullList");\n        list.innerHTML = "";\n\n        if (!pulls.length) {\n          list.innerHTML =\n            \'<article class="list-item"><div class="list-copy">\' +\n            \'<strong>No open pull requests</strong>\' +\n            \'<p>Your update queue is clear.</p></div></article>\';\n        }\n\n        pulls.forEach(pull => {\n          const item = document.createElement("button");\n          item.className = "list-item";\n          item.style.cssText = "width:100%;color:inherit;text-align:left";\n          item.onclick = () => openPullReview(pull);\n          item.innerHTML =\n            \'<div class="list-icon">\' + pull.number + \'</div>\' +\n            \'<div class="list-copy"><strong></strong><p></p></div>\' +\n            \'<span class="tiny-btn">Review</span>\';\n          item.querySelector("strong").textContent = pull.title || "Untitled update";\n          item.querySelector("p").textContent =\n            (pull.branch || "branch") + " · opened by " + (pull.user || "unknown");\n          list.appendChild(item);\n        });\n\n        $("#openUpdatesValue").textContent = String(pulls.length);\n        $("#pullCountLabel").textContent = String(pulls.length) + " pending";\n      } catch (error) {\n        showToast(error.message);\n      }\n    }\n\n    function showDemoPull(number) {\n      state.currentPull = { number, demo: true };\n      $("#modalTitle").textContent = "Proposal #" + number;\n      $("#modalText").textContent =\n        "This is a demonstration proposal. A live proposal would show the exact " +\n        "GitHub branch, tests, changed files and merge status.";\n      $("#modalCode").textContent =\n        "Branch: xsi-ai/proposal-" + number + "\\n" +\n        "Risk: LOW\\n" +\n        "Validation: 6/6 passed\\n" +\n        "Deployment: waits for owner approval";\n      $("#modal").classList.add("show");\n    }\n\n    function openPullReview(pull) {\n      state.currentPull = pull;\n      $("#modalTitle").textContent = "Pull request #" + pull.number;\n      $("#modalText").textContent =\n        "Review this GitHub update before approving it. Merging will allow the " +\n        "connected deployment platform to deploy the new main branch.";\n      $("#modalCode").textContent =\n        "Title: " + (pull.title || "") + "\\n" +\n        "Branch: " + (pull.branch || "") + "\\n" +\n        "Author: " + (pull.user || "") + "\\n" +\n        "URL: " + (pull.url || "");\n      $("#modal").classList.add("show");\n    }\n\n    function closeModal() {\n      $("#modal").classList.remove("show");\n    }\n\n    async function approveCurrentPull() {\n      const pull = state.currentPull;\n      if (!pull) return;\n\n      if (pull.demo || !state.connected) {\n        closeModal();\n        showToast("Demo proposal approved.");\n        return;\n      }\n\n      try {\n        await apiFetch("/api/pulls/" + pull.number + "/merge", { method: "POST" });\n        closeModal();\n        showToast("Pull request merged.");\n        await loadPullRequests();\n        await refreshStatus();\n      } catch (error) {\n        showToast(error.message);\n      }\n    }\n\n    async function rejectCurrentPull() {\n      const pull = state.currentPull;\n      if (!pull) return;\n\n      if (pull.demo || !state.connected) {\n        closeModal();\n        showToast("Demo proposal rejected.");\n        return;\n      }\n\n      try {\n        await apiFetch("/api/pulls/" + pull.number + "/reject", { method: "POST" });\n        closeModal();\n        showToast("Pull request closed.");\n        await loadPullRequests();\n        await refreshStatus();\n      } catch (error) {\n        showToast(error.message);\n      }\n    }\n\n    async function requestAction(action) {\n      if (!state.connected) {\n        showToast(\n          action === "restart"\n            ? "Restart simulated in demo mode."\n            : "Redeploy simulated in demo mode."\n        );\n        return;\n      }\n\n      try {\n        await apiFetch("/api/actions/" + action, { method: "POST" });\n        showToast(action === "restart" ? "Restart requested." : "Redeploy requested.");\n      } catch (error) {\n        showToast(error.message);\n      }\n    }\n\n    async function refreshLogs() {\n      if (!state.connected) {\n        showToast("Demo logs refreshed.");\n        return;\n      }\n\n      try {\n        const result = await apiFetch("/api/logs");\n        $("#logBox").textContent = (result.lines || []).join("\\n") || "No logs available.";\n        showToast("Logs refreshed.");\n      } catch (error) {\n        showToast(error.message);\n      }\n    }\n\n    function installDemoApp(name) {\n      $("#updateRequest").value =\n        "Install the XSI app: " + name +\n        ". Keep it modular, add tests and create a reviewed GitHub pull request.";\n      openPage("updates");\n      showToast(name + " added to the update request.");\n    }\n\n    window.addEventListener("load", async () => {\n      hydrateSettings();\n      if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {\n        navigator.serviceWorker.register("/sw.js").catch(() => {});\n      }\n\n      if (state.apiUrl && state.ownerKey) {\n        try {\n          await connectControlApi();\n        } catch (_) {\n          setConnectionUi(false);\n        }\n      } else {\n        setConnectionUi(false);\n      }\n    });\n  </script>\n</body>\n</html>\n'
MANIFEST_JSON = '{\n  "name": "XSI Control",\n  "short_name": "XSI Control",\n  "description": "Private mobile control centre for the XSI Discord bot.",\n  "start_url": "/",\n  "scope": "/",\n  "display": "standalone",\n  "background_color": "#070b16",\n  "theme_color": "#070b16"\n}'
SERVICE_WORKER_JS = 'const CACHE = "xsi-control-clean-v3";\nconst CORE = ["/", "/static/index.html", "/manifest.webmanifest"];\nself.addEventListener("install", event => {\n  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE)));\n});\nself.addEventListener("activate", event => {\n  event.waitUntil(\n    caches.keys().then(keys =>\n      Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))\n    )\n  );\n});\nself.addEventListener("fetch", event => {\n  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));\n});\n'

app = FastAPI(
    title="XSI Control API",
    docs_url="/api/docs",
    redoc_url=None,
)

allowed_origins_raw = os.getenv("XSI_ALLOWED_ORIGINS", "*").strip()
allowed_origins = (
    ["*"]
    if allowed_origins_raw == "*"
    else [item.strip() for item in allowed_origins_raw.split(",") if item.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

SESSION_SECONDS = 12 * 60 * 60
sessions: dict[str, float] = {}
github_token_cache: dict[str, Any] = {"token": "", "expires_at": 0.0}


class LoginBody(BaseModel):
    key: str = Field(min_length=8, max_length=500)


class UpdateRequestBody(BaseModel):
    request: str = Field(min_length=5, max_length=5000)


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def require_session(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Owner login required.")

    token = authorization[7:].strip()
    expires_at = sessions.get(token, 0.0)
    if expires_at <= time.time():
        sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Owner session expired.")
    return token


def repository() -> tuple[str, str]:
    owner = env("GITHUB_REPO_OWNER")
    repo = env("GITHUB_REPO_NAME")
    if not owner or not repo:
        raise HTTPException(
            status_code=503,
            detail="GITHUB_REPO_OWNER and GITHUB_REPO_NAME are not configured.",
        )
    return owner, repo


def create_github_app_token() -> str:
    direct_token = env("GITHUB_TOKEN")
    if direct_token:
        return direct_token

    cached = str(github_token_cache.get("token") or "")
    cached_expiry = float(github_token_cache.get("expires_at") or 0.0)
    if cached and cached_expiry > time.time() + 120:
        return cached

    app_id = env("GITHUB_APP_ID")
    installation_id = env("GITHUB_INSTALLATION_ID")
    private_key = os.getenv("GITHUB_PRIVATE_KEY", "").replace("\\n", "\n").strip()

    if not app_id or not installation_id or not private_key:
        raise HTTPException(
            status_code=503,
            detail="GitHub App credentials are not configured on the backend.",
        )
    if jwt is None:
        raise HTTPException(
            status_code=500,
            detail="PyJWT[crypto] is required for GitHub App authentication.",
        )

    now = int(time.time())
    app_jwt = jwt.encode(
        {"iat": now - 60, "exp": now + 540, "iss": app_id},
        private_key,
        algorithm="RS256",
    )

    request = urllib.request.Request(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        data=b"{}",
        method="POST",
        headers={
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "XSI-Control",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise HTTPException(
            status_code=502,
            detail=f"GitHub App authentication failed: {detail}",
        ) from exc
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub connection failed: {exc.reason}",
        ) from exc

    token = str(payload.get("token") or "")
    expires_at_text = str(payload.get("expires_at") or "")
    if not token:
        raise HTTPException(status_code=502, detail="GitHub returned no installation token.")

    # Installation tokens normally last an hour. Cache conservatively for 50 minutes.
    github_token_cache["token"] = token
    github_token_cache["expires_at"] = time.time() + 50 * 60
    return token


def github_api(
    path: str,
    *,
    method: str = "GET",
    payload: Any | None = None,
) -> Any:
    token = create_github_app_token()
    url = "https://api.github.com" + path
    body = json.dumps(payload).encode("utf-8") if payload is not None else None

    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "XSI-Control",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1600]
        raise HTTPException(
            status_code=exc.code if 400 <= exc.code < 600 else 502,
            detail=f"GitHub API error: {detail}",
        ) from exc
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub connection failed: {exc.reason}",
        ) from exc


def optional_service_request(
    *,
    url_env: str,
    token_env: str,
    method: str = "POST",
) -> dict[str, Any]:
    url = env(url_env)
    token = env(token_env)
    if not url:
        raise HTTPException(
            status_code=501,
            detail=f"{url_env} is not configured for this optional action.",
        )

    request = urllib.request.Request(
        url,
        data=b"{}" if method != "GET" else None,
        method=method,
        headers={
            "Authorization": f"Bearer {token}" if token else "",
            "Content-Type": "application/json",
            "User-Agent": "XSI-Control",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": response.status,
                "body": raw[:2000],
            }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise HTTPException(status_code=502, detail=f"Service action failed: {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Service connection failed: {exc.reason}") from exc


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.get("/manifest.webmanifest")
def manifest() -> Response:
    return Response(
        MANIFEST_JSON,
        media_type="application/manifest+json",
    )


@app.get("/sw.js")
def service_worker() -> Response:
    return Response(
        SERVICE_WORKER_JS,
        media_type="application/javascript",
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "xsi-control",
        "version": "professional-clean-v2",
    }


@app.post("/api/login")
def login(body: LoginBody) -> dict[str, Any]:
    configured_key = env("XSI_CONTROL_ADMIN_KEY")
    if not configured_key:
        raise HTTPException(
            status_code=503,
            detail="XSI_CONTROL_ADMIN_KEY is not configured.",
        )

    if not secrets.compare_digest(body.key, configured_key):
        raise HTTPException(status_code=403, detail="Incorrect owner access key.")

    token = secrets.token_urlsafe(40)
    sessions[token] = time.time() + SESSION_SECONDS
    return {"token": token, "expires_in": SESSION_SECONDS}


@app.get("/api/status")
def status(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_session(authorization)
    owner, repo = repository()

    repository_data = github_api(f"/repos/{owner}/{repo}")
    pulls = github_api(f"/repos/{owner}/{repo}/pulls?state=open&per_page=50")
    commits = github_api(f"/repos/{owner}/{repo}/commits?per_page=1")
    latest = commits[0] if isinstance(commits, list) and commits else {}

    return {
        "repo": repository_data.get("full_name"),
        "private": bool(repository_data.get("private")),
        "default_branch": repository_data.get("default_branch"),
        "open_pull_requests": len(pulls) if isinstance(pulls, list) else 0,
        "latest_commit": {
            "sha": str(latest.get("sha") or "")[:8],
            "message": str(
                ((latest.get("commit") or {}).get("message") or "")
            ).splitlines()[0][:160],
        },
    }


@app.get("/api/pulls")
def list_pulls(authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
    require_session(authorization)
    owner, repo = repository()
    pulls = github_api(f"/repos/{owner}/{repo}/pulls?state=open&per_page=30")

    return [
        {
            "number": pull.get("number"),
            "title": pull.get("title"),
            "branch": (pull.get("head") or {}).get("ref"),
            "base": (pull.get("base") or {}).get("ref"),
            "url": pull.get("html_url"),
            "user": (pull.get("user") or {}).get("login"),
            "draft": bool(pull.get("draft")),
        }
        for pull in (pulls if isinstance(pulls, list) else [])
    ]


@app.post("/api/pulls/{number}/merge")
def merge_pull(
    number: int,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    require_session(authorization)
    owner, repo = repository()
    return github_api(
        f"/repos/{owner}/{repo}/pulls/{number}/merge",
        method="PUT",
        payload={
            "merge_method": "squash",
            "commit_title": f"XSI approved update #{number}",
        },
    )


@app.post("/api/pulls/{number}/reject")
def reject_pull(
    number: int,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    require_session(authorization)
    owner, repo = repository()
    return github_api(
        f"/repos/{owner}/{repo}/pulls/{number}",
        method="PATCH",
        payload={"state": "closed"},
    )


@app.post("/api/update-request")
def create_update_request(
    body: UpdateRequestBody,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    require_session(authorization)
    owner, repo = repository()
    title = body.request.strip().splitlines()[0][:100]

    labels = [item.strip() for item in env(
        "XSI_UPDATE_REQUEST_LABELS",
        "xsi-update-request",
    ).split(",") if item.strip()]

    issue_payload: dict[str, Any] = {
        "title": f"[XSI Update] {title}",
        "body": (
            "## XSI mobile update request\n\n"
            f"{body.request.strip()}\n\n"
            "_Created from the private XSI Control app. "
            "This request still requires the normal V23 AI analysis, tests and owner approval._"
        ),
    }
    if labels:
        issue_payload["labels"] = labels

    issue = github_api(
        f"/repos/{owner}/{repo}/issues",
        method="POST",
        payload=issue_payload,
    )
    return {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "url": issue.get("html_url"),
    }


@app.post("/api/actions/restart")
def restart_action(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    require_session(authorization)
    return optional_service_request(
        url_env="XSI_RESTART_WEBHOOK_URL",
        token_env="XSI_RESTART_WEBHOOK_TOKEN",
    )


@app.post("/api/actions/redeploy")
def redeploy_action(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    require_session(authorization)
    return optional_service_request(
        url_env="XSI_REDEPLOY_WEBHOOK_URL",
        token_env="XSI_REDEPLOY_WEBHOOK_TOKEN",
    )


@app.get("/api/logs")
def logs(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_session(authorization)
    log_url = env("XSI_LOGS_ENDPOINT_URL")
    log_token = env("XSI_LOGS_ENDPOINT_TOKEN")

    if not log_url:
        return {
            "lines": [
                "Live log endpoint is not configured.",
                "Set XSI_LOGS_ENDPOINT_URL on the Control API service.",
            ]
        }

    request = urllib.request.Request(
        log_url,
        method="GET",
        headers={
            "Authorization": f"Bearer {log_token}" if log_token else "",
            "User-Agent": "XSI-Control",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise HTTPException(status_code=502, detail=f"Log endpoint failed: {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Log endpoint connection failed: {exc.reason}") from exc

    return {"lines": text.splitlines()[-200:]}
