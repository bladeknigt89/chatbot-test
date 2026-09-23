(function () {
  "use strict";

  if (window.__LocalAIChatWidgetLoaded) {
    return;
  }
  window.__LocalAIChatWidgetLoaded = true;

  function currentScript() {
    return document.currentScript || document.querySelector("script[data-agent][src*='chat-widget']");
  }

  var script = currentScript();
  var agentId = (script && script.getAttribute("data-agent")) || "";
  var apiKey = (script && script.getAttribute("data-api-key")) || "";
  var apiBase = (script && script.getAttribute("data-api-base")) || guessApiBase(script);
  var userConfig = window.ChatWidgetConfig || {};

  function guessApiBase(node) {
    if (!node || !node.src) {
      return window.location.origin;
    }
    try {
      var url = new URL(node.src, window.location.href);
      return url.origin;
    } catch (err) {
      return window.location.origin;
    }
  }

  var state = {
    open: false,
    loading: false,
    sessionId: null,
    messages: [],
    config: {
      primaryColor: userConfig.primaryColor || "#2563eb",
      title: userConfig.title || "Chat",
      position: userConfig.position || "right",
      welcomeMessage: userConfig.welcomeMessage || "Üdvözlöm! Miben segíthetek?",
      showSources: userConfig.showSources !== false
    }
  };

  var style = document.createElement("style");
  style.textContent = [
    ".lacw-root{all:initial;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;position:fixed;z-index:2147483000;bottom:20px;}",
    ".lacw-root *{box-sizing:border-box;font-family:inherit;}",
    ".lacw-launcher{width:56px;height:56px;border:0;border-radius:50%;color:#fff;cursor:pointer;box-shadow:0 10px 24px rgba(15,23,42,.25);display:flex;align-items:center;justify-content:center;}",
    ".lacw-panel{width:min(380px,calc(100vw - 24px));height:min(560px,calc(100vh - 100px));background:#fff;border-radius:18px;box-shadow:0 18px 50px rgba(15,23,42,.28);display:flex;flex-direction:column;overflow:hidden;margin-bottom:12px;}",
    ".lacw-header{padding:14px 16px;color:#fff;display:flex;align-items:center;justify-content:space-between;gap:8px;}",
    ".lacw-header h3{margin:0;font-size:15px;font-weight:700;}",
    ".lacw-header button{background:transparent;border:0;color:#fff;cursor:pointer;font-size:13px;}",
    ".lacw-messages{flex:1;overflow:auto;padding:16px;background:#f8fafc;display:flex;flex-direction:column;gap:10px;}",
    ".lacw-msg{max-width:85%;padding:10px 12px;border-radius:14px;font-size:14px;line-height:1.45;white-space:pre-wrap;}",
    ".lacw-msg.user{margin-left:auto;background:var(--lacw-color,#2563eb);color:#fff;}",
    ".lacw-msg.bot{margin-right:auto;background:#fff;border:1px solid #e2e8f0;color:#0f172a;}",
    ".lacw-sources{font-size:12px;color:#475569;margin-top:6px;}",
    ".lacw-form{display:flex;gap:8px;padding:12px;border-top:1px solid #e2e8f0;background:#fff;}",
    ".lacw-form textarea{flex:1;resize:none;border:1px solid #cbd5e1;border-radius:12px;padding:10px;font-size:14px;min-height:44px;max-height:96px;}",
    ".lacw-form button{border:0;border-radius:12px;color:#fff;padding:0 14px;cursor:pointer;font-weight:600;}",
    ".lacw-error{color:#b91c1c;font-size:13px;padding:0 16px 8px;}",
    ".lacw-hidden{display:none;}"
  ].join("");
  document.head.appendChild(style);

  var root = document.createElement("div");
  root.className = "lacw-root";
  document.body.appendChild(root);

  function applyPosition() {
    root.style.right = "";
    root.style.left = "";
    if (state.config.position === "left") {
      root.style.left = "20px";
    } else {
      root.style.right = "20px";
    }
  }

  function render() {
    applyPosition();
    root.style.setProperty("--lacw-color", state.config.primaryColor);
    var messages = state.messages
      .map(function (msg) {
        var sources = "";
        if (msg.sources && msg.sources.length) {
          sources =
            '<div class="lacw-sources">Forrás:<br>' +
            msg.sources
              .map(function (src) {
                var extra = src.page_number ? " – " + src.page_number + ". oldal" : "";
                if (src.sheet_name) extra += " – " + src.sheet_name;
                return "- " + escapeHtml(src.document_name) + extra;
              })
              .join("<br>") +
            "</div>";
        }
        return (
          '<div class="lacw-msg ' +
          msg.role +
          '">' +
          escapeHtml(msg.text) +
          sources +
          "</div>"
        );
      })
      .join("");
    root.innerHTML =
      (state.open
        ? '<div class="lacw-panel">' +
          '<div class="lacw-header" style="background:' +
          state.config.primaryColor +
          '"><div><h3>' +
          escapeHtml(state.config.title) +
          "</h3></div><div>" +
          '<button type="button" data-act="reset">Új beszélgetés</button> ' +
          '<button type="button" data-act="close">Bezár</button></div></div>' +
          '<div class="lacw-messages" data-role="messages">' +
          messages +
          (state.loading ? '<div class="lacw-msg bot">Válasz írása…</div>' : "") +
          "</div>" +
          (state.error ? '<div class="lacw-error">' + escapeHtml(state.error) + "</div>" : "") +
          '<form class="lacw-form"><textarea name="message" placeholder="Írjon üzenetet…" rows="1"></textarea>' +
          '<button type="submit" style="background:' +
          state.config.primaryColor +
          '">Küldés</button></form></div>'
        : "") +
      '<button class="lacw-launcher" type="button" data-act="toggle" style="background:' +
      state.config.primaryColor +
      '" aria-label="Chat">' +
      (state.open ? "×" : "💬") +
      "</button>";

    var box = root.querySelector('[data-role="messages"]');
    if (box) box.scrollTop = box.scrollHeight;

    var form = root.querySelector("form");
    if (form) {
      form.addEventListener("submit", onSubmit);
      var area = form.querySelector("textarea");
      area.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          form.requestSubmit();
        }
      });
    }
    root.querySelectorAll("[data-act]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var act = btn.getAttribute("data-act");
        if (act === "toggle" || act === "close") {
          state.open = act === "toggle" ? !state.open : false;
          render();
        }
        if (act === "reset") {
          state.sessionId = null;
          state.messages = [
            { role: "bot", text: state.config.welcomeMessage, sources: [] }
          ];
          state.error = "";
          render();
        }
      });
    });
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function onSubmit(event) {
    event.preventDefault();
    var textarea = event.target.querySelector("textarea");
    var text = (textarea.value || "").trim();
    if (!text || state.loading) return;
    state.messages.push({ role: "user", text: text, sources: [] });
    state.loading = true;
    state.error = "";
    render();
    sendMessage(text);
  }

  function sendMessage(text) {
    fetch(apiBase.replace(/\/$/, "") + "/api/chat/" + encodeURIComponent(agentId), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + apiKey
      },
      body: JSON.stringify({
        message: text,
        session_id: state.sessionId,
        stream: true,
        include_sources: state.config.showSources !== false
      })
    })
      .then(function (response) {
        if (!response.ok) {
          return response.json().then(function (body) {
            throw new Error(body.detail || "A chat kérés sikertelen.");
          });
        }
        var contentType = response.headers.get("content-type") || "";
        if (contentType.indexOf("text/event-stream") !== -1) {
          return readStream(response);
        }
        return response.json().then(function (body) {
          finish(body.message, body.sources || [], body.session_id);
        });
      })
      .catch(function (err) {
        state.loading = false;
        state.error = err.message || "Hálózati hiba.";
        render();
      });
  }

  function readStream(response) {
    var bot = { role: "bot", text: "", sources: [] };
    state.messages.push(bot);
    var reader = response.body.getReader();
    var decoder = new TextDecoder();
    var buffer = "";
    function pump() {
      return reader.read().then(function (result) {
        buffer += decoder.decode(result.value || new Uint8Array(), { stream: !result.done });
        var parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        parts.forEach(function (block) {
          var event = "message";
          var dataLine = "";
          block.split("\n").forEach(function (line) {
            if (line.indexOf("event:") === 0) event = line.slice(6).trim();
            if (line.indexOf("data:") === 0) dataLine += line.slice(5).trim();
          });
          if (!dataLine) return;
          var payload = JSON.parse(dataLine);
          if (event === "token") {
            bot.text += payload.text || "";
            renderKeeping(bot);
          } else if (event === "sources") {
            bot.sources = payload;
          } else if (event === "done") {
            state.sessionId = payload.session_id;
            bot.text = payload.message || bot.text;
          }
        });
        if (result.done) {
          state.loading = false;
          render();
          return;
        }
        return pump();
      });
    }
    return pump();
  }

  function renderKeeping(bot) {
    state.loading = true;
    render();
  }

  function finish(message, sources, sessionId) {
    state.sessionId = sessionId;
    state.messages.push({ role: "bot", text: message, sources: sources });
    state.loading = false;
    render();
  }

  function loadConfig() {
    if (!agentId) {
      state.error = "Hiányzó data-agent attribútum.";
      render();
      return;
    }
    fetch(apiBase.replace(/\/$/, "") + "/api/widget/" + encodeURIComponent(agentId) + "/config")
      .then(function (response) {
        if (!response.ok) throw new Error("A widget konfigurációja nem tölthető.");
        return response.json();
      })
      .then(function (cfg) {
        state.config.primaryColor = userConfig.primaryColor || cfg.primary_color || state.config.primaryColor;
        state.config.title = userConfig.title || cfg.title || cfg.agent_name;
        state.config.position = userConfig.position || cfg.position || "right";
        state.config.welcomeMessage =
          userConfig.welcomeMessage || cfg.welcome_message || state.config.welcomeMessage;
        if (typeof userConfig.showSources === "boolean") {
          state.config.showSources = userConfig.showSources;
        } else if (typeof cfg.show_sources === "boolean") {
          state.config.showSources = cfg.show_sources;
        }
        state.messages = [{ role: "bot", text: state.config.welcomeMessage, sources: [] }];
        render();
      })
      .catch(function () {
        state.messages = [{ role: "bot", text: state.config.welcomeMessage, sources: [] }];
        render();
      });
  }

  loadConfig();
})();
