//versión validada en servidor DE INDEX
//29 abril 2025 FUNCIONANDO SIN CONTROL DE HUMANO

const { webcrypto } = require('crypto');
globalThis.crypto = webcrypto;
const { makeWASocket, useMultiFileAuthState, DisconnectReason } = require("@whiskeysockets/baileys");
const { Boom } = require("@hapi/boom");
const axios = require("axios");
const mensajesProcesados = new Set();
let botRetryCount = 0;
const MAX_BOT_RETRIES = 5; // Intentar reiniciar el bot hasta 5 veces
const BOT_RETRY_DELAY = 15000; // Esperar 15 segundos entre reintentos

const MAX_GPT_RETRIES = 3;
const GPT_RETRY_DELAY = 5000;

async function callGPT(message, sender, retryCount = 0) {
    try {
        console.log({ level: 30, time: new Date().toISOString(), pid: process.pid, hostname: require('os').hostname(), class: "gpt", msg: "Enviando mensaje a GPT:", message: message, from: sender });
        const response = await axios.post("http://195.26.243.211:5000/gpt", {
            message: message,
            from: sender,
            timeout: 10000
        }, {
            timeout: 10000
        });

        if (response.data.status === "human_active" || response.data.reply === null) {
            console.log("👤 Humano activo o sin respuesta del bot. No se envía mensaje.");
            return null;
        } else {
            const gptReply = response.data.reply || "🤖 Lo siento, no pude procesar tu solicitud en este momento.";
            console.log({ level: 30, time: new Date().toISOString(), pid: process.pid, hostname: require('os').hostname(), class: "gpt", msg: "🧠 GPT respondió:", reply: gptReply });
            return gptReply;
        }
    } catch (error) {
        console.error("❌ Error al comunicarse con GPT:", error);
        if (retryCount < MAX_GPT_RETRIES) {
            console.log(`🔌 Reintentando llamada a GPT en ${GPT_RETRY_DELAY / 1000} segundos... (Intento ${retryCount + 1}/${MAX_GPT_RETRIES})`);
            await new Promise(resolve => setTimeout(resolve, GPT_RETRY_DELAY));
            return callGPT(message, sender, retryCount + 1);
        } else {
            console.error(`🚫 Se alcanzó el máximo de reintentos al llamar a GPT.`);
            throw error; // Re-lanza el error para que lo capture el manejador principal
        }
    }
}

