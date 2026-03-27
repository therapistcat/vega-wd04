import fs from "fs/promises";
import path from "path";

import express from "express";
import axios from "axios";
import pino from "pino";
import qrcode from "qrcode-terminal";
import {
  DisconnectReason,
  downloadMediaMessage,
  fetchLatestBaileysVersion,
  makeWASocket,
  useMultiFileAuthState,
} from "@whiskeysockets/baileys";

const PORT = Number(process.env.PORT || 3000);
const FASTAPI_WHATSAPP_URL =
  process.env.FASTAPI_WHATSAPP_URL || "http://127.0.0.1:8000/api/v1/whatsapp/message";
const AUTH_DIR = process.env.BAILEYS_AUTH_DIR || "./auth_info";
const MAX_FORWARD_RETRIES = Number(process.env.BAILEYS_FORWARD_RETRIES || 3);
const logger = pino({ level: process.env.LOG_LEVEL || "info" });

const app = express();
app.use(express.json({ limit: "50mb" }));

let sock = null;
let reconnectTimer = null;
let bridgeState = {
  connected: false,
  connecting: false,
  lastQrAt: null,
  lastConnectedAt: null,
  lastClosedAt: null,
  lastDisconnectReason: null,
  reconnectCount: 0,
  loggedInPhone: null,
};

function extractDigits(value) {
  return String(value || "").replace(/\D/g, "");
}

function isValidPhone(phone) {
  return Boolean(phone) && /^\d+$/.test(phone) && phone.length <= 15;
}

function toReplyJid(input) {
  const phone = extractDigits(String(input || "").split("@")[0]);
  if (!isValidPhone(phone)) {
    return null;
  }
  return `${phone}@s.whatsapp.net`;
}

function resolvePhoneFromMessage(message) {
  const rawJid = String(message?.key?.remoteJid || "");
  let phone = null;

  if (rawJid.endsWith("@s.whatsapp.net")) {
    phone = extractDigits(rawJid.replace("@s.whatsapp.net", ""));
  } else if (rawJid.endsWith("@lid")) {
    const participantCandidates = [
      message?.participant,
      message?.key?.participant,
      message?.message?.deviceSentMessage?.destinationJid,
    ];

    for (const candidate of participantCandidates) {
      const candidateValue = String(candidate || "");
      if (!candidateValue.endsWith("@s.whatsapp.net")) {
        continue;
      }
      const candidatePhone = extractDigits(candidateValue.replace("@s.whatsapp.net", ""));
      if (isValidPhone(candidatePhone)) {
        phone = candidatePhone;
        break;
      }
    }
  } else {
    phone = extractDigits(rawJid.split("@")[0]);
  }

  console.log(`RAW JID: ${rawJid} | EXTRACTED PHONE: ${phone || "INVALID"}`);

  if (!isValidPhone(phone)) {
    logger.warn({ rawJid, extractedPhone: phone }, "Unable to resolve a valid phone number from incoming message");
    return null;
  }

  return { rawJid, phone, replyJid: `${phone}@s.whatsapp.net` };
}

async function ensureAuthDir() {
  await fs.mkdir(AUTH_DIR, { recursive: true });
}

async function resetAuthDir() {
  logger.warn({ authDir: AUTH_DIR }, "Resetting Baileys auth directory");
  await fs.rm(AUTH_DIR, { recursive: true, force: true });
  await ensureAuthDir();
}

function markState(patch) {
  bridgeState = { ...bridgeState, ...patch };
}

function scheduleReconnect(reason = "unknown") {
  if (reconnectTimer) {
    return;
  }
  markState({
    connected: false,
    connecting: false,
    lastDisconnectReason: reason,
    reconnectCount: bridgeState.reconnectCount + 1,
  });
  logger.warn({ reason, reconnectCount: bridgeState.reconnectCount }, "Scheduling bridge reconnect");
  reconnectTimer = setTimeout(async () => {
    reconnectTimer = null;
    try {
      await startBridge();
    } catch (error) {
      logger.error({ error }, "Bridge reconnect failed");
      scheduleReconnect("reconnect_failure");
    }
  }, 3000);
}

async function bufferToBase64(buffer) {
  if (!buffer) return "";
  return Buffer.from(buffer).toString("base64");
}

