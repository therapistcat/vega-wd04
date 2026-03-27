import express from "express";

const PORT = Number(process.env.PORT || 3000);
const app = express();

app.get("/health", (_req, res) => {
  res.json({
    ok: true,
    service: "whatsapp-bridge",
    transport: "whapi-cloud",
    note: "Baileys transport is disabled. Configure Whapi to call FastAPI directly.",
  });
});

app.listen(PORT, () => {
  console.log(`Whapi transport placeholder listening on port ${PORT}`);
  console.log("Baileys/QR/auth_info flow is disabled. Use Whapi webhook -> FastAPI directly.");
});