async function startBot() {
    // console.log(`🤖 Intentando iniciar el bot (intento ${botRetryCount + 1})...`); // Log de depuración, puede ser ruidoso
    try {
        const { state, saveCreds } = await useMultiFileAuthState("auth_info_baileys");

    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: true,
        crypto: crypto
    });

    // Eventos
    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("connection.update", ({ connection, lastDisconnect }) => {
        if (connection === "close") {
            // @ts-ignore // Ignorar posible error de TypeScript si no lo usas
            const statusCode = lastDisconnect.error?.output?.statusCode;
            const isLoggedOut = statusCode === DisconnectReason.loggedOut;
            const isConflict = lastDisconnect.error?.message?.includes('Stream Errored (conflict)') ||
                               lastDisconnect.error?.output?.payload?.error?.includes('conflict');

            console.log("❌ Conexión cerrada."); // Mantener este log
            if (lastDisconnect.error && !isLoggedOut) { // No loguear el error si es un logout normal
                console.error("🔍 Razón de desconexión:", lastDisconnect.error);
            }

            if (isLoggedOut) {
                console.log("🚫 Sesión cerrada explícitamente. No se reconectará. Elimina 'auth_info_baileys' y reinicia.");
                // Podrías querer limpiar auth_info_baileys aquí si es apropiado
                // require('fs').rmSync('./auth_info_baileys', { recursive: true, force: true });
                // process.exit(1); // O simplemente salir
                return; // No reconectar
            } else if (isConflict) {
                console.warn("⚔️ Conflicto de sesión (reemplazada). Se intentará reconectar."); // Cambiado a warn
                // Para conflictos, a veces es mejor esperar un poco más o forzar una nueva sesión.
                // Por ahora, solo reintentaremos como cualquier otra desconexión no-logout.
                // Podrías considerar eliminar auth_info_baileys aquí si los conflictos son persistentes.
            }

            // Lógica de reconexión general
            if (botRetryCount < MAX_BOT_RETRIES) {
                console.log(`🔌 Intentando reconectar el bot en ${BOT_RETRY_DELAY / 1000} segundos...`);
                setTimeout(() => {
                    botRetryCount++;
                    startBot();
                }, BOT_RETRY_DELAY);
            } else {
                console.error(`🚫 Se alcanzó el máximo de reintentos (${MAX_BOT_RETRIES}). El bot no se reiniciará más.`);
                process.exit(1); // Salir si no se puede reconectar después de varios intentos
            }
        } else if (connection === "open") {
            console.log("✅ ¡Bot conectado exitosamente!");
            botRetryCount = 0; // Resetear contador de reintentos en conexión exitosa
        }
        // La llave de cierre extra y el 'else if' duplicado se eliminan.
        // El '});' de abajo es el cierre correcto del callback de sock.ev.on("connection.update", ...).
    });

    sock.ev.on("messages.upsert", async ({ messages }) => {
        const msg = messages[0];
        if (!msg.message || msg.key.fromMe || !msg.key.id) return;
        if (mensajesProcesados.has(msg.key.id)) return;
        mensajesProcesados.add(msg.key.id);
        setTimeout(() => mensajesProcesados.delete(msg.key.id), 30000);

        const texto = extractMessageText(msg);
        if (!texto || texto.trim().length < 2) return;

        const sender = msg.key.remoteJid;
        // console.log("💬 Mensaje recibido:", texto); // Puede ser muy verboso para producción

        // ====== INICIO: CÓDIGO AÑADIDO (Verificación si es un grupo) ======
        // Verificar si el remitente (sender) es un JID de grupo.
        // Los JID de grupo en baileys suelen terminar en '@g.us'.
        if (sender && sender.endsWith('@g.us')) {
            console.log(`🚪 [GRUPO] Mensaje de ${sender} ignorado (proviene de un grupo).`);
            return; // Si es un grupo, sale de la función y no procesa más el mensaje.
        }
        // ====== FIN: CÓDIGO AÑADIDO (Verificación si es un grupo) ======


        // 🔐 Detectar si es un token tipo Totalpass (5-8 caracteres, alfanumérico, sin espacios)
        //  const tokenRegex = /^[A-Z0-9]{5,8}$/i;
        // if (tokenRegex.test(texto.trim())) {
        //     const respuestaToken = "✅ ¡Gracias por enviar tu token de Totalpass! Ya quedó registrado para tu clase. 💪";
        //     //console.log("🔐 Token detectado. Respuesta automática enviada.");
        //     //await sock.sendMessage(sender, { text: respuestaToken });
        //     //return;
        // }

        // 🧠 GPT: enviar a servidor Flask
        try {
            const gptReply = await callGPT(texto, sender);
            if (gptReply) {
                 console.log({ level: 30, time: new Date().toISOString(), pid: process.pid, hostname: require('os').hostname(), class: "gpt", msg: "🧠 GPT respondió:", reply: gptReply });
                await sock.sendMessage(sender, { text: gptReply });
            }
        } catch (error) {
            console.error("❌ Error al comunicarse con GPT:", error);
            await sock.sendMessage(sender, { text: "⚠️ No se pudo obtener respuesta de la IA." });
        }
    });
    } catch (error) { // Catch para el try que inicia en la línea 16
        console.error("❌ Error crítico dentro de startBot:", error); // Mantener este error
        // Reintentar iniciar el bot si no se han superado los reintentos
        if (botRetryCount < MAX_BOT_RETRIES) {
            // console.log(`🔌 Reintentando startBot en ${BOT_RETRY_DELAY / 1000} segundos debido a error crítico interno...`); // Log de depuración
            setTimeout(() => {
                botRetryCount++;
                startBot(); // La llamada recursiva a startBot ya está envuelta en el catch de la llamada inicial
            }, BOT_RETRY_DELAY);
        } else {
            console.error(`🚫 Se alcanzó el máximo de reintentos en startBot. Saliendo.`);
            process.exit(1);
        }
    }
}

//  Función auxiliar para extraer texto limpio
function extractMessageText(msg) {
    return msg.message?.conversation ||
           msg.message?.extendedTextMessage?.text ||
           msg.message?.imageMessage?.caption ||
           null;
}

// Manejador global de promesas no capturadas (ayuda con errores como los Timeouts)
process.on('unhandledRejection', (reason, promise) => {
   console.error('🚫 Promesa rechazada no manejada en:', promise, 'razón:', reason);
   // Podrías decidir reiniciar el bot aquí también, con precaución para evitar bucles.
   // Por ejemplo, podrías incrementar un contador de errores graves y salir si excede un umbral.
});

process.on('uncaughtException', (error, origin) => {
   console.error('🚫 Error no capturado:', error);
   console.error('🚫 Origen del error:', origin);
   // Es más seguro salir en un error no capturado, ya que el estado de la app puede ser inconsistente.
   process.exit(1);
});


// Iniciar el bot
startBot().catch(err => {
   console.error("❌ Error fatal al iniciar el bot la primera vez:", err); // Mantener este error
   if (botRetryCount < MAX_BOT_RETRIES) {
       // console.log(`🔌 Reintentando iniciar el bot en ${BOT_RETRY_DELAY / 1000} segundos debido a error fatal inicial...`); // Log de depuración
       setTimeout(() => {
           botRetryCount++;
           startBot(); // La llamada recursiva a startBot ya está envuelta en el catch de la llamada inicial
       }, BOT_RETRY_DELAY);
   } else {
        console.error(`🚫 Se alcanzó el máximo de reintentos (${MAX_BOT_RETRIES}) durante el inicio inicial. Saliendo.`);
        process.exit(1);
   }
});