async function normalizeIncomingMessage(message) {
  const resolvedSender = resolvePhoneFromMessage(message);
  if (!resolvedSender) {
    return null;
  }

  const { phone, rawJid, replyJid } = resolvedSender;
  const content =
    message.message?.conversation
      ? { type: "text", text: message.message.conversation }
      : message.message?.extendedTextMessage?.text
        ? { type: "text", text: message.message.extendedTextMessage.text }
        : message.message?.audioMessage
          ? { type: "audio", raw: message.message.audioMessage }
          : message.message?.imageMessage
            ? { type: "image", raw: message.message.imageMessage }
            : message.message?.videoMessage
              ? { type: "video", raw: message.message.videoMessage }
              : message.message?.locationMessage
                ? { type: "location", raw: message.message.locationMessage }
                : null;

  if (!phone || !content) {
    return null;
  }

  if (content.type === "text") {
    return { phone, type: "text", text: content.text, replyJid, rawJid };
  }

  if (content.type === "location") {
    return {
      phone,
      type: "location",
      replyJid,
      rawJid,
      location: {
        latitude: content.raw.degreesLatitude,
        longitude: content.raw.degreesLongitude,
      },
    };
  }

  const mediaBuffer = await downloadMediaMessage(
    message,
    "buffer",
    {},
    {
      logger,
      reuploadRequest: sock?.updateMediaMessage,
    },
  );

  const mediaBase64 = await bufferToBase64(mediaBuffer);

  if (content.type === "audio") {
    return {
      phone,
      type: "audio",
      replyJid,
      rawJid,
      audio: {
        base64: mediaBase64,
        mime_type: content.raw.mimetype || "audio/ogg",
      },
    };
  }

  if (content.type === "image") {
    return {
      phone,
      type: "image",
      replyJid,
      rawJid,
      image: {
        base64: mediaBase64,
        mime_type: content.raw.mimetype || "image/jpeg",
      },
    };
  }

  if (content.type === "video") {
    return {
      phone,
      type: "video",
      replyJid,
      rawJid,
      video: {
        base64: mediaBase64,
        mime_type: content.raw.mimetype || "video/mp4",
      },
    };
  }

  return null;
}

async function forwardToFastAPI(payload) {
  let lastError = null;
  for (let attempt = 1; attempt <= MAX_FORWARD_RETRIES; attempt += 1) {
    try {
      await axios.post(FASTAPI_WHATSAPP_URL, payload, {
        timeout: 60000,
        headers: { "Content-Type": "application/json" },
      });
      logger.info({ phone: payload.phone, type: payload.type, attempt }, "Forwarded message to FastAPI");
      return;
    } catch (error) {
      lastError = error;
      logger.error({ error, attempt, phone: payload.phone, type: payload.type }, "Failed forwarding message to FastAPI");
    }
  }
  throw lastError;
}

async function buildSocket() {
  await ensureAuthDir();
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  const nextSock = makeWASocket({
    auth: state,
    version,
    printQRInTerminal: false,
    logger,
    markOnlineOnConnect: false,
    browser: ["Mumbai Smart Civic", "Chrome", "1.0.0"],
    defaultQueryTimeoutMs: 60000,
    connectTimeoutMs: 60000,
    retryRequestDelayMs: 250,
    keepAliveIntervalMs: 15000,
    emitOwnEvents: false,
    syncFullHistory: false,
    generateHighQualityLinkPreview: false,
    getMessage: async () => undefined,
  });

  nextSock.ev.on("creds.update", saveCreds);
  return nextSock;
}

async function startBridge() {
  if (bridgeState.connecting) {
    logger.info("Bridge connection attempt already in progress");
    return;
  }

  markState({ connecting: true });
  logger.info({ authDir: path.resolve(AUTH_DIR) }, "Starting Baileys bridge");

  sock = await buildSocket();

  sock.ev.on("connection.update", async ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      markState({ lastQrAt: new Date().toISOString(), connected: false, loggedInPhone: null });
      logger.info("QR generated. Scan it with the test phone. Keep only one WhatsApp Web session active.");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "open") {
      const loggedInPhone = extractDigits(String(sock?.user?.id || "").split("@")[0]) || null;
      markState({
        connecting: false,
        connected: true,
        lastConnectedAt: new Date().toISOString(),
        lastDisconnectReason: null,
        loggedInPhone,
      });
      logger.info({ phone: loggedInPhone }, "Baileys bridge connected");
    }

    if (connection === "close") {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const reason = statusCode || "unknown";
      markState({
        connecting: false,
        connected: false,
        lastClosedAt: new Date().toISOString(),
        lastDisconnectReason: String(reason),
      });
      logger.warn({ reason }, "Baileys connection closed");

      if (statusCode === DisconnectReason.loggedOut) {
        logger.warn("WhatsApp session logged out. Clearing stale auth and requiring fresh QR.");
        try {
          await resetAuthDir();
        } catch (error) {
          logger.error({ error }, "Failed to reset auth directory after logout");
        }
        scheduleReconnect("logged_out");
        return;
      }

      scheduleReconnect(String(reason));
    }
  });

  sock.ev.on("messages.upsert", async ({ messages }) => {
    for (const msg of messages || []) {
      try {
        if (msg.key?.fromMe) continue;
        const normalized = await normalizeIncomingMessage(msg);
        if (!normalized) {
          logger.info("Skipping unsupported incoming WhatsApp payload");
          continue;
        }
        await forwardToFastAPI(normalized);
      } catch (error) {
        logger.error({ error }, "Failed to process incoming WhatsApp message");
      }
    }
  });
}

app.post("/send", async (req, res) => {
  try {
    const phoneInput = req.body?.phone || req.body?.jid;
    const replyJid = toReplyJid(phoneInput);
    const text = String(req.body?.text || "").trim();
    if (!replyJid || !text) {
      logger.error({ phoneInput, textLength: text.length }, "Invalid phone or text for WhatsApp send");
      return res.status(400).json({ ok: false, error: "phone and text are required" });
    }
    if (!bridgeState.connected || !sock) {
      return res.status(503).json({ ok: false, error: "WhatsApp bridge is not connected" });
    }

    let lastError = null;
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      try {
        logger.info({ jid: replyJid, attempt }, "Sending to JID");
        await sock.sendMessage(replyJid, { text });
        logger.info({ jid: replyJid, attempt }, "WhatsApp message sent");
        return res.json({ ok: true });
      } catch (error) {
        lastError = error;
        logger.error({ error, jid: replyJid, attempt }, "Failed to send WhatsApp message");
      }
    }

    return res.status(500).json({ ok: false, error: String(lastError) });
  } catch (error) {
    logger.error({ error }, "Unhandled /send failure");
    return res.status(500).json({ ok: false, error: String(error) });
  }
});

app.post("/reset-session", async (_req, res) => {
  try {
    await resetAuthDir();
    markState({
      connected: false,
      connecting: false,
      loggedInPhone: null,
      lastDisconnectReason: "manual_reset",
    });
    scheduleReconnect("manual_reset");
    return res.json({ ok: true });
  } catch (error) {
    logger.error({ error }, "Failed to reset session");
    return res.status(500).json({ ok: false, error: String(error) });
  }
});

app.get("/health", (_req, res) => {
  res.json({
    ok: true,
    service: "baileys-bridge",
    connected: bridgeState.connected,
    connecting: bridgeState.connecting,
    logged_in_phone: bridgeState.loggedInPhone,
    last_qr_at: bridgeState.lastQrAt,
    last_connected_at: bridgeState.lastConnectedAt,
    last_closed_at: bridgeState.lastClosedAt,
    last_disconnect_reason: bridgeState.lastDisconnectReason,
    reconnect_count: bridgeState.reconnectCount,
    auth_dir: path.resolve(AUTH_DIR),
  });
});

app.listen(PORT, () => {
  logger.info(
    { port: PORT, fastapi: FASTAPI_WHATSAPP_URL, authDir: path.resolve(AUTH_DIR) },
    "Baileys bridge listening",
  );
  logger.info("Use only one active WhatsApp Web session for the test account while troubleshooting.");
});

resetAuthDir()
  .then(() => startBridge())
  .catch((error) => {
    logger.error({ error }, "Failed to start Baileys bridge");
    process.exit(1);
  });
